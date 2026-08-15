"""
Pipeline End-to-End — TASK-14
Kết nối TASK-10 → TASK-11 → TASK-12 → TASK-13 thành một hàm duy nhất.

Flow:
  question
    → plan_query()           [TASK-10] QueryPlan
    → extract_subgraph()     [TASK-11] LCCIDs
    → hybrid_search()        [TASK-12] Top-k ScoredTextUnit
    → assemble_context()     [TASK-13] context string
    → generate_answer()      [TASK-13] {answer, citations, context_used}

Trả về PipelineResult TypedDict.
"""
import logging
import os
import re
import time
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
from neo4j import GraphDatabase
from qdrant_client import QdrantClient

from src.ingestion.vectorizer import load_model
from src.utils.llm_config import make_llm_client
from src.retrieval.answer_generator import generate_answer
from src.retrieval.context_assembler import assemble_context
from src.retrieval.query_planner import QueryPlan, plan_query
from src.retrieval.semantic_filter import hybrid_search
from src.retrieval.ablation_config import FULL, AblationConfig
from src.retrieval.subgraph_extractor import extract_subgraph
from src.retrieval.transitional import mo_ta_thay_doi, thu_thap_chuyen_tiep
from src.retrieval.verifier import verify_citations

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 25
CONTEXT_MAX_TOKENS = int(os.getenv('PIPE_CONTEXT_MAX_TOKENS', '6000'))


# ---------------------------------------------------------------------------
# Temporal helpers (Option C Phần 2 — temporal-aware retrieval)
# ---------------------------------------------------------------------------

_TEMPORAL_ISO_PATTERNS = [
    (re.compile(r"^\d{4}-\d{2}-\d{2}$"), lambda s: s),                # YYYY-MM-DD
    (re.compile(r"^\d{4}-\d{2}$"), lambda s: f"{s}-15"),              # YYYY-MM → mid-month
    (re.compile(r"^\d{4}$"), lambda s: f"{s}-12-31"),                  # YYYY → end-of-year
    # Lý do dùng end-of-year cho YYYY: câu hỏi "năm 2024" thường ý chỉ "trong
    # khoảng nào đó của năm 2024" — point query đầu năm (01-01) sẽ miss VB có
    # hiệu lực sau 01-01 (VD Luật ĐĐ 2024 valid_from=2024-08-01). End-of-year
    # cover full năm, mid-month tương tự cho YYYY-MM.
]


# Dấu hiệu câu hỏi đang hỏi về HIỆN TẠI, dù có nhắc một mốc quá khứ.
# Mốc quá khứ trong câu hỏi của người dân thường là NGÀY SỰ VIỆC XẢY RA, không
# phải ngày cần tra luật: V031 "lỡ lấn đất từ năm 2010 … NAY quy hoạch đã điều
# chỉnh" bị chốt mốc 2010 nên Giai đoạn 2 loại sạch Luật Đất đai 2024 và NĐ
# 101/2024 — đúng hai văn bản là đáp án. V032 "sử dụng ổn định từ năm 1990"
# cũng vậy.
# Khi thấy dấu hiệu hiện tại, chuyển sang truy hồi rộng (không lọc thời gian):
# rộng là lựa chọn AN TOÀN vì nó kéo cả văn bản cũ lẫn mới, còn lọc chặt mới là
# hành vi mạo hiểm.
_DAU_HIEU_HIEN_TAI = (
    "hiện nay", "hiện tại", "bây giờ", "đến nay", "tới nay", "tới giờ",
    "đến giờ", "ngày nay", "nay ", " nay,", " nay.", "giờ ",
    "hiện có", "hiện đang", "hiện là", "hiện nắm", "còn hiệu lực không",
)


def _hoi_ve_hien_tai(question: str) -> bool:
    """Câu hỏi có dấu hiệu hỏi về hiện tại (dù nhắc mốc quá khứ)."""
    q = (question or "").lower()
    return any(t in q for t in _DAU_HIEU_HIEN_TAI)


def _resolve_temporal_anchor(anchor: str | None) -> str | None:
    """Convert temporal_anchor từ planner thành ISO date cho Cypher filter.

    Trả về:
      - ISO date string nếu anchor là date cụ thể → Cypher filter strict tại thời điểm này.
      - None nếu anchor vague ('luat-cu', 'unspecified_past', 'trước-...') → broad retrieve
        (Cypher KHÔNG filter theo thời gian, kéo cả VB cũ + mới; prompt sẽ guide LLM).

    Args:
        anchor: temporal_intent.temporal_anchor từ QueryPlan.

    Returns:
        ISO date "YYYY-MM-DD" hoặc None.
    """
    if not anchor:
        return None
    if anchor in ("luat-cu", "unspecified_past"):
        return None
    if anchor.startswith("trước-") or anchor.startswith("sau-"):
        return None  # phạm vi mở rộng, để broad
    for pattern, fmt in _TEMPORAL_ISO_PATTERNS:
        if pattern.match(anchor):
            return fmt(anchor)
    return None  # unrecognized → broad


# Tên tỉnh/huyện xuất hiện trong kho (3 phạm vi hiệu lực). Dùng để phát hiện
# câu hỏi CÓ nêu địa phương hay không.
_TEN_DIA_PHUONG = (
    "tp.hcm", "tp hcm", "tphcm", "hồ chí minh", "thành phố hồ chí minh",
    "đồng nai", "biên hòa", "thủ đức", "củ chi", "bình chánh", "hóc môn",
    "nhà bè", "cần giờ", "long thành", "trảng bom", "nhơn trạch", "phú lý",
)


def _co_neu_dia_phuong(question: str) -> bool:
    q = (question or "").lower()
    return any(t in q for t in _TEN_DIA_PHUONG)


def ap_dung_guard_pham_vi(query_plan: dict, question: str) -> dict:
    """Câu KHÔNG nêu địa phương thì 'toan-quoc' là cam kết quá tay.

    Trạng thái đúng là CHƯA XÁC ĐỊNH (None), và _resolve_allowed_jurisdictions
    đã xử lý trạng thái đó chính xác từ Fix A (09/07/2026): None → cho phép mọi
    tỉnh. Bộ lập kế hoạch tự chốt 'toan-quoc' cho câu không nêu tỉnh sẽ loại sạch
    văn bản cấp tỉnh — mà nhiều câu (lệ phí, hạn mức, bảng giá đất) lại có đáp án
    nằm đúng ở cấp tỉnh. V120 "lệ phí khai sinh muộn bao nhiêu" là ca điển hình.

    CẢNH BÁO PHẠM VI: guard này chạm 55/137 câu (40%). Nó KHÔNG phải bản vá
    phẫu thuật mà là đổi chính sách phạm vi truy hồi — phải đo trước khi bật.
    Mặc định TẮT.
    """
    if query_plan.get("jurisdiction") != "toan-quoc":
        return query_plan
    if _co_neu_dia_phuong(question):
        return query_plan
    out = dict(query_plan)
    out["jurisdiction"] = None
    logger.info("GUARD PHẠM VI — câu không nêu địa phương: toan-quoc → None")
    return out


def ap_dung_lop_thoi_gian(query_plan: dict, question: str) -> dict:
    """Điều chỉnh query_plan["temporal"] theo ý định thời gian của câu hỏi.

    TÁCH RIÊNG để khâu đánh giá dùng CHUNG với pipeline. Trước đây harness gọi
    thẳng extract_subgraph nên bỏ qua lớp này và lọc chặt hơn hệ thật — mọi con
    số tuyệt đối đo được đều thấp hơn thực tế (các Δ thì không ảnh hưởng vì mọi
    biến thể trong một mẻ dùng chung norm_ids).

    Ba nhánh, đều dẫn tới truy hồi RỘNG (không lọc thời gian) khi cần kéo cả văn
    bản cũ lẫn mới; rộng là lựa chọn an toàn, lọc chặt mới là mạo hiểm:
      - hồ sơ dở dang / sự kiện mới  → có thể vắt qua hai khung quy định
      - câu hỏi có dấu hiệu hiện tại → mốc quá khứ là ngày SỰ VIỆC, không phải
        ngày tra luật
      - mốc mơ hồ                     → không chốt được ngày
    """
    ti = query_plan.get("temporal_intent", {}) or {}
    if not ti.get("has_temporal_context"):
        return query_plan
    case_status = ti.get("case_status")
    anchor = ti.get("temporal_anchor")
    if case_status in ("do-dang", "moi"):
        resolved, reason = None, f"span-regime (case_status={case_status})"
    elif _hoi_ve_hien_tai(question):
        resolved = None
        reason = f"broad (mốc {anchor} là ngày sự việc, câu hỏi hỏi về hiện tại)"
    else:
        resolved = _resolve_temporal_anchor(anchor)
        reason = f"strict date={resolved}" if resolved else "broad (mốc mơ hồ)"
    out = dict(query_plan)
    out["temporal"] = resolved
    logger.info(
        f"TEMPORAL MODE — anchor='{anchor}' status='{case_status}' → {reason}"
    )
    return out


# ---------------------------------------------------------------------------
# Output type
# ---------------------------------------------------------------------------

class PipelineResult(TypedDict):
    question: str
    query_plan: QueryPlan
    response_mode: str           # mode đã resolve cho answer generation
    lccids_count: int
    top_k_count: int
    context_tokens: int
    context: str            # full assembled context — dùng cho faithfulness eval
    answer: str
    citations: list[dict]
    context_used: bool
    elapsed_seconds: float
    verifier: dict | None        # thống kê Verifier agent (None nếu verify=False)
    # Câu mô tả khi quy định đã thay đổi trong tập văn bản ứng viên (việc 3).
    # "" khi không có thay đổi hoặc khi tắt cờ. CỐ Ý để riêng, KHÔNG nhét vào
    # prompt: prompt đã được tinh chỉnh kỹ chống thuật ngữ giả và rò nhãn
    # (D-14/D-16), thêm chữ vào đó là rủi ro không cần thiết. Tầng trình bày
    # (demo/UI) tự ghép câu này lên trước câu trả lời.
    canh_bao_thay_doi: str
    # True khi câu trả lời lấy từ LLM cache (không gọi API). Cần cho việc hâm
    # cache trước buổi demo: không có trường này thì không cách nào biết cache
    # có ăn hay không, và `precache_demo` báo "cached mới" cho cả hai trường hợp.
    cache_hit: bool


# ---------------------------------------------------------------------------
# Clients factory
# ---------------------------------------------------------------------------

def _build_clients(llm_mode: str = "claude") -> tuple:
    """Khởi tạo Neo4j driver, Qdrant client, LLM client, embedding model từ .env.

    llm_mode: "claude" (eval, thuần) | "claude-fallback" (Claude+Gemini drop) |
    "gemini" (end-to-end). Mặc định "claude" → eval reproducible.
    """
    neo4j_driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "")),
    )
    qdrant_client = QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", "6333")),
    )
    anthropic_client = make_llm_client(mode=llm_mode)
    model = load_model()
    return neo4j_driver, qdrant_client, anthropic_client, model


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    question: str,
    *,
    neo4j_driver=None,
    qdrant_client=None,
    anthropic_client=None,
    model=None,
    top_k: int = DEFAULT_TOP_K,
    max_tokens: int = CONTEXT_MAX_TOKENS,
    force_jurisdiction: str | None = None,
    llm_cache_dir: Path | None = None,
    response_mode: str | None = None,
    verify: bool = False,
    verify_tier: int = 1,
    llm_mode: str = "claude",
    ablation: AblationConfig = FULL,
    refers_mode: str | None = None,
    budget_mode: str | None = None,
    chuyen_tiep: bool = False,
    rerank_mode: str | None = None,
) -> PipelineResult:
    """Chạy toàn bộ pipeline RAG cho một câu hỏi pháp lý tiếng Việt.

    Args:
        question: Câu hỏi tiếng Việt của người dùng.
        neo4j_driver: Driver Neo4j (tự khởi tạo nếu None).
        qdrant_client: Qdrant client (tự khởi tạo nếu None).
        anthropic_client: Anthropic client (tự khởi tạo nếu None).
        model: Embedding model BGE-M3 (tự load nếu None).
        top_k: Số TextUnit trả về từ hybrid_search.
        max_tokens: Token budget tối đa cho context.

    Returns:
        PipelineResult với đầy đủ thông tin pipeline. Retrieval luôn chạy
        best-effort kể cả khi query_plan thiếu field (không còn Confirmation Loop).
    """
    t_start = time.perf_counter()

    # Lazy init clients
    _own_clients = neo4j_driver is None
    if _own_clients:
        neo4j_driver, qdrant_client, anthropic_client, model = _build_clients(llm_mode)

    try:
        # --- TASK-10: Query Planning ---
        logger.info(f"run_pipeline: plan_query cho '{question[:60]}...'")
        query_plan = plan_query(question, anthropic_client, neo4j_driver=neo4j_driver)
        logger.info(
            f"run_pipeline: plan={query_plan['theme']}/{query_plan['jurisdiction']}"
        )

        # Resolve answer mode: explicit override > planner auto-detect > "general".
        resolved_mode = response_mode or query_plan.get("response_mode") or "general"
        logger.info(f"run_pipeline: response_mode='{resolved_mode}'")

        # Inject jurisdiction từ ground truth (eval): áp dụng khi câu hỏi KHÔNG nêu
        # địa phương (jurisdiction=None). Tương đương điều kiện cũ "missing jurisdiction"
        # nhưng không phụ thuộc Confirmation Loop (đã gỡ). Hệ 1Q-1A luôn chạy best-effort.
        if force_jurisdiction and query_plan["jurisdiction"] is None:
            query_plan["jurisdiction"] = force_jurisdiction
            logger.info(
                f"run_pipeline: force_jurisdiction='{force_jurisdiction}' áp dụng"
            )

        # --- TEMPORAL LAYER (Option C Phần 2) ---
        query_plan = ap_dung_lop_thoi_gian(query_plan, question)

        # --- TASK-11: Sub-graph Extraction ---
        logger.info("run_pipeline: extract_subgraph")
        norm_ids, graph_comp_ids = extract_subgraph(
            question, query_plan, neo4j_driver, qdrant_client, model,
            ablation=ablation,
        )
        logger.info(f"run_pipeline: {len(norm_ids)} norm_ids, {len(graph_comp_ids)} graph_comp_ids từ Stage 2+3")

        # Không tìm được văn bản liên quan
        if not norm_ids:
            elapsed = time.perf_counter() - t_start
            return PipelineResult(
                question=question,
                query_plan=query_plan,
                response_mode=resolved_mode,
                lccids_count=0,
                top_k_count=0,
                context_tokens=0,
                context="",
                answer="Không tìm thấy văn bản pháp luật liên quan đến câu hỏi này.",
                citations=[],
                context_used=False,
                elapsed_seconds=round(elapsed, 2),
                verifier=None,
                canh_bao_thay_doi="",
                cache_hit=False,
            )

        # --- Việc 3: phát hiện quy định đã thay đổi + điều khoản chuyển tiếp ---
        # Tất định, chỉ 2 truy vấn Neo4j. Cảnh báo CHỈ nổ khi tập ứng viên thật
        # sự có văn bản đã hết hiệu lực — nổ ở mọi câu sẽ thành lời rào đón.
        canh_bao, chuyen_tiep_comp_ids = "", None
        if chuyen_tiep:
            cap, comp_ids = thu_thap_chuyen_tiep(norm_ids, neo4j_driver)
            if cap:
                chuyen_tiep_comp_ids = comp_ids or None
                canh_bao = mo_ta_thay_doi(cap, bool(comp_ids))
                logger.info(
                    f"run_pipeline: phát hiện {len(cap)} văn bản đã bị thay thế, "
                    f"{len(comp_ids)} điều khoản chuyển tiếp"
                )

        # --- TASK-12: Hybrid Search ---
        logger.info("run_pipeline: hybrid_search")
        scored_units = hybrid_search(
            question,
            norm_ids,
            qdrant_client,
            model,
            top_k=top_k,
            graph_component_ids=graph_comp_ids,
            neo4j_driver=neo4j_driver,
            procedure_id=query_plan.get("procedure"),
            refers_mode=refers_mode,
            budget_mode=budget_mode,
            extra_component_ids=chuyen_tiep_comp_ids,
            rerank_mode=rerank_mode,
        )
        logger.info(f"run_pipeline: {len(scored_units)} scored units")

        # --- TASK-13a: Context Assembly ---
        logger.info("run_pipeline: assemble_context")
        context = assemble_context(scored_units, neo4j_driver, max_tokens=max_tokens)
        context_tokens = max(1, int(len(context) / 3.5))

        # --- TASK-13b: Answer Generation ---
        logger.info("run_pipeline: generate_answer")
        result = generate_answer(
            question, context, anthropic_client, cache_dir=llm_cache_dir, mode=resolved_mode
        )

        # --- Verifier agent (tầng multi-agent, tùy chọn) ---
        # Mặc định verify=False → hành vi pipeline gốc KHÔNG đổi. Khi bật: lọc
        # citation theo grounding (tier 1, $0) hoặc + LLM support judge (tier 2, API).
        citations = result["citations"]
        verifier_info = None
        if verify:
            vr = verify_citations(
                question, context, result["answer"], citations,
                tier=verify_tier, llm_client=anthropic_client,
            )
            citations = vr["filtered_citations"]
            verifier_info = {
                "n_input": vr["n_input"], "n_kept": vr["n_kept"],
                "n_dropped": vr["n_dropped"], "n_flagged": vr["n_flagged"],
                "tier": vr["tier"], "verdicts": vr["verdicts"],
            }
            logger.info(
                f"run_pipeline: verifier tier={vr['tier']} "
                f"{vr['n_input']}→{vr['n_kept']} citations "
                f"(drop {vr['n_dropped']}, flag {vr['n_flagged']})"
            )

        elapsed = time.perf_counter() - t_start
        logger.info(
            f"run_pipeline: hoàn thành trong {elapsed:.1f}s — "
            f"{len(citations)} citations"
        )

        return PipelineResult(
            question=question,
            query_plan=query_plan,
            response_mode=resolved_mode,
            lccids_count=len(norm_ids),
            top_k_count=len(scored_units),
            context_tokens=context_tokens,
            context=context,
            answer=result["answer"],
            citations=citations,
            context_used=result["context_used"],
            elapsed_seconds=round(elapsed, 2),
            verifier=verifier_info,
            canh_bao_thay_doi=canh_bao,
            cache_hit=bool(result.get("cache_hit")),
        )

    finally:
        if _own_clients:
            neo4j_driver.close()
