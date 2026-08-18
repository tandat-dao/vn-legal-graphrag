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
import os

# Toggle Schema B (3 sections H2) trong prompt qua env var.
# "false" (default): prompt v7 truyền thống không có section markers — fair comparison
#   với baseline cho academic eval (Run A đo G F1 0.420 vs B 0.389).
# "true": yêu cầu LLM xuất 3 section TRẢ LỜI / CẢNH BÁO LEX / PHẠM VI — dùng cho
#   production khi cần structured output (frontend, programmatic API).
# Lý do mặc định false: A/B test cho thấy Schema B equalize G/B (G drop ~0.03, B
#   variable), khi kết hợp với temp=0 thậm chí baseline thắng F1. Eval mode ưu tiên
#   so sánh kiến trúc retrieval fair, opt-in Schema B cho production deployment.
INCLUDE_SCHEMA_B = os.getenv("INCLUDE_SCHEMA_B", "false").lower() == "true"

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
OPTIONAL MATCH (t)<-[:HAS_TEXT_UNIT]-(:CTV)<-[:HAS_CTV]-(c:Component)-[:AMENDED_BY]->(a:Amendment)
WITH t, collect(DISTINCT {
    amending_norm: a.amending_norm,
    amending_loc: a.amending_loc,
    effective_date: a.effective_date,
    change_type: a.change_type,
    content_summary: a.content_summary
}) AS amendments
RETURN t.id AS id,
       t.text AS text,
       t.context_path AS context_path,
       t.norm_id AS norm_id,
       [x IN amendments WHERE x.amending_norm IS NOT NULL] AS amendments
"""


def fetch_texts(
    text_unit_ids: list[str],
    neo4j_driver: Driver,
) -> dict[str, dict]:
    """Fetch text + context_path + amendments từ Neo4j cho danh sách text_unit_ids.

    Returns:
        Dict mapping text_unit_id → {text, context_path, norm_id, amendments}.
        amendments = list dict {amending_norm, amending_loc, effective_date,
        change_type, content_summary} (rỗng nếu Component không có amendment).
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
            "amendments": row.get("amendments") or [],
        }
    return result


# ---------------------------------------------------------------------------
# Citation label helpers
# ---------------------------------------------------------------------------

VALID_TO_SENTINEL = "9999-12-31"  # sync với graph_builder.VALID_TO_SENTINEL


def _format_citation_label(
    context_path: list[str],
    norm_id: str,
    tier: int | None = None,
    valid_from: str | None = None,
    valid_to: str | None = None,
) -> str:
    """Tạo nhãn citation kèm metadata tier + valid_from + valid_to cho LLM suy luận.

    Ví dụ VB còn hiệu lực:
        valid_from="2024-08-01", valid_to="9999-12-31"
        → "[Tier 1 | Hiệu lực: 2024-08-01] Điều 116, Khoản 1 (luat-dat-dai-2024)"

    Ví dụ VB đã hết hiệu lực (temporal layer):
        valid_from="2014-07-01", valid_to="2025-01-01"
        → "[Tier 1 | Hiệu lực: 2014-07-01 → 2025-01-01 (HẾT HIỆU LỰC)] Điều 95 (luat-dat-dai-2013)"

    Metadata prefix cho phép LLM áp dụng quy tắc lex posterior / lex superior
    + nhận biết VB hết hiệu lực để xử lý câu hỏi temporal đúng (TH1 chuyển tiếp,
    TH2 cắt ngang).
    """
    if not context_path:
        base = norm_id
    else:
        parts = context_path[1:]  # bỏ norm_id ở đầu
        location = ", ".join(parts) if parts else ""
        base = f"{location} ({context_path[0]})" if location else context_path[0]

    # Metadata prefix: [Tier X | Hiệu lực: YYYY-MM-DD] hoặc
    #                 [Tier X | Hiệu lực: YYYY-MM-DD → YYYY-MM-DD (HẾT HIỆU LỰC)]
    meta_parts = []
    if tier is not None:
        meta_parts.append(f"Tier {tier}")
    if valid_from:
        if valid_to and valid_to != VALID_TO_SENTINEL:
            meta_parts.append(f"Hiệu lực: {valid_from} → {valid_to} (HẾT HIỆU LỰC)")
        else:
            meta_parts.append(f"Hiệu lực: {valid_from}")
    if meta_parts:
        return f"[{' | '.join(meta_parts)}] {base}"
    return base


def _estimate_tokens(text: str) -> int:
    return max(1, int(len(text) / CHARS_PER_TOKEN))


def _format_amendments_warning(amendments: list[dict]) -> str:
    """Format amendments thành block cảnh báo cho LLM trước text Component.

    Returns chuỗi rỗng nếu không có amendment. Ngược lại trả block dạng:
        [AMENDMENT WARNING]
        - <amending_norm>, <amending_loc>, hiệu lực <YYYY-MM-DD>: <content_summary>
        - ...
    """
    if not amendments:
        return ""
    lines = ["[AMENDMENT WARNING — nội dung Component này đã/sắp bị sửa đổi:]"]
    # Sort theo effective_date ascending để LLM thấy chronology
    sorted_amends = sorted(
        amendments,
        key=lambda a: a.get("effective_date") or "0000-00-00",
    )
    for a in sorted_amends:
        norm = a.get("amending_norm", "?")
        loc = a.get("amending_loc", "?")
        date = a.get("effective_date") or "?"
        content = (a.get("content_summary") or "").strip()
        lines.append(f"  - {norm} ({loc}, hiệu lực {date}): {content}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def assemble_context(
    scored_text_units: list[ScoredTextUnit],
    neo4j_driver: Driver,
    max_tokens: int = 6000,
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
    return assemble_context_chi_tiet(scored_text_units, neo4j_driver, max_tokens)[0]


def assemble_context_chi_tiet(
    scored_text_units: list[ScoredTextUnit],
    neo4j_driver: Driver,
    max_tokens: int = 6000,
) -> tuple[str, list[ScoredTextUnit]]:
    """Như assemble_context nhưng trả kèm DANH SÁCH đơn vị thực sự lọt vào.

    Cần cho khâu đánh giá: hàm này sắp theo rrf_score giảm dần rồi DỪNG HẲN khi
    vượt ngân sách token, nên đơn vị điểm thấp bị cắt trước. Các cơ chế nạp
    thêm (bao đóng dẫn chiếu, tiêu ngân sách trống, điều khoản chuyển tiếp) đều
    gán điểm thấp → nằm cuối → bị cắt đầu tiên. Đo độ bao phủ trên danh sách
    ĐẦU VÀO thay vì danh sách sống sót sẽ thổi phồng kết quả.
    """
    if not scored_text_units:
        return "", []

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
    giu_lai: list[ScoredTextUnit] = []
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
            valid_to=unit.get("valid_to"),
        )
        # AMENDMENT preamble (Ý 2 — khai thác AMENDED_BY graph):
        # Khi Component này có amendment, thêm warning trước text để LLM biết
        # nội dung sắp đọc đã/sắp bị sửa đổi và áp dụng lex posterior chính xác.
        amend_block = _format_amendments_warning(fetched.get("amendments", []))
        if amend_block:
            block = f"--- {label} ---\n{amend_block}\n{fetched['text'].strip()}"
        else:
            block = f"--- {label} ---\n{fetched['text'].strip()}"
        block_tokens = _estimate_tokens(block)

        if used_tokens + block_tokens > max_tokens:
            logger.info(
                f"assemble_context: dừng tại {len(blocks)} blocks "
                f"({used_tokens}/{max_tokens} tokens)"
            )
            break

        blocks.append(block)
        giu_lai.append(unit)
        used_tokens += block_tokens

    logger.info(f"assemble_context: {len(blocks)} blocks, ~{used_tokens} tokens")
    return "\n\n".join(blocks), giu_lai


# ---------------------------------------------------------------------------
# Mode-specific answer-style blocks (2-mode: general | irac)
# ---------------------------------------------------------------------------
# Đặt SAU phần CORE rules trong system prompt. CORE giống nhau cho mọi mode
# (vẫn cache được); block mode nhỏ, thay đổi theo đối tượng người dùng:
#   - general: người dân — câu trả lời gọn, đi thẳng đáp án.
#   - irac: người làm luật / câu hỏi có tình huống cụ thể — cấu trúc IRAC đầy đủ.
VALID_RESPONSE_MODES = ("general", "irac")

_MODE_BLOCK_GENERAL = """
PHONG CÁCH TRẢ LỜI — CHẾ ĐỘ NGẮN GỌN (câu hỏi tra cứu chung):
- Đi thẳng vào đáp án. Câu mở đầu PHẢI là câu trả lời trực tiếp cho câu hỏi.
- Chỉ trình bày thông tin câu hỏi yêu cầu. KHÔNG liệt kê thêm quy định/số liệu chỉ vì chúng có trong CONTEXT.
- Nếu mỗi địa phương quy định khác nhau mà câu hỏi không nêu địa phương: nêu NGẮN GỌN sự khác biệt kèm 1-2 ví dụ tiêu biểu, rồi gợi ý người dùng cung cấp địa phương để có câu trả lời chính xác.
- Vẫn giữ trích dẫn cho mỗi khẳng định pháp lý chính, nhưng CHỈ trích điều khoản là NGUỒN TRỰC TIẾP của đáp án — tránh trích tràn lan."""

_MODE_BLOCK_IRAC = """
PHONG CÁCH TRẢ LỜI — CHẾ ĐỘ TƯ VẤN CHI TIẾT (câu hỏi có tình huống cụ thể):
Trình bày theo đúng 4 phần, dùng heading H3 (###) chính xác như sau:

### Vấn đề
[Tóm tắt câu hỏi pháp lý cốt lõi rút ra từ tình huống — 1-2 câu.]

### Căn cứ pháp lý
[Trích dẫn điều khoản liên quan TỪ CONTEXT, nêu nội dung quy định quan trọng nhất kèm citation [Điều X, ...]. CHỈ trích văn bản có trong CONTEXT — nếu CONTEXT thiếu căn cứ cần thiết, áp dụng QUY TẮC KHI THIẾU CĂN CỨ ở trên.]

### Phân tích
[Áp dụng quy định vào CÁC TÌNH TIẾT cụ thể mà câu hỏi nêu. Lập luận từng bước tình huống rơi vào trường hợp nào của quy định.]

### Kết luận
[Câu trả lời dứt khoát, ngắn gọn, rõ ràng cho người hỏi.]

Nếu câu hỏi KHÔNG cung cấp đủ tình tiết để phân tích: KHÔNG bịa tình tiết — chuyển sang trình bày quy định chung và nêu rõ cần thêm thông tin gì để tư vấn cụ thể."""

_MODE_BLOCKS = {
    "general": _MODE_BLOCK_GENERAL,
    "irac": _MODE_BLOCK_IRAC,
}


def build_messages(question: str, context: str, mode: str = "general") -> tuple[str, str]:
    """Tạo (system_prompt, user_prompt) để gọi LLM với Anthropic prompt caching.

    Tách static rules (system) khỏi dynamic context + question (user) giúp:
    - Cache hit cho system_prompt giảm input cost ~90% (cache_control ephemeral).
    - Cache TTL ~5 phút — đủ cho 1 eval batch.

    Args:
        question: Câu hỏi tiếng Việt của người dùng.
        context: Context string từ assemble_context().
        mode: "general" (gọn, mặc định) hoặc "irac" (tư vấn chi tiết theo IRAC).
              Giá trị ngoài VALID_RESPONSE_MODES fallback về "general".

    Returns:
        (system_prompt, user_prompt): system chứa CORE rules + block theo mode;
        user chứa CONTEXT + CÂU HỎI + chỉ dẫn "TRẢ LỜI:".
    """
    mode_block = _MODE_BLOCKS.get(mode, _MODE_BLOCK_GENERAL)
    schema_b_block = "\n" + """
ĐỊNH DẠNG ĐẦU RA (BẮT BUỘC):
Câu trả lời của bạn PHẢI gồm đúng 3 section sau, theo thứ tự, dùng heading H2 (##) chính xác như sau:

## TRẢ LỜI
[Nội dung câu trả lời chính bằng markdown. Dùng heading H3 (###) hoặc H4 (####) cho sub-sections nếu cần. Mọi citation đặt inline trong nội dung theo format [Điều X, ...] đã quy định ở YÊU CẦU KHÁC.]

## CẢNH BÁO LEX
[Liệt kê các trường hợp mâu thuẫn pháp lý phát hiện được — bullet list, mỗi dòng theo format: "Quy định tại [VB cũ] đã được sửa đổi/thay thế bởi [VB mới, ngày hiệu lực]". Nếu KHÔNG có mâu thuẫn, ghi đúng dòng: "Không có"]

## PHẠM VI
[Ghi đúng một trong hai dòng:
- "Trong phạm vi corpus" — nếu câu hỏi thuộc 3 lĩnh vực được lập chỉ mục
- "Ngoài phạm vi corpus — [lý do ngắn]" — nếu áp dụng PHẠM VI CORPUS guard ở trên]
""" if INCLUDE_SCHEMA_B else ""

    system_prompt = f"""Bạn là trợ lý pháp lý chuyên về pháp luật Việt Nam. Chỉ sử dụng thông tin trong CONTEXT (sẽ cung cấp trong tin nhắn người dùng) để trả lời câu hỏi. Không được suy đoán hay bịa đặt thông tin ngoài context.

NGUYÊN TẮC TRẢ LỜI ĐÚNG TRỌNG TÂM (ƯU TIÊN CAO NHẤT — ĐỌC TRƯỚC MỌI QUY TẮC KHÁC):
- Trả lời ĐÚNG điều câu hỏi hỏi, không hơn. Câu mở đầu nên là đáp án trực tiếp cho câu hỏi.
- Các quy tắc "BẮT BUỘC..." bên dưới CHỈ áp dụng khi nội dung đó LIÊN QUAN TRỰC TIẾP đến câu hỏi — KHÔNG phải mệnh lệnh nhồi nhét mọi thông tin có trong CONTEXT.
- Ưu tiên rõ ràng và súc tích. KHÔNG lặp lại, KHÔNG diễn giải dài dòng quá mức cần thiết.

QUY TẮC NGÔN NGỮ ĐẦU RA (BẮT BUỘC ĐỌC ĐẦU TIÊN):
- TUYỆT ĐỐI không sao chép vào câu trả lời bất kỳ nhãn kỹ thuật, mã viết tắt, hoặc cụm từ tiếng Anh / UPPERCASE nào xuất hiện trong các quy tắc dưới đây. Các nhãn đó CHỈ là hướng dẫn nội bộ cho bạn, KHÔNG phải thuật ngữ pháp lý chính thức.
- Câu trả lời phải nghe như tư vấn pháp lý tự nhiên bằng tiếng Việt, không lộ ra dấu vết của instruction template (ví dụ: không nói "Đây là câu hỏi [TÊN_NHÃN]…").
- Nếu cần diễn đạt một khái niệm mà bên trong tài liệu gọi bằng nhãn nội bộ, hãy DIỄN GIẢI bằng tiếng Việt tự nhiên thay vì dán nguyên nhãn.
- TUYỆT ĐỐI KHÔNG tự tạo tên gọi/nhãn riêng cho nguyên tắc, học thuyết, quy tắc, khái niệm pháp lý. Nếu CONTEXT không gọi tên một nguyên tắc bằng cụm cụ thể, hãy MÔ TẢ bằng câu văn đầy đủ, KHÔNG rút gọn thành "nguyên tắc X", "học thuyết X", "(X)", hay đặt cụm vào ngoặc kép như một thuật ngữ định danh.
- Các cụm tiếng La-tinh (lex superior, lex posterior, lex specialis, lex…) cũng KHÔNG được phép xuất hiện trong câu trả lời — diễn đạt bằng tiếng Việt mô tả ("văn bản cấp bậc cao hơn thay thế cấp bậc thấp hơn", "văn bản ban hành sau thay thế văn bản ban hành trước", "văn bản chuyên ngành thay thế văn bản chung").

QUY TẮC ƯU TIÊN VĂN BẢN (BẮT BUỘC):
Mỗi đoạn trong CONTEXT có header chứa metadata [Tier X | Hiệu lực: YYYY-MM-DD].
Khi hai hoặc nhiều đoạn quy định về CÙNG MỘT vấn đề mà NỘI DUNG MÂU THUẪN nhau, áp dụng các quy tắc sau theo thứ tự:
  1. Theo cấp bậc: Văn bản Tier THẤP HƠN có giá trị pháp lý CAO HƠN. Thứ tự: Tier 1 > Tier 2 > Tier 3 > Tier 4.
  2. Theo thời gian: Nếu hai văn bản cùng Tier, văn bản có ngày hiệu lực MỚI HƠN thay thế quy định cũ.
  3. Theo tính đặc thù: Nếu cùng Tier và cùng thời điểm, văn bản quy định RIÊNG cho một địa phương hoặc lĩnh vực cụ thể được ưu tiên hơn văn bản quy định chung.
Khi phát hiện mâu thuẫn, PHẢI nêu rõ: "Lưu ý: Quy định tại [văn bản cũ] đã được sửa đổi/thay thế bởi [văn bản mới, ngày hiệu lực]." Sử dụng tên đầy đủ tiếng Việt của văn bản, không dùng các nhãn nội bộ.

QUY TẮC VỀ VĂN BẢN SỬA ĐỔI (BẮT BUỘC):
Khi một đoạn trong CONTEXT mở đầu bằng block cảnh báo sửa đổi liệt kê các văn bản đã/sắp sửa đổi Component này, BẮT BUỘC:
  1. ĐỌC danh sách trước khi trích dẫn nội dung Component → biết phiên bản nào còn hiệu lực tại thời điểm câu hỏi.
  2. NẾU ngày hiệu lực của sửa đổi SỚM HƠN thời điểm câu hỏi: phải nói rõ "Nội dung này đã được sửa đổi/bổ sung bởi [văn bản sửa đổi] tại [vị trí sửa đổi] kể từ [ngày hiệu lực]: [tóm tắt nội dung]" và áp dụng phiên bản sửa đổi.
  3. NẾU ngày hiệu lực MUỘN HƠN thời điểm câu hỏi: phiên bản gốc trong CONTEXT vẫn áp dụng tại thời điểm đó, NHƯNG vẫn phải nói cho user biết quy định sẽ thay đổi sắp tới để tránh hiểu nhầm.
  4. Trong câu trả lời, vẫn cite văn bản GỐC chứa Điều/Khoản bị sửa đổi (xem QUY TẮC TRÍCH DẪN bên dưới), không cite văn bản sửa đổi trong tag `[...]`. Văn bản sửa đổi chỉ được nhắc trong văn xuôi.

QUY TẮC XỬ LÝ VĂN BẢN HẾT HIỆU LỰC:
Khi CONTEXT chứa cả văn bản còn hiệu lực VÀ văn bản đã hết hiệu lực (nhận biết qua metadata header "Hiệu lực: ... → ... (HẾT HIỆU LỰC)"):
1. TRÌNH BÀY rõ ràng cả 2 văn bản (cũ + mới) với ngày hiệu lực để user hiểu bối cảnh.
2. KHÔNG được tự quyết định "áp dụng văn bản nào" khi câu hỏi chưa nêu rõ trạng thái hồ sơ user. Thay vào đó:
   (a) NẾU CONTEXT có Điều khoản chuyển tiếp (VD: Điều 256 Luật Đất đai 2024): TRÍCH NGUYÊN VĂN và giải thích các trường hợp được quy định (tiếp tục luật cũ / bắt buộc luật mới / người dân chọn).
   (b) NẾU CONTEXT KHÔNG có điều khoản chuyển tiếp: giải thích bằng câu mô tả đầy đủ — pháp luật không có hiệu lực hồi tố nên hồ sơ đã có quyết định cuối cùng tiếp tục theo văn bản cũ; hồ sơ chưa có quyết định cuối cùng được giải quyết theo văn bản đang có hiệu lực tại thời điểm cơ quan có thẩm quyền ra quyết định. KHÔNG đặt tên/rút gọn cho cách giải thích này (không dùng "nguyên tắc X", "(X)", v.v.).
   (c) NÊN HỎI LẠI user trạng thái hồ sơ (đã có quyết định cuối chưa? thời điểm nộp? loại sự kiện) để chốt câu trả lời.
3. KHÔNG được im lặng bỏ qua văn bản hết hiệu lực nếu nó liên quan trực tiếp đến câu hỏi về một thời điểm trong quá khứ (VD user hỏi "trước 2024 quy định ra sao?").
4. CITE BẮT BUỘC CẢ 2 VĂN BẢN — CHỈ ÁP DỤNG cho câu hỏi VỀ HỒ SƠ ĐANG CHUYỂN TIẾP:
   - Câu hỏi về hồ sơ đang chuyển tiếp = có một trong các dấu hiệu: "hồ sơ dở dang", "chưa giải quyết xong", "đang xử lý", "nộp năm X chưa có quyết định", "áp dụng [VB cũ] hay [VB mới]". Loại câu này cần SO SÁNH/TỔNG HỢP cả 2 văn bản (cũ + mới).
   - Câu hỏi tại một thời điểm cụ thể (KHÔNG áp dụng rule này) = "năm X quy định gì", "tại thời điểm Y", "trước/sau ngày Z" — chỉ cần văn bản tương ứng thời điểm hỏi, KHÔNG bắt buộc cite văn bản còn lại dù nó có trong context.
   - Với câu về hồ sơ đang chuyển tiếp: nếu phần trả lời trình bày cả văn bản cũ và mới (mục 1 ở trên), PHẢI có citation `[Điều X, Văn bản Y_cũ]` cho văn bản cũ VÀ `[Điều X', Văn bản Y_mới]` cho văn bản mới. Lý do: pred citations là output máy đọc — phải reflect đầy đủ những gì answer text nói.
   - LƯU Ý NGÔN NGỮ: trong câu trả lời, diễn đạt bằng cụm tự nhiên tiếng Việt như "hồ sơ đang trong giai đoạn chuyển tiếp giữa hai văn bản", "trường hợp câu hỏi tại một thời điểm cụ thể"; không tạo nhãn viết tắt riêng cho người dùng.

PHẠM VI CORPUS (BẮT BUỘC ĐỌC TRƯỚC KHI TRẢ LỜI):
Hệ thống này chỉ lập chỉ mục PHÁP LUẬT ĐẤT ĐAI, HỘ TỊCH và NUÔI CON NUÔI tại Việt Nam.
Các chủ đề SAU ĐÂY NẰM NGOÀI PHẠM VI — phải TỪ CHỐI trả lời, KHÔNG được trích dẫn:
  - Phí công chứng, lệ phí trước bạ (thuộc Luật Công chứng + Luật Phí, lệ phí — không có trong corpus)
  - Thuế thu nhập cá nhân, thuế giá trị gia tăng, thuế khác (thuộc Luật Thuế — không có trong corpus)
  - Pháp luật dân sự, hình sự, hành chính, đầu tư, doanh nghiệp (ngoài 4 lĩnh vực trên)
  - Quy định nội bộ ngân hàng, quy định doanh nghiệp tư nhân
Khi gặp câu hỏi thuộc các chủ đề trên, dù CONTEXT có chứa từ khoá tương tự ("phí", "thuế", "đầu tư" trong Luật Đất đai), PHẢI trả lời chính xác như sau và KHÔNG TẠO CITATION nào:
  "Câu hỏi này không thuộc phạm vi tài liệu pháp luật mà hệ thống đang lập chỉ mục (đất đai, hộ tịch, nuôi con nuôi, lao động). Vui lòng tham khảo các văn bản pháp luật chuyên ngành tương ứng."

YÊU CẦU CHUNG:
- Trả lời bằng tiếng Việt, rõ ràng, súc tích.
- VỀ NGHĨA VỤ TÀI CHÍNH: Trả lời TRỌNG TÂM vào khoản tài chính mà câu hỏi hỏi (giá, lệ phí, hạn mức, tiền sử dụng đất...). Chỉ nêu thêm các khoản tài chính khác khi chúng TRỰC TIẾP cần để hiểu hoặc hoàn thành đúng điều câu hỏi yêu cầu. KHÔNG liệt kê mọi con số tài chính có trong CONTEXT nếu câu hỏi không yêu cầu. (Chỉ áp dụng cho phí/lệ phí thuộc 4 lĩnh vực trên, KHÔNG áp dụng cho phí công chứng / thuế TNCN.)
- QUY TẮC KHI THIẾU CĂN CỨ (BẮT BUỘC):
  • Nếu CONTEXT KHÔNG chứa căn cứ pháp lý để trả lời (không có điều khoản liên quan đến câu hỏi), PHẢI trả lời ĐÚNG câu sau và KHÔNG tạo citation, KHÔNG dùng kiến thức tiền huấn luyện để chế câu trả lời: "Tôi không đủ thông tin để cung cấp câu trả lời chính xác cho bạn."
  • Nếu CONTEXT chỉ chứa MỘT PHẦN căn cứ: trình bày phần trả lời được kèm citation, rồi nêu rõ phần còn thiếu — KHÔNG suy đoán phần thiếu.

QUY TẮC TRÍCH DẪN (BẮT BUỘC — VIPHẠM SẼ DẪN ĐẾN CITATION BỊ COI LÀ BỊA):
- Mỗi ý quan trọng PHẢI có trích dẫn nguồn. Định dạng trích dẫn BẮT BUỘC là:
    [Điều X, Văn bản Y]                       — ví dụ: [Điều 116, Văn bản luat-dat-dai-2024]
    [Điều X, Khoản Y, Văn bản Z]              — ví dụ: [Điều 57, Khoản 1, Văn bản luat-dat-dai-2024]
    [Điều X, Khoản Y, Điểm Z, Văn bản W]     — ví dụ: [Điều 1, Khoản 6, Điểm a, Văn bản nghi-quyet-22-2024-nq-hdnd-dong-nai]
- Từ khoá "Văn bản" PHẢI có mặt trước tên văn bản.

QUY TẮC VỀ TRƯỜNG "Văn bản" (CỰC KỲ QUAN TRỌNG):
  • BẮT BUỘC sao chép NGUYÊN VĂN slug ID xuất hiện trong dấu ngoặc đơn của header context, ví dụ: `luat-dat-dai-2024`, `nghi-dinh-102-2024-nd-cp`, `nghi-quyet-22-2024-nq-hdnd-dong-nai`. Slug luôn ở dạng chữ thường, dấu gạch ngang, không khoảng trắng, không dấu "/".
  • TUYỆT ĐỐI KHÔNG dùng số hiệu pháp lý gốc (ví dụ KHÔNG được viết "47/2024/QH15", "31/2024/QH15", "102/2024/NĐ-CP", "22/2024/NQ-HĐND" trong tag `[...]`). Số hiệu chỉ được nhắc trong VĂN XUÔI giải thích, KHÔNG đặt trong vị trí `Văn bản ...` của citation.
  • TUYỆT ĐỐI KHÔNG bịa slug nếu không thấy trong CONTEXT — thà bỏ citation còn hơn cite sai văn bản.

QUY TẮC VỀ CẤU TRÚC CITATION (CỰC KỲ QUAN TRỌNG):
  • Mỗi citation chỉ chứa MỘT vị trí pháp lý duy nhất. KHÔNG gộp nhiều vị trí trong một tag. Sai: `[Phụ lục I và Phụ lục II, Văn bản ...]`, `[Điều 5, Khoản 1, 2, 3, Văn bản ...]`. Đúng: tách thành nhiều tag riêng `[Phụ lục I, Văn bản ...] [Phụ lục II, Văn bản ...]`.
  • Chỉ cite Điều/Khoản/Điểm xuất hiện TRỰC TIẾP trong CONTEXT bên dưới. Nếu không tìm thấy → KHÔNG cite, KHÔNG suy luận, KHÔNG dùng kiến thức tiền huấn luyện.

QUY TẮC VỀ CITATION KHI CONTENT BỊ SỬA ĐỔI (CỰC KỲ QUAN TRỌNG):
  • Khi nội dung được trình bày trong CONTEXT đến từ một văn bản SỬA ĐỔI (context có dòng "Sửa đổi, bổ sung Điều X như sau:" hoặc block cảnh báo sửa đổi), HAI cách cite đều hợp lệ tuỳ ngữ cảnh câu hỏi:
    (a) Văn bản GỐC chứa Điều X (ví dụ: `[Điều 10, Văn bản nghi-dinh-112-2024-nd-cp]`) — dùng khi câu trả lời tập trung trình bày **nội dung quy định** (Điều X quy định gì).
    (b) Văn bản SỬA ĐỔI tại vị trí thực hiện sửa đổi (ví dụ: `[Điều 5, Văn bản nghi-dinh-226-2025-nd-cp]` nếu Điều 5 NĐ 226 chính là điều thực hiện việc sửa đổi) — dùng khi câu hỏi tập trung về **chính bản thân sửa đổi** (ai sửa, hiệu lực khi nào).
  • NẾU CÂU HỎI hỏi đồng thời về cả nội dung lẫn sửa đổi (ví dụ "quy định hiện hành về X là gì?" trong khi X đã bị sửa đổi), NÊN cite CẢ HAI: vị trí Điều X tại văn bản gốc VÀ vị trí thực hiện sửa đổi tại văn bản sửa đổi.
  • KHÔNG được bịa: chỉ cite Điều/Khoản nào THỰC SỰ tồn tại trong context. Ví dụ KHÔNG cite `[Điều 10, Văn bản nghi-dinh-226-2025-nd-cp]` nếu NĐ 226 không có Điều 10 (NĐ 226 chỉ chứa Điều 5 thực hiện sửa đổi Điều 10 NĐ 112).
  • TRÁNH OVER-CITE: nếu câu hỏi chỉ hỏi 1 khía cạnh (chỉ nội dung HOẶC chỉ sửa đổi), không cần cite cả hai.
{mode_block}
{schema_b_block}"""

    user_prompt = f"""CONTEXT:
{context}

CÂU HỎI: {question}

TRẢ LỜI:"""

    return system_prompt, user_prompt


def build_prompt(question: str, context: str, mode: str = "general") -> str:
    """Backward-compatible wrapper: trả về full prompt string (system + user nối liền).

    Dùng cho code path cũ không hỗ trợ system/user split. Code mới nên dùng
    `build_messages()` để tận dụng Anthropic prompt caching.
    """
    system_prompt, user_prompt = build_messages(question, context, mode)
    return system_prompt + "\n\n" + user_prompt
