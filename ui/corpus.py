"""Corpus reader cho UI demo — Task 1 (`ui/docs/UI_DEMO_SPEC.md` mục 6).

Đọc toàn bộ `data/raw/*.md` MỘT LẦN lúc startup, cache trong bộ nhớ, phục vụ:
  (a) dựng đồ thị Norm cho bước 4 (Stage 2 traversal) mà KHÔNG cần Neo4j —
      nhờ vậy máy A (Neo4j rỗng) vẫn vẽ được đồ thị ở chế độ `replay`;
  (b) tra nguyên văn Điều/Khoản/Điểm khi người xem bấm vào một citation.

Nguồn cạnh đồ thị khớp với `src/ingestion/graph_builder.py`:
  - `implements`        → cạnh [:IMPLEMENTS] (norm con → norm cha)
  - `amended_by_norms`  → cạnh [:AMENDS]     (norm sửa đổi → norm bị sửa)
Cả hai trường có thể là string | list | null (D-23) → luôn chuẩn hóa về list.

Ghi chú về YAML: spec khuyến nghị tránh thư viện nếu được, nhưng frontmatter
thật có list nhiều dòng (`amended_by_norms`) và chuỗi `summary` dài chứa cả
dấu ':' — tách tay dễ sai. `pyyaml` đã có sẵn trong `requirements.txt` và
chính `src/ingestion/parser.py` cũng dùng `yaml.safe_load`, nên dùng lại cho
nhất quán với đường đọc dữ liệu của hệ thống.
"""
from __future__ import annotations

import logging
import re
import threading
from pathlib import Path
from typing import Any, TypedDict

import yaml

logger = logging.getLogger(__name__)

# Ba file này nằm trong data/raw/ nhưng KHÔNG phải văn bản QPPL
# (đồng bộ với `_NON_NORM_FILES` của src/ingestion/graph_builder.py).
_NON_NORM_FILES = {"crossref_decisions.md", "mapping_table.md", "review_log.md"}

DEFAULT_RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

# Sentinel valid_to khi văn bản còn hiệu lực (đồng bộ graph_builder/context_assembler).
VALID_TO_SENTINEL = "9999-12-31"

# Heading trong thân bài: `## Điều N.` / `## Phụ lục ...` / `### Khoản N.` /
# `#### Điểm a.` / `##### Tiết N.`
_HEADING_RE = re.compile(r"^(#{2,5})\s+(.*?)\s*$")
_DIEU_RE = re.compile(r"^Điều\s+([^.\s]+)\.?", re.IGNORECASE)
_PHU_LUC_RE = re.compile(r"^Phụ\s*lục\s*([^.]*)", re.IGNORECASE)
# Giữ TRỌN đường dẫn sau "Phụ lục" (VD "I - Phần III - Mục I"), không cắt ở
# dấu gạch: một văn bản có thể có nhiều mục cùng số Phụ lục I, cắt ngắn thì
# ba mục khác nhau đều thành "I" và tra cứu luôn rơi vào mục đầu tiên.
_KHOAN_RE = re.compile(r"^Khoản\s+([^.\s]+)\.?", re.IGNORECASE)
_DIEM_RE = re.compile(r"^Điểm\s+([^.\s]+)\.?", re.IGNORECASE)
_TIET_RE = re.compile(r"^Tiết\s+([^.\s]+)\.?", re.IGNORECASE)

# Sentinel cho Phụ lục không đánh số (đồng bộ `dieu='_default'` của parse_citations).
PHU_LUC_DEFAULT = "_default"


# ---------------------------------------------------------------------------
# Kiểu dữ liệu
# ---------------------------------------------------------------------------

class NormMeta(TypedDict):
    """Metadata một văn bản (frontmatter đã chuẩn hóa) + cây nội dung."""
    id: str
    title: str
    so_hieu: str | None
    tier: int | None
    theme: str | None
    jurisdiction: str | None
    implements: list[str]
    amended_by_norms: list[str]
    valid_from: str | None
    valid_to: str | None
    source_url: str | None
    source_vbhn: str | None
    summary: str | None
    file: str
    muc: list[dict]      # cây nội dung: Điều/Phụ lục → Khoản → Điểm → Tiết


# ---------------------------------------------------------------------------
# Helper chuẩn hóa frontmatter
# ---------------------------------------------------------------------------

def _as_list(value: Any) -> list[str]:
    """Chuẩn hóa string | list | None → list[str] (D-23: implements đa-cha)."""
    if value is None:
        return []
    if isinstance(value, str):
        value = value.strip()
        return [value] if value else []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if isinstance(v, (str, int)) and str(v).strip()]
    return []


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _norm_key(text: str) -> str:
    """Khóa so khớp: bỏ khoảng trắng thừa + hạ chữ thường."""
    return " ".join(str(text).split()).lower()


# ---------------------------------------------------------------------------
# Parse thân bài → cây Điều/Khoản/Điểm/Tiết
# ---------------------------------------------------------------------------

def _new_node(cap: str, so: str | None, heading: str) -> dict:
    return {"cap": cap, "so": so, "heading": heading, "text": "", "con": []}


def _classify_heading(level: int, text: str) -> tuple[str, str | None]:
    """Trả (cap, so) cho một heading thân bài.

    cap ∈ 'dieu' | 'phu_luc' | 'khoan' | 'diem' | 'tiet' | 'khac'.
    """
    if level == 2:
        m = _DIEU_RE.match(text)
        if m:
            return "dieu", m.group(1)
        m = _PHU_LUC_RE.match(text)
        if m:
            return "phu_luc", (m.group(1) or PHU_LUC_DEFAULT)
        return "khac", None
    if level == 3:
        m = _KHOAN_RE.match(text)
        return ("khoan", m.group(1)) if m else ("khac", None)
    if level == 4:
        m = _DIEM_RE.match(text)
        return ("diem", m.group(1)) if m else ("khac", None)
    m = _TIET_RE.match(text)
    return ("tiet", m.group(1)) if m else ("khac", None)


def parse_body(body: str) -> list[dict]:
    """Parse thân bài markdown → cây node (Điều/Phụ lục ở cấp cao nhất).

    Dung thứ với heading lạ: gắn vào cây với cap='khac' thay vì raise —
    UI demo ưu tiên không sập giữa buổi bảo vệ.
    """
    roots: list[dict] = []
    stack: list[tuple[int, dict]] = []   # (level, node)

    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            cap, so = _classify_heading(level, text)
            node = _new_node(cap, so, text)
            while stack and stack[-1][0] >= level:
                stack.pop()
            if stack:
                stack[-1][1]["con"].append(node)
            else:
                roots.append(node)
            stack.append((level, node))
        else:
            if not stack:
                continue  # nội dung trước heading đầu tiên — bỏ qua
            node = stack[-1][1]
            node["text"] = f"{node['text']}\n{line}" if node["text"] else line

    return roots


def render_node(node: dict, *, kem_heading: bool = True) -> str:
    """Ghép heading + nội dung + toàn bộ cấp con thành nguyên văn hiển thị."""
    parts: list[str] = []
    if kem_heading and node.get("heading"):
        parts.append(node["heading"])
    if node.get("text"):
        parts.append(node["text"])
    for child in node.get("con", []):
        parts.append(render_node(child))
    return "\n".join(p for p in parts if p).strip()


# ---------------------------------------------------------------------------
# Đọc file .md
# ---------------------------------------------------------------------------

def _split_frontmatter(content: str) -> tuple[dict, str]:
    """Tách frontmatter YAML và thân bài. Trả ({}, content) nếu không có."""
    parts = content.split("---", 2)
    if len(parts) < 3 or parts[0].strip():
        return {}, content
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as e:
        logger.warning(f"Frontmatter YAML lỗi — bỏ qua metadata: {e}")
        return {}, parts[2]
    if not isinstance(meta, dict):
        return {}, parts[2]
    return meta, parts[2]


def parse_norm_file(filepath: Path) -> NormMeta | None:
    """Đọc một file văn bản → NormMeta. Trả None nếu file không có `id`."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except OSError as e:
        logger.warning(f"Không đọc được {filepath.name}: {e}")
        return None

    meta, body = _split_frontmatter(content)
    norm_id = _as_str(meta.get("id"))
    if not norm_id:
        logger.warning(f"{filepath.name}: frontmatter thiếu 'id' — bỏ qua.")
        return None

    # `graph_builder.py` Pass 3 chỉ tạo cạnh AMENDS khi `amended_by_norms` là
    # LIST (`isinstance(amended_by, list)`) — khác `implements` vốn nhận cả
    # string. Nếu frontmatter dùng scalar thì Neo4j KHÔNG có cạnh đó, còn UI
    # vẫn vẽ → đồ thị demo lệch với hệ thật. Cảnh báo để phát hiện sớm.
    if isinstance(meta.get("amended_by_norms"), str) and meta["amended_by_norms"].strip():
        logger.warning(
            f"{filepath.name}: 'amended_by_norms' là string — graph_builder Pass 3 "
            "chỉ xử lý list nên Neo4j sẽ KHÔNG có cạnh AMENDS này. "
            "Sửa frontmatter thành list để đồ thị UI khớp với hệ thật."
        )

    return NormMeta(
        id=norm_id,
        title=_as_str(meta.get("title")) or norm_id,
        so_hieu=_as_str(meta.get("so_hieu")),
        tier=_as_int(meta.get("tier")),
        theme=_as_str(meta.get("theme")),
        jurisdiction=_as_str(meta.get("jurisdiction")),
        implements=_as_list(meta.get("implements")),
        amended_by_norms=_as_list(meta.get("amended_by_norms")),
        valid_from=_as_str(meta.get("valid_from")),
        valid_to=_as_str(meta.get("valid_to")),
        source_url=_as_str(meta.get("source_url")),
        source_vbhn=_as_str(meta.get("source_vbhn")),
        summary=_as_str(meta.get("summary")),
        file=filepath.name,
        muc=parse_body(body),
    )


# ---------------------------------------------------------------------------
# Cache + API công khai
# ---------------------------------------------------------------------------

_CACHE: dict[str, NormMeta] | None = None
_CACHE_DIR: Path | None = None
_LOCK = threading.Lock()


def load_corpus(
    raw_dir: Path | str | None = None,
    *,
    refresh: bool = False,
) -> dict[str, NormMeta]:
    """Đọc toàn bộ `data/raw/*.md` (bỏ 3 file không phải văn bản), cache in-memory.

    Args:
        raw_dir: Thư mục chứa .md (mặc định `data/raw/` của repo).
        refresh: True → đọc lại từ đĩa kể cả khi đã cache.

    Returns:
        dict[norm_id, NormMeta] — thứ tự theo tên file.
    """
    global _CACHE, _CACHE_DIR
    directory = Path(raw_dir) if raw_dir else DEFAULT_RAW_DIR

    with _LOCK:
        if _CACHE is not None and not refresh and _CACHE_DIR == directory:
            return _CACHE

        corpus: dict[str, NormMeta] = {}
        if not directory.is_dir():
            logger.warning(f"Không tìm thấy thư mục corpus: {directory}")
        else:
            for path in sorted(directory.glob("*.md")):
                if path.name in _NON_NORM_FILES:
                    continue
                norm = parse_norm_file(path)
                if norm is None:
                    continue
                if norm["id"] in corpus:
                    logger.warning(
                        f"Trùng id '{norm['id']}' giữa {corpus[norm['id']]['file']} "
                        f"và {path.name} — giữ bản đầu tiên."
                    )
                    continue
                corpus[norm["id"]] = norm

        _CACHE, _CACHE_DIR = corpus, directory
        logger.info(f"load_corpus: {len(corpus)} văn bản từ {directory}")
        return corpus


def norm_graph(raw_dir: Path | str | None = None) -> dict[str, list[dict]]:
    """Dựng đồ thị Norm (nodes + edges) từ frontmatter — không cần Neo4j.

    Chỉ giữ cạnh mà CẢ HAI đầu đều có trong corpus — giống `graph_builder.py`
    (Cypher `MATCH ... MATCH ... MERGE` nên tham chiếu tới văn bản ngoài corpus
    không tạo cạnh nào trong Neo4j thật). Các tham chiếu treo được log ở mức
    debug và đếm trong `bo_qua`.

    Returns:
        {"nodes": [...], "edges": [...], "bo_qua": [...]}
        - node: id, title, so_hieu, tier, jurisdiction, theme, valid_from, valid_to
        - edge: source, target, type ∈ {"IMPLEMENTS", "AMENDS"}
    """
    corpus = load_corpus(raw_dir)

    nodes = [
        {
            "id": n["id"],
            "title": n["title"],
            "so_hieu": n["so_hieu"],
            "tier": n["tier"],
            "jurisdiction": n["jurisdiction"],
            "theme": n["theme"],
            "valid_from": n["valid_from"],
            "valid_to": n["valid_to"],
        }
        for n in corpus.values()
    ]

    edges: list[dict] = []
    bo_qua: list[dict] = []
    seen: set[tuple[str, str, str]] = set()

    def _add(source: str, target: str, loai: str) -> None:
        if source not in corpus or target not in corpus:
            bo_qua.append({"source": source, "target": target, "type": loai})
            return
        key = (source, target, loai)
        if key in seen:
            return
        seen.add(key)
        edges.append({"source": source, "target": target, "type": loai})

    for norm in corpus.values():
        # IMPLEMENTS: văn bản này hướng dẫn thi hành văn bản cha.
        for parent in norm["implements"]:
            _add(norm["id"], parent, "IMPLEMENTS")
        # AMENDS: văn bản sửa đổi → văn bản này (nghi-quyet-254 AMENDS luat-dat-dai-2024).
        for amender in norm["amended_by_norms"]:
            _add(amender, norm["id"], "AMENDS")

    if bo_qua:
        logger.debug(
            f"norm_graph: bỏ {len(bo_qua)} cạnh trỏ tới văn bản ngoài corpus."
        )
    return {"nodes": nodes, "edges": edges, "bo_qua": bo_qua}


# ---------------------------------------------------------------------------
# Tra nguyên văn
# ---------------------------------------------------------------------------

def _clean_so(value: str | None) -> str | None:
    """Chuẩn hóa số hiệu vị trí: bỏ tiền tố ('Điều 3' → '3'), bỏ dấu chấm cuối."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    for pattern in (_DIEU_RE, _KHOAN_RE, _DIEM_RE, _TIET_RE):
        m = pattern.match(text)
        if m:
            return m.group(1).strip().rstrip(".")
    m = _PHU_LUC_RE.match(text)
    if m:
        return (m.group(1) or PHU_LUC_DEFAULT).strip().rstrip(".")
    return text.rstrip(".")


def _find_child(node_list: list[dict], cap: str, so: str) -> dict | None:
    target = _norm_key(so)
    for node in node_list:
        if node.get("cap") == cap and node.get("so") and _norm_key(node["so"]) == target:
            return node
    return None


def _find_muc(norm: NormMeta, dieu: str) -> dict | None:
    """Tìm Điều (hoặc Phụ lục) theo số hiệu trong một văn bản."""
    so = _clean_so(dieu)
    if not so:
        return None
    node = _find_child(norm["muc"], "dieu", so)
    if node is not None:
        return node
    # Phụ lục: '_default' khớp Phụ lục đầu tiên không đánh số hoặc duy nhất.
    phu_luc = [n for n in norm["muc"] if n.get("cap") == "phu_luc"]
    if not phu_luc:
        return None
    if _norm_key(so) == PHU_LUC_DEFAULT:
        return phu_luc[0]
    node = _find_child(phu_luc, "phu_luc", so)
    if node is not None:
        return node
    # Hai chiều lệch nhau đều phải tra được:
    #  - trích dẫn ngắn hơn tiêu đề ("I" ↔ "I - Phần III - Mục I") → khớp phần đầu;
    #  - trích dẫn dài hơn vì kèm một mẩu tiêu đề ("I - Phần III - Mục I. Trình tự")
    #    → lấy mục có số hiệu DÀI NHẤT là phần đầu của trích dẫn, nếu lấy mục ngắn
    #    nhất thì "Mục VII" sẽ rơi nhầm vào "Mục VI".
    target = _norm_key(so)
    for n in phu_luc:
        if n.get("so") and _norm_key(n["so"]).startswith(target):
            return n
    ung_vien = [n for n in phu_luc
                if n.get("so") and target.startswith(_norm_key(n["so"]))]
    if ung_vien:
        return max(ung_vien, key=lambda n: len(_norm_key(n["so"])))
    return None


def get_component_text(
    norm_id: str,
    dieu: str,
    khoan: str | None = None,
    diem: str | None = None,
    raw_dir: Path | str | None = None,
) -> str | None:
    """Tra nguyên văn một vị trí pháp lý từ `data/raw/*.md`.

    Args:
        norm_id: slug văn bản, VD 'luat-dat-dai-2024'.
        dieu: số Điều ('116') hoặc ký hiệu Phụ lục ('I', '1A', '_default').
        khoan: số Khoản (None → trả nguyên Điều kèm mọi cấp con).
        diem: ký hiệu Điểm (None → trả nguyên Khoản kèm mọi cấp con).

    Returns:
        Nguyên văn (kèm heading các cấp) hoặc None nếu không tìm thấy.
    """
    corpus = load_corpus(raw_dir)
    norm = corpus.get(norm_id)
    if norm is None:
        return None

    node = _find_muc(norm, dieu)
    if node is None:
        return None

    if khoan is not None and str(khoan).strip():
        so_khoan = _clean_so(khoan)
        node = _find_child(node["con"], "khoan", so_khoan) if so_khoan else None
        if node is None:
            return None

    if diem is not None and str(diem).strip():
        so_diem = _clean_so(diem)
        node = _find_child(node["con"], "diem", so_diem) if so_diem else None
        if node is None:
            return None

    text = render_node(node)
    return text or None


# ---------------------------------------------------------------------------
# CLI kiểm tra nhanh (không cần DB): python -m ui.corpus
# ---------------------------------------------------------------------------

def _main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    corpus = load_corpus()
    graph = norm_graph()

    print(f"\n=== CORPUS: {len(corpus)} văn bản ===")
    for norm in corpus.values():
        print(
            f"  tier {norm['tier']} | {norm['theme'] or '?':<13} | "
            f"{norm['jurisdiction'] or '?':<10} | {len(norm['muc']):>3} mục | {norm['id']}"
        )

    print(f"\n=== ĐỒ THỊ: {len(graph['nodes'])} node, {len(graph['edges'])} cạnh ===")
    for loai in ("IMPLEMENTS", "AMENDS"):
        canh = [e for e in graph["edges"] if e["type"] == loai]
        print(f"\n[{loai}] {len(canh)} cạnh:")
        for e in canh:
            print(f"  {e['source']} → {e['target']}")

    if graph["bo_qua"]:
        print(
            f"\n(Bỏ {len(graph['bo_qua'])} cạnh trỏ tới văn bản ngoài corpus — "
            "giống Neo4j: MATCH không khớp thì không tạo cạnh.)"
        )


if __name__ == "__main__":
    _main()
