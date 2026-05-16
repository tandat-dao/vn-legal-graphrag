"""
Query Planner — TASK-10
Nhận câu hỏi tiếng Việt, dùng Claude Haiku 4.5 để extract:
  theme, procedure, jurisdiction, temporal
Trả về QueryPlan TypedDict.

Quy tắc tự động:
  - Hộ tịch và Nuôi con nuôi luôn gán jurisdiction = "toan-quoc" (không hỏi lại)
  - Đất đai không có jurisdiction → is_complete = False, missing_fields = ["jurisdiction"]
"""
import json
import logging
import os

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

# Các theme luôn áp dụng toàn quốc — không cần hỏi lại người dùng
_NATIONAL_THEMES = {"ho-tich", "nuoi-con-nuoi"}

MODEL = "claude-haiku-4-5-20251001"

_SYSTEM_PROMPT = """\
Bạn là bộ phân loại câu hỏi pháp lý Việt Nam. Nhiệm vụ: extract 4 trường từ câu hỏi người dùng.

Trả về JSON với đúng 4 trường (không có trường nào khác):
{
  "theme": <"dat-dai" | "ho-tich" | "nuoi-con-nuoi" | null>,
  "procedure": <một trong các giá trị dưới đây | null>,
  "jurisdiction": <"toan-quoc" | "tp-hcm" | "dong-nai" | null>,
  "temporal": <chuỗi ngày "YYYY-MM-DD" nếu câu hỏi đề cập thời điểm cụ thể | null>
}

Giá trị hợp lệ của procedure:
- "chuyen-muc-dich-su-dung-dat"   — chuyển mục đích sử dụng đất (đất nông nghiệp → đất ở)
- "cap-so-do-lan-dau"             — cấp giấy chứng nhận quyền sử dụng đất (sổ đỏ) lần đầu
- "dang-ky-khai-sinh"             — đăng ký khai sinh
- "cap-ban-sao-trich-luc-ho-tich" — cấp bản sao / trích lục hộ tịch
- "dang-ky-nuoi-con-nuoi"         — đăng ký nuôi con nuôi trong nước
- "dang-ky-lai-nuoi-con-nuoi"     — đăng ký lại nuôi con nuôi trong nước

Quy tắc quan trọng:
1. Nếu câu hỏi liên quan Hộ tịch hoặc Nuôi con nuôi: LUÔN gán jurisdiction = "toan-quoc".
2. Nếu câu hỏi liên quan Đất đai nhưng không đề cập địa phương: trả jurisdiction = null.
3. TP.HCM / Thành phố Hồ Chí Minh / HCM → "tp-hcm"
4. Đồng Nai / tỉnh Đồng Nai → "dong-nai"
5. Nếu không xác định được trường nào → trả null cho trường đó.
6. KHÔNG thêm trường nào khác ngoài 4 trường trên.
7. Chỉ trả về JSON thuần — không có markdown, không có giải thích.
"""


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class QueryPlan(TypedDict):
    theme: str | None
    procedure: str | None
    jurisdiction: str | None
    temporal: str | None
    is_complete: bool
    missing_fields: list[str]


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def _call_llm(client: anthropic.Anthropic, question: str) -> dict:
    """Gọi Claude Haiku, parse JSON response."""
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
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning(f"LLM trả về JSON không hợp lệ: {raw!r} — lỗi: {e}")
        return {}


def _validate_and_clean(raw: dict) -> dict:
    """Validate giá trị, xóa giá trị ngoài danh sách hợp lệ."""
    theme = raw.get("theme")
    procedure = raw.get("procedure")
    jurisdiction = raw.get("jurisdiction")
    temporal = raw.get("temporal")

    if theme not in VALID_THEMES:
        theme = None
    if procedure not in VALID_PROCEDURES:
        procedure = None
    if jurisdiction not in VALID_JURISDICTIONS:
        jurisdiction = None
    if not isinstance(temporal, str):
        temporal = None

    return {
        "theme": theme,
        "procedure": procedure,
        "jurisdiction": jurisdiction,
        "temporal": temporal,
    }


def _apply_jurisdiction_rules(fields: dict) -> dict:
    """Tự động gán jurisdiction cho Hộ tịch / Nuôi con nuôi."""
    theme = fields["theme"]
    if theme in _NATIONAL_THEMES and fields["jurisdiction"] is None:
        fields = dict(fields)
        fields["jurisdiction"] = "toan-quoc"
    return fields


def _compute_completeness(fields: dict) -> tuple[bool, list[str]]:
    """Xác định is_complete và missing_fields.

    Đất đai bắt buộc có jurisdiction vì quy định khác nhau giữa địa phương.
    Hộ tịch + Nuôi con nuôi luôn toan-quoc nên không bao giờ missing jurisdiction.
    """
    missing: list[str] = []
    if fields["theme"] is None:
        missing.append("theme")
    if fields["procedure"] is None:
        missing.append("procedure")

    theme = fields["theme"]
    if theme == "dat-dai" and fields["jurisdiction"] is None:
        missing.append("jurisdiction")

    return (len(missing) == 0, missing)


def plan_query(question: str, client: anthropic.Anthropic) -> QueryPlan:
    """Phân tích câu hỏi, trả về QueryPlan.

    Args:
        question: Câu hỏi tiếng Việt từ người dùng.
        client: Anthropic client đã khởi tạo.

    Returns:
        QueryPlan với đầy đủ các trường.
    """
    raw = _call_llm(client, question)
    fields = _validate_and_clean(raw)
    fields = _apply_jurisdiction_rules(fields)
    is_complete, missing = _compute_completeness(fields)

    logger.info(
        f"plan_query | theme={fields['theme']} procedure={fields['procedure']} "
        f"jurisdiction={fields['jurisdiction']} temporal={fields['temporal']} "
        f"is_complete={is_complete} missing={missing}"
    )

    return QueryPlan(
        theme=fields["theme"],
        procedure=fields["procedure"],
        jurisdiction=fields["jurisdiction"],
        temporal=fields["temporal"],
        is_complete=is_complete,
        missing_fields=missing,
    )


def build_confirmation_prompt(missing_fields: list[str]) -> str:
    """Tạo câu hỏi ngược lại người dùng khi thiếu thông tin.

    Args:
        missing_fields: Danh sách trường còn thiếu từ QueryPlan.

    Returns:
        Câu hỏi tiếng Việt yêu cầu người dùng bổ sung thông tin.
    """
    parts: list[str] = []

    if "theme" in missing_fields:
        parts.append(
            "Bạn muốn tra cứu thủ tục thuộc lĩnh vực nào? "
            "(Đất đai / Hộ tịch / Nuôi con nuôi)"
        )
    if "procedure" in missing_fields:
        parts.append("Bạn muốn tra cứu thủ tục hành chính cụ thể nào?")
    if "jurisdiction" in missing_fields:
        parts.append(
            "Bất động sản / đất đai của bạn thuộc tỉnh/thành phố nào? "
            "(TP. Hồ Chí Minh / Đồng Nai / địa phương khác)"
        )

    if not parts:
        return "Vui lòng cung cấp thêm thông tin để tôi có thể hỗ trợ chính xác hơn."

    return " ".join(parts)


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
        status = "✅" if plan["is_complete"] else f"❌ thiếu {plan['missing_fields']}"
        print(f"\nQ: {q}")
        print(f"   theme={plan['theme']} procedure={plan['procedure']} "
              f"jurisdiction={plan['jurisdiction']} temporal={plan['temporal']}")
        print(f"   {status}")
        if not plan["is_complete"]:
            print(f"   → {build_confirmation_prompt(plan['missing_fields'])}")
