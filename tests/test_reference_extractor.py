"""Test cho reference_extractor — trích và giải chiếu dẫn chiếu cấp điều khoản."""
from __future__ import annotations

import src.ingestion.reference_extractor as R


# ---------------------------------------------------------------------------
# Chuẩn hoá tên văn bản
# ---------------------------------------------------------------------------

def test_chuan_hoa_ten_bo_nam_va_ngoac():
    assert R._chuan_hoa_ten("Luật Đất đai 2013") == "luật đất đai"
    assert R._chuan_hoa_ten("Luật Đất đai (Luật số 31/2024/QH15)") == "luật đất đai"
    assert R._chuan_hoa_ten("  Luật   Hộ Tịch  ") == "luật hộ tịch"


def test_chuan_hoa_so_hieu():
    assert R._chuan_hoa_so_hieu(" 31/2024/qh15 ") == "31/2024/QH15"


# ---------------------------------------------------------------------------
# Tách danh sách địa chỉ
# ---------------------------------------------------------------------------

def test_tach_danh_sach():
    assert R._tach_danh_sach("1, 2 và 3") == ["1", "2", "3"]
    assert R._tach_danh_sach("100") == ["100"]
    assert R._tach_danh_sach(None) == []


# ---------------------------------------------------------------------------
# Phân giải văn bản theo thời điểm — cùng một tên, hai bản qua các năm
# ---------------------------------------------------------------------------

def _idx_hai_ban_dat_dai():
    return {
        "luat-dat-dai-2013": R.NormIndex(
            norm_id="luat-dat-dai-2013", so_hieu="45/2013/QH13",
            title="Luật Đất đai 2013", valid_from="2014-07-01",
        ),
        "luat-dat-dai-2024": R.NormIndex(
            norm_id="luat-dat-dai-2024", so_hieu="31/2024/QH15",
            title="Luật Đất đai", valid_from="2024-08-01",
        ),
    }


def test_chon_theo_thoi_diem_van_ban_cu_tro_ban_cu():
    idx = _idx_hai_ban_dat_dai()
    ung_vien = ["luat-dat-dai-2013", "luat-dat-dai-2024"]
    # Quyết định 2016 dẫn "của Luật Đất đai" → phải là bản 2013
    assert R._chon_theo_thoi_diem(ung_vien, idx, "2016-05-26") == "luat-dat-dai-2013"


def test_chon_theo_thoi_diem_van_ban_moi_tro_ban_moi():
    idx = _idx_hai_ban_dat_dai()
    ung_vien = ["luat-dat-dai-2013", "luat-dat-dai-2024"]
    assert R._chon_theo_thoi_diem(ung_vien, idx, "2026-01-31") == "luat-dat-dai-2024"


def test_chon_theo_thoi_diem_mot_ung_vien_thi_tra_luon():
    idx = _idx_hai_ban_dat_dai()
    assert R._chon_theo_thoi_diem(["luat-dat-dai-2024"], idx, "") == "luat-dat-dai-2024"


def test_lexicon_gop_hai_ban_cung_ten():
    lex = R.build_name_lexicon(_idx_hai_ban_dat_dai())
    assert set(lex["luật đất đai"]) == {"luat-dat-dai-2013", "luat-dat-dai-2024"}


# ---------------------------------------------------------------------------
# Xác định phạm vi dẫn chiếu
# ---------------------------------------------------------------------------

def test_pham_vi_cua_luat_nay_la_noi_bo():
    loai, dich, _ = R._xac_dinh_pham_vi(
        " của Luật này", "luat-dat-dai-2024", {}, {}, {}
    )
    assert (loai, dich) == ("noi_bo", "luat-dat-dai-2024")


def test_pham_vi_khong_co_chi_dau_mac_dinh_noi_bo():
    """Quy ước soạn thảo QPPL: 'Điều 7' trơn = cùng văn bản."""
    loai, dich, _ = R._xac_dinh_pham_vi(
        " thì cơ quan có thẩm quyền", "nghi-dinh-102-2024-nd-cp", {}, {}, {}
    )
    assert (loai, dich) == ("noi_bo", "nghi-dinh-102-2024-nd-cp")


def test_pham_vi_tra_theo_so_hieu():
    so_hieu_map = {"71/2024/NĐ-CP": "nghi-dinh-71-2024-nd-cp"}
    loai, dich, _ = R._xac_dinh_pham_vi(
        " của Nghị định số 71/2024/NĐ-CP", "x", so_hieu_map, {}, {}
    )
    assert (loai, dich) == ("lien_van_ban", "nghi-dinh-71-2024-nd-cp")


def test_pham_vi_so_hieu_ngoai_kho_bao_ly_do():
    loai, dich, ly_do = R._xac_dinh_pham_vi(
        " của Nghị định số 999/2099/NĐ-CP", "x", {}, {}, {}
    )
    assert loai == "lien_van_ban" and dich is None
    assert "ngoài kho" in ly_do


def test_pham_vi_theo_ten_dung_phan_giai_thoi_diem():
    idx = _idx_hai_ban_dat_dai()
    lex = R.build_name_lexicon(idx)
    # Nguồn là văn bản 2013 → "của Luật Đất đai" phải trỏ bản 2013
    idx["quyet-dinh-cu"] = R.NormIndex(
        norm_id="quyet-dinh-cu", so_hieu="18/2016/QĐ-UBND",
        title="Quyết định 18/2016", valid_from="2016-05-26",
    )
    loai, dich, _ = R._xac_dinh_pham_vi(
        " của Luật Đất đai thì", "quyet-dinh-cu", {}, idx, lex
    )
    assert (loai, dich) == ("lien_van_ban", "luat-dat-dai-2013")


# ---------------------------------------------------------------------------
# Trích dẫn chiếu từ một dòng — các bẫy
# ---------------------------------------------------------------------------

def _trich(text: str, norm_id: str = "n1"):
    return R._extract_from_line(text, norm_id, [norm_id, "Điều 1."], {}, {}, {})


def test_khong_bat_nham_cum_dieu_kien():
    """'các điều kiện sau đây' KHÔNG phải dẫn chiếu — phải có CHỮ SỐ sau 'điều'."""
    refs = _trich("Người sử dụng đất phải đáp ứng các điều kiện sau đây:")
    assert [r for r in refs if r.loai != "tu_than"] == []


def test_bat_dan_chieu_don_gian():
    refs = [r for r in _trich("theo quy định tại Điều 137 của Luật này")
            if r.loai != "tu_than"]
    assert len(refs) == 1
    assert refs[0].dich_dieu == "137" and refs[0].loai == "noi_bo"


def test_bat_khoan_va_dieu():
    refs = [r for r in _trich("quy định tại khoản 2 Điều 143 của Luật này")
            if r.loai != "tu_than"]
    assert len(refs) == 1
    assert (refs[0].dich_dieu, refs[0].dich_khoan) == ("143", "2")


def test_bat_danh_sach_nhieu_dieu():
    refs = [r for r in _trich("quy định tại các điều 100, 101 và 102 của Luật này")
            if r.loai != "tu_than"]
    assert sorted(r.dich_dieu for r in refs) == ["100", "101", "102"]


def test_bat_danh_sach_nhieu_khoan_cung_dieu():
    refs = [r for r in _trich("tại các khoản 1, 2 và 3 Điều 100 của Luật này")
            if r.loai != "tu_than"]
    assert {r.dich_khoan for r in refs} == {"1", "2", "3"}
    assert {r.dich_dieu for r in refs} == {"100"}


def test_tu_tham_chieu_duoc_danh_dau_rieng():
    refs = _trich("quy định tại khoản 7 Điều này")
    assert any(r.loai == "tu_than" for r in refs)


def test_bo_qua_html_comment():
    """Địa chỉ trong annotation amended_by trỏ vào VĂN BẢN SỬA, không phải dẫn chiếu."""
    import tempfile, os, textwrap
    noi_dung = textwrap.dedent("""\
        ---
        id: "n-test"
        title: "Văn bản thử"
        valid_from: "2024-01-01"
        ---

        ## Điều 1. Thử

        ### Khoản 1.

        Nội dung không có dẫn chiếu nào.
        <!-- amended_by: 49/2026/NĐ-CP, khoản 1 Điều 13, hiệu lực: 31/01/2026, nội dung: sửa -->
        """)
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "n-test.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write(noi_dung)
        idx, shm = R.build_norm_index(d)
        refs = R.extract_from_file(p, idx, shm)
    # "khoản 1 Điều 13" nằm trong comment → không được tính
    assert [r for r in refs if r.dich_dieu == "13"] == []


# ---------------------------------------------------------------------------
# Dẫn chiếu KHOẢN/ĐIỂM ANH EM — "khoản 1 và khoản 2 Điều này"
# ---------------------------------------------------------------------------

def _trich_ngu_canh(text, dieu="9", khoan=None):
    return R._extract_from_line(text, "n1", ["n1", "Điều %s." % dieu], {}, {}, {},
                                (dieu, khoan))


def test_khoan_anh_em_khong_phai_tu_tham_chieu():
    """'khoản 1 và khoản 2 Điều này' trỏ sang khoản KHÁC, không phải tự trỏ."""
    refs = [r for r in _trich_ngu_canh(
        "không có giấy tờ quy định tại khoản 1 và khoản 2 Điều này thì")
        if r.loai != "tu_than"]
    assert {r.dich_khoan for r in refs} == {"1", "2"}
    assert all(r.dich_dieu == "9" for r in refs)


def test_khoan_anh_em_dang_rut_gon():
    refs = [r for r in _trich_ngu_canh("quy định tại khoản 1, 2 và 3 Điều này")
            if r.loai != "tu_than"]
    assert {r.dich_khoan for r in refs} == {"1", "2", "3"}


def test_khoan_anh_em_don_le():
    refs = [r for r in _trich_ngu_canh("theo khoản 4 Điều này")
            if r.loai != "tu_than"]
    assert [r.dich_khoan for r in refs] == ["4"]


def test_diem_anh_em_trong_cung_khoan():
    refs = [r for r in _trich_ngu_canh("quy định tại điểm a và điểm b khoản này",
                                       dieu="9", khoan="3")
            if r.loai != "tu_than"]
    assert {r.dich_diem for r in refs} == {"a", "b"}
    assert all(r.dich_khoan == "3" for r in refs)


def test_dieu_nay_tron_van_la_tu_tham_chieu():
    """'Điều này' đứng một mình KHÔNG tạo cạnh."""
    refs = _trich_ngu_canh("theo quy định tại Điều này")
    assert all(r.loai == "tu_than" or r.dich_khoan is None for r in refs)


def test_khong_co_ngu_canh_thi_bo_qua():
    """Không biết đang ở Điều nào thì không đoán bừa."""
    refs = [r for r in R._extract_from_line(
        "quy định tại khoản 1 Điều này", "n1", ["n1"], {}, {}, {}, (None, None))
        if r.loai != "tu_than"]
    assert refs == []


def test_tach_danh_sach_bo_tu_khoa_lap():
    assert R._tach_danh_sach("1 và khoản 2") == ["1", "2"]
    assert R._tach_danh_sach("a, điểm b") == ["a", "b"]
