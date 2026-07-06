"""
Naive RAG Baseline — TASK-16
Baseline so sánh khoa học với GraphRAG: cùng dữ liệu (data/raw/*.md), cùng embedding
(BGE-M3), cùng LLM (Claude Sonnet 4.6 qua generate_answer), CHỈ KHÁC retrieval.

Retrieval đặc trưng "naive":
  - Fixed-size chunking trên text thô (mặc định 512 ký tự, overlap 50).
  - Không phân rã theo Điều/Khoản/Điểm/Tiết.
  - Không có Knowledge Graph, không có metadata filter, không có hybrid scoring.
  - Pure vector top-k cosine trên Qdrant collection riêng "baseline_legal_texts".

Mục đích: chứng minh giá trị gia tăng của ontology + graph traversal trong Phase 4.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from pathlib import Path
from typing import TypedDict

import anthropic
import yaml
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from src.ingestion.vectorizer import encode_text, load_model
from src.retrieval.answer_generator import generate_answer
from src.utils.llm_config import make_anthropic_client

logger = logging.getLogger(__name__)

COLLECTION_NAME = "baseline_legal_texts"
VECTOR_DIM = 1024
DEFAULT_CHUNK_SIZE = 512
DEFAULT_OVERLAP = 50
DEFAULT_TOP_K = 10
BATCH_SIZE = 100

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


# ---------------------------------------------------------------------------
# Output type — khớp PipelineResult để TASK-17 evaluation chấm được cùng một dict
# ---------------------------------------------------------------------------

class BaselineResult(TypedDict):
    question: str
    answer: str
    citations: list[dict]
    context_used: bool
    top_k_count: int
    context_tokens: int
    context: str           # full assembled context — dùng cho faithfulness eval
    elapsed_seconds: float
    # Các field GraphRAG không có trong baseline (để None nhằm giữ schema chung)
    query_plan: None
    lccids_count: int


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def fixed_chunker(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[str]:
    """Cắt text thành các chunk cố định theo ký tự, có overlap.

    Args:
        text: Nội dung text gốc (đã strip frontmatter).
        chunk_size: Số ký tự mỗi chunk (mặc định 512).
        overlap: Số ký tự chồng lấn giữa 2 chunk liền kề (mặc định 50).

    Returns:
        List các chunk string, không rỗng.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size phải > 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap phải trong [0, chunk_size)")

    text = text.strip()
    if not text:
        return []

    step = chunk_size - overlap
    chunks: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        chunk = text[i : i + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        if i + chunk_size >= n:
            break
        i += step
    return chunks


# ---------------------------------------------------------------------------
# File parsing
# ---------------------------------------------------------------------------

def _parse_md_file(path: Path) -> tuple[str, str]:
    """Tách frontmatter và body từ file .md. Trả về (norm_id, body).

    Raises:
        ValueError: nếu không có frontmatter hoặc thiếu field `id`.
    """
    content = path.read_text(encoding="utf-8")
    m = _FRONTMATTER_RE.match(content)
    if not m:
        raise ValueError(f"{path.name}: thiếu YAML frontmatter ở đầu file")
    meta = yaml.safe_load(m.group(1)) or {}
    norm_id = meta.get("id")
    if not norm_id:
        raise ValueError(f"{path.name}: thiếu field 'id' trong frontmatter")
    body = content[m.end() :]
    return norm_id, body


def _chunk_id(norm_id: str, idx: int) -> int:
    """Deterministic int ID cho Qdrant point (CLAUDE.md quy tắc #4)."""
    h = hashlib.sha256(f"{norm_id}#{idx}".encode()).hexdigest()[:16]
    return int(h, 16)


# ---------------------------------------------------------------------------
# Qdrant collection management
# ---------------------------------------------------------------------------

def _ensure_baseline_collection(client: QdrantClient) -> None:
    existing = {c.name for c in client.get_collections().collections}
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
        )
        logger.info(f"Tạo Qdrant collection '{COLLECTION_NAME}' (dim={VECTOR_DIM}).")
    else:
        logger.info(f"Collection '{COLLECTION_NAME}' đã tồn tại.")


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

def run_baseline_ingestion(
    data_dir: str,
    *,
    qdrant_client: QdrantClient | None = None,
    model=None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> dict:
    """Đọc tất cả data/raw/*.md, chunk, encode, upsert vào collection baseline.

    Idempotent: upsert sẽ overwrite vector cùng id (cùng norm_id + chunk_idx).

    Args:
        data_dir: Thư mục chứa các .md (thường là 'data/raw/').
        qdrant_client: Qdrant client (tự khởi tạo từ env nếu None).
        model: Embedding model BGE-M3 (tự load nếu None).
        chunk_size, overlap: Tham số chunking.

    Returns:
        Dict thống kê: {files_processed, total_chunks, collection}.
    """
    data_path = Path(data_dir)
    if not data_path.is_dir():
        raise ValueError(f"data_dir không tồn tại: {data_dir}")

    own_qdrant = qdrant_client is None
    if own_qdrant:
        qdrant_client = QdrantClient(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", "6333")),
        )
    if model is None:
        model = load_model()

    _ensure_baseline_collection(qdrant_client)

    md_files = sorted(data_path.glob("*.md"))
    # Bỏ qua các file phụ trợ không phải văn bản pháp luật
    md_files = [
        p for p in md_files
        if p.name not in {"mapping_table.md", "crossref_decisions.md", "review_log.md"}
    ]
    logger.info(f"Tìm thấy {len(md_files)} file .md cần index.")

    total_chunks = 0
    batch: list[PointStruct] = []

    for path in md_files:
        try:
            norm_id, body = _parse_md_file(path)
        except ValueError as e:
            logger.warning(f"Bỏ qua {path.name}: {e}")
            continue

        chunks = fixed_chunker(body, chunk_size=chunk_size, overlap=overlap)
        logger.info(f"  {path.name} → {len(chunks)} chunks (norm_id={norm_id})")

        for idx, chunk_text in enumerate(chunks):
            vector = encode_text(model, chunk_text)
            payload = {
                "norm_id": norm_id,
                "chunk_idx": idx,
                "text": chunk_text,
            }
            batch.append(
                PointStruct(
                    id=_chunk_id(norm_id, idx),
                    vector=vector,
                    payload=payload,
                )
            )
            total_chunks += 1

            if len(batch) == BATCH_SIZE:
                qdrant_client.upsert(collection_name=COLLECTION_NAME, points=batch)
                batch = []

    if batch:
        qdrant_client.upsert(collection_name=COLLECTION_NAME, points=batch)

    logger.info(
        f"run_baseline_ingestion xong: {len(md_files)} files, {total_chunks} chunks."
    )

    if own_qdrant:
        qdrant_client.close()

    return {
        "files_processed": len(md_files),
        "total_chunks": total_chunks,
        "collection": COLLECTION_NAME,
    }


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

def _build_baseline_context(scored_chunks: list[dict]) -> str:
    """Ghép top-k chunks thành context string với header chỉ ra văn bản nguồn.

    Header dùng id văn bản (không có Điều/Khoản/Tier/valid_from vì baseline
    không biết structure) — LLM tự suy ra Điều X từ nội dung chunk nếu có.

    Format header: '--- Văn bản: {norm_id}, chunk {idx} ---'
    """
    blocks = []
    for c in scored_chunks:
        norm_id = c.get("norm_id", "unknown")
        idx = c.get("chunk_idx", -1)
        text = c.get("text", "").strip()
        if not text:
            continue
        blocks.append(f"--- Văn bản: {norm_id}, chunk {idx} ---\n{text}")
    return "\n\n".join(blocks)


def run_baseline_query(
    question: str,
    *,
    qdrant_client: QdrantClient | None = None,
    anthropic_client: anthropic.Anthropic | None = None,
    model=None,
    top_k: int = DEFAULT_TOP_K,
    llm_cache_dir: Path | None = None,
    mode: str = "general",
) -> BaselineResult:
    """Pure vector search + LLM. Trả về output schema giống run_pipeline().

    Args:
        question: Câu hỏi tiếng Việt.
        qdrant_client, anthropic_client, model: tự khởi tạo từ env nếu None.
        top_k: Số chunks lấy ra từ Qdrant (mặc định 10 — phù hợp với token budget LLM
               cho chunks 512 chars).

    Returns:
        BaselineResult — cùng schema PipelineResult của TASK-14 để TASK-17 evaluate
        chung được. Các field GraphRAG-only (query_plan, lccids_count, ...) = None/0.
    """
    t_start = time.perf_counter()

    own_qdrant = qdrant_client is None
    if own_qdrant:
        qdrant_client = QdrantClient(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", "6333")),
        )
    if anthropic_client is None:
        anthropic_client = make_anthropic_client()
    if model is None:
        model = load_model()

    try:
        # Vector search thuần — không filter, không hybrid
        question_vec = encode_text(model, question)
        hits = qdrant_client.query_points(
            collection_name=COLLECTION_NAME,
            query=question_vec,
            limit=top_k,
        ).points
        scored_chunks = [
            {
                "norm_id": h.payload.get("norm_id"),
                "chunk_idx": h.payload.get("chunk_idx"),
                "text": h.payload.get("text", ""),
                "score": h.score,
            }
            for h in hits
        ]
        logger.info(f"run_baseline_query: {len(scored_chunks)} chunks từ Qdrant")

        context = _build_baseline_context(scored_chunks)
        context_tokens = max(1, int(len(context) / 3.5))

        if not context:
            elapsed = time.perf_counter() - t_start
            return BaselineResult(
                question=question,
                answer="Không tìm thấy chunk liên quan trong baseline corpus.",
                citations=[],
                context_used=False,
                top_k_count=0,
                context_tokens=0,
                context="",
                elapsed_seconds=round(elapsed, 2),
                query_plan=None,
                lccids_count=0,
            )

        # Dùng đúng generate_answer của GraphRAG để cùng prompt + cùng LLM + cùng mode
        gen = generate_answer(question, context, anthropic_client, cache_dir=llm_cache_dir, mode=mode)

        elapsed = time.perf_counter() - t_start
        logger.info(
            f"run_baseline_query: hoàn thành trong {elapsed:.1f}s — "
            f"{len(gen['citations'])} citations"
        )

        return BaselineResult(
            question=question,
            answer=gen["answer"],
            citations=gen["citations"],
            context_used=gen["context_used"],
            top_k_count=len(scored_chunks),
            context_tokens=context_tokens,
            context=context,
            elapsed_seconds=round(elapsed, 2),
            query_plan=None,
            lccids_count=0,
        )

    finally:
        if own_qdrant:
            qdrant_client.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Naive RAG baseline (TASK-16)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ing = sub.add_parser("ingest", help="Chunk + index data/raw/*.md vào Qdrant baseline")
    p_ing.add_argument("--data-dir", default="data/raw/")
    p_ing.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    p_ing.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP)

    p_q = sub.add_parser("query", help="Chạy 1 câu hỏi qua baseline")
    p_q.add_argument("question")
    p_q.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)

    args = parser.parse_args()

    if args.cmd == "ingest":
        stats = run_baseline_ingestion(
            args.data_dir, chunk_size=args.chunk_size, overlap=args.overlap
        )
        print(stats)
    elif args.cmd == "query":
        result = run_baseline_query(args.question, top_k=args.top_k)
        print(f"\n=== ANSWER ({result['elapsed_seconds']}s, {len(result['citations'])} citations) ===\n")
        print(result["answer"])
        print(f"\n=== CITATIONS ({len(result['citations'])}) ===")
        for c in result["citations"]:
            print(f"  - {c}")
