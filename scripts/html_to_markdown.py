"""Chuyển HTML lưu từ vbpl.vn thành markdown theo format `parser.py` đòi hỏi.

    python scripts/html_to_markdown.py                      # data/raw_html/ → data/raw/
    python scripts/html_to_markdown.py --out-dir /tmp/thu    # ghi nơi khác để soát trước
    python scripts/html_to_markdown.py --dry-run             # chỉ liệt kê cặp file

Mỗi văn bản gồm 2 file đã lưu: bản toàn văn và bản `_luoc-do.html`.

⚠️ ĐẦU RA LÀ BẢN NHÁP, KHÔNG NẠP THẲNG ĐƯỢC. HTML không chứa `theme`, `summary`,
`id` theo quy ước dự án, và không có chú thích `<!-- amended_by -->` ở cấp điều
khoản (bản toàn văn là văn bản gốc, không phải VBHN). Script điền placeholder
`TODO` cho những chỗ đó và liệt kê tất cả vào `data/raw/TODO_review.md`.

Cấu trúc HTML (khảo sát 2026-08-18):
  • Toàn văn: <div id="rc-tabs-0-panel-toan-van">, các đoạn <p class="MsoNormal prov-*">
    với 6 class: prov-chapter, prov-section, prov-article, prov-clause, prov-item,
    prov-content. Bốn cấp là ANH EM PHẲNG — phân cấp nằm ở class, không ở lồng nhau.
  • Thuộc tính: <div id="rc-tabs-0-panel-thuoc-tinh">, bảng key/value.
  • Lược đồ: <div id="rc-tabs-0-panel-luoc-do">, tiêu đề nhóm "Tên quan hệ (N)"
    rồi <ul><li><a>Tên văn bản</a></li></ul>. Thẻ <a> KHÔNG có href → chỉ lấy được
    số hiệu từ text, phải tra bảng để ra slug.
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

for _luong in (sys.stdout, sys.stderr):
    if getattr(_luong, "encoding", "").lower() != "utf-8":
        try:
            _luong.reconfigure(encoding="utf-8")
        except Exception:                           # noqa: BLE001
            pass

GOC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC))

from bs4 import BeautifulSoup                       # noqa: E402

PANEL_TOAN_VAN = "rc-tabs-0-panel-toan-van"
PANEL_THUOC_TINH = "rc-tabs-0-panel-thuoc-tinh"
PANEL_LUOC_DO = "rc-tabs-0-panel-luoc-do"

# Số hiệu → slug id của corpus. Không khớp → ghi TODO thay vì đoán bừa.
SO_HIEU_TO_SLUG = {
    "45/2019/QH14": "bo-luat-lao-dong-2019",
    "10/2012/QH13": "bo-luat-lao-dong-2012",
    "145/2020/NĐ-CP": "nghi-dinh-145-2020-nd-cp",
    "293/2025/NĐ-CP": "nghi-dinh-293-2025-nd-cp",
}

# "Loại văn bản" trong panel thuộc tính → tier (bảng tier CỨNG của dự án).
LOAI_TO_TIER = {
    "bộ luật": 1, "luật": 1, "nghị quyết của quốc hội": 1,
    "nghị định": 2, "pháp lệnh": 2,
    "thông tư": 3, "thông tư liên tịch": 3,
    "quyết định": 4, "nghị quyết": 4,
}

# Nhóm lược đồ → trường frontmatter. Nhóm không nằm ở đây chỉ ghi TODO.
NHOM_IMPLEMENTS = ("được hướng dẫn áp dụng", "được quy định chi tiết")
NHOM_AMENDED = ("được sửa đổi bổ sung",)
NHOM_TODO = ("được thay thế", "bị bãi bỏ", "căn cứ ban hành", "được hợp nhất",
             "được đính chính", "được dẫn chiếu")

_RE_KHOAN = re.compile(r"^(\d+)\.\s*(.*)$", re.DOTALL)
_RE_DIEM = re.compile(r"^([a-zA-ZđĐ]{1,2})\)\s*(.*)$", re.DOTALL)
_RE_SO_HIEU = re.compile(r"(\d+[a-zA-Z]?/\d{4}/[A-ZĐa-zđ\-]+)")
_RE_NHOM = re.compile(r"^(.*?)\s*\((\d+)\)\s*$")
# Rác thường gặp trong bản in công báo
_RE_RAC = re.compile(r"^(CÔNG BÁO/Số|Trang \d+|^\d+$)", re.IGNORECASE)


def _gon(s: str) -> str:
    """Gộp mọi khoảng trắng thành 1 dấu cách (quy tắc unwrap của dự án)."""
    return " ".join((s or "").split())


def _slugify(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("đ", "d").replace("Đ", "D").lower()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s)).strip("-")


def _ngay(s: str) -> str | None:
    """DD/MM/YYYY → YYYY-MM-DD. Trả None nếu là '--' hoặc không parse được."""
    s = _gon(s)
    if not s or s in ("--", "-"):
        return None
    try:
        return datetime.strptime(s, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Panel thuộc tính
# ---------------------------------------------------------------------------

def doc_thuoc_tinh(soup: BeautifulSoup) -> dict:
    """Bảng key/value → dict. Mỗi <tr> có thể chứa NHIỀU cặp key/value."""
    panel = soup.find(id=PANEL_THUOC_TINH)
    if not panel:
        return {}
    thuoc_tinh: dict[str, str] = {}
    khoa = ("Số hiệu", "Loại văn bản", "Ngày ban hành", "Ngày có hiệu lực",
            "Ngày hết hiệu lực", "Tình trạng hiệu lực", "Cơ quan ban hành",
            "Người ký", "Chức danh", "Ngành", "Lĩnh vực")
    for td in panel.find_all("td"):
        text = _gon(td.get_text(" ", strip=True))
        for k in khoa:
            if text.startswith(k):
                thuoc_tinh[k] = _gon(text[len(k):])
                break
    return thuoc_tinh


def doc_thuoc_tinh_tu_luoc_do(soup_ld: BeautifulSoup) -> dict:
    """Dự phòng: lấy thuộc tính từ khối “VĂN BẢN ĐANG XEM” của file lược đồ.

    3/4 file mẫu có panel thuộc tính RỖNG (trang lưu lúc tab khác đang mở nên
    React chưa render tab đó), nhưng khối này trong file lược đồ vẫn đủ dữ liệu.
    """
    panel = soup_ld.find(id=PANEL_LUOC_DO)
    if not panel:
        return {}
    dong = [d for d in panel.get_text("\n", strip=True).split("\n") if d.strip()]
    try:
        bat_dau = next(i for i, d in enumerate(dong) if "ĐANG XEM" in d.upper())
    except StopIteration:
        return {}
    khoa = {"Số hiệu", "Loại văn bản", "Ngày ban hành", "Ngày có hiệu lực",
            "Ngày hết hiệu lực", "Tình trạng hiệu lực", "Cơ quan ban hành",
            "Người ký", "Chức danh", "Ngành", "Lĩnh vực"}
    tt: dict[str, str] = {}
    for i in range(bat_dau, len(dong) - 1):
        if dong[i] in khoa and dong[i + 1] not in khoa:
            tt.setdefault(dong[i], _gon(dong[i + 1]))
    return tt


def doc_source_url(soup: BeautifulSoup) -> str | None:
    link = soup.find("link", {"rel": "canonical"})
    if link and link.get("href"):
        return link["href"]
    meta = soup.find("meta", {"property": "og:url"})
    return meta.get("content") if meta else None


# ---------------------------------------------------------------------------
# Panel toàn văn → markdown
# ---------------------------------------------------------------------------

def _bang_markdown(table) -> list[str]:
    """<table> → bảng markdown. Hàng đầu làm header."""
    rows = []
    for tr in table.find_all("tr"):
        cells = [_gon(td.get_text(" ", strip=True)) for td in tr.find_all(["td", "th"])]
        if any(cells):
            rows.append(cells)
    if not rows:
        return []
    n = max(len(r) for r in rows)
    rows = [r + [""] * (n - len(r)) for r in rows]
    out = ["| " + " | ".join(rows[0]) + " |",
           "|" + "|".join([" --- "] * n) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return out


def chuyen_toan_van(soup: BeautifulSoup) -> tuple[list[str], dict]:
    """Panel toàn văn → (dòng markdown, thống kê)."""
    panel = soup.find(id=PANEL_TOAN_VAN)
    if not panel:
        return [], {"loi": "không tìm thấy panel toàn văn"}

    els = [t for t in panel.find_all(class_=True)
           if any(c.startswith("prov-") for c in t.get("class", []))]

    # Trang render lặp một số khối. Bản lặp KHÔNG có `id` lẫn `parent-id` (hai
    # thuộc tính neo của site), trong khi bản thật luôn có ít nhất một. Kiểm chứng
    # trên NĐ 145: cả 13 thẻ mồ côi đều trùng nội dung với một thẻ có neo.
    # Lọc ở đây (trước khi dựng cấu trúc) thay vì dedupe khi đang duyệt, vì chỗ
    # chèn heading placeholder nằm giữa hai bản lặp sẽ làm dedupe theo Điều trượt.
    _co_neo = {_gon(t.get_text(" ", strip=True))
               for t in els if t.get("id") or t.get("parent-id")}
    _sach = [t for t in els
             if t.get("id") or t.get("parent-id")
             or _gon(t.get_text(" ", strip=True)) not in _co_neo]
    _so_lap = len(els) - len(_sach)
    els = _sach

    if not els:
        # Văn bản cũ (vd Bộ luật 10/2012): DOM không có class prov-*, heading là
        # <p><b>Điều N. …</b></p>. Chuyển sang nhận dạng theo mẫu chữ.
        return chuyen_toan_van_cu(panel)

    dong: list[str] = []
    tk = {"dieu": 0, "khoan": 0, "diem": 0, "bang": 0, "bo_chuong_muc": 0, "rac": 0,
          "trung_lap_bo": _so_lap}
    bang_da_xu_ly: set[int] = set()
    duong_dan: list[str] = []          # context_path hiện tại (để bắt trùng)
    cac_duong_dan: list[tuple[str, ...]] = []
    # (class, text) đã phát trong Điều hiện tại — chống khối bị render 2 lần
    da_phat: set[tuple[str, str]] = set()
    so_dieu: list[int] = []

    # Tiền xử lý: HTML nguồn có thể MẤT hẳn thẻ heading của vài Điều (quan sát ở
    # NĐ 145: Điều 4, 31, 62). Khoản của chúng sẽ dính vào Điều liền trước →
    # context_path trùng → deterministic ID trùng (CLAUDE.md cấm). Biết trước số
    # Điều nào thiếu thì chèn được heading placeholder ngay chỗ số khoản quay đầu.
    _co = [int(m.group(1)) for m in
           (re.match(r"^Điều (\d+)\.", _gon(t.get_text(" ", strip=True)))
            for t in els if "prov-article" in t.get("class", [])) if m]
    thieu_heading = sorted(set(range(1, max(_co) + 1)) - set(_co)) if _co else []
    tk["dieu_thieu_heading"] = list(thieu_heading)
    khoan_cuoi = 0
    dieu_hien_tai = 0

    def them_heading(muc: int, nhan: str, than: str = "") -> None:
        if dong and dong[-1] != "":
            dong.append("")
        dong.append("#" * muc + " " + nhan)
        dong.append("")
        if than:
            dong.append(than)
            dong.append("")

    for the in els:
        loai = [c for c in the.get("class", []) if c.startswith("prov-")][0]

        # Ô trong bảng: xử lý cả <table> một lần, bỏ qua các ô còn lại
        bang = the.find_parent("table")
        if bang is not None:
            if id(bang) in bang_da_xu_ly:
                continue
            bang_da_xu_ly.add(id(bang))
            md = _bang_markdown(bang)
            if md:
                if dong and dong[-1] != "":
                    dong.append("")
                dong.extend(md)
                dong.append("")
                tk["bang"] += 1
            continue

        text = _gon(the.get_text(" ", strip=True))
        if not text or text == "--":
            continue

        # Chương/Mục bị validator CẤM → bỏ (gồm cả dòng tên chương viết hoa)
        if loai in ("prov-chapter", "prov-section"):
            tk["bo_chuong_muc"] += 1
            continue

        if _RE_RAC.match(text):
            tk["rac"] += 1
            continue

        # Khối bị trang render 2 lần: cùng class + cùng chữ trong CÙNG một Điều.
        # (Quan sát ở NĐ 145: khối của Điều mất heading xuất hiện lặp.)
        if loai != "prov-article":
            khoa_lap = (loai, text)
            if khoa_lap in da_phat:
                tk["trung_lap_bo"] += 1
                continue
            da_phat.add(khoa_lap)

        if loai == "prov-article":
            nhan = text if text.lower().startswith("điều") else f"Điều {text}"
            them_heading(2, nhan)
            tk["dieu"] += 1
            da_phat.clear()
            khoan_cuoi = 0
            m_so = re.match(r"^Điều (\d+)\.", nhan)
            if m_so:
                so_dieu.append(int(m_so.group(1)))
                dieu_hien_tai = int(m_so.group(1))
            duong_dan = [nhan]
            cac_duong_dan.append(tuple(duong_dan))
        elif loai == "prov-clause":
            m = _RE_KHOAN.match(text)
            so_khoan = int(m.group(1)) if m else None

            # Số khoản quay đầu (vd 3 → 1) giữa một Điều = ranh giới của Điều bị
            # mất heading. Chèn placeholder để nội dung nằm đúng chỗ, kèm TODO.
            # Chọn số Điều thiếu NHỎ NHẤT LỚN HƠN Điều hiện tại — không chỉ đầu
            # hàng đợi: một số Điều thiếu heading (vd Điều 31) không tạo ra khoản
            # quay đầu nên không bao giờ khớp, và sẽ chặn các số phía sau.
            _ung_vien = [n for n in thieu_heading if n > dieu_hien_tai]
            if so_khoan is not None and so_khoan <= khoan_cuoi and _ung_vien:
                so_moi = _ung_vien[0]
                thieu_heading.remove(so_moi)
                nhan_moi = (f"Điều {so_moi}. TODO — HTML nguồn thiếu tên Điều, "
                            "bổ sung thủ công")
                them_heading(2, nhan_moi)
                tk["dieu"] += 1
                tk["dieu_chen_placeholder"] = tk.get("dieu_chen_placeholder", 0) + 1
                da_phat.clear()
                dieu_hien_tai, khoan_cuoi = so_moi, 0
                duong_dan = [nhan_moi]
                cac_duong_dan.append(tuple(duong_dan))

            if m:
                nhan, than = f"Khoản {m.group(1)}.", _gon(m.group(2))
                khoan_cuoi = so_khoan
            else:
                nhan, than = "Khoản.", text
            them_heading(3, nhan, than)
            tk["khoan"] += 1
            duong_dan = duong_dan[:1] + [nhan]
            cac_duong_dan.append(tuple(duong_dan))
        elif loai == "prov-item":
            m = _RE_DIEM.match(text)
            if m:
                nhan, than = f"Điểm {m.group(1)}.", _gon(m.group(2))
            else:
                nhan, than = "Điểm.", text
            them_heading(4, nhan, than)
            tk["diem"] += 1
            duong_dan = duong_dan[:2] + [nhan]
            cac_duong_dan.append(tuple(duong_dan))
        else:                                        # prov-content
            if dong and dong[-1] != "":
                dong.append("")
            dong.append(text)
            dong.append("")

    tk["duong_dan_trung"] = [p for p in set(cac_duong_dan)
                             if cac_duong_dan.count(p) > 1]
    tk["dieu_chua_chen"] = list(thieu_heading)   # còn sót, không tìm được ranh giới
    return dong, tk


def chuyen_toan_van_cu(panel) -> tuple[list[str], dict]:
    """Bản HTML cũ không có class prov-*: nhận dạng cấp bậc theo mẫu chữ.

    Quy ước quan sát được (Bộ luật 10/2012): heading Điều nằm trong <b>; Chương/Mục
    là <p align="center"> in đậm; khoản/điểm là <p> thường mở đầu bằng "N." / "a)".
    """
    dong: list[str] = []
    tk = {"dieu": 0, "khoan": 0, "diem": 0, "bang": 0, "bo_chuong_muc": 0, "rac": 0,
          "trung_lap_bo": 0, "che_do": "HTML cũ (không có class prov-*)"}
    duong_dan: list[str] = []
    cac_duong_dan: list[tuple[str, ...]] = []
    so_dieu: list[int] = []

    def them(muc: int, nhan: str, than: str = "") -> None:
        if dong and dong[-1] != "":
            dong.append("")
        dong.append("#" * muc + " " + nhan)
        dong.append("")
        if than:
            dong.append(than)
            dong.append("")

    for p in panel.find_all("p"):
        text = _gon(p.get_text(" ", strip=True))
        if not text or _RE_RAC.match(text):
            tk["rac"] += 1 if text else 0
            continue
        if re.match(r"^(Chương|Mục|PHẦN)\b", text, re.IGNORECASE) or (
                p.get("align") == "center" and text.isupper()):
            tk["bo_chuong_muc"] += 1
            continue

        m_dieu = re.match(r"^Điều (\d+)\.\s*(.*)$", text)
        if m_dieu:
            nhan = f"Điều {m_dieu.group(1)}. {_gon(m_dieu.group(2))}".strip()
            them(2, nhan)
            tk["dieu"] += 1
            so_dieu.append(int(m_dieu.group(1)))
            duong_dan = [nhan]
            cac_duong_dan.append(tuple(duong_dan))
            continue
        if not duong_dan:
            # Lời nói đầu ("Căn cứ …", "Quốc hội ban hành …") nằm TRƯỚC Điều 1.
            # `parser.py` bắt buộc mọi nội dung phải có heading cha → giữ lại sẽ
            # ném ValueError và chặn cả mẻ ingestion. Corpus hiện có cũng không
            # chứa phần này (file bắt đầu thẳng bằng `## Điều`). → bỏ.
            tk["rac"] += 1
            continue

        m_khoan = _RE_KHOAN.match(text)
        m_diem = _RE_DIEM.match(text)
        if m_khoan:
            nhan = f"Khoản {m_khoan.group(1)}."
            them(3, nhan, _gon(m_khoan.group(2)))
            tk["khoan"] += 1
            duong_dan = duong_dan[:1] + [nhan]
            cac_duong_dan.append(tuple(duong_dan))
        elif m_diem:
            nhan = f"Điểm {m_diem.group(1)}."
            them(4, nhan, _gon(m_diem.group(2)))
            tk["diem"] += 1
            duong_dan = duong_dan[:2] + [nhan]
            cac_duong_dan.append(tuple(duong_dan))
        else:
            if dong and dong[-1] != "":
                dong.append("")
            dong += [text, ""]

    tk["duong_dan_trung"] = [p for p in set(cac_duong_dan)
                             if cac_duong_dan.count(p) > 1]
    if so_dieu:
        tk["dieu_thieu_heading"] = [i for i in range(1, max(so_dieu) + 1)
                                    if i not in so_dieu]
    return dong, tk


# ---------------------------------------------------------------------------
# Panel lược đồ
# ---------------------------------------------------------------------------

def doc_luoc_do(soup: BeautifulSoup) -> dict[str, list[str]]:
    """→ {tên nhóm (lowercase): [tên văn bản, ...]}. Nhóm rỗng bị loại."""
    panel = soup.find(id=PANEL_LUOC_DO)
    if not panel:
        return {}
    nhom: dict[str, list[str]] = {}
    for ul in panel.find_all("ul"):
        tieu_de = None
        for chuoi in ul.find_all_previous(string=True, limit=40):
            m = _RE_NHOM.match(_gon(str(chuoi)))
            if m and m.group(1):
                tieu_de = m.group(1)
                break
        if not tieu_de:
            continue
        muc = [_gon(a.get_text(" ", strip=True)) for a in ul.find_all("a")]
        muc = [m for m in muc if m and m != "--"]
        if muc:
            nhom.setdefault(tieu_de.lower(), []).extend(muc)
    return nhom


def _slug_tu_ten(ten_vb: str) -> tuple[str | None, str | None]:
    """Tên văn bản trong lược đồ → (slug, số hiệu). slug=None nếu không tra được."""
    m = _RE_SO_HIEU.search(ten_vb)
    if not m:
        return None, None
    so_hieu = m.group(1)
    return SO_HIEU_TO_SLUG.get(so_hieu), so_hieu


def phan_loai_quan_he(nhom: dict[str, list[str]]) -> tuple[list[str], list[str], list[str]]:
    """→ (implements, amended_by_norms, ghi_chú TODO)."""
    implements: list[str] = []
    amended: list[str] = []
    todo: list[str] = []

    for ten_nhom, muc in nhom.items():
        for vb in muc:
            slug, so_hieu = _slug_tu_ten(vb)
            if any(k in ten_nhom for k in NHOM_IMPLEMENTS):
                dich = implements
            elif any(k in ten_nhom for k in NHOM_AMENDED):
                dich = amended
                todo.append(
                    f"⚠️ CHIỀU QUAN HỆ: nhóm “{ten_nhom}” là văn bản mà VĂN BẢN NÀY "
                    f"sửa đổi, trong khi `amended_by_norms` nghĩa là văn bản SỬA "
                    f"VĂN BẢN NÀY — ngược chiều. Kiểm tra thủ công: {vb[:70]}")
            elif any(k in ten_nhom for k in NHOM_TODO):
                todo.append(f"Quan hệ “{ten_nhom}”: {vb[:80]}"
                            + (f" (slug: {slug})" if slug else
                               f" (chưa map slug{': ' + so_hieu if so_hieu else ''})"))
                continue
            else:
                continue
            if slug:
                dich.append(slug)
            elif so_hieu:
                todo.append(f"Chưa map slug cho “{so_hieu}” (nhóm “{ten_nhom}”)")
            else:
                todo.append(f"Không đọc được số hiệu từ: {vb[:70]}")
    return implements, amended, todo


# ---------------------------------------------------------------------------
# Frontmatter + kiểm tra
# ---------------------------------------------------------------------------

def _yaml_list(items: list[str]) -> str:
    if not items:
        return "null"
    if len(items) == 1:
        return f'"{items[0]}"'
    return "[" + ", ".join(f'"{i}"' for i in items) + "]"


def dung_frontmatter(vb_id, title, so_hieu, tier, implements, valid_from,
                     valid_to, source_url, amended) -> list[str]:
    return [
        "---",
        f'id: "{vb_id}"',
        f'title: "{title}"',
        f'so_hieu: "{so_hieu}"' if so_hieu else 'so_hieu: null  # TODO',
        f"tier: {tier}" if tier else "tier: 0  # TODO: không suy được từ HTML",
        'theme: "lao-dong"',
        'jurisdiction: "toan-quoc"',
        f"implements: {_yaml_list(implements)}",
        f'valid_from: "{valid_from}"' if valid_from else "valid_from: null  # TODO",
        f'valid_to: "{valid_to}"' if valid_to else "valid_to: null",
        f'source_url: "{source_url}"' if source_url else "source_url: null  # TODO",
        "source_vbhn: null",
        f"amended_by_norms: {_yaml_list(amended)}",
        'summary: "TODO: viết 3-5 câu tóm tắt phạm vi văn bản (thủ tục, đối tượng, '
        'địa phương) — do con người viết, dùng cho Stage 1 retrieval"',
        "---",
        "",
    ]


def kiem_tra(dong_body: list[str], tk: dict) -> list[str]:
    """Bắt các lỗi format mà `validate_metadata.py` sẽ chặn."""
    loi = []
    re_thieu_thang = re.compile(r"^(Điều|Khoản|Điểm|Tiết)\s+\S+\.")
    for i, d in enumerate(dong_body, 1):
        if re_thieu_thang.match(d):
            loi.append(f"dòng {i}: “{d[:50]}” trông như heading nhưng THIẾU dấu #")
        if re.match(r"^---\s*$", d):
            loi.append(f"dòng {i}: có `---` trong thân bài (validator cấm)")
    for p in tk.get("duong_dan_trung", []):
        loi.append(f"context_path TRÙNG: {' > '.join(p)}")
    if tk.get("loi"):
        loi.append(tk["loi"])
    if tk.get("dieu", 0) == 0:
        loi.append("không trích được Điều nào — kiểm tra lại panel toàn văn")
    return loi


# ---------------------------------------------------------------------------
# Điều phối
# ---------------------------------------------------------------------------

def tim_cap_file(thu_muc: Path) -> list[tuple[Path, Path | None]]:
    cap = []
    for f in sorted(thu_muc.glob("*.html")):
        if f.name.endswith("_luoc-do.html"):
            continue
        ld = f.with_name(f.stem + "_luoc-do.html")
        cap.append((f, ld if ld.exists() else None))
    return cap


def xu_ly(f_toan_van: Path, f_luoc_do: Path | None, out_dir: Path) -> dict:
    soup = BeautifulSoup(f_toan_van.read_text(encoding="utf-8", errors="replace"),
                         "html.parser")
    soup_ld = BeautifulSoup(
        f_luoc_do.read_text(encoding="utf-8", errors="replace"), "html.parser"
    ) if f_luoc_do else None

    tt = doc_thuoc_tinh(soup)
    nguon_tt = "panel thuộc tính"
    if not tt and soup_ld is not None:
        tt = doc_thuoc_tinh_tu_luoc_do(soup_ld)
        nguon_tt = "khối “VĂN BẢN ĐANG XEM” của file lược đồ (panel thuộc tính rỗng)"
    so_hieu = tt.get("Số hiệu")
    loai_vb = tt.get("Loại văn bản", "")
    tier = LOAI_TO_TIER.get(loai_vb.lower().strip())
    valid_from = _ngay(tt.get("Ngày có hiệu lực", ""))
    valid_to = _ngay(tt.get("Ngày hết hiệu lực", ""))
    source_url = doc_source_url(soup)

    vb_id = SO_HIEU_TO_SLUG.get(so_hieu or "") or _slugify(f"{loai_vb} {so_hieu or f_toan_van.stem}")
    title = f"{loai_vb} {so_hieu}".strip() if so_hieu else _gon(f_toan_van.stem)

    body, tk = chuyen_toan_van(soup)

    implements: list[str] = []
    amended: list[str] = []
    todo: list[str] = []
    if soup_ld is not None:
        implements, amended, todo = phan_loai_quan_he(doc_luoc_do(soup_ld))
    else:
        todo.append("KHÔNG có file _luoc-do.html → implements/amended_by_norms bỏ trống")

    todo.append(f"Nguồn thuộc tính: {nguon_tt}")
    if tk.get("che_do"):
        todo.append(f"Chế độ parse: {tk['che_do']} — cấu trúc suy từ mẫu chữ, "
                    "cần soát kỹ hơn bản có class ngữ nghĩa")
    if tk.get("dieu_thieu_heading"):
        todo.append(
            f"⚠️ HTML nguồn THIẾU heading cho Điều {tk['dieu_thieu_heading']} — "
            f"đã chèn {tk.get('dieu_chen_placeholder', 0)} heading placeholder "
            "“TODO — HTML nguồn thiếu tên Điều”. PHẢI thay bằng tên Điều thật "
            "(tra công báo/vbpl) trước khi ingest.")
    if tk.get("dieu_chua_chen"):
        todo.append(f"⚠️ Điều {tk['dieu_chua_chen']} thiếu heading và KHÔNG xác định "
                    "được ranh giới → nội dung vẫn nằm nhầm ở Điều liền trước")
    if tk.get("trung_lap_bo"):
        todo.append(f"Đã bỏ {tk['trung_lap_bo']} đoạn bị trang render lặp "
                    "(cùng nội dung, cùng Điều) — soát lại nếu thấy thiếu nội dung")

    if not tier:
        todo.append(f"Không suy được tier từ loại văn bản “{loai_vb}”")
    if not valid_from:
        todo.append("Không đọc được ngày có hiệu lực → valid_from cần điền tay")
    todo.append("summary: bắt buộc người viết (D-08) — placeholder hiện là TODO")
    todo.append("theme=lao-dong, jurisdiction=toan-quoc do script GÁN CỨNG — xác nhận lại")
    if tk.get("bang"):
        todo.append(f"{tk['bang']} bảng đã chuyển sang markdown — soát lại nội dung số liệu")
    todo.append("Không có chú thích <!-- amended_by --> (bản toàn văn ≠ VBHN) → "
                "Amendment node/Gap 4 sẽ trống cho văn bản này")

    loi = kiem_tra(body, tk)
    out_dir.mkdir(parents=True, exist_ok=True)
    dich = out_dir / f"{vb_id}.md"
    dich.write_text("\n".join(dung_frontmatter(
        vb_id, title, so_hieu, tier, implements, valid_from, valid_to,
        source_url, amended) + body).rstrip() + "\n", encoding="utf-8")

    return {"file_nguon": f_toan_van.name, "file_dich": dich, "id": vb_id,
            "title": title, "tier": tier, "so_hieu": so_hieu,
            "implements": implements, "amended": amended,
            "tk": tk, "todo": todo, "loi": loi}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--html-dir", default="data/raw_html")
    ap.add_argument("--out-dir", default="data/raw")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    thu_muc = Path(args.html_dir)
    cap = tim_cap_file(thu_muc)
    if not cap:
        print(f"Không thấy file .html nào trong {thu_muc}")
        return 1

    print(f"Tìm thấy {len(cap)} văn bản:")
    for tv, ld in cap:
        print(f"  • {tv.name[:60]}  | lược đồ: {'có' if ld else 'THIẾU'}")
    if args.dry_run:
        print("\n[dry-run] Không ghi gì.")
        return 0

    out_dir = Path(args.out_dir)
    ket_qua = [xu_ly(tv, ld, out_dir) for tv, ld in cap]

    bao_cao = ["# TODO — soát thủ công file sinh từ HTML", "",
               f"Sinh bởi `scripts/html_to_markdown.py` lúc {datetime.now():%Y-%m-%d %H:%M}.",
               "", "**Các file dưới đây là BẢN NHÁP.** Chưa điền xong thì không chạy "
               "`graph_builder` — thiếu `summary` sẽ hỏng Stage 1 retrieval, sai `theme` "
               "sẽ hỏng định tuyến Gap 1.", ""]
    for r in ket_qua:
        tk = r["tk"]
        bao_cao += [
            f"## {r['file_dich'].name}", "",
            f"- Nguồn: `{r['file_nguon']}`",
            f"- id `{r['id']}` · số hiệu `{r['so_hieu']}` · tier `{r['tier']}`",
            f"- Trích được: {tk.get('dieu',0)} Điều, {tk.get('khoan',0)} Khoản, "
            f"{tk.get('diem',0)} Điểm, {tk.get('bang',0)} bảng "
            f"(bỏ {tk.get('bo_chuong_muc',0)} dòng Chương/Mục, {tk.get('rac',0)} dòng rác)",
            f"- implements: `{r['implements'] or 'null'}` · "
            f"amended_by_norms: `{r['amended'] or 'null'}`", "",
        ]
        if r["loi"]:
            bao_cao += ["**LỖI FORMAT (phải sửa):**", ""]
            bao_cao += [f"- ❌ {e}" for e in r["loi"]] + [""]
        bao_cao += ["**Cần soát:**", ""] + [f"- [ ] {t}" for t in r["todo"]] + [""]

    (out_dir / "TODO_review.md").write_text("\n".join(bao_cao), encoding="utf-8")

    print()
    for r in ket_qua:
        tk = r["tk"]
        trang_thai = "❌ có lỗi" if r["loi"] else "✅"
        print(f"{trang_thai} {r['file_dich'].name:34} "
              f"{tk.get('dieu',0):>4} Điều {tk.get('khoan',0):>4} Khoản "
              f"{tk.get('diem',0):>4} Điểm {tk.get('bang',0):>2} bảng")
        for e in r["loi"]:
            print(f"     ❌ {e}")
    print(f"\nĐã ghi {len(ket_qua)} file .md + {out_dir/'TODO_review.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
