"""
Pipeline End-to-End — TASK-14
Kết nối TASK-10 → TASK-11 → TASK-12 → TASK-13 thành một hàm duy nhất.

Flow:
  question
    → plan_query()           [TASK-10] QueryPlan
    → (nếu thiếu field)      → trả về confirmation_needed
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
from src.utils.llm_config import make_anthropic_client
from src.retrieval.answer_generator import generate_answer
from src.retrieval.context_assembler import assemble_context
from src.retrieval.query_planner import QueryPlan, build_confirmation_prompt, plan_query
from src.retrieval.semantic_filter import hybrid_search
from src.retrieval.subgraph_extractor import extract_subgraph

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 25
CONTEXT_MAX_TOKENS = 6000


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


# ---------------------------------------------------------------------------
# Output type
# ---------------------------------------------------------------------------

class PipelineResult(TypedDict):
    question: str
    query_plan: QueryPlan
    confirmation_needed: bool
    confirmation_prompt: str | None
    lccids_count: int
    top_k_count: int
    context_tokens: int
    context: str            # full assembled context — dùng cho faithfulness eval
    answer: str
    citations: list[dict]
    context_used: bool
    elapsed_seconds: float


# ---------------------------------------------------------------------------
# Clients factory
# ---------------------------------------------------------------------------

def _build_clients() -> tuple:
    """Khởi tạo Neo4j driver, Qdrant client, Anthropic client, embedding model từ .env."""
    neo4j_driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "")),
    )
    qdrant_client = QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", "6333")),
    )
    anthropic_client = make_anthropic_client()
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
    bypass_completeness: bool = False,
    llm_cache_dir: Path | None = None,
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
        PipelineResult với đầy đủ thông tin pipeline.
        Nếu câu hỏi thiếu thông tin → confirmation_needed=True, answer="".
    """
    t_start = time.perf_counter()

    # Lazy init clients
    _own_clients = neo4j_driver is None
    if _own_clients:
        neo4j_driver, qdrant_client, anthropic_client, model = _build_clients()

    try:
        # --- TASK-10: Query Planning ---
        logger.info(f"run_pipeline: plan_query cho '{question[:60]}...'")
        query_plan = plan_query(question, anthropic_client, neo4j_driver=neo4j_driver)
        logger.info(
            f"run_pipeline: plan={query_plan['theme']}/{query_plan['jurisdiction']} "
            f"complete={query_plan['is_complete']}"
        )

        # Bypass Confirmation Loop cho evaluation: inject jurisdiction từ ground truth
        # nếu được cung cấp. Chỉ unblock khi jurisdiction là field thiếu duy nhất.
        if force_jurisdiction and not query_plan["is_complete"]:
            if "jurisdiction" in query_plan["missing_fields"]:
                query_plan["jurisdiction"] = force_jurisdiction
                query_plan["missing_fields"] = [
                    f for f in query_plan["missing_fields"] if f != "jurisdiction"
                ]
                if not query_plan["missing_fields"]:
                    query_plan["is_complete"] = True
                logger.info(
                    f"run_pipeline: force_jurisdiction='{force_jurisdiction}' áp dụng, "
                    f"is_complete={query_plan['is_complete']}"
                )

        # Bypass toàn diện cho evaluation: chấp nhận query_plan thiếu field (procedure,
        # theme...) và chạy retrieval với best-effort. Dùng cho TASK-17 để đo retrieval
        # + generation thuần, không đo cơ chế Confirmation Loop. KHÔNG dùng trong production.
        if bypass_completeness and not query_plan["is_complete"]:
            logger.info(
                f"run_pipeline: bypass_completeness=True — bỏ qua missing={query_plan['missing_fields']}, "
                f"tiếp tục retrieval với best-effort"
            )
            query_plan["is_complete"] = True

        # Thiếu thông tin → yêu cầu xác nhận
        if not query_plan["is_complete"]:
            confirmation_prompt = build_confirmation_prompt(query_plan["missing_fields"])
            elapsed = time.perf_counter() - t_start
            return PipelineResult(
                question=question,
                query_plan=query_plan,
                confirmation_needed=True,
                confirmation_prompt=confirmation_prompt,
                lccids_count=0,
                top_k_count=0,
                context_tokens=0,
                context="",
                answer="",
                citations=[],
                context_used=False,
                elapsed_seconds=round(elapsed, 2),
            )

        # --- TEMPORAL LAYER (Option C Phần 2) ---
        # Khi câu hỏi có yếu tố thời gian/dở dang/regime change, điều chỉnh
        # query_plan["temporal"] để retrieval bao gồm VB hết hiệu lực.
        ti = query_plan.get("temporal_intent", {}) or {}
        if ti.get("has_temporal_context"):
            case_status = ti.get("case_status")
            anchor = ti.get("temporal_anchor")
            # Hồ sơ dở dang / sự kiện mới phát sinh có thể span 2 regime → broad retrieve
            # để pull CẢ VB lúc nộp lẫn VB hiện hành. Hệ thống sẽ trình bày 2 khung
            # cho user, không tự quyết áp dụng cái nào (xem prompt rule TEMPORAL).
            if case_status in ("do-dang", "moi"):
                resolved = None
                reason = f"span-regime (case_status={case_status})"
            else:
                resolved = _resolve_temporal_anchor(anchor)
                reason = f"strict date={resolved}" if resolved else "broad (vague anchor)"
            query_plan = dict(query_plan)  # immutable copy
            query_plan["temporal"] = resolved
            logger.info(
                f"run_pipeline: TEMPORAL MODE — anchor='{anchor}' "
                f"status='{case_status}' → {reason}"
            )

        # --- TASK-11: Sub-graph Extraction ---
        logger.info("run_pipeline: extract_subgraph")
        norm_ids, graph_comp_ids = extract_subgraph(
            question, query_plan, neo4j_driver, qdrant_client, model
        )
        logger.info(f"run_pipeline: {len(norm_ids)} norm_ids, {len(graph_comp_ids)} graph_comp_ids từ Stage 2+3")

        # Không tìm được văn bản liên quan
        if not norm_ids:
            elapsed = time.perf_counter() - t_start
            return PipelineResult(
                question=question,
                query_plan=query_plan,
                confirmation_needed=False,
                confirmation_prompt=None,
                lccids_count=0,
                top_k_count=0,
                context_tokens=0,
                context="",
                answer="Không tìm thấy văn bản pháp luật liên quan đến câu hỏi này.",
                citations=[],
                context_used=False,
                elapsed_seconds=round(elapsed, 2),
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
        )
        logger.info(f"run_pipeline: {len(scored_units)} scored units")

        # --- TASK-13a: Context Assembly ---
        logger.info("run_pipeline: assemble_context")
        context = assemble_context(scored_units, neo4j_driver, max_tokens=max_tokens)
        context_tokens = max(1, int(len(context) / 3.5))

        # --- TASK-13b: Answer Generation ---
        logger.info("run_pipeline: generate_answer")
        result = generate_answer(question, context, anthropic_client, cache_dir=llm_cache_dir)

        elapsed = time.perf_counter() - t_start
        logger.info(
            f"run_pipeline: hoàn thành trong {elapsed:.1f}s — "
            f"{len(result['citations'])} citations"
        )

        return PipelineResult(
            question=question,
            query_plan=query_plan,
            confirmation_needed=False,
            confirmation_prompt=None,
            lccids_count=len(norm_ids),
            top_k_count=len(scored_units),
            context_tokens=context_tokens,
            context=context,
            answer=result["answer"],
            citations=result["citations"],
            context_used=result["context_used"],
            elapsed_seconds=round(elapsed, 2),
        )

    finally:
        if _own_clients:
            neo4j_driver.close()
