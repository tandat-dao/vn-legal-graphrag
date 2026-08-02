"""Đối chiếu parser với ĐỊNH DẠNG LOG THẬT của `src/` — rủi ro lớn nhất của luồng `live`.

Máy A không chạy `live` được, nên tới trước buổi bảo vệ vẫn chưa ai thấy
`ui/trace.py` parse log thật. Nếu một regex lệch, bước tương ứng trên UI chỉ hiện
dòng log mờ — và chỉ lộ ra khi máy B chạy, thường là quá muộn.

Tệp này chặn trước: dựng lại **đúng** chuỗi log mà `src/` sinh ra (bám sát f-string
trong code, dùng chính hằng số của `src/`), rồi khẳng định parser trả về đúng bước
và đủ trường mà frontend đọc. Không cần Neo4j/Qdrant/LLM.

Sửa `src/` mà đổi định dạng log → test này đỏ, thay vì demo hỏng âm thầm.
"""
import pytest

from ui.trace import parse_message

# Hằng số thật của src/, để chuỗi log dựng ra không lệch với lúc chạy.
from src.retrieval.semantic_filter import _MAX_PER_NORM, _MAX_PER_TIER


# ---------------------------------------------------------------------------
# Bước 2 — Query Planner
# ---------------------------------------------------------------------------

def test_buoc2_plan():
    step, d = parse_message("src.retrieval.query_planner",
        "plan_query | theme=dat-dai procedure=chuyen-muc-dich-su-dung-dat "
        "jurisdiction=tp-hcm temporal=None temporal_ctx=False")
    assert step == "plan"
    assert d["theme"] == "dat-dai"
    assert d["jurisdiction"] == "tp-hcm"
    assert d["procedure"] == "chuyen-muc-dich-su-dung-dat"


def test_buoc2_temporal():
    step, d = parse_message("src.pipeline",
        "run_pipeline: TEMPORAL MODE — anchor='2025-06-01' status='dang-xu-ly' → point-in-time")
    assert step == "temporal"
    assert d["temporal_anchor"] == "2025-06-01"
    assert d["case_status"] == "dang-xu-ly"
    assert d["reason"] == "point-in-time"


def test_buoc2_cache_hit():
    step, d = parse_message("src.retrieval.query_planner",
                            "plan_query: cache HIT (ab12cd34) — $0 API")
    assert step == "plan" and d["cache_hit"] is True


# ---------------------------------------------------------------------------
# Bước 3 — Stage 1: PHẢI có `ranked` (frontend đọc `d.ranked`)
# ---------------------------------------------------------------------------

def test_buoc3_stage1_co_bang_ranked():
    step, d = parse_message("src.retrieval.subgraph_extractor",
        "Stage 1: top-5 scores=[0.624, 0.518, 0.401, 0.287, 0.203], threshold=0.3 "
        "→ 3 norm_ids = ['luat-dat-dai-2024', 'nghi-dinh-102-2024-nd-cp', "
        "'quyet-dinh-69-2024-qd-ubnd-tp-hcm']")
    assert step == "stage1"
    # Frontend: `if (d.ranked) renderStage1(d)` — thiếu khóa này là bước 3 TRỐNG.
    assert "ranked" in d, "thiếu `ranked` → renderStage1 không chạy, bước 3 trắng"
    assert d["top_n"] == 5 and d["threshold"] == 0.3 and d["n_norms"] == 3
    assert len(d["ranked"]) == 5, "phải liệt kê CẢ norm bị loại để thấy ngưỡng cắt ở đâu"

    giu = [r for r in d["ranked"] if r["chon"]]
    loai = [r for r in d["ranked"] if not r["chon"]]
    assert len(giu) == 3 and len(loai) == 2
    assert giu[0]["norm_id"] == "luat-dat-dai-2024" and giu[0]["score"] == 0.624
    assert all(r["norm_id"] is None for r in loai)
    # score giảm dần theo rank
    diem = [r["score"] for r in d["ranked"]]
    assert diem == sorted(diem, reverse=True)


def test_buoc3_stage1_no_theme_ablation():
    step, d = parse_message("src.retrieval.subgraph_extractor",
        "Stage 1 [no-theme]: 2 norm_ids = ['luat-dat-dai-2024', 'luat-dat-dai-2013']")
    assert step == "stage1"
    assert d["no_theme"] is True
    assert len(d["ranked"]) == 2 and all(r["chon"] for r in d["ranked"])


# ---------------------------------------------------------------------------
# Bước 4 — Stage 2
# ---------------------------------------------------------------------------

def test_buoc4_stage2_norm_ids():
    step, d = parse_message("src.retrieval.subgraph_extractor",
        "Stage 2 (norm_ids): 5 norms (jurisdiction=tp-hcm, temporal=None): "
        "['luat-dat-dai-2024', 'nghi-dinh-102-2024-nd-cp']")
    assert step == "stage2"
    # Frontend: `if (d.norm_ids) renderStage2(d)` → thiếu là bước 4 + đồ thị trống.
    assert d["norm_ids"] == ["luat-dat-dai-2024", "nghi-dinh-102-2024-nd-cp"]
    assert d["n_norms"] == 5 and d["jurisdiction"] == "tp-hcm"


# ---------------------------------------------------------------------------
# Bước 5 — Stage 3
# ---------------------------------------------------------------------------

def test_buoc5_stage3():
    step, d = parse_message("src.retrieval.subgraph_extractor",
        "Stage 3: 42 graph_component_ids mapped for procedure chuyen-muc-dich-su-dung-dat")
    assert step == "stage3"
    assert d["n_components"] == 42
    assert d["procedure"] == "chuyen-muc-dich-su-dung-dat"


def test_buoc5_tong_vao_hybrid():
    step, d = parse_message("src.pipeline",
        "run_pipeline: 5 norm_ids, 42 graph_comp_ids từ Stage 2+3")
    assert step == "stage3"
    assert d["n_norm_ids"] == 5 and d["n_graph_comp_ids"] == 42


# ---------------------------------------------------------------------------
# Bước 6 — Hybrid search + Context
# ---------------------------------------------------------------------------

def _log_hybrid() -> str:
    """Dựng ĐÚNG f-string của `semantic_filter.hybrid_search`, dùng hằng số thật."""
    return (
        "hybrid_search: top-25 | pass-1(struct-cite)=2, "
        "pass-0.5(label-keyword)=0, pass0(dense-floor)=9, "
        "pass1(rrf-breadth)=6, "
        "pass2(depth)=8 | "
        f"caps: per_norm={_MAX_PER_NORM}, per_tier={_MAX_PER_TIER} | "
        "best rrf=0.0328 | tier_dist={1: 10, 2: 8, 4: 7} | "
        "norm_dist={'luat-dat-dai-2024': 10, 'nghi-dinh-102-2024-nd-cp': 8}"
    )


def test_buoc6_phan_bo_pass():
    step, d = parse_message("src.retrieval.semantic_filter", _log_hybrid())
    assert step == "hybrid"
    # Frontend: `if (h.passes)` mới vẽ dải phân bổ pass.
    assert "passes" in d, "thiếu `passes` → bước 6 mất dải phân bổ 4 pass"
    assert d["passes"] == {"struct_cite": 2, "label_keyword": 0,
                           "dense_floor": 9, "rrf_breadth": 6, "depth": 8}
    assert sum(d["passes"].values()) == d["top_k"] == 25
    assert d["caps"]["per_norm"] == _MAX_PER_NORM
    assert d["best_rrf"] == 0.0328
    assert d["tier_dist"] and d["norm_dist"]


def test_buoc6_ung_vien_dau_vao():
    step, d = parse_message("src.retrieval.semantic_filter",
                            "hybrid_search: dense=50, keyword=12, graph=42 candidates")
    assert step == "hybrid"
    assert (d["dense"], d["keyword"], d["graph"]) == (50, 12, 42)


def test_buoc6_token_budget():
    step, d = parse_message("src.retrieval.context_assembler",
                            "assemble_context: 25 blocks, ~2180 tokens")
    assert step == "context"
    assert d["n_blocks"] == 25 and d["tokens"] == 2180

    step, d = parse_message("src.retrieval.context_assembler",
                            "assemble_context: dừng tại 25 blocks (5980/6000 tokens)")
    assert step == "context"
    assert d["bi_cat"] is True and d["max_tokens"] == 6000


# ---------------------------------------------------------------------------
# Bước 7 — Câu trả lời + Verifier
# ---------------------------------------------------------------------------

def test_buoc7_generate():
    step, d = parse_message("src.retrieval.answer_generator",
        "generate_answer: 1348 chars, 4 citations, "
        "sections={'tra_loi': True, 'can_cu': True, 'luu_y': False}")
    assert step == "generate"
    assert d["n_chars"] == 1348 and d["n_citations"] == 4
    assert d["sections"]["tra_loi"] is True and d["sections"]["luu_y"] is False


def test_buoc7_generate_cache_hit():
    step, d = parse_message("src.retrieval.answer_generator",
                            "generate_answer: cache HIT (ab12cd34) — $0 API")
    assert step == "generate" and d["cache_hit"] is True


@pytest.mark.parametrize("mod,msg", [
    ("src.retrieval.verifier", "verify_citations: tier=1 in=6 kept=4 dropped=2 flagged=0"),
    ("src.pipeline", "run_pipeline: verifier tier=1 6→4 citations (drop 2, flag 0)"),
])
def test_buoc7_verifier(mod, msg):
    """Bật checkbox Verifier ở UI thì hai dòng này mới xuất hiện — cả hai phải parse."""
    step, d = parse_message(mod, msg)
    assert step == "verify"
    assert d["tier"] == 1 and d["n_input"] == 6 and d["n_kept"] == 4
    assert d["n_dropped"] == 2 and d["n_flagged"] == 0


def test_buoc7_hoan_thanh():
    step, d = parse_message("src.pipeline",
                            "run_pipeline: hoàn thành trong 18.7s — 4 citations")
    assert step == "done"
    assert d["elapsed_seconds"] == 18.7 and d["n_citations"] == 4


# ---------------------------------------------------------------------------
# Ba tùy chọn trên UI phải để lại dấu vết trong trace
# ---------------------------------------------------------------------------

def test_ep_jurisdiction_hien_ra_trace():
    step, d = parse_message("src.pipeline",
                            "run_pipeline: force_jurisdiction='dong-nai' áp dụng")
    assert step == "plan"
    assert d["force_jurisdiction"] == "dong-nai" and d["ap_dung"] is True


def test_response_mode_hien_ra_trace():
    step, d = parse_message("src.pipeline", "run_pipeline: response_mode='irac'")
    assert step == "plan" and d["response_mode"] == "irac"


# ---------------------------------------------------------------------------
# Toàn cảnh: đủ 7 bước
# ---------------------------------------------------------------------------

def test_mot_luot_chay_phu_du_7_buoc():
    """Chuỗi log của một lượt `live` điển hình phải phủ hết 7 bước hiển thị."""
    luot = [
        ("src.pipeline", "run_pipeline: plan_query cho 'Hạn mức giao đất ở...'"),
        ("src.retrieval.query_planner",
         "plan_query | theme=dat-dai procedure=chuyen-muc-dich-su-dung-dat "
         "jurisdiction=tp-hcm temporal=None temporal_ctx=False"),
        ("src.pipeline", "run_pipeline: plan=dat-dai/tp-hcm"),
        ("src.retrieval.subgraph_extractor",
         "Stage 1: top-5 scores=[0.624, 0.518, 0.401], threshold=0.3 "
         "→ 2 norm_ids = ['luat-dat-dai-2024', 'nghi-dinh-102-2024-nd-cp']"),
        ("src.retrieval.subgraph_extractor",
         "Stage 2 (norm_ids): 5 norms (jurisdiction=tp-hcm, temporal=None): "
         "['luat-dat-dai-2024']"),
        ("src.retrieval.subgraph_extractor",
         "Stage 3: 42 graph_component_ids mapped for procedure chuyen-muc-dich-su-dung-dat"),
        ("src.retrieval.semantic_filter", _log_hybrid()),
        ("src.retrieval.context_assembler", "assemble_context: 25 blocks, ~2180 tokens"),
        ("src.retrieval.answer_generator",
         "generate_answer: 1348 chars, 4 citations, sections={'tra_loi': True}"),
        ("src.pipeline", "run_pipeline: hoàn thành trong 18.7s — 4 citations"),
    ]
    buoc = {parse_message(m, s)[0] for m, s in luot}
    for can in ("plan", "stage1", "stage2", "stage3", "hybrid", "context", "generate", "done"):
        assert can in buoc, f"không dòng log nào cho bước {can}: {sorted(buoc)}"
    # và không dòng nào bị bỏ sót
    assert all(parse_message(m, s)[0] for m, s in luot)
