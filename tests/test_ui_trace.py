"""Unit test cho `ui/trace.py` — Task 2 của `ui/docs/UI_DEMO_SPEC.md`.

Mọi chuỗi log / context trong file này viết tay THEO ĐÚNG format sinh ra bởi
`src/` (spec mục 5.1 và 5.2). Không cần Neo4j, Qdrant hay LLM.
"""
import logging

from ui.trace import (
    ContextBlock,
    TraceCollector,
    link_citations,
    pair_stage1,
    parse_context,
    parse_label,
    parse_message,
    parse_vi_tri,
)


# ---------------------------------------------------------------------------
# parse_message — Query planner + temporal
# ---------------------------------------------------------------------------

def test_parse_plan():
    step, data = parse_message("src.pipeline", "run_pipeline: plan=dat-dai/tp-hcm")
    assert step == "plan"
    assert data == {"theme": "dat-dai", "jurisdiction": "tp-hcm"}


def test_parse_plan_jurisdiction_none():
    step, data = parse_message("src.pipeline", "run_pipeline: plan=dat-dai/None")
    assert step == "plan"
    assert data["jurisdiction"] is None


def test_parse_response_mode():
    step, data = parse_message("src.pipeline", "run_pipeline: response_mode='irac'")
    assert (step, data) == ("plan", {"response_mode": "irac"})


def test_parse_force_jurisdiction():
    step, data = parse_message(
        "src.pipeline", "run_pipeline: force_jurisdiction='dong-nai' áp dụng"
    )
    assert step == "plan"
    assert data["force_jurisdiction"] == "dong-nai"


def test_parse_plan_query_summary():
    step, data = parse_message(
        "src.retrieval.query_planner",
        "plan_query | theme=dat-dai procedure=chuyen-muc-dich-su-dung-dat "
        "jurisdiction=None temporal=None temporal_ctx=True",
    )
    assert step == "plan"
    assert data["theme"] == "dat-dai"
    assert data["procedure"] == "chuyen-muc-dich-su-dung-dat"
    assert data["jurisdiction"] is None
    assert data["temporal"] is None
    assert data["has_temporal_context"] is True


def test_parse_plan_cache_hit():
    step, data = parse_message(
        "src.retrieval.query_planner", "plan_query: cache HIT (a1b2c3d4) — $0 API"
    )
    assert step == "plan"
    assert data == {"cache_hit": True, "cache_key": "a1b2c3d4"}


def test_parse_temporal_strict_date():
    step, data = parse_message(
        "src.pipeline",
        "run_pipeline: TEMPORAL MODE — anchor='2023' status='da-xong' "
        "→ strict date=2023-12-31",
    )
    assert step == "temporal"
    assert data["temporal_anchor"] == "2023"
    assert data["case_status"] == "da-xong"
    assert data["temporal"] == "2023-12-31"
    assert data["broad"] is False


def test_parse_temporal_span_regime():
    _, data = parse_message(
        "src.pipeline",
        "run_pipeline: TEMPORAL MODE — anchor='None' status='do-dang' "
        "→ span-regime (case_status=do-dang)",
    )
    assert data["temporal_anchor"] is None
    assert data["temporal"] is None
    assert data["broad"] is True


# ---------------------------------------------------------------------------
# parse_message — Stage 1/2/3
# ---------------------------------------------------------------------------

def test_parse_stage1():
    step, data = parse_message(
        "src.retrieval.subgraph_extractor",
        "Stage 1: top-5 scores=[0.712, 0.688, 0.401, 0.288, 0.201], "
        "threshold=0.3 → 3 norm_ids = ['luat-dat-dai-2024', "
        "'nghi-dinh-102-2024-nd-cp', 'quyet-dinh-69-2024-qd-ubnd-tp-hcm']",
    )
    assert step == "stage1"
    assert data["top_n"] == 5
    assert data["threshold"] == 0.3
    assert data["n_norms"] == 3
    assert data["scores"][0] == 0.712
    assert data["no_theme"] is False

    ranked = data["ranked"]
    assert len(ranked) == 5
    assert ranked[0]["norm_id"] == "luat-dat-dai-2024"
    assert ranked[0]["chon"] is True
    # Hai norm cuối dưới ngưỡng → bị loại, không gán norm_id
    assert ranked[3]["chon"] is False and ranked[3]["norm_id"] is None
    assert ranked[3]["duoi_nguong"] is True


def test_parse_stage1_no_theme():
    step, data = parse_message(
        "src.retrieval.subgraph_extractor",
        "Stage 1 [no-theme]: 2 norm_ids = ['luat-ho-tich-2014', "
        "'nghi-dinh-123-2015-nd-cp']",
    )
    assert step == "stage1"
    assert data["no_theme"] is True
    assert data["norm_ids"] == ["luat-ho-tich-2014", "nghi-dinh-123-2015-nd-cp"]
    assert [r["norm_id"] for r in data["ranked"]] == data["norm_ids"]


def test_pair_stage1_fallback_duoi_nguong():
    # Không norm nào vượt ngưỡng → stage1_norm_ids giữ top-1
    ranked = pair_stage1([0.21, 0.19], ["luat-dat-dai-2024"], 0.3)
    assert ranked[0]["chon"] is True
    assert ranked[0]["duoi_nguong"] is True
    assert ranked[1]["chon"] is False


def test_parse_stage2_norm_ids():
    step, data = parse_message(
        "src.retrieval.subgraph_extractor",
        "Stage 2 (norm_ids): 2 norms (jurisdiction=tp-hcm, temporal=None): "
        "['luat-dat-dai-2024', 'quyet-dinh-69-2024-qd-ubnd-tp-hcm']",
    )
    assert step == "stage2"
    assert data["n_norms"] == 2
    assert data["jurisdiction"] == "tp-hcm"
    assert data["temporal"] is None
    assert len(data["norm_ids"]) == 2


def test_parse_stage2_norm_ids_co_temporal():
    _, data = parse_message(
        "src.retrieval.subgraph_extractor",
        "Stage 2 (norm_ids): 1 norms (jurisdiction=None, temporal=2023-12-31): "
        "['luat-dat-dai-2013']",
    )
    assert data["temporal"] == "2023-12-31"
    assert data["jurisdiction"] is None


def test_parse_stage3():
    step, data = parse_message(
        "src.retrieval.subgraph_extractor",
        "Stage 3: 17 graph_component_ids mapped for procedure "
        "chuyen-muc-dich-su-dung-dat",
    )
    assert step == "stage3"
    assert data["n_components"] == 17
    assert data["procedure"] == "chuyen-muc-dich-su-dung-dat"


def test_parse_stage23_summary():
    step, data = parse_message(
        "src.pipeline", "run_pipeline: 6 norm_ids, 17 graph_comp_ids từ Stage 2+3"
    )
    assert step == "stage3"
    assert data == {"n_norm_ids": 6, "n_graph_comp_ids": 17}


# ---------------------------------------------------------------------------
# parse_message — Hybrid search + context
# ---------------------------------------------------------------------------

def test_parse_hybrid_struct_cite():
    step, data = parse_message(
        "src.retrieval.semantic_filter",
        "hybrid_search Path -1 (struct cite): cites=[('13', '1')] → 2 comps "
        "→ 2 text_units",
    )
    assert step == "hybrid"
    assert data["n_components"] == 2
    assert data["n_text_units"] == 2
    assert data["struct_cites"] == [("13", "1")]


def test_parse_hybrid_candidates():
    _, data = parse_message(
        "src.retrieval.semantic_filter",
        "hybrid_search: dense=50, keyword=12, graph=17 candidates",
    )
    assert data == {"dense": 50, "keyword": 12, "graph": 17}


def test_parse_hybrid_rarity():
    _, data = parse_message(
        "src.retrieval.semantic_filter",
        "hybrid_search: rarity stats — 6 norms, 41 components mapped, "
        "9 required concepts",
    )
    assert data["n_norms"] == 6
    assert data["n_components_mapped"] == 41
    assert data["n_required_concepts"] == 9


def test_parse_hybrid_pass_allocation():
    step, data = parse_message(
        "src.retrieval.semantic_filter",
        "hybrid_search: top-25 | pass-1(struct-cite)=2, pass-0.5(label-keyword)=0, "
        "pass0(dense-floor)=9, pass1(rrf-breadth)=6, pass2(depth)=8 | "
        "caps: per_norm=3, per_tier={1: 8, 2: 8, 3: 6, 4: 8} | best rrf=0.0328 | "
        "tier_dist={1: 10, 2: 7, 4: 8} | norm_dist={'luat-dat-dai-2024': 3}",
    )
    assert step == "hybrid"
    assert data["top_k"] == 25
    assert data["passes"] == {
        "struct_cite": 2, "label_keyword": 0, "dense_floor": 9,
        "rrf_breadth": 6, "depth": 8,
    }
    assert data["caps"]["per_norm"] == 3
    assert data["caps"]["per_tier"] == {1: 8, 2: 8, 3: 6, 4: 8}
    assert data["best_rrf"] == 0.0328
    assert data["tier_dist"] == {1: 10, 2: 7, 4: 8}
    assert data["norm_dist"] == {"luat-dat-dai-2024": 3}


def test_parse_assemble_context():
    step, data = parse_message(
        "src.retrieval.context_assembler", "assemble_context: 25 blocks, ~4210 tokens"
    )
    assert step == "context"
    assert data == {"n_blocks": 25, "tokens": 4210}


def test_parse_assemble_context_bi_cat():
    step, data = parse_message(
        "src.retrieval.context_assembler",
        "assemble_context: dừng tại 21 blocks (5980/6000 tokens)",
    )
    assert step == "context"
    assert data["bi_cat"] is True
    assert data["n_blocks"] == 21
    assert data["tokens"] == 5980
    assert data["max_tokens"] == 6000


# ---------------------------------------------------------------------------
# parse_message — Generate / verify / done
# ---------------------------------------------------------------------------

def test_parse_generate_cache_hit():
    step, data = parse_message(
        "src.retrieval.answer_generator",
        "generate_answer: cache HIT (9f8e7d6c5b4a3210) — $0 API",
    )
    assert step == "generate"
    assert data["cache_hit"] is True
    assert data["cache_key"] == "9f8e7d6c5b4a3210"


def test_parse_generate_stats():
    step, data = parse_message(
        "src.retrieval.answer_generator",
        "generate_answer: 1820 chars, 4 citations, "
        "sections={'tra_loi': True, 'canh_bao_lex': False}",
    )
    assert step == "generate"
    assert data["n_chars"] == 1820
    assert data["n_citations"] == 4
    assert data["sections"] == {"tra_loi": True, "canh_bao_lex": False}
    assert data["cache_hit"] is False


def test_parse_verifier_pipeline():
    step, data = parse_message(
        "src.pipeline", "run_pipeline: verifier tier=1 6→4 citations (drop 2, flag 0)"
    )
    assert step == "verify"
    assert data == {
        "tier": 1, "n_input": 6, "n_kept": 4, "n_dropped": 2, "n_flagged": 0,
    }


def test_parse_verify_citations():
    step, data = parse_message(
        "src.retrieval.verifier",
        "verify_citations: tier=2 in=6 kept=5 dropped=1 flagged=2",
    )
    assert step == "verify"
    assert data["tier"] == 2 and data["n_flagged"] == 2


def test_parse_done():
    step, data = parse_message(
        "src.pipeline", "run_pipeline: hoàn thành trong 21.7s — 4 citations"
    )
    assert step == "done"
    assert data == {"elapsed_seconds": 21.7, "n_citations": 4}


# ---------------------------------------------------------------------------
# parse_message — fallback
# ---------------------------------------------------------------------------

def test_parse_khong_khop_suy_tu_ten_logger():
    step, data = parse_message(
        "src.retrieval.semantic_filter", "hybrid_search: một dòng log mới chưa biết"
    )
    assert step == "hybrid"
    assert data == {}


def test_parse_hoan_toan_la_tra_ve_none():
    step, data = parse_message("khong.biet", "một dòng hoàn toàn lạ")
    assert step is None
    assert data == {}


# ---------------------------------------------------------------------------
# TraceCollector
# ---------------------------------------------------------------------------

def _collector_logger(name: str):
    """Tạo logger riêng + collector gắn vào (không đụng logger 'src' toàn cục)."""
    collector = TraceCollector()
    log = logging.getLogger(name)
    log.handlers = [collector]
    log.setLevel(logging.INFO)
    log.propagate = False
    return log, collector


def test_collector_phat_event_co_cau_truc():
    log, collector = _collector_logger("test_ui_trace.src.pipeline")
    log.info("run_pipeline: plan=dat-dai/tp-hcm")
    log.info("assemble_context: 25 blocks, ~4210 tokens")

    events = collector.drain()
    assert [e["seq"] for e in events] == [0, 1]
    assert events[0]["step"] == "plan"
    assert events[0]["kind"] == "log"
    assert events[0]["raw"] == "run_pipeline: plan=dat-dai/tp-hcm"
    assert events[0]["data"]["theme"] == "dat-dai"
    assert events[1]["step"] == "context"
    assert all(isinstance(e["t"], float) for e in events)


def test_collector_giu_raw_khi_khong_parse_duoc():
    log, collector = _collector_logger("test_ui_trace.src.pipeline")
    log.info("run_pipeline: plan=dat-dai/tp-hcm")
    log.info("một dòng log hoàn toàn mới của src")

    events = collector.drain()
    assert len(events) == 2
    # Không khớp regex lẫn tên logger → gắn vào bước hiện hành, giữ nguyên raw
    assert events[1]["data"] == {}
    assert events[1]["raw"] == "một dòng log hoàn toàn mới của src"
    assert events[1]["step"] == "plan"


def test_collector_push_thu_cong_va_reset():
    collector = TraceCollector()
    collector.push("question", kind="result", data={"question": "abc"})
    collector.push("done", kind="done", data={"n_citations": 2})
    events = collector.drain()
    assert [e["kind"] for e in events] == ["result", "done"]
    assert [e["seq"] for e in events] == [0, 1]

    collector.reset()
    collector.push("question", kind="result", data={})
    assert collector.drain()[0]["seq"] == 0


# ---------------------------------------------------------------------------
# parse_label / parse_context (spec mục 5.2)
# ---------------------------------------------------------------------------

def test_parse_label_con_hieu_luc():
    info = parse_label(
        "[Tier 4 | Hiệu lực: 2024-09-30] Điều 3, Khoản 1 "
        "(quyet-dinh-69-2024-qd-ubnd-tp-hcm)"
    )
    assert info["tier"] == 4
    assert info["valid_from"] == "2024-09-30"
    assert info["valid_to"] is None
    assert info["het_hieu_luc"] is False
    assert info["vi_tri"] == "Điều 3, Khoản 1"
    assert info["norm_id"] == "quyet-dinh-69-2024-qd-ubnd-tp-hcm"


def test_parse_label_het_hieu_luc():
    info = parse_label(
        "[Tier 1 | Hiệu lực: 2014-07-01 → 2025-01-01 (HẾT HIỆU LỰC)] "
        "Điều 95 (luat-dat-dai-2013)"
    )
    assert info["tier"] == 1
    assert info["valid_from"] == "2014-07-01"
    assert info["valid_to"] == "2025-01-01"
    assert info["het_hieu_luc"] is True
    assert info["vi_tri"] == "Điều 95"
    assert info["norm_id"] == "luat-dat-dai-2013"


def test_parse_label_chi_co_slug():
    info = parse_label("luat-dat-dai-2024")
    assert info["tier"] is None
    assert info["valid_from"] is None
    assert info["vi_tri"] == ""
    assert info["norm_id"] == "luat-dat-dai-2024"


def test_parse_label_sentinel_valid_to():
    info = parse_label("[Tier 1 | Hiệu lực: 2024-08-01] Điều 116 (luat-dat-dai-2024)")
    assert info["valid_to"] is None
    assert info["het_hieu_luc"] is False


CONTEXT_MAU = """--- [Tier 4 | Hiệu lực: 2024-09-30] Điều 3. Hạn mức giao đất ở cho cá nhân, Khoản 3. (quyet-dinh-69-2024-qd-ubnd-tp-hcm) ---
Điều 3. Hạn mức giao đất ở cho cá nhân
Khoản 3.
Các xã của các huyện Bình Chánh, Hóc Môn: không quá 250 m2/cá nhân.

--- [Tier 2 | Hiệu lực: 2024-09-11] Điều 10. Trình tự, Khoản 1. (nghi-dinh-112-2024-nd-cp) ---
[AMENDMENT WARNING — nội dung Component này đã/sắp bị sửa đổi:]
  - nghi-dinh-226-2025-nd-cp (khoản 10 Điều 5, hiệu lực 2025-08-15): sửa đổi, bổ sung khoản này
Điều 10. Trình tự
Khoản 1.
Nội dung khoản 1 của Điều 10.

--- luat-dat-dai-2024 ---
Nội dung không có context_path.
"""


def test_parse_context_tach_du_block():
    blocks = parse_context(CONTEXT_MAU)
    assert len(blocks) == 3
    assert [b["index"] for b in blocks] == [0, 1, 2]
    assert blocks[0]["norm_id"] == "quyet-dinh-69-2024-qd-ubnd-tp-hcm"
    assert blocks[0]["tier"] == 4
    assert blocks[0]["amendments"] == []
    assert "250 m2/cá nhân" in blocks[0]["text"]
    assert blocks[0]["text"].startswith("Điều 3.")


def test_parse_context_amendment_warning():
    block = parse_context(CONTEXT_MAU)[1]
    assert len(block["amendments"]) == 1
    am = block["amendments"][0]
    assert am["amending_norm"] == "nghi-dinh-226-2025-nd-cp"
    assert am["amending_loc"] == "khoản 10 Điều 5"
    assert am["effective_date"] == "2025-08-15"
    assert am["content_summary"] == "sửa đổi, bổ sung khoản này"
    # Block cảnh báo đã được tách khỏi nguyên văn
    assert "AMENDMENT WARNING" not in block["text"]
    assert block["text"].startswith("Điều 10. Trình tự")


def test_parse_context_label_chi_co_slug():
    block = parse_context(CONTEXT_MAU)[2]
    assert block["norm_id"] == "luat-dat-dai-2024"
    assert block["vi_tri"] == ""
    assert block["tier"] is None
    assert block["text"] == "Nội dung không có context_path."


def test_parse_context_rong():
    assert parse_context("") == []
    assert parse_context("   ") == []


# ---------------------------------------------------------------------------
# parse_vi_tri / link_citations (spec mục 5.3)
# ---------------------------------------------------------------------------

def test_parse_vi_tri_tieu_de_co_dau_phay():
    vt = parse_vi_tri(
        "Điều 1. Quy định hạn mức đất ở đối với hộ gia đình, cá nhân và mục đích "
        "áp dụng hạn mức như sau, Khoản 1., Điểm b."
    )
    assert vt == {
        "loai": "dieu", "dieu": "1", "khoan": "1", "diem": "b", "tiet": None,
    }


def test_parse_vi_tri_lay_cap_sau_o_cuoi():
    # Tiêu đề Điều của văn bản sửa đổi chứa sẵn ", Khoản 3" — cấp thật nằm ở
    # CUỐI chuỗi (context_path ghép bằng ", "), phải lấy match cuối.
    vt = parse_vi_tri(
        "Điều 1. Sửa đổi, bổ sung Điều 5, Khoản 3 của Nghị định số 112/2024/NĐ-CP, "
        "Khoản 2., Điểm a."
    )
    assert vt["dieu"] == "1"
    assert vt["khoan"] == "2"
    assert vt["diem"] == "a"


def test_parse_vi_tri_phu_luc():
    vt = parse_vi_tri("Phụ lục I - Phần V - Mục VI. Trình tự, Khoản 2.")
    assert vt["loai"] == "phu_luc"
    assert vt["dieu"] == "i"
    assert vt["khoan"] == "2"


def _block(index: int, vi_tri: str, norm_id: str) -> ContextBlock:
    return ContextBlock(
        index=index, label="", tier=None, valid_from=None, valid_to=None,
        het_hieu_luc=False, vi_tri=vi_tri, norm_id=norm_id,
        amendments=[], text="", raw="",
    )


BLOCKS_MAU = [
    _block(0, "Điều 3. Hạn mức, Khoản 3.", "quyet-dinh-69-2024-qd-ubnd-tp-hcm"),
    _block(1, "Điều 3. Hạn mức, Khoản 1.", "quyet-dinh-69-2024-qd-ubnd-tp-hcm"),
    _block(2, "Điều 1. Quy định, Khoản 1., Điểm b.", "quyet-dinh-18-2016-qd-ubnd-tp-hcm"),
    _block(3, "Phụ lục I. Biểu mức thu", "quyet-dinh-92-2025-qd-ubnd-dong-nai"),
]


def test_link_citations_khop_chinh_xac():
    cits = [{
        "dieu": "3", "khoan": "3", "diem": None, "tiet": None,
        "van_ban": "quyet-dinh-69-2024-qd-ubnd-tp-hcm", "loai": "dieu",
    }]
    ket = link_citations(cits, BLOCKS_MAU)
    assert ket[0]["block_index"] == 0
    assert ket[0]["khop"] == "chinh-xac"


def test_link_citations_khop_gan_dung_khi_lech_khoan():
    # Khoản 9 không có trong context → vẫn nối tới block cùng Điều, đánh dấu gần đúng
    cits = [{
        "dieu": "3", "khoan": "9", "diem": None, "tiet": None,
        "van_ban": "quyet-dinh-69-2024-qd-ubnd-tp-hcm", "loai": "dieu",
    }]
    ket = link_citations(cits, BLOCKS_MAU)
    assert ket[0]["block_index"] in (0, 1)
    assert ket[0]["khop"] == "gan-dung"
    # Chú thích nêu ĐÚNG cấp lệch (cùng cấp, khác số)
    assert ket[0]["chu_thich"] == "khớp gần đúng — context ở Khoản 3, citation nêu Khoản 9"


def test_link_citations_chu_thich_khi_citation_sau_hon_block():
    # Ca thật quan sát trên 137 câu: citation nêu tới Điểm, block chỉ tới Khoản
    cits = [{
        "dieu": "3", "khoan": "1", "diem": "a", "tiet": None,
        "van_ban": "quyet-dinh-69-2024-qd-ubnd-tp-hcm", "loai": "dieu",
    }]
    ket = link_citations(cits, BLOCKS_MAU)
    assert ket[0]["block_index"] == 1
    assert ket[0]["khop"] == "gan-dung"
    assert ket[0]["chu_thich"] == (
        "khớp gần đúng — context chỉ tới cấp Khoản, citation nêu Điểm a"
    )


def test_link_citations_khop_toi_diem():
    cits = [{
        "dieu": "1", "khoan": "1", "diem": "b", "tiet": None,
        "van_ban": "quyet-dinh-18-2016-qd-ubnd-tp-hcm", "loai": "dieu",
    }]
    ket = link_citations(cits, BLOCKS_MAU)
    assert ket[0]["block_index"] == 2
    assert ket[0]["khop"] == "chinh-xac"


def test_link_citations_phu_luc_default():
    cits = [{
        "dieu": "_default", "khoan": None, "diem": None, "tiet": None,
        "van_ban": "quyet-dinh-92-2025-qd-ubnd-dong-nai", "loai": "phu_luc",
    }]
    ket = link_citations(cits, BLOCKS_MAU)
    assert ket[0]["block_index"] == 3
    assert ket[0]["khop"] == "chinh-xac"


def test_link_citations_khong_tim_thay():
    cits = [{
        "dieu": "999", "khoan": None, "diem": None, "tiet": None,
        "van_ban": "luat-dat-dai-2024", "loai": "dieu",
    }]
    ket = link_citations(cits, BLOCKS_MAU)
    assert ket[0]["block_index"] is None
    assert ket[0]["khop"] == "khong-tim-thay"
    assert "không tìm thấy trong context" in ket[0]["chu_thich"]


def test_link_citations_giu_thu_tu_va_citation_goc():
    cits = [
        {"dieu": "999", "khoan": None, "diem": None, "tiet": None,
         "van_ban": "luat-dat-dai-2024", "loai": "dieu"},
        {"dieu": "3", "khoan": "1", "diem": None, "tiet": None,
         "van_ban": "quyet-dinh-69-2024-qd-ubnd-tp-hcm", "loai": "dieu"},
    ]
    ket = link_citations(cits, BLOCKS_MAU)
    assert len(ket) == 2
    assert ket[0]["citation"] is cits[0]
    assert ket[1]["block_index"] == 1


def test_link_citations_rong():
    assert link_citations([], BLOCKS_MAU) == []
