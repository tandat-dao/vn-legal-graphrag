"""Test cho module phát hiện thay đổi quy định + điều khoản chuyển tiếp (việc 3)."""
from __future__ import annotations

from src.retrieval.transitional import _khoang_cach_ngay, mo_ta_thay_doi


# ---------------------------------------------------------------------------
# Khoảng cách ngày — dùng để chọn bản kế nhiệm
# ---------------------------------------------------------------------------

def test_khoang_cach_ngay_cung_ngay_bang_khong():
    assert _khoang_cach_ngay("2024-09-30", "2024-09-30") == 0


def test_khoang_cach_ngay_doi_xung():
    assert _khoang_cach_ngay("2024-08-01", "2025-01-01") == \
           _khoang_cach_ngay("2025-01-01", "2024-08-01")


def test_khoang_cach_ngay_thieu_du_lieu_tra_so_lon():
    assert _khoang_cach_ngay(None, "2024-01-01") > 10**8
    assert _khoang_cach_ngay("không-phải-ngày", "2024-01-01") > 10**8


def test_khoang_cach_chon_dung_ban_ke_nhiem():
    """QĐ 18/2016 hết hiệu lực 2024-09-30: QĐ 69/2024 gần hơn QĐ 52/2016 nhiều."""
    het = "2024-09-30"
    assert _khoang_cach_ngay("2024-09-30", het) < _khoang_cach_ngay("2017-01-01", het)


# ---------------------------------------------------------------------------
# Câu mô tả — ranh giới giữa cung cấp thông tin và phán quyết pháp lý
# ---------------------------------------------------------------------------

def _cap_mau():
    return [{
        "cu": "quyet-dinh-18-2016-qd-ubnd-tp-hcm",
        "cu_tu": "2016-05-26", "cu_den": "2024-09-30",
        "moi": "quyet-dinh-69-2024-qd-ubnd-tp-hcm", "moi_tu": "2024-09-30",
    }]


def test_khong_co_cap_thi_khong_no_canh_bao():
    """Cảnh báo nổ ở mọi câu sẽ thành lời rào đón vô nghĩa."""
    assert mo_ta_thay_doi([], False) == ""
    assert mo_ta_thay_doi([], True) == ""


def test_mo_ta_neu_du_ca_hai_van_ban_va_moc_thoi_gian():
    s = mo_ta_thay_doi(_cap_mau(), False)
    assert "quyet-dinh-18-2016-qd-ubnd-tp-hcm" in s
    assert "quyet-dinh-69-2024-qd-ubnd-tp-hcm" in s
    assert "2024-09-30" in s


def test_khong_dung_chu_hoi_to():
    """Hồi tố là nguyên tắc của luật hình sự, không áp cho lĩnh vực hành chính."""
    for co_dk in (True, False):
        assert "hồi tố" not in mo_ta_thay_doi(_cap_mau(), co_dk).lower()


def test_khong_khang_dinh_truong_hop_cua_nguoi_dung():
    """Hệ thống chỉ biết văn bản đã đổi, KHÔNG biết tình tiết vụ việc."""
    s = mo_ta_thay_doi(_cap_mau(), True).lower()
    # không được phán "trường hợp của bạn là ..."
    assert "trường hợp của bạn" not in s
    # phải nói rõ là phụ thuộc tình tiết
    assert "tình tiết" in s


def test_luon_khuyen_hoi_chuyen_gia():
    for co_dk in (True, False):
        assert "chuyên gia pháp lý" in mo_ta_thay_doi(_cap_mau(), co_dk)


def test_nhac_dieu_khoan_chuyen_tiep_chi_khi_tim_duoc():
    co = mo_ta_thay_doi(_cap_mau(), True)
    khong = mo_ta_thay_doi(_cap_mau(), False)
    assert "điều khoản chuyển tiếp" in co
    assert "điều khoản chuyển tiếp" not in khong


def test_thieu_ban_ke_nhiem_van_mo_ta_duoc():
    cap = [{"cu": "x", "cu_tu": "2016-01-01", "cu_den": "2024-09-30",
            "moi": None, "moi_tu": None}]
    s = mo_ta_thay_doi(cap, False)
    assert "x" in s and "2024-09-30" in s
    assert "None" not in s


# ---------------------------------------------------------------------------
# Ưu tiên văn bản cụ thể nhất khi có nhiều thay đổi cùng lúc
# ---------------------------------------------------------------------------

def test_nhieu_cap_thi_bao_them_so_luong():
    cap = [
        {"cu": "qd-18", "cu_tier": 4, "cu_tu": "2016-05-26", "cu_den": "2024-09-30",
         "moi": "qd-69", "moi_tu": "2024-09-30"},
        {"cu": "luat-2013", "cu_tier": 1, "cu_tu": "2014-07-01", "cu_den": "2025-01-01",
         "moi": "luat-2024", "moi_tu": "2024-08-01"},
    ]
    s = mo_ta_thay_doi(cap, False)
    # Nêu cái đầu danh sách (đã sắp theo tầng) và cho biết còn cái khác
    assert "qd-18" in s
    assert "1 văn bản khác" in s


def test_mot_cap_thi_khong_nhac_van_ban_khac():
    s = mo_ta_thay_doi(_cap_mau(), False)
    assert "văn bản khác" not in s


# ---------------------------------------------------------------------------
# Lớp thời gian — mốc quá khứ là ngày SỰ VIỆC hay ngày tra luật?
# ---------------------------------------------------------------------------

def test_hoi_ve_hien_tai_bat_dung_cac_dau_hieu():
    from src.pipeline import _hoi_ve_hien_tai
    assert _hoi_ve_hien_tai("lấn đất từ 2010, nay quy hoạch đã điều chỉnh")
    assert _hoi_ve_hien_tai("sử dụng từ 1990 và hiện có nhà ở")
    assert _hoi_ve_hien_tai("nộp hồ sơ cuối 2024, tới giờ chưa trả kết quả")
    assert not _hoi_ve_hien_tai("Hạn mức giao đất ở tại Củ Chi là bao nhiêu?")
    assert not _hoi_ve_hien_tai("")


def test_cau_hoi_hien_tai_thi_KHONG_lot_theo_moc_qua_khu():
    """V031/V032: mốc 2010/1990 là ngày sự việc — lọc theo đó sẽ loại sạch đáp án."""
    from src.pipeline import ap_dung_lop_thoi_gian
    plan = {"temporal_intent": {"has_temporal_context": True,
                                "case_status": "khac", "temporal_anchor": "2010"}}
    ra = ap_dung_lop_thoi_gian(plan, "lấn đất từ năm 2010, nay quy hoạch đã điều chỉnh")
    assert ra["temporal"] is None


def test_cau_hoi_ve_qua_khu_thi_VAN_lot_chat():
    from src.pipeline import ap_dung_lop_thoi_gian
    plan = {"temporal_intent": {"has_temporal_context": True,
                                "case_status": "khac", "temporal_anchor": "2016"}}
    ra = ap_dung_lop_thoi_gian(plan, "Năm 2016 hạn mức đất ở là bao nhiêu?")
    assert ra["temporal"] == "2016-12-31"


def test_ho_so_do_dang_luon_rong():
    from src.pipeline import ap_dung_lop_thoi_gian
    plan = {"temporal_intent": {"has_temporal_context": True,
                                "case_status": "do-dang", "temporal_anchor": "2024"}}
    assert ap_dung_lop_thoi_gian(plan, "hồ sơ nộp 2024")["temporal"] is None


def test_khong_co_yeu_to_thoi_gian_thi_giu_nguyen():
    from src.pipeline import ap_dung_lop_thoi_gian
    plan = {"temporal_intent": {"has_temporal_context": False}, "temporal": "giu-nguyen"}
    assert ap_dung_lop_thoi_gian(plan, "câu hỏi thường")["temporal"] == "giu-nguyen"
