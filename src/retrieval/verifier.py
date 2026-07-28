"""
Verifier Agent — tầng multi-agent (Generator → Verifier → prune).

Mục đích: kiểm soát OVER-CITATION — nguyên nhân chi phối khiến F1 thấp dù Norm
Recall đã cao (ROOT_CAUSE_ANALYSIS: 47 citation dư là nguyên nhân DOMINANT của
precision thấp). Pipeline gốc chỉ có một lượt Generator sinh đáp án rồi parse
citation, không ai kiểm lại. Verifier là một agent phản biện đọc lại đáp án nháp
và LỌC citation trước khi trả ra — mẫu Self-Refine / CRITIC.

Thiết kế = "faithfulness metric được nâng thành filter inline": tái dùng trực tiếp
hạ tầng `src/evaluation/faithfulness.py` (không có vòng import vì faithfulness chỉ
phụ thuộc anthropic/stdlib, không phụ thuộc retrieval).

  Lớp 1 — Grounding (deterministic, $0): citation có header tương ứng trong
    CONTEXT không? Reuse `faithfulness._citation_in_context`. Citation không
    grounded ~= bịa (hallucinated) → DROP (an toàn: gần như không bao giờ đúng).

  Lớp 2 — Support (LLM judge Haiku, ~$0.001/citation, TÙY CHỌN): chunk được cite
    có THỰC SỰ khẳng định claim không? Reuse `faithfulness._judge_citation`.
    Mặc định UNSUPPORTED → "flag" (giữ lại nhưng đánh dấu) để tránh over-prune do
    judge noise; `drop_unsupported=True` để prune cứng.

Chính sách prune BẢO THỦ: chỉ DROP khi chắc chắn (ungrounded; hoặc unsupported
khi drop_unsupported=True). Mục tiêu nâng precision mà không hi sinh recall oan.

Tier:
  0 = no-op (trả nguyên citations) — nhánh ablation "KHÔNG verifier"
  1 = grounding prune (deterministic, $0) — MẶC ĐỊNH khi bật verify
  2 = grounding + LLM support judge (TỐN Haiku API)
"""
from __future__ import annotations

import logging
from typing import TypedDict

import anthropic

# Tái dùng có chủ đích phần lõi của faithfulness (grounding + judge). faithfulness
# không import retrieval nên không tạo circular import.
from src.evaluation.faithfulness import (
    _citation_in_context,
    _extract_chunk_for_citation,
    _judge_citation,
)

logger = logging.getLogger(__name__)

VALID_VERIFY_TIERS = (0, 1, 2)


class CitationVerdict(TypedDict):
    citation: dict
    grounded: bool
    supported: bool | None    # None nếu Tier < 2 (không chạy judge)
    verdict: str              # "keep" | "drop" | "flag"
    reason: str


class VerifierResult(TypedDict):
    filtered_citations: list[dict]   # citations sau khi bỏ verdict 'drop'
    verdicts: list[CitationVerdict]  # chi tiết từng citation (cho phân tích/ablation)
    n_input: int
    n_kept: int
    n_dropped: int
    n_flagged: int
    tier: int                        # tier THỰC SỰ chạy (downgrade nếu thiếu client)


def _passthrough(citations: list[dict], tier: int, reason: str) -> VerifierResult:
    """Trả nguyên citations (Tier 0 hoặc không có citation)."""
    return VerifierResult(
        filtered_citations=list(citations),
        verdicts=[
            CitationVerdict(citation=c, grounded=True, supported=None,
                            verdict="keep", reason=reason)
            for c in citations
        ],
        n_input=len(citations),
        n_kept=len(citations),
        n_dropped=0,
        n_flagged=0,
        tier=tier,
    )


def verify_citations(
    question: str,
    context: str,
    answer: str,
    citations: list[dict],
    *,
    tier: int = 1,
    llm_client: anthropic.Anthropic | None = None,
    drop_unsupported: bool = False,
) -> VerifierResult:
    """Phản biện + lọc citations của đáp án nháp.

    Args:
        question: câu hỏi gốc (lưu lại + dùng cho relevance judge tương lai).
        context: context string từ assemble_context — nguồn grounding.
        answer: full answer text từ generate_answer — cho judge snippet.
        citations: pred citations từ parse_citations.
        tier: 0 no-op | 1 grounding ($0) | 2 grounding + support judge (API).
        llm_client: Anthropic client; BẮT BUỘC cho tier 2 (thiếu → fallback tier 1).
        drop_unsupported: tier 2 — True: UNSUPPORTED bị DROP; False: chỉ "flag"
            (giữ lại). Mặc định False (bảo thủ, tránh over-prune).

    Returns:
        VerifierResult: filtered_citations (đã bỏ 'drop') + verdict từng citation.
        Citations giữ nguyên thứ tự đầu vào.
    """
    if tier not in VALID_VERIFY_TIERS:
        logger.warning(f"verify_citations: tier={tier} không hợp lệ → dùng tier 1")
        tier = 1

    # Tier 0 hoặc không có citation: no-op
    if tier == 0:
        return _passthrough(citations, tier=0, reason="verifier_disabled")
    if not citations:
        return _passthrough(citations, tier=tier, reason="no_citations")

    enable_t2 = tier >= 2 and llm_client is not None
    if tier >= 2 and llm_client is None:
        logger.warning("verify_citations: tier 2 cần llm_client — fallback tier 1 ($0)")

    verdicts: list[CitationVerdict] = []
    for c in citations:
        grounded = _citation_in_context(c, context)
        if not grounded:
            verdicts.append(CitationVerdict(
                citation=c, grounded=False, supported=None,
                verdict="drop", reason="citation_not_in_context"))
            continue

        if not enable_t2:
            verdicts.append(CitationVerdict(
                citation=c, grounded=True, supported=None,
                verdict="keep", reason="grounded"))
            continue

        # Tier 2: hỏi judge chunk có support claim không
        chunk = _extract_chunk_for_citation(c, context)
        if not chunk:
            # Grounded nhưng không tách được chunk → giữ (không phạt oan)
            verdicts.append(CitationVerdict(
                citation=c, grounded=True, supported=None,
                verdict="keep", reason="chunk_extract_failed"))
            continue
        judge = _judge_citation(c, answer, chunk, llm_client)
        if judge["supported"]:
            verdicts.append(CitationVerdict(
                citation=c, grounded=True, supported=True,
                verdict="keep", reason=judge["reason"]))
        else:
            verdicts.append(CitationVerdict(
                citation=c, grounded=True, supported=False,
                verdict="drop" if drop_unsupported else "flag",
                reason=judge["reason"]))

    filtered = [v["citation"] for v in verdicts if v["verdict"] != "drop"]
    n_dropped = sum(1 for v in verdicts if v["verdict"] == "drop")
    n_flagged = sum(1 for v in verdicts if v["verdict"] == "flag")

    logger.info(
        f"verify_citations: tier={2 if enable_t2 else 1} in={len(citations)} "
        f"kept={len(filtered)} dropped={n_dropped} flagged={n_flagged}"
    )
    return VerifierResult(
        filtered_citations=filtered,
        verdicts=verdicts,
        n_input=len(citations),
        n_kept=len(filtered),
        n_dropped=n_dropped,
        n_flagged=n_flagged,
        tier=2 if enable_t2 else 1,
    )
