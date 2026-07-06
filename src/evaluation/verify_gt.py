"""
Verify GT eval set v2 — kiểm tra test_set_v2.json theo docs/GT_AUTHORING_GUIDE.md.

Khác validate_test_set.py (dev set cũ, chỉ schema): script này verify CITATION
NGƯỢC CORPUS — mỗi (van_ban, dieu, khoan, diem) trong ground_truth_citations phải
resolve về một heading THẬT trong data/raw/*.md (tái dùng parser.parse_file).
Đây là hiện thực hóa Bước 4 của guide: "GT sai còn tệ hơn GT ít".

Usage:
    python -m src.evaluation.verify_gt                      # mặc định test_set_v2.json
    python -m src.evaluation.verify_gt path/to/file.json
    python -m src.evaluation.verify_gt --final              # enforce đủ phân bổ 150
"""
import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

from src.ingestion.parser import parse_file

VALID_THEMES = {"dat-dai", "ho-tich", "nuoi-con-nuoi"}
VALID_JURISDICTIONS = {"toan-quoc", "tp-hcm", "dong-nai"}
VALID_GAPS = {"gap1", "gap2", "gap3", "gap4", "negative"}
VALID_DIFFICULTY = {"easy", "medium", "hard"}
VALID_SUBTYPES = {"obvious", "trap", "underspecified", "composite", "register", None}
# subtype archetype:<slug> hợp lệ cho gap1
_ARCHETYPE_RE = re.compile(r"^archetype:[a-z0-9\-]+$")

ID_RE = re.compile(r"^V\d{3}$")

REQUIRED_FIELDS = {
    "id", "question", "theme", "jurisdiction", "gap_type", "subtype",
    "difficulty", "ground_truth_answer", "ground_truth_citations",
}

# File trong data/raw/ không phải văn bản QPPL (không parse)
_NON_NORM_FILES = {"mapping_table.md", "crossref_decisions.md", "review_log.md"}

# Phân bổ CHỐT theo guide §1 (enforce khi --final).
# Lưu ý: gap2=26 (dư 1 so kế hoạch — cặp đảo cận-nghèo hộ tịch đáng giữ),
# bù bằng register=19 để tổng đúng 150.
_TARGET = {
    "gap1": 25, "gap2": 26, "gap3": 25, "gap4": 25,
    "negative/obvious": 8, "negative/trap": 6,
    "underspecified": 8, "composite": 8, "register": 19,
    "total": 150,
}

_DIEU_RE = re.compile(r"^Điều\s+(\w+)")
_KHOAN_RE = re.compile(r"^Khoản\s+(\w+)")
_DIEM_RE = re.compile(r"^Điểm\s+(\w+)")


def _norm_text(s: str) -> str:
    """Chuẩn hóa để so khớp Phụ lục: NFC, lowercase, gộp khoảng trắng."""
    return " ".join(unicodedata.normalize("NFC", s).lower().split())


def build_corpus_index(raw_dir: Path) -> dict:
    """Parse toàn bộ data/raw/*.md → index vị trí hợp lệ theo norm.

    Returns:
        {norm_id: {"dieu": set, "dieu_khoan": set, "dieu_khoan_diem": set,
                   "phu_luc": set các label chuẩn hóa}}
    """
    index: dict = {}
    for f in sorted(raw_dir.glob("*.md")):
        if f.name in _NON_NORM_FILES:
            continue
        parsed = parse_file(str(f))
        norm_id = parsed["metadata"]["id"]
        entry = index.setdefault(norm_id, {
            "dieu": set(), "dieu_khoan": set(),
            "dieu_khoan_diem": set(), "phu_luc": set(),
        })
        entry.setdefault("phu_luc_khoan", set())
        for node in parsed["nodes"]:
            # context_path = [norm_id, "Điều X. ..."|"Phụ lục ...", "Khoản Y.", ...]
            dieu = khoan = diem = pl = None
            for seg in node["context_path"][1:]:
                if seg.startswith("Phụ lục"):
                    pl = _norm_text(seg)
                    entry["phu_luc"].add(pl)
                    continue
                m = _DIEU_RE.match(seg)
                if m:
                    dieu = m.group(1)
                    continue
                m = _KHOAN_RE.match(seg)
                if m:
                    khoan = m.group(1)
                    if pl:
                        entry["phu_luc_khoan"].add((pl, khoan))
                    continue
                m = _DIEM_RE.match(seg)
                if m:
                    diem = m.group(1)
            if dieu:
                entry["dieu"].add(dieu)
                if khoan:
                    entry["dieu_khoan"].add((dieu, khoan))
                    if diem:
                        entry["dieu_khoan_diem"].add((dieu, khoan, diem))
    return index


def verify_citation(cit: dict, index: dict) -> str | None:
    """Kiểm 1 citation resolve trong corpus. Trả về message lỗi hoặc None nếu OK."""
    vb = cit.get("van_ban")
    if vb not in index:
        return f"van_ban '{vb}' không có trong corpus"
    entry = index[vb]
    dieu = str(cit.get("dieu") or "").strip()
    if not dieu:
        return "citation thiếu 'dieu'"

    # Citation Phụ lục (format harness: loai="phu_luc", dieu=ký hiệu "1B"|"I"|"_default")
    if cit.get("loai") == "phu_luc" or dieu.lower().startswith("phụ lục"):
        if not entry["phu_luc"]:
            return f"{vb} không có Phụ lục nào"
        if dieu == "_default":
            matched = set(entry["phu_luc"])  # norm chỉ có phụ lục không ký hiệu
        else:
            target = _norm_text(dieu if dieu.lower().startswith("phụ lục")
                                else f"phụ lục {dieu}")
            matched = {pl for pl in entry["phu_luc"]
                       if pl.startswith(target) or target.startswith(pl)}
            if not matched:
                return f"Phụ lục '{dieu}' không khớp Phụ lục nào trong {vb}"
        khoan = cit.get("khoan")
        if khoan is not None:
            khoan = str(khoan).strip()
            if not any((pl, khoan) in entry["phu_luc_khoan"] for pl in matched):
                return f"Phụ lục '{dieu}' Khoản {khoan} không tồn tại trong {vb}"
        return None

    if dieu not in entry["dieu"]:
        return f"Điều {dieu} không tồn tại trong {vb}"
    khoan = cit.get("khoan")
    if khoan is not None:
        khoan = str(khoan).strip()
        if (dieu, khoan) not in entry["dieu_khoan"]:
            return f"Điều {dieu} Khoản {khoan} không tồn tại trong {vb}"
        diem = cit.get("diem")
        if diem is not None:
            diem = str(diem).strip()
            if (dieu, khoan, diem) not in entry["dieu_khoan_diem"]:
                return f"Điều {dieu} K{khoan} Điểm {diem} không tồn tại trong {vb}"
    return None


def validate_item(item: dict, idx: int, index: dict, all_ids: set) -> list[str]:
    """Kiểm schema + logic subtype + citation cho 1 câu."""
    errors: list[str] = []
    pre = f"[{idx}] id={item.get('id', '?')}"

    missing = REQUIRED_FIELDS - set(item.keys())
    if missing:
        return [f"{pre}: thiếu field {sorted(missing)}"]

    if not ID_RE.match(item["id"]):
        errors.append(f"{pre}: id phải dạng V###")
    if item["gap_type"] not in VALID_GAPS:
        errors.append(f"{pre}: gap_type '{item['gap_type']}' không hợp lệ")
    if item["difficulty"] not in VALID_DIFFICULTY:
        errors.append(f"{pre}: difficulty '{item['difficulty']}' không hợp lệ")

    sub = item.get("subtype")
    if sub is not None and sub not in VALID_SUBTYPES and not _ARCHETYPE_RE.match(sub):
        errors.append(f"{pre}: subtype '{sub}' không hợp lệ")

    theme, juris = item["theme"], item["jurisdiction"]
    is_negative = item["gap_type"] == "negative"
    if theme is not None and theme not in VALID_THEMES:
        errors.append(f"{pre}: theme '{theme}' không hợp lệ")
    if theme is None and not is_negative:
        errors.append(f"{pre}: theme=null chỉ cho negative-obvious")
    if juris is not None and juris not in VALID_JURISDICTIONS:
        errors.append(f"{pre}: jurisdiction '{juris}' không hợp lệ")
    if juris is None and sub not in ("underspecified", "obvious") and not is_negative:
        errors.append(f"{pre}: jurisdiction=null chỉ cho underspecified/negative")

    cits = item["ground_truth_citations"]
    if is_negative:
        if sub not in ("obvious", "trap"):
            errors.append(f"{pre}: negative phải có subtype obvious|trap")
        if cits:
            errors.append(f"{pre}: negative phải có citations rỗng")
    else:
        if not cits:
            errors.append(f"{pre}: câu non-negative phải có ≥1 citation")
        for c in cits:
            err = verify_citation(c, index)
            if err:
                errors.append(f"{pre}: CITATION LỖI — {err}")

    if sub == "underspecified" and juris is not None:
        errors.append(f"{pre}: underspecified phải có jurisdiction=null")
    if sub == "register":
        pid = item.get("pair_id")
        if not pid or pid not in all_ids:
            errors.append(f"{pre}: register cần pair_id trỏ về câu gốc tồn tại")
    # gap1 thuần phải gắn archetype; các subtype hành vi (composite/register/
    # underspecified) được phép lấy gap1 làm gap chính mà không cần archetype
    if (item["gap_type"] == "gap1"
            and sub not in ("composite", "register", "underspecified")
            and not (sub and str(sub).startswith("archetype:"))):
        errors.append(f"{pre}: gap1 thuần phải có subtype 'archetype:<slug>'")

    return errors


def check_register_pairs(items: list[dict]) -> list[str]:
    """Câu register phải GIỮ NGUYÊN citations của câu gốc (guide §7)."""
    errors = []
    by_id = {it["id"]: it for it in items}
    for it in items:
        if it.get("subtype") == "register":
            pair = by_id.get(it.get("pair_id"))
            if pair and it["ground_truth_citations"] != pair["ground_truth_citations"]:
                errors.append(
                    f"id={it['id']}: citations KHÁC câu gốc {it['pair_id']} "
                    "(register phải giữ nguyên citations)"
                )
    return errors


def distribution_report(items: list[dict], final: bool) -> tuple[list[str], list[str]]:
    """Đếm theo nhóm guide §1. Trả về (báo cáo, lỗi nếu --final)."""
    def bucket(it):
        sub = it.get("subtype") or ""
        if it["gap_type"] == "negative":
            return f"negative/{sub}"
        if sub in ("underspecified", "composite", "register"):
            return sub
        return it["gap_type"]

    counts = Counter(bucket(it) for it in items)
    counts["total"] = len(items)
    lines = ["", "── Phân bổ hiện tại vs mục tiêu ──"]
    errors = []
    for key, target in _TARGET.items():
        got = counts.get(key, 0)
        mark = "✅" if got >= target else "…"
        lines.append(f"  {key:<20} {got:>3} / {target}  {mark}")
        if final and got != target:
            errors.append(f"--final: nhóm '{key}' có {got}, cần {target}")
    for extra in ("theme", "difficulty"):
        c = Counter(str(it.get(extra)) for it in items)
        lines.append(f"  ({extra}: {dict(sorted(c.items()))})")
    return lines, errors


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify GT eval set v2 ngược corpus")
    ap.add_argument("path", nargs="?", default="data/evaluation/test_set_v2.json")
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--final", action="store_true",
                    help="Enforce đủ phân bổ 150 câu (chạy trước khi freeze)")
    args = ap.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"❌ Không tìm thấy {path}")
        return 1
    items = json.loads(path.read_text(encoding="utf-8"))

    print(f"🔍 Verify {len(items)} câu trong {path} ngược corpus {args.raw_dir}/ ...")
    index = build_corpus_index(Path(args.raw_dir))
    print(f"   Corpus index: {len(index)} norm")

    errors: list[str] = []
    ids = [it.get("id") for it in items]
    all_ids = set(ids)
    dup = [i for i, n in Counter(ids).items() if n > 1]
    if dup:
        errors.append(f"id trùng lặp: {dup}")

    for i, item in enumerate(items):
        errors.extend(validate_item(item, i, index, all_ids))
    errors.extend(check_register_pairs(items))

    report, dist_errors = distribution_report(items, args.final)
    errors.extend(dist_errors)
    print("\n".join(report))

    if errors:
        print(f"\n❌ {len(errors)} LỖI:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"\n✅ PASS — {len(items)} câu hợp lệ, mọi citation resolve trong corpus.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
