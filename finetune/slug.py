"""TASK-FT-04 — Suy slug văn bản từ `doc_name`, CƠ KHÍ (không dùng LLM).

Convention slug (CLAUDE.md §CONVENTIONS): `[loai-van-ban]-[slug-ten]-[nam]`

    "Luật Địa chất và Khoáng sản của Quốc hội, số 54/2024/QH15"
        -> luat-dia-chat-va-khoang-san-2024
    "Luật Bảo hiểm y tế số 25/2008/QH12 của Quốc hội"
        -> luat-bao-hiem-y-te-2008

Slug sinh ra ở đây là **slug tổng hợp**, KHÔNG có trong corpus 32 văn bản. Đó là
chủ ý (kế hoạch §TASK-FT-04, "Nguyên tắc cốt lõi"): mẫu huấn luyện phải dạy mô
hình *chép slug từ header ngữ cảnh*, chứ không phải *nhớ slug*. Điều kiện duy
nhất là slug phải xuất hiện trong header ngữ cảnh của chính mẫu đó.

Module này CỐ Ý không import gì từ `src/` — nó chỉ là hàm chuỗi thuần, test được
độc lập.
"""
from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------------------
# Bảng loại văn bản -> tiền tố slug. Bộ dữ liệu thangvip chỉ có "Luật"
# (`doc_type_name` một giá trị duy nhất), nhưng giữ đủ 4 tier để hàm dùng lại
# được và để test phủ được convention của CLAUDE.md.
# ---------------------------------------------------------------------------
_LOAI_PREFIXES: list[tuple[str, str]] = [
    ("bo luat", "bo-luat"),
    ("luat", "luat"),
    ("phap lenh", "phap-lenh"),
    ("nghi dinh", "nghi-dinh"),
    ("nghi quyet", "nghi-quyet"),
    ("thong tu lien tich", "thong-tu-lien-tich"),
    ("thong tu", "thong-tu"),
    ("quyet dinh", "quyet-dinh"),
]

# "số 54/2024/QH15", "số 31/2004/QH11", "56/2024/QH15"
_SO_HIEU_RE = re.compile(r"\b(\d{1,4})\s*/\s*(\d{4})\s*/\s*([A-Za-zĐđ]{2,}\d*(?:-[A-Za-zĐđ]+)*)")
# "năm 2015"
_NAM_RE = re.compile(r"\bnăm\s+(\d{4})\b", re.IGNORECASE)

# Cụm nhiễu trong doc_name, xoá trước khi slug hoá tên.
_NOISE_PATTERNS = [
    r"của\s+Quốc\s+hội",
    r"của\s+Hội\s+đồng\s+nhân\s+dân\s+và\s+Uỷ\s+ban\s+nhân\s+dân",
    r"của\s+Hội\s+đồng\s+nhân\s+dân",
    r"của\s+Uỷ\s+ban\s+nhân\s+dân",
    r"của\s+Ủy\s+ban\s+nhân\s+dân",
    r"của\s+Chính\s+phủ",
    r"\bsố\b",
]

# Trần số từ của phần tên. Chỉ chạm tới các "Luật sửa đổi, bổ sung một số điều
# của Luật A, Luật B, Luật C..." — slug dài 30 từ không giống bất kỳ slug thật
# nào nên sẽ dạy mô hình một bề mặt chuỗi lệch với lúc đánh giá.
MAX_NAME_WORDS = 12


def strip_diacritics(text: str) -> str:
    """Bỏ dấu tiếng Việt, giữ nguyên chữ cái Latin. `đ`/`Đ` xử lý riêng vì NFD
    không tách được gạch ngang của nó."""
    text = text.replace("đ", "d").replace("Đ", "D")
    nfd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def slugify(text: str) -> str:
    """Chuỗi tuỳ ý -> `lowercase-co-gach-ngang-khong-dau`."""
    ascii_text = strip_diacritics(text).lower()
    ascii_text = re.sub(r"[^a-z0-9]+", "-", ascii_text)
    return ascii_text.strip("-")


def normalize_doc_name(doc_name: str) -> str:
    """Chuẩn hoá để SO KHỚP (lọc rò rỉ): bỏ dấu, lowercase, gộp khoảng trắng.

    Giữ lại dấu `/` để số hiệu pháp lý (`31/2024/QH15`) vẫn so khớp được.
    """
    text = strip_diacritics(doc_name).lower()
    text = re.sub(r"[^a-z0-9/]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_so_hieu(doc_name: str) -> str | None:
    """Số hiệu pháp lý dạng `54/2024/QH15`, chuẩn hoá về lowercase không dấu.

    Trả None nếu doc_name không chứa số hiệu (ví dụ: các bản "Dự thảo Luật ...").
    """
    m = _SO_HIEU_RE.search(doc_name)
    if not m:
        return None
    # Giữ NGUYÊN chữ số như trong văn bản (kể cả số 0 đứng đầu: `04/2020/TT-BTP`)
    # — vừa là khoá so khớp rò rỉ, vừa là thành phần slug của văn bản dưới luật.
    return f"{m.group(1)}/{m.group(2)}/{strip_diacritics(m.group(3)).lower()}"


def extract_year(doc_name: str) -> str | None:
    """Năm ban hành: ưu tiên năm trong số hiệu, sau đó cụm "năm YYYY"."""
    m = _SO_HIEU_RE.search(doc_name)
    if m:
        return m.group(2)
    m = _NAM_RE.search(doc_name)
    if m:
        return m.group(1)
    return None


def _detect_loai(doc_name: str) -> str | None:
    head = normalize_doc_name(doc_name)
    for probe, prefix in _LOAI_PREFIXES:
        if head.startswith(probe + " ") or head == probe:
            return prefix
    return None


def _strip_noise(doc_name: str) -> str:
    text = doc_name
    # Bỏ số hiệu TRƯỚC (chứa dấu `/` sẽ thành gạch ngang thừa nếu để lại).
    text = _SO_HIEU_RE.sub(" ", text)
    for pat in _NOISE_PATTERNS:
        text = re.sub(pat, " ", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip(" ,.-")


def doc_name_to_slug(doc_name: str) -> str | None:
    """`doc_name` -> slug theo convention, hoặc None nếu không suy được.

    Trả None (KHÔNG đoán bừa) khi:
      - không nhận ra loại văn bản ở đầu chuỗi, hoặc
      - không có năm ban hành (mọi bản "Dự thảo Luật ..." rơi vào ca này).

    "Không suy được thì bỏ" là chủ ý: slug bịa sẽ dạy mô hình một bề mặt chuỗi
    không tồn tại, mà đó đúng là lỗi thiết kế nặng nhất của task này.
    """
    if not doc_name or not doc_name.strip():
        return None

    year = extract_year(doc_name)
    if year is None:
        return None

    # Văn bản dưới luật: convention thật đặt SỐ HIỆU vào slug, không đặt tên
    # (`nghi-dinh-102-2024-nd-cp`, `thong-tu-04-2020-tt-btp`). Bộ thangvip không
    # có ca nào (chỉ một `doc_type_name` = "Luật") nhưng để đúng convention.
    loai_head = _detect_loai(doc_name)
    so_hieu = extract_so_hieu(doc_name)
    if loai_head not in (None, "luat", "bo-luat") and so_hieu is not None:
        num, nam, ky_hieu = so_hieu.split("/")
        return f"{loai_head}-{num}-{nam}-{slugify(ky_hieu)}"

    text = _strip_noise(doc_name)

    # "Luật của Quốc hội số 26/2001/QH10 về Giao thông đường bộ"
    # -> sau _strip_noise còn "Luật về Giao thông đường bộ" -> tên nằm sau "về".
    m = re.match(r"^(.*?)\s+về\s+(.+)$", text, flags=re.IGNORECASE)
    if m and len(m.group(1).split()) <= 2:
        loai = _detect_loai(m.group(1) + " x")
        name = m.group(2)
    else:
        loai = _detect_loai(text)
        if loai is None:
            return None
        # Bỏ đúng số từ của cụm loại văn bản khỏi phần tên.
        n_words = len(loai.split("-"))
        name = " ".join(text.split()[n_words:])

    if loai is None or not name.strip():
        return None

    name_slug = slugify(name)
    if not name_slug:
        return None

    words = name_slug.split("-")
    if len(words) > MAX_NAME_WORDS:
        name_slug = "-".join(words[:MAX_NAME_WORDS])

    return f"{loai}-{name_slug}-{year}"


def build_slug_map(doc_names: list[str]) -> dict[str, str]:
    """doc_name -> slug, đã khử trùng slug.

    Hai `doc_name` khác nhau có thể ra cùng slug (bị cắt ở MAX_NAME_WORDS, hoặc
    trùng tên khác năm ban hành đã gộp). Khi đó thêm hậu tố `-b2`, `-b3`… để
    slug vẫn là khoá duy nhất — nếu không, hai văn bản khác nhau sẽ mang cùng
    một mã trong dữ liệu huấn luyện.
    """
    out: dict[str, str] = {}
    used: dict[str, int] = {}
    for name in sorted(set(doc_names)):
        slug = doc_name_to_slug(name)
        if slug is None:
            continue
        if slug in used:
            used[slug] += 1
            slug = f"{slug}-b{used[slug]}"
            used[slug] = 1
        else:
            used[slug] = 1
        out[name] = slug
    return out
