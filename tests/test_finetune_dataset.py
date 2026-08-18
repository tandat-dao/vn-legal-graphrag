"""Test cho finetune/build_dataset.py (TASK-FT-04).

Trọng tâm là DoD 2 và DoD 3 — hai thứ mà sai thì cả 5 000 mẫu vô dụng:

    DoD 2  0 mẫu còn khớp danh sách chặn
    DoD 3  100% khối trích dẫn parse được bằng CHÍNH `parse_citations`, VÀ
           round-trip đúng về (Điều, Khoản, Điểm, slug) đã dùng để dựng

Không tải bộ dữ liệu HuggingFace ở đây: các test dưới chạy trên `Article` dựng
tay nên nhanh và tất định. Test cuối đọc file jsonl thật NẾU đã sinh (bỏ qua
nếu chưa) — đó mới là phép kiểm trên đúng bộ sẽ đem đi huấn luyện.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from finetune.build_dataset import (
    OUT_DIR,
    REFUSAL_NO_BASIS,
    REFUSAL_OUT_OF_SCOPE,
    Article,
    da_dang_hoa_mo_dau,
    doc_bi_ro_ri,
    dung_answer,
    fmt_citation,
    load_blocklist,
    load_test_question_ngrams,
    pack_baseline,
    pack_graphrag,
    parse_article,
    question_bi_ro_ri,
    suy_citation,
)
from src.retrieval.answer_generator import parse_citations
from src.retrieval.context_assembler import build_messages

RAW = (
    "Điều 12. Mức thu phí\n\n"
    "1. Mức thu áp dụng cho cá nhân là 20.000 đồng một lần.\n\n"
    "a) Trường hợp nộp trực tiếp: 20.000 đồng.\n\n"
    "b) Trường hợp nộp trực tuyến: 10.000 đồng.\n\n"
    "2. Mức thu áp dụng cho tổ chức là 50.000 đồng một lần.\n\n"
    "3. Cơ quan thu phí có trách nhiệm niêm yết công khai mức thu.\n"
)


def _art(dieu: str = "12", slug: str = "luat-vi-du-2019") -> Article:
    art = parse_article("Luật Ví dụ của Quốc hội, số 01/2019/QH14", slug,
                        RAW.replace("Điều 12.", f"Điều {dieu}."))
    assert art is not None
    return art


# ---------------------------------------------------------------------------
# Phân rã Điều / Khoản / Điểm
# ---------------------------------------------------------------------------
def test_parse_article():
    art = _art()
    assert art.dieu == "12"
    assert art.tieu_de == "Mức thu phí"
    assert art.khoan_set == {"1", "2", "3"}
    diem_map = next(d for k, _, d in art.khoan if k == "1")
    assert set(diem_map) == {"a", "b"}


def test_parse_article_khong_bat_dau_bang_dieu():
    assert parse_article("d", "s", "1. Nội dung nào đó không có tiêu đề Điều.") is None


# ---------------------------------------------------------------------------
# DoD 3 — cú pháp khối trích dẫn, round-trip qua parse_citations THẬT
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "cit, chuoi",
    [
        ({"dieu": "5", "khoan": None, "diem": None, "tiet": None,
          "van_ban": "luat-vi-du-2019", "loai": "dieu"},
         "[Điều 5, Văn bản luat-vi-du-2019]"),
        ({"dieu": "12", "khoan": "1", "diem": None, "tiet": None,
          "van_ban": "luat-vi-du-2019", "loai": "dieu"},
         "[Điều 12, Khoản 1, Văn bản luat-vi-du-2019]"),
        ({"dieu": "12", "khoan": "1", "diem": "b", "tiet": None,
          "van_ban": "nghi-dinh-vi-du-2021-nd-cp", "loai": "dieu"},
         "[Điều 12, Khoản 1, Điểm b, Văn bản nghi-dinh-vi-du-2021-nd-cp]"),
    ],
)
def test_fmt_citation_dung_cu_phap_va_round_trip(cit, chuoi):
    assert fmt_citation(cit) == chuoi
    assert parse_citations(chuoi) == [cit]


def test_khong_dung_tiet_va_muc_dong_phan():
    """`Tiết` không xuất hiện ở 0/401 khối thật; `Mục`/`Dòng`/`Phần` bị parser bỏ
    qua IM LẶNG (ca thật V119/V131) nên tuyệt đối không được sinh ra."""
    cit = {"dieu": "12", "khoan": "1", "diem": "b", "tiet": None,
           "van_ban": "luat-vi-du-2019", "loai": "dieu"}
    s = fmt_citation(cit)
    for cam in ("Tiết", "Mục", "Dòng", "Phần"):
        assert cam not in s


def test_dung_answer_round_trip():
    art = _art()
    cits = suy_citation("Theo Khoản 1 Điều 12 Luật Ví dụ, mức thu là 20.000 đồng.", art)
    ans = dung_answer("Theo Khoản 1 Điều 12 Luật Ví dụ, mức thu là 20.000 đồng.",
                      cits, random.Random(0))
    assert parse_citations(ans) == cits
    assert ans.endswith("].")


def test_dung_answer_hai_citation_khong_bi_dedupe():
    art = _art()
    prose = "Khoản 1 Điều 12 quy định mức cá nhân, còn Khoản 2 Điều 12 quy định mức tổ chức."
    cits = suy_citation(prose, art)
    assert len(cits) == 2
    ans = dung_answer(prose, cits, random.Random(1))
    assert parse_citations(ans) == cits  # hai khối khác nhau -> dedupe không nuốt


# ---------------------------------------------------------------------------
# Suy Điều / Khoản / Điểm — "không suy được thì giữ ở cấp Điều, đừng bịa"
# ---------------------------------------------------------------------------
def test_suy_citation_khong_co_khoan_thi_giu_cap_dieu():
    art = _art()
    cits = suy_citation("Điều 12 quy định về mức thu phí nói chung.", art)
    assert cits == [{"dieu": "12", "khoan": None, "diem": None, "tiet": None,
                     "van_ban": "luat-vi-du-2019", "loai": "dieu"}]


def test_suy_citation_bo_khoan_khong_ton_tai():
    art = _art()
    cits = suy_citation("Theo Khoản 9 Điều 12, mức thu là …", art)  # Điều 12 không có Khoản 9
    assert cits[0]["khoan"] is None


def test_suy_citation_dieu_lech_thi_bo_han_mau():
    art = _art()
    assert suy_citation("Theo Khoản 1 Điều 99, quy định như sau …", art) is None


def test_suy_citation_diem_chi_gan_khi_khong_mo_ho():
    art = _art()
    # đúng một Khoản + một Điểm có thật -> gán Điểm
    assert suy_citation("Điểm b Khoản 1 Điều 12 quy định 10.000 đồng.", art)[0]["diem"] == "b"
    # hai Khoản -> Điểm mơ hồ, không gán
    hai = suy_citation("Khoản 1 và Khoản 2 Điều 12, xem thêm điểm b.", art)
    assert all(c["diem"] is None for c in hai)


# ---------------------------------------------------------------------------
# DoD 2 — lọc rò rỉ
# ---------------------------------------------------------------------------
def test_blocklist_phu_het_van_ban_corpus():
    """Blocklist chống rò rỉ phải phủ MỌI văn bản trong data/raw/.

    Trước đây chốt cứng `== 32`; corpus mở rộng (thêm lĩnh vực lao động) làm test
    đỏ dù blocklist chạy đúng — phủ NHIỀU hơn là tốt hơn. Nay suy số lượng từ
    chính corpus để không phải sửa test mỗi lần thêm văn bản.
    """
    from finetune.build_dataset import RAW_DIR

    so_van_ban = sum(1 for p in RAW_DIR.glob("*.md")
                     if p.read_text(encoding="utf-8").startswith("---"))
    names, so_hieu, rows = load_blocklist()
    assert len(rows) == so_van_ban
    assert len(rows) >= 32, "corpus không được nhỏ đi so với mốc 32 văn bản"
    assert so_hieu, "phải bắt được số hiệu từ title"
    assert any("dat dai" in n for n in names)


@pytest.mark.parametrize(
    "doc_name",
    [
        "Luật Hộ tịch của Quốc hội, số 60/2014/QH13",
        "Luật Nuôi con nuôi của Quốc hội, số 52/2010/QH12",
        "Luật sửa đổi, bổ sung một số điều của Luật Đất đai số 31/2024/QH15, "
        "Luật Nhà ở số 27/2023/QH15, Luật Kinh doanh bất động sản số 29/2023/QH15 "
        "và Luật Các tổ chức tín dụng số 32/2024/QH15 của Quốc hội, số 43/2024/QH15",
    ],
)
def test_ro_ri_bi_chan(doc_name):
    names, so_hieu, _ = load_blocklist()
    assert doc_bi_ro_ri(doc_name, names, so_hieu) is not None


def test_van_ban_sach_khong_bi_chan_oan():
    names, so_hieu, _ = load_blocklist()
    assert doc_bi_ro_ri("Luật Địa chất và Khoáng sản của Quốc hội, số 54/2024/QH15",
                        names, so_hieu) is None


def test_cau_hoi_trung_test_set_bi_chan():
    grams, tokens = load_test_question_ngrams()
    q = json.loads(Path("data/evaluation/test_set_v2.json").read_text(encoding="utf-8"))[0]
    assert question_bi_ro_ri(q["question"], grams, tokens) is not None
    assert question_bi_ro_ri(
        "Khoáng sản nhóm II bao gồm những loại vật liệu nào?", grams, tokens
    ) is None


def test_loc_5_gram_co_y_bao_thu():
    """5-gram bắt cả cụm rập khuôn ("cơ quan nào có thẩm quyền", "mức thu phí thẩm
    định hồ sơ") nên drop cả câu hỏi thực ra độc lập. Chấp nhận: pool còn 16 962
    cặp QA cho 4 000 mẫu trả lời được, mất dữ liệu rẻ hơn nhiều so với rò rỉ."""
    grams, tokens = load_test_question_ngrams()
    assert question_bi_ro_ri(
        "Cơ quan nào có thẩm quyền phân nhóm khoáng sản theo mục đích quản lý?",
        grams, tokens,
    ) == "trung 5-gram voi test_set_v2"


# ---------------------------------------------------------------------------
# Hai khuôn header — phải khớp NGUYÊN VĂN api_contract.md §6
# ---------------------------------------------------------------------------
def test_khuon_header_graphrag():
    arts = [_art("12"), _art("13"), _art("14"), _art("15")]
    ctx, n = pack_graphrag(arts, 0, 2019, 40_000, random.Random(3))
    assert n > 0
    dong = ctx.split("\n")[0]
    assert dong.startswith("--- [Tier 1 | Hiệu lực: 2019-01-01] Điều 12. Mức thu phí, Khoản 1.")
    assert dong.endswith("(luat-vi-du-2019) ---")


def test_khuon_header_baseline():
    arts = [_art("12"), _art("13"), _art("14"), _art("15")]
    ctx, n = pack_baseline(arts, 0, "1", 6_000, random.Random(3))
    assert n > 0
    assert ctx.startswith("--- Văn bản: luat-vi-du-2019, chunk ")
    # slug đứng SAU "Văn bản: ", không nằm trong ngoặc đơn như khuôn GraphRAG
    assert "(luat-vi-du-2019)" not in ctx


# ---------------------------------------------------------------------------
# Hai chuỗi từ chối phải NGUYÊN VĂN như trong system prompt
# ---------------------------------------------------------------------------
def test_chuoi_tu_choi_nguyen_van_trong_system_prompt():
    system, _ = build_messages("q", "c", "general")
    assert REFUSAL_OUT_OF_SCOPE in system, "chuỗi rào phạm vi corpus phải khớp prompt"
    assert REFUSAL_NO_BASIS in system, "chuỗi thiếu căn cứ phải khớp prompt"


def test_khong_dung_hang_so_nhanh_truy_hoi_rong():
    """`pipeline.py:233` là nhánh truy hồi RỖNG — mô hình sinh chưa từng được gọi
    (api_contract.md §7.1). Khác ca, không được dạy."""
    cam = "Không tìm thấy văn bản pháp luật liên quan đến câu hỏi này."
    assert REFUSAL_NO_BASIS != cam
    assert REFUSAL_OUT_OF_SCOPE != cam


# ---------------------------------------------------------------------------
# Đa dạng hoá câu mở đầu
# ---------------------------------------------------------------------------
def test_da_dang_hoa_mo_dau():
    prose = "Theo Khoản 1 Điều 12 Luật Ví dụ, mức thu áp dụng cho cá nhân là 20.000 đồng."
    ket_qua = {da_dang_hoa_mo_dau(prose, random.Random(i)) for i in range(40)}
    assert len(ket_qua) > 1, "phải sinh ra nhiều hơn một kiểu mở đầu"
    for k in ket_qua:
        assert k.strip()
        assert "20.000 đồng" in k, "phần nội dung không được mất"


def test_da_dang_hoa_mo_dau_giu_nguyen_khi_khong_khop():
    prose = "Mức thu áp dụng cho cá nhân là 20.000 đồng."
    for i in range(10):
        assert da_dang_hoa_mo_dau(prose, random.Random(i)) == prose


# ---------------------------------------------------------------------------
# Kiểm trên file thật (bỏ qua nếu chưa sinh)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("ten", ["train", "val"])
def test_file_da_sinh(ten):
    path = OUT_DIR / f"{ten}.jsonl"
    meta_path = OUT_DIR / f"{ten}_meta.jsonl"
    if not path.exists():
        pytest.skip("chưa chạy `python -m finetune.build_dataset`")

    names, so_hieu, _ = load_blocklist()
    system_ref, _ = build_messages("q", "c", "general")
    n_ok = 0
    with path.open(encoding="utf-8") as f, meta_path.open(encoding="utf-8") as g:
        for line, mline in zip(f, g):
            rec, meta = json.loads(line), json.loads(mline)
            # Đúng khoá `messages` mà finetune/train_qlora.py:80 nhận diện —
            # khoá khác thì load_rows raise ValueError.
            assert set(rec) == {"messages"}
            assert [m["role"] for m in rec["messages"]] == ["system", "user", "assistant"]
            system, user, assistant = (m["content"] for m in rec["messages"])
            # system prompt trùng khít cái lúc đánh giá
            assert system == system_ref
            # DoD 2
            assert doc_bi_ro_ri(meta["doc_name"], names, so_hieu) is None
            # DoD 3
            got = parse_citations(assistant)
            assert got == meta["citations"], meta["sample_id"]
            if meta["kind"] == "answerable":
                assert got
                for c in got:
                    assert f"Văn bản {c['van_ban']}" in assistant
                    assert c["van_ban"] in user
            else:
                assert got == []
            n_ok += 1
    assert n_ok > 0


def test_dinh_dang_khop_train_qlora_load_rows():
    """`load_rows` của train_qlora.py chỉ nhận `messages` hoặc ba trường rời;
    khoá khác → ValueError. Test này chốt hợp đồng đó bằng chính logic của nó."""
    from finetune.build_dataset import Sample, to_record

    rec = to_record(Sample(
        sample_id="FT00000", doc_name="d", slug="luat-vi-du-2019",
        header_format="graphrag", kind="answerable", question="q", context="c",
        answer="a [Điều 1, Văn bản luat-vi-du-2019].", citations=[], n_blocks=1,
    ))
    assert "messages" in rec, "train_qlora.py:80 kiểm đúng khoá này"
    assert [m["role"] for m in rec["messages"]] == ["system", "user", "assistant"]
