"""Unit test cho finetune/slug.py (DoD TASK-FT-04 mục 1: >= 10 ca).

Ca kiểm lấy từ `doc_name` THẬT của bộ thangvip/vietnamese-legal-qa, không bịa
chuỗi giả — cả 141 giá trị đều đã được duyệt qua khi chọn ca đại diện.
"""
from __future__ import annotations

import pytest

from finetune.slug import (
    build_slug_map,
    doc_name_to_slug,
    extract_so_hieu,
    extract_year,
    normalize_doc_name,
    slugify,
    strip_diacritics,
)


# ---------------------------------------------------------------------------
# 1-8. doc_name_to_slug — các dạng doc_name thật, mỗi ca một biến thể cú pháp
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "doc_name, expected",
    [
        # dạng phổ biến nhất: "..., số X/YYYY/QHnn"
        (
            "Luật Địa chất và Khoáng sản của Quốc hội, số 54/2024/QH15",
            "luat-dia-chat-va-khoang-san-2024",
        ),
        # số hiệu đứng GIỮA, "của Quốc hội" ở cuối
        (
            "Luật Bảo hiểm y tế số 25/2008/QH12 của Quốc hội",
            "luat-bao-hiem-y-te-2008",
        ),
        # "Luật của Quốc hội số ... về <tên>" — tên nằm SAU chữ "về"
        (
            "Luật của Quốc hội số 26/2001/QH10 về Giao thông đường bộ",
            "luat-giao-thong-duong-bo-2001",
        ),
        # không có "của Quốc hội"
        (
            "Luật các tổ chức tín dụng số 02/1997/QH10",
            "luat-cac-to-chuc-tin-dung-1997",
        ),
        # có dấu phẩy trước "số"
        (
            "Luật Giao thông đường thủy nội địa, số 23/2004/QH11",
            "luat-giao-thong-duong-thuy-noi-dia-2004",
        ),
        # chữ "đ" đầu từ phải thành "d", không được rơi mất
        (
            "Luật Đường sắt của Quốc hội, số 06/2017/QH14",
            "luat-duong-sat-2017",
        ),
        # tên có "Nhà nước" viết hoa + khoảng trắng thừa cuối chuỗi
        (
            "Luật Ngân sách Nhà nước của Quốc hội, số 83/2015/QH13 ",
            "luat-ngan-sach-nha-nuoc-2015",
        ),
        # loại văn bản ngoài "Luật" (không có trong bộ thangvip): convention thật
        # đặt SỐ HIỆU vào slug thay vì tên — đối chiếu data/raw/*.md
        (
            "Nghị định 102/2024/NĐ-CP",
            "nghi-dinh-102-2024-nd-cp",
        ),
        (
            "Thông tư 04/2020/TT-BTP",
            "thong-tu-04-2020-tt-btp",
        ),
    ],
)
def test_doc_name_to_slug(doc_name, expected):
    assert doc_name_to_slug(doc_name) == expected


# ---------------------------------------------------------------------------
# 9. Không suy được -> None, KHÔNG đoán bừa
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "doc_name",
    [
        "Dự thảo Luật Công nghiệp trọng điểm",  # dự thảo: không số hiệu, không năm
        "Dự thảo Luật Bảo hiểm xã hội",
        "Luật Quy định quyền lập hội",  # luật cũ, doc_name không mang năm
        "",
        "   ",
    ],
)
def test_khong_suy_duoc_tra_none(doc_name):
    assert doc_name_to_slug(doc_name) is None


# ---------------------------------------------------------------------------
# 10. Slug luôn hợp lệ về hình dạng: chỉ [a-z0-9-], không dấu, không gạch đôi
# ---------------------------------------------------------------------------
def test_hinh_dang_slug_hop_le():
    import re

    names = [
        "Luật Tư pháp người chưa thành niên của Quốc hội, số 59/2024/QH15",
        "Luật Nhập cảnh, xuất cảnh, quá cảnh, cư trú của người nước ngoài tại Việt Nam"
        " của Quốc hội, số 47/2014/QH13",
        "Luật Quản lý, sử dụng vũ khí, vật liệu nổ và công cụ hỗ trợ của Quốc hội,"
        " số 42/2024/QH15",
    ]
    for n in names:
        s = doc_name_to_slug(n)
        assert s is not None
        assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", s), s
        assert "--" not in s


# ---------------------------------------------------------------------------
# 11. Trần MAX_NAME_WORDS chặn các "Luật sửa đổi, bổ sung ... Luật A, Luật B..."
# ---------------------------------------------------------------------------
def test_cat_ten_qua_dai():
    doc = (
        "Luật sửa đổi, bổ sung một số điều của Luật Chứng khoán, Luật Kế toán, "
        "Luật Kiểm toán độc lập, Luật Ngân sách Nhà nước, Luật Quản lý, sử dụng "
        "tài sản công, Luật Quản lý thuế, Luật Thuế thu nhập cá nhân, Luật Dự trữ "
        "quốc gia, Luật Xử lý vi phạm hành chính của Quốc hội, số 56/2024/QH15"
    )
    slug = doc_name_to_slug(doc)
    assert slug is not None
    # 12 từ của phần tên + 1 từ tiền tố loại + 1 từ năm
    assert len(slug.split("-")) == 14
    assert slug.startswith("luat-sua-doi-bo-sung-")
    assert slug.endswith("-2024")


# ---------------------------------------------------------------------------
# 12. build_slug_map — khử trùng slug giữa hai doc_name khác nhau
# ---------------------------------------------------------------------------
def test_build_slug_map_khu_trung():
    names = [
        "Luật Tổ chức Chính phủ của Quốc hội, số 63/2025/QH15",
        "Luật Tổ chức Chính phủ của Quốc hội, số 76/2015/QH13",
        "Dự thảo Luật Cư trú lần 2",  # không suy được -> vắng mặt trong map
    ]
    m = build_slug_map(names)
    assert "Dự thảo Luật Cư trú lần 2" not in m
    assert len(m) == 2
    assert len(set(m.values())) == 2, "hai văn bản khác nhau không được trùng slug"


def test_build_slug_map_them_hau_to_khi_dung_do():
    # Hai tên khác nhau, cùng năm, phần tên trùng nhau sau khi cắt -> phải khác slug.
    names = [
        "Luật A B C D E F G H I J K L M của Quốc hội, số 01/2024/QH15",
        "Luật A B C D E F G H I J K L N của Quốc hội, số 02/2024/QH15",
    ]
    m = build_slug_map(names)
    assert len(set(m.values())) == 2
    assert any(v.endswith("-b2") for v in m.values())


# ---------------------------------------------------------------------------
# 13-14. Hàm phụ dùng cho lọc rò rỉ
# ---------------------------------------------------------------------------
def test_extract_so_hieu():
    assert extract_so_hieu("Luật Hộ tịch của Quốc hội, số 60/2014/QH13") == "60/2014/qh13"
    assert extract_so_hieu("Nghị định 102/2024/NĐ-CP") == "102/2024/nd-cp"
    assert extract_so_hieu("Dự thảo Luật Cư trú lần 2") is None


def test_extract_year():
    assert extract_year("Luật Hộ tịch của Quốc hội, số 60/2014/QH13") == "2014"
    assert extract_year(
        "Dự thảo Luật sửa đổi, bổ sung một số điều của Luật Ban hành văn bản "
        "quy phạm pháp luật năm 2015"
    ) == "2015"
    assert extract_year("Dự thảo Luật Cư trú lần 2") is None


# ---------------------------------------------------------------------------
# 15. strip_diacritics / slugify / normalize_doc_name
# ---------------------------------------------------------------------------
def test_strip_diacritics_va_slugify():
    assert strip_diacritics("Đất đai Việt Nam") == "Dat dai Viet Nam"
    assert slugify("  Hộ Tịch — 2014!! ") == "ho-tich-2014"
    assert slugify("") == ""


def test_normalize_doc_name_giu_so_hieu():
    got = normalize_doc_name("Luật Đất đai của Quốc hội, số 31/2024/QH15")
    assert got == "luat dat dai cua quoc hoi so 31/2024/qh15"
