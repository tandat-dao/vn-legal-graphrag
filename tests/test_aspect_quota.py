"""Test cho hạn ngạch theo khía cạnh bản thể luận (việc 5)."""
from __future__ import annotations

from src.retrieval.semantic_filter import (_ASPECT_BUDGET, _KHIA_CANH_TU_KHOA,
                                           _nhan_dien_khia_canh)


def test_sau_khia_canh_dung_bang_ontology():
    """Danh sách phải khớp core_v1.json — không tự thêm khái niệm mới."""
    import json
    concepts = {c["id"] for c in json.load(
        open("data/ontology/core_v1.json", encoding="utf-8"))["concepts"]}
    assert set(_KHIA_CANH_TU_KHOA) == concepts


def test_nhan_dien_han_muc():
    assert "han-muc" in _nhan_dien_khia_canh(
        "Hạn mức giao đất ở cho cá nhân tối đa bao nhiêu?")


def test_nhan_dien_khau_ngu_met_vuong():
    assert "han-muc" in _nhan_dien_khia_canh("một hộ được tới 300 mét vuông đất ở?")


def test_nhan_dien_le_phi():
    assert "nghia-vu-tai-chinh" in _nhan_dien_khia_canh(
        "Ai phải nộp lệ phí đăng ký và mức lệ phí là bao nhiêu?")


def test_nhan_dien_nhieu_khia_canh_cung_luc():
    kq = _nhan_dien_khia_canh("Điều kiện là gì và hồ sơ gồm những giấy tờ nào?")
    assert {"dieu-kien", "ho-so-giay-to"} <= kq


def test_cau_khong_co_tu_khoa_thi_khong_nhan_dien():
    """Không nhận ra thì cơ chế phải im, không được đoán bừa."""
    assert _nhan_dien_khia_canh("Văn bản này ban hành năm nào?") == set()


def test_khong_phu_thuoc_hoa_thuong():
    a = _nhan_dien_khia_canh("HẠN MỨC giao đất")
    b = _nhan_dien_khia_canh("hạn mức giao đất")
    assert a == b == {"han-muc"}


def test_dau_vao_rong_an_toan():
    assert _nhan_dien_khia_canh("") == set()
    assert _nhan_dien_khia_canh(None) == set()


def test_ngan_sach_nho_hon_so_khia_canh():
    """Hạn ngạch là tái phân bổ chỗ, không được ăn hết top_k."""
    assert 0 < _ASPECT_BUDGET < len(_KHIA_CANH_TU_KHOA)
