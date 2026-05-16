"""
Context Assembler — TASK-13 (phần 1)
Nhận ScoredTextUnit list từ TASK-12, fetch text từ Neo4j, sắp xếp theo tier,
cắt tỉa theo token budget, trả về context string + build prompt.

Thứ tự sắp xếp: tier 1 trước tier 4 (Luật → NĐ → TT → QĐ UBND),
cùng tier sắp xếp theo rrf_score giảm dần.

Token budget: ước tính ≈ len(text) / 3.5 chars per token (Vietnamese BPE heuristic).
"""
import json
import logging

from neo4j import Driver

from src.retrieval.semantic_filter import ScoredTextUnit

logger = logging.getLogger(__name__)

CHARS_PER_TOKEN = 3.5  # heuristic cho tiếng Việt với BPE tokenizer


# ---------------------------------------------------------------------------
# Neo4j text fetch
# ---------------------------------------------------------------------------

_FETCH_TEXT_CYPHER = """
MATCH (t:TextUnit)
WHERE t.id IN $ids
RETURN t.id AS id,
       t.text AS text,
       t.context_path AS context_path,
       t.norm_id AS norm_id
"""


def fetch_texts(
    text_unit_ids: list[str],
    neo4j_driver: Driver,
) -> dict[str, dict]:
    """Fetch text + context_path từ Neo4j cho danh sách text_unit_ids.

    Returns:
        Dict mapping text_unit_id → {text, context_path, norm_id}.
    """
    if not text_unit_ids:
        return {}
    with neo4j_driver.session() as session:
        rows = session.run(_FETCH_TEXT_CYPHER, ids=text_unit_ids).data()

    result = {}
    for row in rows:
        context_path = row["context_path"]
        # context_path lưu trong Neo4j dưới dạng JSON string hoặc list
        if isinstance(context_path, str):
            try:
                context_path = json.loads(context_path)
            except (json.JSONDecodeError, TypeError):
                context_path = [context_path]
        result[row["id"]] = {
            "text": row["text"] or "",
            "context_path": context_path or [],
            "norm_id": row["norm_id"] or "",
        }
    return result


# ---------------------------------------------------------------------------
# Citation label helpers
# ---------------------------------------------------------------------------

def _format_citation_label(
    context_path: list[str],
    norm_id: str,
    tier: int | None = None,
    valid_from: str | None = None,
) -> str:
    """Tạo nhãn citation kèm metadata tier + valid_from cho LLM suy luận.

    Ví dụ:
        context_path=["luat-dat-dai-2024", "Điều 116", "Khoản 1"], tier=1, valid_from="2024-08-01"
        → "[Tier 1 | Hiệu lực: 2024-08-01] Điều 116, Khoản 1 (luat-dat-dai-2024)"

    Metadata prefix cho phép LLM áp dụng quy tắc lex posterior / lex superior
    mà KHÔNG cần inline `amended_by` annotation trong markdown nguồn.
    """
    if not context_path:
        base = norm_id
    else:
        parts = context_path[1:]  # bỏ norm_id ở đầu
        location = ", ".join(parts) if parts else ""
        base = f"{location} ({context_path[0]})" if location else context_path[0]

    # Metadata prefix: [Tier X | Hiệu lực: YYYY-MM-DD]
    meta_parts = []
    if tier is not None:
        meta_parts.append(f"Tier {tier}")
    if valid_from:
        meta_parts.append(f"Hiệu lực: {valid_from}")
    if meta_parts:
        return f"[{' | '.join(meta_parts)}] {base}"
    return base


def _estimate_tokens(text: str) -> int:
    return max(1, int(len(text) / CHARS_PER_TOKEN))


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def assemble_context(
    scored_text_units: list[ScoredTextUnit],
    neo4j_driver: Driver,
    max_tokens: int = 3000,
) -> str:
    """Sắp xếp TextUnit theo tier, fetch text, cắt tỉa theo token budget.

    Args:
        scored_text_units: Kết quả từ hybrid_search() (TASK-12).
        neo4j_driver: Neo4j driver để fetch text.
        max_tokens: Token budget tối đa cho context.

    Returns:
        Context string sẵn sàng đưa vào LLM prompt.
        Rỗng nếu không có text_unit nào.
    """
    if not scored_text_units:
        return ""

    # Sắp xếp: tier tăng dần (1 trước), cùng tier thì rrf_score giảm dần
    sorted_units = sorted(
        scored_text_units,
        key=lambda u: (u["tier"] or 99, -u["rrf_score"]),
    )

    # Fetch text từ Neo4j
    ids = [u["text_unit_id"] for u in sorted_units]
    text_map = fetch_texts(ids, neo4j_driver)

    # Build context với token budget
    blocks: list[str] = []
    used_tokens = 0

    for unit in sorted_units:
        tid = unit["text_unit_id"]
        fetched = text_map.get(tid)
        if not fetched or not fetched["text"].strip():
            continue

        label = _format_citation_label(
            fetched["context_path"],
            fetched["norm_id"],
            tier=unit.get("tier"),
            valid_from=unit.get("valid_from"),
        )
        block = f"--- {label} ---\n{fetched['text'].strip()}"
        block_tokens = _estimate_tokens(block)

        if used_tokens + block_tokens > max_tokens:
            logger.info(
                f"assemble_context: dừng tại {len(blocks)} blocks "
                f"({used_tokens}/{max_tokens} tokens)"
            )
            break

        blocks.append(block)
        used_tokens += block_tokens

    logger.info(f"assemble_context: {len(blocks)} blocks, ~{used_tokens} tokens")
    return "\n\n".join(blocks)


def build_prompt(question: str, context: str) -> str:
    """Tạo prompt yêu cầu LLM trả lời bằng tiếng Việt với trích dẫn bắt buộc.

    Format trích dẫn inline trong câu trả lời:
        [Điều X, Khoản Y, Văn bản Z]

    Args:
        question: Câu hỏi tiếng Việt của người dùng.
        context: Context string từ assemble_context().

    Returns:
        Prompt string hoàn chỉnh để gửi vào LLM.
    """
    return f"""Bạn là trợ lý pháp lý chuyên về pháp luật Việt Nam. Chỉ sử dụng thông tin trong CONTEXT dưới đây để trả lời câu hỏi. Không được suy đoán hay bịa đặt thông tin ngoài context.

Yêu cầu bắt buộc:
- Trả lời bằng tiếng Việt, rõ ràng, súc tích.
- Mỗi ý quan trọng PHẢI có trích dẫn nguồn. Định dạng trích dẫn BẮT BUỘC là:
    [Điều X, Văn bản Y]                       — ví dụ: [Điều 116, Văn bản luat-dat-dai-2024]
    [Điều X, Khoản Y, Văn bản Z]              — ví dụ: [Điều 57, Khoản 1, Văn bản luat-dat-dai-2024]
    [Điều X, Khoản Y, Điểm Z, Văn bản W]     — ví dụ: [Điều 1, Khoản 6, Điểm a, Văn bản nghi-quyet-22-2024-nq-hdnd-dong-nai]
  Từ khoá "Văn bản" PHẢI có mặt trước tên văn bản. Dùng id văn bản từ header "--- ... ---" trong CONTEXT.
- Nếu context không đủ thông tin để trả lời, nêu rõ điều đó.

CONTEXT:
{context}

CÂU HỎI: {question}

TRẢ LỜI:"""
