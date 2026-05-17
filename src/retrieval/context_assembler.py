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

    # Tôn trọng thứ tự RRF từ hybrid_search (đã tích hợp tier multiplier + graph boost).
    # Sort lại theo tier sẽ phá hoại boost: Tier 4 (NQ địa phương, NQ 254 với tier=1
    # nhưng AMENDS) bị đẩy xuống cuối context, dễ bị token budget cắt.
    # LLM vẫn nhận tier qua header "[Tier X | Hiệu lực: YYYY-MM-DD]" của từng block,
    # nên việc áp dụng lex superior/posterior không phụ thuộc vào thứ tự block.
    sorted_units = sorted(
        scored_text_units,
        key=lambda u: -u["rrf_score"],
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

QUY TẮC ƯU TIÊN VĂN BẢN (BẮT BUỘC):
Mỗi đoạn trong CONTEXT có header chứa metadata [Tier X | Hiệu lực: YYYY-MM-DD].
Khi hai hoặc nhiều đoạn quy định về CÙNG MỘT vấn đề mà NỘI DUNG MÂU THUẪN nhau, áp dụng các quy tắc sau theo thứ tự:
  1. Lex superior (cấp bậc): Văn bản Tier THẤP HƠN có giá trị pháp lý CAO HƠN (Tier 1 > Tier 2 > Tier 3 > Tier 4).
  2. Lex posterior (thời gian): Nếu ĐỒNG CẤP (cùng Tier), văn bản có ngày hiệu lực MỚI HƠN thay thế quy định cũ.
  3. Lex specialis (đặc thù): Nếu đồng cấp và đồng thời, văn bản quy định RIÊNG cho một địa phương hoặc lĩnh vực cụ thể được ưu tiên hơn văn bản quy định chung.
Khi phát hiện mâu thuẫn, PHẢI nêu rõ: "Lưu ý: Quy định tại [văn bản cũ] đã được sửa đổi/thay thế bởi [văn bản mới, ngày hiệu lực]."

PHẠM VI CORPUS (BẮT BUỘC ĐỌC TRƯỚC KHI TRẢ LỜI):
Hệ thống này chỉ lập chỉ mục PHÁP LUẬT ĐẤT ĐAI, HỘ TỊCH và NUÔI CON NUÔI tại Việt Nam.
Các chủ đề SAU ĐÂY NẰM NGOÀI PHẠM VI — phải TỪ CHỐI trả lời, KHÔNG được trích dẫn:
  - Phí công chứng, lệ phí trước bạ (thuộc Luật Công chứng + Luật Phí, lệ phí — không có trong corpus)
  - Thuế thu nhập cá nhân, thuế giá trị gia tăng, thuế khác (thuộc Luật Thuế — không có trong corpus)
  - Pháp luật dân sự, hình sự, hành chính, lao động, đầu tư, doanh nghiệp (ngoài 3 lĩnh vực trên)
  - Quy định nội bộ ngân hàng, quy định doanh nghiệp tư nhân
Khi gặp câu hỏi thuộc các chủ đề trên, dù CONTEXT có chứa từ khoá tương tự ("phí", "thuế", "đầu tư" trong Luật Đất đai), PHẢI trả lời chính xác như sau và KHÔNG TẠO CITATION nào:
  "Câu hỏi này không thuộc phạm vi tài liệu pháp luật mà hệ thống đang lập chỉ mục (đất đai, hộ tịch, nuôi con nuôi). Vui lòng tham khảo các văn bản pháp luật chuyên ngành tương ứng."

YÊU CẦU KHÁC:
- Trả lời bằng tiếng Việt, rõ ràng, súc tích.
- BẮT BUỘC TRÌNH BÀY NGHĨA VỤ TÀI CHÍNH: Khi trả lời các câu hỏi về "điều kiện", "quy trình", "thủ tục" liên quan đến một địa phương trong 3 lĩnh vực trên, BẮT BUỘC phải đưa ra CÁC YẾU TỐ TÀI CHÍNH (hạn mức giao đất, lệ phí thẩm định, tiền bảo vệ đất lúa, các tỷ lệ thu tiền sử dụng đất ưu đãi 30%/50%/100%) nếu có trong CONTEXT. (Lưu ý: chỉ áp dụng cho phí/lệ phí thuộc 3 lĩnh vực trên, KHÔNG áp dụng cho phí công chứng / thuế TNCN.)
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
