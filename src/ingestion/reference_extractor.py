"""
Reference Extractor — trích xuất dẫn chiếu cấp điều khoản từ data/raw/*.md.

Văn bản QPPL dẫn chiếu chéo liên tục ở cấp Điều/Khoản/Điểm:
    "... theo quy định tại khoản 2 Điều 143 của Luật này"
    "... trừ trường hợp quy định tại Điều 100 của Luật Đất đai"

Lược đồ hiện tại KHÔNG có quan hệ nào biểu diễn loại liên kết này: chỉ có
quan hệ giữa văn bản (IMPLEMENTS/AMENDS) và phân rã trong văn bản
(HAS_COMPONENT). Module này sinh ra cặp (Component nguồn → Component đích)
để dựng quan hệ [:REFERS_TO].

Bốn nhóm dẫn chiếu được nhận diện:
    tu_than      "Điều này", "khoản này", "điểm này"        → trỏ về chính nó
    noi_bo       "Điều 137 của Luật này", "Điều 137"        → cùng văn bản
    lien_van_ban "khoản 2 Điều 65 của Luật Đất đai"         → văn bản khác
    mo_ho        "theo pháp luật về đất đai"                 → KHÔNG giải chiếu được

Chạy trực tiếp để đo tỉ lệ giải chiếu (cổng chặn, $0, không cần database):
    python -m src.ingestion.reference_extractor
"""
from __future__ import annotations

import glob
import os
import re
from dataclasses import dataclass, field

import yaml

from src.ingestion.parser import generate_id

# File trong data/raw/ không phải văn bản QPPL (không có frontmatter `id:`)
_SKIP_FILES = {"crossref_decisions.md", "mapping_table.md", "review_log.md"}

# Loại văn bản có thể xuất hiện trong dẫn chiếu
_LOAI_VB = r"(?:Luật|Bộ luật|Nghị định|Thông tư|Nghị quyết|Quyết định|Pháp lệnh)"

# "của Luật này" / "của Nghị định này" → dẫn chiếu nội bộ, KHÔNG mơ hồ văn bản
_SCOPE_NOI_BO = re.compile(rf"^\s*(?:của\s+)?{_LOAI_VB}\s+này")

# "của Luật Đất đai" / "Nghị định số 71/2024/NĐ-CP" → dẫn chiếu liên văn bản.
# Bắt số hiệu nếu có (tra thẳng sang norm_id); nếu không thì gom tối đa 5 từ sau
# tên loại văn bản rồi đối chiếu với từ điển tên (_khop_ten_van_ban).
_SCOPE_LIEN_VB = re.compile(
    rf"^\s*(?:của\s+)?(?P<loai>{_LOAI_VB})\s*"
    rf"(?:số\s+(?P<so_hieu>[\dA-Za-zĐ/\-]+)"
    rf"|(?P<ten>(?:\s*[^\s,.;:()]+){{1,5}}))"
)

# Dẫn chiếu tự thân: "Điều này", "khoản này", "điểm này"
_REF_TU_THAN = re.compile(r"\b(?P<cap>[ĐđKkĐđ]iều|khoản|điểm)\s+này\b")

# Dẫn chiếu có địa chỉ cụ thể. Ba phần đều tùy chọn nhưng phải có ít nhất Điều
# hoặc khoản. Cho phép dạng liệt kê: "các khoản 1, 2 và 3 Điều 100".
# LƯU Ý: bắt buộc có CHỮ SỐ sau "điều" để không dính "các điều kiện sau đây".
_REF_DIA_CHI = re.compile(
    r"(?:các\s+)?"
    r"(?:điểm\s+(?P<diem>[a-zđ](?:\s*,\s*[a-zđ]|\s+và\s+[a-zđ])*)\s+)?"
    r"(?:khoản\s+(?P<khoan>\d+(?:\s*,\s*\d+|\s+và\s+\d+)*)\s*)?"
    r"(?:[Đđ]iều\s+(?P<dieu>\d+(?:\s*,\s*\d+|\s+và\s+\d+)*))?",
)

# Dạng đơn giản hơn dùng để quét: tìm mọi cụm bắt đầu bằng điểm/khoản/Điều + số
_REF_QUET = re.compile(
    r"(?:các\s+)?"
    r"(?:(?:điểm|khoản|[Đđ]iều)\s+[\da-zđ]+(?:\s*,\s*[\da-zđ]+)*(?:\s+và\s+[\da-zđ]+)?\s*){1,3}"
)

# HTML comment (annotation amended_by / original_v) — PHẢI loại bỏ trước khi
# trích dẫn chiếu: địa chỉ trong đó trỏ vào VĂN BẢN SỬA ĐỔI, không phải dẫn
# chiếu chéo của văn bản đang xét.
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)

_HEADING = re.compile(r"^(#{2,5})\s+(.+?)\s*$")
_DIEU_NUM = re.compile(r"^Điều\s+(\d+)\b")
_KHOAN_NUM = re.compile(r"^Khoản\s+(\d+)\b")
_DIEM_KY = re.compile(r"^Điểm\s+([a-zđ]+)\b")


@dataclass
class NormIndex:
    """Chỉ mục một văn bản: tra từ số Điều/Khoản/Điểm → context_path."""

    norm_id: str
    so_hieu: str
    title: str
    valid_from: str = ""
    # "137" → "Điều 137. Tên điều"
    dieu_heading: dict[str, str] = field(default_factory=dict)
    # ("137", "2", None) → context_path đầy đủ
    component_path: dict[tuple, list[str]] = field(default_factory=dict)


@dataclass
class Reference:
    """Một dẫn chiếu đã trích được."""

    nguon_norm: str
    nguon_path: list[str]          # context_path của Component chứa dẫn chiếu
    loai: str                      # tu_than | noi_bo | lien_van_ban | mo_ho
    raw: str                       # nguyên văn cụm dẫn chiếu
    dich_norm: str | None = None   # norm_id đích (None nếu chưa/không giải được)
    dich_path: list[str] | None = None
    ly_do_that_bai: str | None = None
    # Địa chỉ đích dạng có cấu trúc — để reference_builder giải chiếu lại theo
    # Component CÓ THẬT trong đồ thị (parser chỉ tạo Component cho heading có
    # nội dung chữ trực tiếp, nên "Điều 5" chỉ chứa Khoản con thì không có node).
    dich_dieu: str | None = None
    dich_khoan: str | None = None
    dich_diem: str | None = None


# ---------------------------------------------------------------------------
# Dựng chỉ mục
# ---------------------------------------------------------------------------

def build_norm_index(raw_dir: str) -> tuple[dict[str, NormIndex], dict[str, str]]:
    """Quét data/raw/*.md → chỉ mục từng văn bản + bảng tra số hiệu → norm_id."""
    indexes: dict[str, NormIndex] = {}
    so_hieu_map: dict[str, str] = {}

    for path in sorted(glob.glob(os.path.join(raw_dir, "*.md"))):
        if os.path.basename(path) in _SKIP_FILES:
            continue
        with open(path, encoding="utf-8") as f:
            content = f.read()
        meta = _read_frontmatter(content)
        if not meta or not meta.get("id"):
            continue

        norm_id = meta["id"]
        idx = NormIndex(
            norm_id=norm_id,
            so_hieu=str(meta.get("so_hieu") or ""),
            title=str(meta.get("title") or ""),
            valid_from=str(meta.get("valid_from") or ""),
        )

        # Duyệt heading để dựng context_path (giống parser.parse_file)
        stack: list[tuple[int, str]] = []
        for line in content.splitlines():
            m = _HEADING.match(line)
            if not m:
                continue
            level, text = len(m.group(1)), m.group(2)
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, text))

            path_parts = [norm_id] + [h[1] for h in stack]
            key = _path_to_key(stack)
            if key:
                idx.component_path[key] = path_parts
            dnum = _DIEU_NUM.match(text)
            if dnum:
                idx.dieu_heading[dnum.group(1)] = text

        indexes[norm_id] = idx
        if idx.so_hieu:
            so_hieu_map[_chuan_hoa_so_hieu(idx.so_hieu)] = norm_id

    return indexes, so_hieu_map


def _path_to_key(stack: list[tuple[int, str]]) -> tuple | None:
    """Chuyển stack heading → khoá (dieu, khoan, diem). None nếu không phải Điều."""
    dieu = khoan = diem = None
    for _lvl, text in stack:
        if (m := _DIEU_NUM.match(text)):
            dieu = m.group(1)
        elif (m := _KHOAN_NUM.match(text)):
            khoan = m.group(1)
        elif (m := _DIEM_KY.match(text)):
            diem = m.group(1)
    return (dieu, khoan, diem) if dieu else None


def _chuan_hoa_so_hieu(s: str) -> str:
    """Chuẩn hoá số hiệu để so khớp: bỏ khoảng trắng, viết hoa."""
    return re.sub(r"\s+", "", s).upper()


def _chuan_hoa_ten(s: str) -> str:
    """Chuẩn hoá tên văn bản: thường hoá, gộp khoảng trắng, bỏ năm ở cuối."""
    s = re.sub(r"\s+", " ", s.strip().lower())
    s = re.sub(r"\s*\(.*$", "", s)          # bỏ phần "(Luật số 31/2024/QH15)"
    s = re.sub(r"\s+(19|20)\d{2}\s*$", "", s)  # bỏ năm ở cuối: "luật đất đai 2013"
    return s.strip()


def build_name_lexicon(indexes: dict[str, NormIndex]) -> dict[str, list[str]]:
    """Từ điển tên văn bản → danh sách norm_id (có thể nhiều bản qua các năm).

    Cần thiết vì phần lớn dẫn chiếu liên văn bản chỉ ghi TÊN, không ghi số hiệu:
    "theo quy định tại Điều 100 của Luật Đất đai". Khi một tên ứng với nhiều
    bản (Luật Đất đai 2013 và 2024), việc chọn bản nào là bài toán THỜI GIAN —
    xem _chon_theo_thoi_diem.
    """
    lex: dict[str, list[str]] = {}
    for norm_id, idx in indexes.items():
        for ten in {_chuan_hoa_ten(idx.title), _chuan_hoa_ten(idx.norm_id.replace("-", " "))}:
            if len(ten) >= 6:  # bỏ tên quá ngắn, dễ khớp nhầm
                lex.setdefault(ten, []).append(norm_id)
    return lex


def _chon_theo_thoi_diem(
    ung_vien: list[str], indexes: dict[str, NormIndex], moc: str
) -> str | None:
    """Chọn bản có hiệu lực tại thời điểm văn bản dẫn chiếu được ban hành.

    Ví dụ: Quyết định 18/2016 nói "của Luật Đất đai" → Luật Đất đai 2013, còn
    Nghị định 49/2026 nói cùng cụm đó → Luật Đất đai 2024.
    """
    if len(ung_vien) == 1:
        return ung_vien[0]
    hop_le = [n for n in ung_vien if not moc or (indexes[n].valid_from or "") <= moc]
    if hop_le:
        return max(hop_le, key=lambda n: indexes[n].valid_from or "")
    return min(ung_vien, key=lambda n: indexes[n].valid_from or "")


def _khop_ten_van_ban(
    loai: str, duoi_ten: str, lexicon: dict[str, list[str]]
) -> list[str] | None:
    """Khớp cụm '<loại> <tên...>' với từ điển, ưu tiên tên DÀI NHẤT khớp được."""
    ung_vien = _chuan_hoa_ten(f"{loai} {duoi_ten}")
    khop = [k for k in lexicon if ung_vien.startswith(k)]
    if not khop:
        return None
    return lexicon[max(khop, key=len)]


def _read_frontmatter(content: str) -> dict | None:
    if not content.startswith("---"):
        return None
    end = content.find("\n---", 3)
    if end == -1:
        return None
    try:
        return yaml.safe_load(content[3:end])
    except yaml.YAMLError:
        return None


# ---------------------------------------------------------------------------
# Trích xuất dẫn chiếu
# ---------------------------------------------------------------------------

def _tach_danh_sach(s: str | None) -> list[str]:
    """'1, 2 và 3' → ['1','2','3']. None → []."""
    if not s:
        return []
    return [p for p in re.split(r"\s*,\s*|\s+và\s+", s.strip()) if p]


def extract_from_file(
    path: str,
    indexes: dict[str, NormIndex],
    so_hieu_map: dict[str, str],
    lexicon: dict[str, list[str]] | None = None,
) -> list[Reference]:
    """Trích mọi dẫn chiếu trong một file .md, đã giải chiếu nếu được."""
    with open(path, encoding="utf-8") as f:
        content = f.read()
    meta = _read_frontmatter(content)
    if not meta or not meta.get("id"):
        return []
    norm_id = meta["id"]
    if lexicon is None:
        lexicon = build_name_lexicon(indexes)

    refs: list[Reference] = []
    stack: list[tuple[int, str]] = []

    for line in content.splitlines():
        m = _HEADING.match(line)
        if m:
            level, text = len(m.group(1)), m.group(2)
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, text))
            continue  # KHÔNG trích dẫn chiếu từ chính heading

        # Bỏ HTML comment: địa chỉ trong annotation amended_by trỏ vào văn bản
        # SỬA ĐỔI, không phải dẫn chiếu chéo của văn bản đang xét.
        body = _HTML_COMMENT.sub(" ", line).strip()
        if not body:
            continue

        nguon_path = [norm_id] + [h[1] for h in stack]
        refs.extend(
            _extract_from_line(body, norm_id, nguon_path, indexes, so_hieu_map, lexicon)
        )

    return refs


def _extract_from_line(
    text: str,
    norm_id: str,
    nguon_path: list[str],
    indexes: dict[str, NormIndex],
    so_hieu_map: dict[str, str],
    lexicon: dict[str, list[str]],
) -> list[Reference]:
    out: list[Reference] = []

    # 1) Dẫn chiếu tự thân — trỏ về chính Component đang đứng, không tạo cạnh mới
    for m in _REF_TU_THAN.finditer(text):
        out.append(
            Reference(
                nguon_norm=norm_id, nguon_path=nguon_path,
                loai="tu_than", raw=m.group(0),
            )
        )

    # 2) Dẫn chiếu có địa chỉ
    for m in re.finditer(
        r"(?:các\s+)?"
        r"(?:điểm\s+(?P<diem>[a-zđ](?:\s*,\s*[a-zđ])*(?:\s+và\s+[a-zđ])?)\s+)?"
        r"(?:khoản\s+(?P<khoan>\d+(?:\s*,\s*\d+)*(?:\s+và\s+\d+)?)\s+)?"
        r"[Đđ]iều\s+(?P<dieu>\d+(?:\s*,\s*\d+)*(?:\s+và\s+\d+)?)",
        text,
    ):
        duoi = text[m.end():m.end() + 70]
        loai, dich_norm, ly_do = _xac_dinh_pham_vi(
            duoi, norm_id, so_hieu_map, indexes, lexicon
        )

        for dnum in _tach_danh_sach(m.group("dieu")):
            khoans = _tach_danh_sach(m.group("khoan")) or [None]
            diems = _tach_danh_sach(m.group("diem")) or [None]
            for kh in khoans:
                for di in diems:
                    ref = Reference(
                        nguon_norm=norm_id, nguon_path=nguon_path,
                        loai=loai, raw=m.group(0).strip(),
                        dich_norm=dich_norm, ly_do_that_bai=ly_do,
                        dich_dieu=dnum, dich_khoan=kh, dich_diem=di,
                    )
                    if dich_norm:
                        _giai_chieu(ref, dich_norm, dnum, kh, di, indexes)
                    out.append(ref)

    return out


def _xac_dinh_pham_vi(
    duoi: str,
    norm_id: str,
    so_hieu_map: dict[str, str],
    indexes: dict[str, NormIndex],
    lexicon: dict[str, list[str]],
) -> tuple[str, str | None, str | None]:
    """Xác định dẫn chiếu trỏ vào văn bản nào, dựa trên phần text NGAY SAU địa chỉ.

    Trả về (loai, dich_norm_id, ly_do_that_bai).
    """
    # "của Luật này" / "của Nghị định này" → chính văn bản đang xét
    if _SCOPE_NOI_BO.match(duoi):
        return "noi_bo", norm_id, None

    m = _SCOPE_LIEN_VB.match(duoi)
    if m:
        so_hieu = m.group("so_hieu")
        if so_hieu:
            dich = so_hieu_map.get(_chuan_hoa_so_hieu(so_hieu))
            if dich:
                return "lien_van_ban", dich, None
            return "lien_van_ban", None, f"ngoài kho: {so_hieu}"

        ten = (m.group("ten") or "").strip()
        ung_vien = _khop_ten_van_ban(m.group("loai"), ten, lexicon)
        if ung_vien:
            moc = (indexes[norm_id].valid_from if norm_id in indexes else "") or ""
            dich = _chon_theo_thoi_diem(ung_vien, indexes, moc)
            if dich:
                return "lien_van_ban", dich, None
        return "lien_van_ban", None, f"tên không có trong kho: {ten[:40]}"

    # Không có chỉ dấu văn bản nào → mặc định trong soạn thảo QPPL là cùng văn bản
    return "noi_bo", norm_id, None


def _giai_chieu(
    ref: Reference,
    dich_norm: str,
    dieu: str,
    khoan: str | None,
    diem: str | None,
    indexes: dict[str, NormIndex],
) -> None:
    """Tra Component đích trong chỉ mục; ghi dich_path hoặc lý do thất bại."""
    idx = indexes.get(dich_norm)
    if idx is None:
        ref.ly_do_that_bai = f"văn bản không có trong kho: {dich_norm}"
        return

    # Thử từ cụ thể nhất tới khái quát nhất: (điều,khoản,điểm) → (điều,khoản) → (điều)
    for key in ((dieu, khoan, diem), (dieu, khoan, None), (dieu, None, None)):
        if key in idx.component_path:
            ref.dich_path = idx.component_path[key]
            ref.dich_norm = dich_norm
            ref.ly_do_that_bai = None
            return

    ref.ly_do_that_bai = (
        f"không tìm thấy Điều {dieu}"
        + (f" Khoản {khoan}" if khoan else "")
        + f" trong {dich_norm}"
    )


def dich_component_id(ref: Reference) -> str | None:
    """ID Component đích (khớp với graph_builder) — None nếu chưa giải chiếu được."""
    return generate_id(ref.dich_path) if ref.dich_path else None


def nguon_component_id(ref: Reference) -> str:
    return generate_id(ref.nguon_path)


# ---------------------------------------------------------------------------
# Cổng chặn — đo tỉ lệ giải chiếu
# ---------------------------------------------------------------------------

def main() -> None:
    from collections import Counter

    raw_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw")
    raw_dir = os.path.normpath(raw_dir)

    indexes, so_hieu_map = build_norm_index(raw_dir)
    lexicon = build_name_lexicon(indexes)
    print(f"Chỉ mục: {len(indexes)} văn bản, {len(so_hieu_map)} số hiệu tra được")
    tong_comp = sum(len(i.component_path) for i in indexes.values())
    print(f"          {tong_comp} Component có địa chỉ Điều/Khoản/Điểm")
    print(f"          {len(lexicon)} tên văn bản trong từ điển\n")

    all_refs: list[Reference] = []
    for path in sorted(glob.glob(os.path.join(raw_dir, "*.md"))):
        if os.path.basename(path) in _SKIP_FILES:
            continue
        all_refs.extend(extract_from_file(path, indexes, so_hieu_map, lexicon))

    loai_count = Counter(r.loai for r in all_refs)
    print(f"=== TỔNG: {len(all_refs)} dẫn chiếu ===")
    for loai, n in loai_count.most_common():
        print(f"  {loai:14s} {n:5d}")

    dia_chi = [r for r in all_refs if r.loai != "tu_than"]
    giai_duoc = [r for r in dia_chi if r.dich_path]
    print(f"\n=== GIẢI CHIẾU (bỏ tự thân) ===")
    print(f"  tổng dẫn chiếu có địa chỉ : {len(dia_chi)}")
    if dia_chi:
        print(
            f"  giải chiếu THÀNH CÔNG     : {len(giai_duoc)} "
            f"({100*len(giai_duoc)/len(dia_chi):.1f}%)"
        )

    for loai in ("noi_bo", "lien_van_ban"):
        nhom = [r for r in dia_chi if r.loai == loai]
        ok = [r for r in nhom if r.dich_path]
        if nhom:
            print(f"    {loai:14s} {len(ok):4d}/{len(nhom):4d} = {100*len(ok)/len(nhom):5.1f}%")

    that_bai = Counter(
        (r.ly_do_that_bai or "?").split(":")[0] for r in dia_chi if not r.dich_path
    )
    if that_bai:
        print("\n=== LÝ DO THẤT BẠI ===")
        for ly_do, n in that_bai.most_common(8):
            print(f"  {n:5d}  {ly_do}")

    # Cạnh REFERS_TO thực tế sinh ra được (bỏ tự-trỏ trong cùng Component)
    canh = {
        (nguon_component_id(r), dich_component_id(r))
        for r in giai_duoc
        if nguon_component_id(r) != dich_component_id(r)
    }
    print(f"\n=== CẠNH [:REFERS_TO] sinh được: {len(canh)} (đã khử trùng lặp) ===")


if __name__ == "__main__":
    main()
