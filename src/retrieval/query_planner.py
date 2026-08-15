"""
Query Planner — TASK-10
Nhận câu hỏi tiếng Việt, dùng mô hình ngôn ngữ để extract:
  theme, procedure, jurisdiction, temporal
Trả về QueryPlan TypedDict.

Quy tắc tự động cho jurisdiction:
  - Câu hỏi CÓ nêu tên địa phương → dùng đúng địa phương đó, BẤT KỂ lĩnh vực.
  - Câu hỏi KHÔNG nêu địa phương: Hộ tịch / Nuôi con nuôi → "toan-quoc";
    Đất đai → None (retrieval chạy best-effort).

Lịch sử: trước 2026-07-28 luật là "Hộ tịch và Nuôi con nuôi LUÔN gán toan-quoc",
xuất phát từ giai đoạn kho ngữ liệu chỉ có văn bản địa phương ở lĩnh vực đất đai.
Giả định đó hết đúng khi kho mở rộng đa lĩnh vực: hộ tịch có nghị quyết lệ phí
cấp tỉnh (NQ 11/2023 Đồng Nai, NQ 124/2016 TP.HCM). Chữ "LUÔN" khiến planner trả
"toan-quoc" ngay cả khi câu hỏi ghi rõ tên tỉnh, làm hard-filter Stage 2 gạt sạch
văn bản cấp tỉnh → F1 = 0 trên các câu hộ tịch có yếu tố địa phương.
"""
import hashlib
import json
import logging
import os
import re
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from typing import TypedDict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_THEMES = ["dat-dai", "ho-tich", "nuoi-con-nuoi"]

VALID_PROCEDURES = [
    "chuyen-muc-dich-su-dung-dat",
    "cap-so-do-lan-dau",
    "dang-ky-khai-sinh",
    "cap-ban-sao-trich-luc-ho-tich",
    "dang-ky-nuoi-con-nuoi",
    "dang-ky-lai-nuoi-con-nuoi",
]

VALID_JURISDICTIONS = ["toan-quoc", "tp-hcm", "dong-nai"]

# Theme lấy "toan-quoc" làm MẶC ĐỊNH khi câu hỏi không nêu địa phương.
# KHÔNG có nghĩa là các theme này luôn thuộc phạm vi toàn quốc: hộ tịch vẫn có
# nghị quyết lệ phí cấp tỉnh. Khi câu hỏi nêu tên tỉnh, giá trị từ planner được
# giữ nguyên và mặc định này không áp dụng (xem _apply_jurisdiction_rules).
_NATIONAL_THEMES = {"ho-tich", "nuoi-con-nuoi"}

MODEL = "claude-haiku-4-5-20251001"

_SYSTEM_PROMPT = """\
Bạn là bộ phân loại câu hỏi pháp lý Việt Nam. Nhiệm vụ: extract 5 trường từ câu hỏi người dùng.

Trả về JSON với đúng 6 trường (không có trường nào khác):
{
  "theme": <"dat-dai" | "ho-tich" | "nuoi-con-nuoi" | null>,
  "procedure": <một trong các giá trị dưới đây | null>,
  "jurisdiction": <"toan-quoc" | "tp-hcm" | "dong-nai" | null>,
  "temporal": <chuỗi ngày "YYYY-MM-DD" nếu câu hỏi đề cập thời điểm cụ thể | null>,
  "response_mode": <"general" | "irac">,
  "temporal_intent": {
    "has_temporal_context": <true | false>,
    "temporal_anchor": <"YYYY-MM-DD" | "trước-YYYY-MM-DD" | "luat-cu" | "unspecified_past" | null>,
    "case_status": <"hoan-tat" | "do-dang" | "moi" | null>,
    "reasoning": <"1 câu giải thích phát hiện">
  }
}

Giá trị hợp lệ của procedure:
- "chuyen-muc-dich-su-dung-dat"   — chuyển mục đích sử dụng đất (đất nông nghiệp → đất ở)
- "cap-so-do-lan-dau"             — cấp giấy chứng nhận quyền sử dụng đất (sổ đỏ) lần đầu
- "dang-ky-khai-sinh"             — đăng ký khai sinh
- "cap-ban-sao-trich-luc-ho-tich" — cấp bản sao / trích lục hộ tịch
- "dang-ky-nuoi-con-nuoi"         — đăng ký nuôi con nuôi trong nước
- "dang-ky-lai-nuoi-con-nuoi"     — đăng ký lại nuôi con nuôi trong nước

Phạm vi của từng theme (RỘNG HƠN danh sách procedure ở trên):
- "dat-dai"        — đất đai nói chung: quyền sử dụng đất, giấy chứng nhận (sổ đỏ), chuyển mục đích sử dụng, hạn mức giao/công nhận đất, bảng giá đất, thu hồi - bồi thường, đăng ký biến động.
- "ho-tich"        — hộ tịch nói chung: khai sinh, khai tử, kết hôn, GIÁM HỘ, nhận cha - mẹ - con, thay đổi/cải chính/bổ sung hộ tịch, xác định lại dân tộc, trích lục và bản sao hộ tịch, đăng ký lại các việc hộ tịch.
- "nuoi-con-nuoi"  — nuôi con nuôi: đăng ký nuôi con nuôi trong nước, đăng ký lại, điều kiện người nhận nuôi và người được nhận làm con nuôi, hệ quả pháp lý.

Quy tắc quan trọng:
0. THEME XÁC ĐỊNH ĐỘC LẬP VỚI PROCEDURE. Danh sách procedure chỉ gồm 6 thủ tục
   được lập chỉ mục sâu; theme thì bao trùm cả lĩnh vực. Nếu câu hỏi thuộc một
   lĩnh vực nêu trên nhưng KHÔNG khớp procedure nào (ví dụ "đăng ký giám hộ",
   "đăng ký khai tử", "cải chính hộ tịch") thì VẪN gán theme đúng và để
   procedure = null. TUYỆT ĐỐI KHÔNG trả theme = null chỉ vì không tìm được
   procedure — làm vậy khiến hệ không lọc được lĩnh vực và trả về rỗng.
1. ƯU TIÊN CAO NHẤT — nếu câu hỏi có NÊU TÊN địa phương thì gán đúng địa phương đó,
   BẤT KỂ thuộc lĩnh vực nào. Mọi lĩnh vực (kể cả Hộ tịch và Nuôi con nuôi) đều có
   thể có quy định riêng của tỉnh, ví dụ mức thu lệ phí do HĐND tỉnh ban hành.
   - TP.HCM / Thành phố Hồ Chí Minh / HCM → "tp-hcm"
   - Đồng Nai / tỉnh Đồng Nai → "dong-nai"
2. Nếu câu hỏi KHÔNG nêu địa phương:
   - Hộ tịch hoặc Nuôi con nuôi → "toan-quoc"
   - Đất đai → null
3. Nếu không xác định được trường nào → trả null cho trường đó.

Quy tắc temporal_intent (PHÂN BIỆT QUÁ KHỨ VÀ HIỆN TẠI):
4. has_temporal_context = true KHI câu hỏi NGẦM hoặc TƯỜNG MINH chỉ tới THỜI ĐIỂM QUÁ KHỨ, hoặc HỒ SƠ DỞ DANG, hoặc REGIME CHANGE. Bao gồm:
   - Tường minh thời điểm: "năm 2020", "trước 2024", "tháng 6/2024", "ngày 15/8/2025"
   - Ngữ cảnh quá khứ: "luật cũ chưa sửa", "hồi xưa", "đời ông bà", "khi tôi mua đất 10 năm trước", "trước khi có luật mới"
   - Hồ sơ dở dang: "hồ sơ tôi nộp tháng trước", "đang ngâm", "chưa có quyết định", "đang giải quyết"
   - Hành vi/sự kiện quá khứ: "hợp đồng ký năm 2010", "đất ông bà để lại từ 1985"
   has_temporal_context = false KHI câu hỏi chỉ về quy định hiện hành ("hạn mức TP.HCM bao nhiêu m²?", "thủ tục cấp sổ đỏ").

5. temporal_anchor — neo thời gian:
   - Nếu có ngày tường minh: dùng "YYYY-MM-DD" hoặc "YYYY-MM" hoặc "YYYY"
   - Nếu chỉ "trước/sau ngày X": dùng "trước-YYYY-MM-DD" hoặc "sau-YYYY-MM-DD"
   - Nếu chung chung "luật cũ" / "trước khi có luật mới": dùng "luat-cu"
   - Nếu rõ là quá khứ nhưng không xác định: dùng "unspecified_past"
   - Nếu has_temporal_context=false: dùng null

6. case_status — trạng thái hồ sơ user (KHÔNG đoán nếu không nói rõ):
   - "hoan-tat" — đã có quyết định hành chính cuối cùng / đã nhận sổ
   - "do-dang" — đã nộp hồ sơ nhưng chưa có quyết định
   - "moi" — sự kiện/hành vi MỚI phát sinh, chưa nộp gì
   - null — không nói rõ

7. reasoning — 1 câu giải thích ngắn (≤ 30 từ) phát hiện temporal.

Quy tắc response_mode (PHÂN BIỆT CÂU HỎI TRA CỨU CHUNG VS TÌNH HUỐNG CỤ THỂ):
8. response_mode = "irac" KHI câu hỏi MÔ TẢ MỘT TÌNH HUỐNG/SỰ VIỆC CỤ THỂ của người hỏi cần áp dụng luật vào tình tiết để ra kết luận. Dấu hiệu:
    - Có chủ thể + tình tiết cụ thể: "Tôi có 500m² đất...", "Gia đình tôi...", "Bên mua đặt cọc 200 triệu...", "Trường hợp của tôi..."
    - Hỏi "tôi có được... không?", "tôi phải làm gì?", "ai đúng/sai?", "có hợp pháp không?" gắn với sự việc đã/đang xảy ra.
    response_mode = "general" KHI câu hỏi TRA CỨU QUY ĐỊNH CHUNG, không gắn tình tiết cá nhân: "Điều kiện X là gì?", "Hạn mức Y bao nhiêu?", "Thủ tục Z gồm những bước nào?", "Văn bản nào sửa đổi...?".
    Khi không chắc → "general".

VÍ DỤ:
Q: "Hạn mức giao đất ở TP.HCM tối đa bao nhiêu m²?"
→ temporal_intent: {"has_temporal_context": false, "temporal_anchor": null, "case_status": null, "reasoning": "Câu hỏi về quy định hiện hành, không có yếu tố thời gian"}

Q: "Năm 2020, hạn mức giao đất ở tại Quận 1 TP.HCM là bao nhiêu?"
→ temporal_intent: {"has_temporal_context": true, "temporal_anchor": "2020", "case_status": null, "reasoning": "Câu hỏi tường minh thời điểm năm 2020 (trước QĐ 69/2024)"}

Q: "Đất nhà tôi mua từ hồi luật cũ chưa sửa, giờ muốn cấp sổ đỏ thì áp dụng luật nào?"
→ temporal_intent: {"has_temporal_context": true, "temporal_anchor": "luat-cu", "case_status": "moi", "reasoning": "Mua đất thời luật cũ nhưng giờ MỚI làm thủ tục cấp GCN"}

Q: "Hồ sơ tôi nộp tháng trước nhưng xã ngâm đến nay chưa có quyết định"
→ temporal_intent: {"has_temporal_context": true, "temporal_anchor": "unspecified_past", "case_status": "do-dang", "reasoning": "Hồ sơ chưa có quyết định cuối — có thể bị áp dụng luật mới nếu không có chuyển tiếp"}

VÍ DỤ response_mode:
Q: "Hạn mức giao đất ở tại TP.HCM tối đa bao nhiêu m²?"
→ "response_mode": "general"   (tra cứu quy định chung, không có tình tiết cá nhân)
Q: "Tôi có 500m² đất nông nghiệp ở Quận 9 mua năm 2010, muốn chuyển 200m² sang đất ở thì có được không?"
→ "response_mode": "irac"      (tình huống cụ thể của người hỏi, cần áp dụng luật vào tình tiết)

Chỉ trả về JSON thuần — không có markdown, không có giải thích ngoài JSON.
"""


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class TemporalIntent(TypedDict):
    """Phát hiện yếu tố thời gian/dở dang/regime change trong câu hỏi user.

    Field temporal cũ vẫn giữ làm legacy (date string nếu có ngày tường minh).
    TemporalIntent mở rộng đầy đủ: ngữ cảnh quá khứ + trạng thái hồ sơ.
    Khi `has_temporal_context=True`, pipeline activate temporal-aware retrieval
    (pull cả VB cũ + VB mới + điều khoản chuyển tiếp).
    """
    has_temporal_context: bool
    temporal_anchor: str | None
    case_status: str | None
    reasoning: str


# Default temporal_intent khi không có yếu tố thời gian
_DEFAULT_TEMPORAL_INTENT: TemporalIntent = {
    "has_temporal_context": False,
    "temporal_anchor": None,
    "case_status": None,
    "reasoning": "",
}

# Giá trị hợp lệ cho temporal_intent
_VALID_CASE_STATUS = {"hoan-tat", "do-dang", "moi"}


VALID_RESPONSE_MODES = ("general", "irac")


class QueryPlan(TypedDict):
    theme: str | None
    procedure: str | None
    jurisdiction: str | None
    temporal: str | None
    temporal_intent: TemporalIntent
    response_mode: str          # "general" (gọn) | "irac" (tư vấn chi tiết)


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# LLM cache cho plan_query — song song answer_generator. Mục đích: tránh
# block toàn pipeline khi Anthropic 529 outage (đã quan sát kéo dài hàng giờ).
# Cache key = hash(MODEL + SYSTEM_PROMPT + question) → invalidate tự động khi
# prompt template thay đổi. Default cache dir = data/evaluation/.planner_cache/.
# ---------------------------------------------------------------------------

_DEFAULT_PLANNER_CACHE_DIR = Path("data/evaluation/.planner_cache")


def _planner_cache_key(question: str) -> str:
    return hashlib.sha256(
        f"{MODEL}|{_SYSTEM_PROMPT}|{question}".encode()
    ).hexdigest()[:16]


def _planner_cache_get(cache_dir: Path | None, key: str) -> dict | None:
    if cache_dir is None:
        return None
    fp = cache_dir / f"{key}.json"
    if not fp.exists():
        return None
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _planner_cache_put(cache_dir: Path | None, key: str, data: dict) -> None:
    if cache_dir is None:
        return
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"{key}.json").write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8"
    )


def _call_llm(
    client: anthropic.Anthropic,
    question: str,
    cache_dir: Path | None = _DEFAULT_PLANNER_CACHE_DIR,
) -> dict:
    """Gọi Claude Haiku để plan câu hỏi, parse JSON response. Có cache."""
    key = _planner_cache_key(question)
    cached = _planner_cache_get(cache_dir, key)
    if cached is not None:
        logger.info(f"plan_query: cache HIT ({key}) — $0 API")
        return cached

    message = client.messages.create(
        model=MODEL,
        max_tokens=256,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": question}],
    )
    raw = message.content[0].text.strip()
    # Strip markdown code fence nếu model bọc JSON trong ```json ... ```
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning(f"LLM trả về JSON không hợp lệ: {raw!r} — lỗi: {e}")
        return {}

    _planner_cache_put(cache_dir, key, parsed)
    return parsed


def _validate_temporal_intent(raw: dict | None) -> TemporalIntent:
    """Validate + sanitize temporal_intent dict từ LLM."""
    if not isinstance(raw, dict):
        return dict(_DEFAULT_TEMPORAL_INTENT)
    has_ctx = bool(raw.get("has_temporal_context", False))
    anchor = raw.get("temporal_anchor")
    if not isinstance(anchor, str) or not anchor.strip():
        anchor = None
    case_status = raw.get("case_status")
    if case_status not in _VALID_CASE_STATUS:
        case_status = None
    reasoning = raw.get("reasoning")
    if not isinstance(reasoning, str):
        reasoning = ""
    # Nếu LLM bảo has_temporal_context=False thì xoá các field phụ để clean
    if not has_ctx:
        return {
            "has_temporal_context": False,
            "temporal_anchor": None,
            "case_status": None,
            "reasoning": reasoning.strip(),
        }
    return {
        "has_temporal_context": True,
        "temporal_anchor": anchor,
        "case_status": case_status,
        "reasoning": reasoning.strip(),
    }


def _validate_and_clean(raw: dict) -> dict:
    """Validate giá trị, xóa giá trị ngoài danh sách hợp lệ."""
    theme = raw.get("theme")
    procedure = raw.get("procedure")
    jurisdiction = raw.get("jurisdiction")
    temporal = raw.get("temporal")
    response_mode = raw.get("response_mode")
    temporal_intent = _validate_temporal_intent(raw.get("temporal_intent"))

    if theme not in VALID_THEMES:
        theme = None
    if procedure not in VALID_PROCEDURES:
        procedure = None
    if jurisdiction not in VALID_JURISDICTIONS:
        jurisdiction = None
    if not isinstance(temporal, str):
        temporal = None
    if response_mode not in VALID_RESPONSE_MODES:
        response_mode = "general"  # default an toàn khi LLM bỏ trống/sai

    return {
        "theme": theme,
        "procedure": procedure,
        "jurisdiction": jurisdiction,
        "temporal": temporal,
        "response_mode": response_mode,
        "temporal_intent": temporal_intent,
    }


def _apply_jurisdiction_rules(fields: dict) -> dict:
    """Tự động gán jurisdiction cho Hộ tịch / Nuôi con nuôi."""
    theme = fields["theme"]
    if theme in _NATIONAL_THEMES and fields["jurisdiction"] is None:
        fields = dict(fields)
        fields["jurisdiction"] = "toan-quoc"
    return fields


# ---------------------------------------------------------------------------
# Backfill theme từ tham chiếu số hiệu văn bản trong câu hỏi
# ---------------------------------------------------------------------------

# Token số hiệu văn bản kiểu "102/2024/NĐ-CP", "69/2024/QĐ-UBND", "31/2024/QH15"
_NORM_NUM_RE = re.compile(
    r"\b\d{1,4}/\d{4}/(?:NĐ-CP|ND-CP|NQ-HĐND|NQ-HDND|QĐ-UBND|QD-UBND|QH\d+|TT-[A-ZĐ\-]+)\b",
    re.IGNORECASE,
)
# Slug-style id nếu user gõ trực tiếp
_NORM_ID_SLUG_RE = re.compile(
    r"\b(?:luat|nghi-dinh|thong-tu|quyet-dinh|nghi-quyet)-[a-z0-9\-]+\b"
)
# "Luật Đất đai YYYY" → suy ra id luat-dat-dai-YYYY
_LUAT_DAT_DAI_RE = re.compile(r"Luật\s+Đất\s+đai\s+(\d{4})", re.IGNORECASE)

_THEME_LOOKUP_CYPHER = """
MATCH (t:Theme)-[:INCLUDES]->(n:Norm)
WHERE ANY(tok IN $tokens WHERE toLower(n.title) CONTAINS toLower(tok))
   OR n.id IN $ids
RETURN DISTINCT t.name AS theme
"""


def _extract_norm_refs(question: str) -> tuple[list[str], list[str]]:
    """Tách tham chiếu văn bản từ câu hỏi.

    Returns:
        (title_tokens, id_candidates) — dùng để CONTAINS Norm.title hoặc match Norm.id.
    """
    tokens = list({m.group(0) for m in _NORM_NUM_RE.finditer(question)})
    ids = list({m.group(0).lower() for m in _NORM_ID_SLUG_RE.finditer(question)})
    for m in _LUAT_DAT_DAI_RE.finditer(question):
        ids.append(f"luat-dat-dai-{m.group(1)}")
    return tokens, list(set(ids))


def _lookup_theme_from_refs(neo4j_driver, tokens: list[str], ids: list[str]) -> str | None:
    """Truy vấn Neo4j: nếu mọi norm reference cùng 1 theme → trả theme, ngược lại None."""
    if not tokens and not ids:
        return None
    try:
        with neo4j_driver.session() as session:
            rows = session.run(_THEME_LOOKUP_CYPHER, tokens=tokens, ids=ids).data()
    except Exception as e:
        logger.warning(f"_lookup_theme_from_refs: Neo4j lỗi — {e}")
        return None
    themes = {row["theme"] for row in rows if row.get("theme") in VALID_THEMES}
    if len(themes) == 1:
        return themes.pop()
    return None


def plan_query(
    question: str,
    client: anthropic.Anthropic,
    neo4j_driver=None,
) -> QueryPlan:
    """Phân tích câu hỏi, trả về QueryPlan.

    Args:
        question: Câu hỏi tiếng Việt từ người dùng.
        client: Anthropic client đã khởi tạo.
        neo4j_driver: Driver Neo4j (tùy chọn). Nếu được cung cấp và LLM trả
            theme=None, hàm sẽ thử backfill theme bằng cách lookup các tham
            chiếu số hiệu văn bản (Nghị định 102/2024/NĐ-CP, Luật Đất đai 2024)
            trong câu hỏi. Chỉ backfill khi LLM trả None — KHÔNG override.

    Returns:
        QueryPlan với đầy đủ các trường.
    """
    raw = _call_llm(client, question)
    fields = _validate_and_clean(raw)

    # Backfill theme từ norm references nếu LLM bỏ trống (defensive: chỉ khi None)
    if fields["theme"] is None and neo4j_driver is not None:
        tokens, ids = _extract_norm_refs(question)
        backfilled = _lookup_theme_from_refs(neo4j_driver, tokens, ids)
        if backfilled is not None:
            logger.info(
                f"plan_query: backfill theme='{backfilled}' từ norm refs "
                f"tokens={tokens} ids={ids}"
            )
            fields["theme"] = backfilled

    fields = _apply_jurisdiction_rules(fields)

    logger.info(
        f"plan_query | theme={fields['theme']} procedure={fields['procedure']} "
        f"jurisdiction={fields['jurisdiction']} temporal={fields['temporal']} "
        f"temporal_ctx={fields['temporal_intent']['has_temporal_context']}"
    )

    return QueryPlan(
        theme=fields["theme"],
        procedure=fields["procedure"],
        jurisdiction=fields["jurisdiction"],
        temporal=fields["temporal"],
        temporal_intent=fields["temporal_intent"],
        response_mode=fields["response_mode"],
    )


# ---------------------------------------------------------------------------
# Entry point (demo)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Lỗi: ANTHROPIC_API_KEY chưa được thiết lập trong .env")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    test_questions = [
        "Phí chuyển mục đích sử dụng đất tại TP.HCM là bao nhiêu?",
        "Phí chuyển mục đích là bao nhiêu?",
        "Điều kiện đăng ký khai sinh là gì?",
        "Hồ sơ đăng ký nuôi con nuôi gồm những gì?",
        "Thủ tục cấp sổ đỏ lần đầu ở Đồng Nai?",
    ]

    for q in test_questions:
        plan = plan_query(q, client)
        print(f"\nQ: {q}")
        print(f"   theme={plan['theme']} procedure={plan['procedure']} "
              f"jurisdiction={plan['jurisdiction']} temporal={plan['temporal']}")
