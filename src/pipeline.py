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
import time
from typing import TypedDict

import anthropic
from dotenv import load_dotenv
from neo4j import GraphDatabase
from qdrant_client import QdrantClient

from src.ingestion.vectorizer import load_model
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
    anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
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
        query_plan = plan_query(question, anthropic_client)
        logger.info(
            f"run_pipeline: plan={query_plan['theme']}/{query_plan['jurisdiction']} "
            f"complete={query_plan['is_complete']}"
        )

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
                answer="",
                citations=[],
                context_used=False,
                elapsed_seconds=round(elapsed, 2),
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
        result = generate_answer(question, context, anthropic_client)

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
            answer=result["answer"],
            citations=result["citations"],
            context_used=result["context_used"],
            elapsed_seconds=round(elapsed, 2),
        )

    finally:
        if _own_clients:
            neo4j_driver.close()
