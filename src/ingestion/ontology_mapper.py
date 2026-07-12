"""
Ontology Mapper — TASK-15 (Phase 4)
Sử dụng Claude Haiku để phân loại tự động (Bottom-up mapping) các Component
vào các Concept đã định nghĩa trong Core Ontology.

Cơ chế:
- Chạy với temperature=0.
- Trả về JSON array chứa các concept_id.
- Tự động filter bỏ các concept_id ngoại lai (hallucinated).
"""
import json
import logging

import anthropic

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5-20251001"

_SYSTEM_PROMPT_TEMPLATE = """\
Bạn là chuyên gia phân loại pháp lý. Nhiệm vụ của bạn là đọc một nội dung điều/khoản pháp luật và phân loại nó vào MỘT HOẶC NHIỀU Khái niệm (Concepts) trong danh sách cho sẵn.

DANH SÁCH KHÁI NIỆM HỢP LỆ:
{concepts_text}

QUY TẮC:
1. Đọc nội dung và xác định xem nội dung đó quy định về khái niệm nào ở trên.
2. Một nội dung có thể thuộc nhiều khái niệm (ví dụ: vừa là 'ho-so-giay-to' vừa là 'nghia-vu-tai-chinh').
3. CHỈ được chọn các ID từ danh sách trên. Không được tự bịa ra ID mới.
4. Nếu nội dung không thuộc bất kỳ khái niệm nào, hãy trả về mảng rỗng `[]`.
5. ĐỊNH DẠNG ĐẦU RA BẮT BUỘC: Chỉ in ra một mảng JSON thuần tuý, KHÔNG có markdown, KHÔNG giải thích.
Ví dụ: ["nghia-vu-tai-chinh", "han-muc"]
"""


def _build_concepts_text(core_data: dict) -> str:
    lines = []
    for c in core_data.get("concepts", []):
        lines.append(f"- ID: '{c['id']}' | Ý nghĩa: {c['name']}")
    return "\n".join(lines)


def map_component_to_concepts(
    client: anthropic.Anthropic,
    text: str,
    core_data: dict,
) -> list[str]:
    """Phân loại text của component vào danh sách concept_ids.

    Args:
        client: Anthropic client.
        text: Nội dung của Component / TextUnit.
        core_data: Dữ liệu từ data/ontology/core_v1.json.

    Returns:
        Danh sách các concept_id hợp lệ.
    """
    valid_concept_ids = {c["id"] for c in core_data.get("concepts", [])}
    if not valid_concept_ids:
        return []

    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
        concepts_text=_build_concepts_text(core_data)
    )

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=128,
            temperature=0.0,
            system=system_prompt,
            messages=[{"role": "user", "content": text}],
        )
        raw = message.content[0].text.strip()

        # Strip markdown fence nếu có
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        parsed = json.loads(raw)

        if not isinstance(parsed, list):
            logger.warning(f"Ontology Mapper trả về không phải list: {parsed}")
            return []

        # Lọc bỏ hallucinated concepts
        mapped_concepts = []
        for cid in parsed:
            cid_str = str(cid).strip()
            if cid_str in valid_concept_ids:
                mapped_concepts.append(cid_str)
            else:
                logger.warning(f"Drop ngoại lai concept_id: {cid_str}")

        return mapped_concepts

    except json.JSONDecodeError as e:
        logger.warning(f"Lỗi parse JSON từ LLM: {raw!r} — {e}")
        return []
    except Exception as e:
        logger.error(f"Lỗi khi gọi Claude API: {e}")
        return []
