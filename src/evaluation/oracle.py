"""
Oracle retrieval baseline (E2a) — TRẦN chẩn đoán.

Đưa THẲNG các đoạn luật của ground-truth citation làm context cho generator
(giả định "retrieval hoàn hảo"). Trả lời câu hỏi chẩn đoán: lỗi còn lại là do
RETRIEVAL hay do GENERATION?

- Nếu Oracle F1 cao mà Full GraphRAG thấp → nút thắt ở retrieval.
- Nếu Oracle F1 cũng không cao → nút thắt ở generation (prompt/model).

Thuộc EVALUATION (phụ thuộc GT), không phải hệ thống độc lập → đặt ở src/evaluation.
Dùng CHÍNH generate_answer + prompt RAG của hệ thống (chỉ khác: context = GT chunks
thay vì retrieval) để so sánh công bằng.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import anthropic

from src.evaluation.build_review_sheet import build_text_index, resolve_citation
from src.retrieval.answer_generator import generate_answer

logger = logging.getLogger(__name__)


def _cit_label(c: dict) -> str:
    """Nhãn block mô phỏng assemble_context: 'Điều X, Khoản Y (van_ban)'."""
    parts = []
    if c.get("loai") == "phu_luc":
        d = c.get("dieu")
        parts.append("Phụ lục" if d == "_default" else f"Phụ lục {d}")
    elif c.get("dieu"):
        parts.append(f"Điều {c['dieu']}")
    if c.get("khoan"):
        parts.append(f"Khoản {c['khoan']}")
    if c.get("diem"):
        parts.append(f"Điểm {c['diem']}")
    return f"{', '.join(parts)} ({c.get('van_ban')})"


def build_oracle_context(gt_citations: list[dict], text_index: dict) -> str:
    """Ghép các đoạn luật GT thành context (format --- label --- \\n text)."""
    blocks = []
    for c in gt_citations:
        src = resolve_citation(c, text_index.get(c.get("van_ban"), []))
        if src:
            blocks.append(f"--- {_cit_label(c)} ---\n{src.strip()}")
    return "\n\n".join(blocks)


def run_oracle_query(
    question: str,
    gt_citations: list[dict],
    text_index: dict,
    llm_client: anthropic.Anthropic,
    cache_dir: Path | None = None,
    mode: str = "general",
) -> dict:
    """Chạy generator trên context = GT chunks. Trả về dict khớp shape baseline.

    text_index: kết quả build_text_index() (build MỘT LẦN, tái dùng cho cả test set).
    """
    t0 = time.perf_counter()
    context = build_oracle_context(gt_citations, text_index)
    gen = generate_answer(question, context, llm_client, cache_dir=cache_dir, mode=mode)
    return {
        "answer": gen["answer"],
        "citations": gen["citations"],
        "context_used": gen["context_used"],
        "top_k_count": len(gt_citations),
        "context": context,
        "elapsed_seconds": round(time.perf_counter() - t0, 2),
    }
