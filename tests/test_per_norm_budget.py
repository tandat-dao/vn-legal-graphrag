"""Test cho ngân sách chiều sâu do đồ thị quyết định (việc 2)."""
from __future__ import annotations

from src.retrieval.semantic_filter import _MAX_PER_NORM, _tinh_per_norm


# ---------------------------------------------------------------------------

def test_per_norm_tat_che_do_giu_hang_so_cu():
    assert _tinh_per_norm(25, 10, None) == _MAX_PER_NORM
    assert _tinh_per_norm(25, 2, None) == _MAX_PER_NORM


def test_per_norm_chuoi_hep_duoc_dao_sau():
    assert _tinh_per_norm(25, 2, "graph") > _MAX_PER_NORM
    assert _tinh_per_norm(25, 3, "graph") > _MAX_PER_NORM


def test_per_norm_chuoi_rong_giu_nguyen_hanh_vi_cu():
    """Trung vị 10 văn bản → phải ra đúng 3 như hằng số cũ."""
    assert _tinh_per_norm(25, 10, "graph") == _MAX_PER_NORM
    assert _tinh_per_norm(25, 15, "graph") == _MAX_PER_NORM


def test_per_norm_khong_bao_gio_siet_hon_hien_tai():
    """Bất biến quan trọng: chỉ NỚI, không bao giờ nhỏ hơn hằng số cũ."""
    for so_norm in range(1, 40):
        assert _tinh_per_norm(25, so_norm, "graph") >= _MAX_PER_NORM


def test_per_norm_co_tran_tren():
    from src.retrieval.semantic_filter import _PER_NORM_TRAN
    assert _tinh_per_norm(25, 1, "graph") == _PER_NORM_TRAN


def test_per_norm_so_norm_bang_khong_an_toan():
    assert _tinh_per_norm(25, 0, "graph") == _MAX_PER_NORM
