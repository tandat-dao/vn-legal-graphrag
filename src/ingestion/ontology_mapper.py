"""
Ontology Mapper — TASK-15 (Phase 4)
Sử dụng Gemini Flash để phân loại tự động (Bottom-up mapping) các Component
vào các Concept đã định nghĩa trong Core Ontology.

Cơ chế:
- Chạy với temperature=0.
- Trả về JSON array chứa các concept_id.
- Tự động filter bỏ các concept_id ngoại lai (hallucinated).

Provider: Gemini (google-genai), model đọc từ env `GEMINI_MODEL_PLANNER`
(mặc định `gemini-2.5-flash`), key từ `GEMINI_API_KEY` — hoặc Vertex AI qua ADC
khi `GEMINI_USE_VERTEX=true` (dùng chung `_build_gemini_client` của D-24).
"""
import json
import logging
import os
import re
import time
from typing import Any

from src.utils.gemini_fallback import _build_gemini_client, _should_fallback_gemini

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.5-flash"

# Gemini 2.5 là thinking model: thinking tiêu token TRONG max_output_tokens (D-24).
# Budget cũ 128 (Claude-tuned) sẽ bị thinking ăn hết → output rỗng/cụt. Mảng JSON
# concept_ids rất ngắn nên 2048 là dư sức cho cả thinking lẫn output.
MAX_OUTPUT_TOKENS = 2048

# ── Chống rate limit ─────────────────────────────────────────────────────────
# Pass 4 gọi LLM cho TỪNG Component (~4500 lượt). Trên free tier Developer API
# (5 request/phút) một mẻ đã chết vì 429; tệ hơn, lỗi bị nuốt và trả `[]` nên
# graph_builder vẫn SET ontology_mapped=true → lỗ hổng câm. Nay: retry có backoff,
# hết retry thì RAISE để lời gọi dừng hẳn thay vì ghi cờ sai.
MAX_RETRIES = 3            # số lần thử LẠI (tổng cộng 4 lượt gọi)
DEFAULT_RETRY_DELAY = 15.0  # giây, khi API không nói rõ phải chờ bao lâu
# Giãn cách tối thiểu giữa hai lần gọi API (tính từ lúc BẮT ĐẦU lượt trước, nên
# thời gian chờ response đã được tính vào — không cộng dồn oan).
# 0.5s ≈ 120 request/phút: dưới xa quota Vertex của gemini-2.5-flash, đủ để không
# dội burst, mà không kéo Pass 4 dài vô ích (4s × 4500 ≈ 5 giờ chỉ để nằm chờ).
# Tính đúng đắn do retry/backoff bên dưới đảm nhiệm, không phải throttle.
# Chạy trên free tier Developer API (5 RPM) thì phải đặt ONTOLOGY_THROTTLE_SEC=13.
THROTTLE_SEC = float(os.getenv("ONTOLOGY_THROTTLE_SEC", "0.5"))

_last_call_ts: float | None = None

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

# Client google-genai dùng lại giữa các lần gọi (Pass 4 gọi hàng nghìn lượt →
# không dựng client mới mỗi Component).
_GEMINI_CLIENT = None


def _planner_model() -> str:
    """Model Gemini cho tác vụ phân loại — đọc env mỗi lần gọi (sau load_dotenv)."""
    return os.getenv("GEMINI_MODEL_PLANNER") or DEFAULT_MODEL


def _get_gemini_client():
    """Lazy-init client google-genai (Developer API bằng GEMINI_API_KEY, hoặc Vertex ADC)."""
    global _GEMINI_CLIENT
    if _GEMINI_CLIENT is None:
        _GEMINI_CLIENT = _build_gemini_client(os.getenv("GEMINI_API_KEY"))
    return _GEMINI_CLIENT


def _is_genai_client(obj: Any) -> bool:
    """True nếu obj là client google-genai (có `.models.generate_content`).

    Call site cũ (`graph_builder`) từng truyền client Anthropic vào tham số đầu;
    `anthropic.Anthropic` cũng có `.models` nhưng KHÔNG có `generate_content` →
    phân biệt được bằng duck-typing, không cần import anthropic.
    """
    models = getattr(obj, "models", None)
    return callable(getattr(models, "generate_content", None))


def _throttle() -> None:
    """Chờ cho đủ THROTTLE_SEC kể từ lần gọi API trước."""
    global _last_call_ts
    if _last_call_ts is not None:
        con_lai = THROTTLE_SEC - (time.monotonic() - _last_call_ts)
        if con_lai > 0:
            time.sleep(con_lai)
    _last_call_ts = time.monotonic()


def _la_loi_tam_thoi(err: Exception) -> bool:
    """True nếu lỗi đáng thử lại: 429/5xx ở tầng API, HOẶC lỗi tầng vận chuyển.

    `_should_fallback_gemini` chỉ nhận diện lỗi có status code hoặc chuỗi đặc trưng
    của API. Nó KHÔNG bắt được `httpx.RemoteProtocolError("Server disconnected
    without sending a response.")` — lỗi này không có `.code`, và chuỗi
    "DISCONNECTED" không chứa "CONNECTION" nên dò chuỗi trượt. Một mẻ Pass 4 đã
    chết ở component 2300/4553 vì đúng lỗi đó bị coi là lỗi logic. `TransportError`
    là lớp cha của mọi lỗi kết nối/timeout của httpx → bắt trọn nhóm này.
    """
    try:
        import httpx
        if isinstance(err, httpx.TransportError):
            return True
    except ImportError:                             # httpx là dep của google-genai
        pass
    return _should_fallback_gemini(err)


def _retry_delay(err: Exception, lan_thu: int) -> float:
    """Số giây nên chờ trước khi thử lại.

    Ưu tiên thông tin do API cung cấp — header `retry-after`, hoặc `retryDelay`
    trong `RetryInfo` / câu "Please retry in 51.4s" mà Gemini trả kèm 429. Không
    có thì backoff luỹ thừa từ DEFAULT_RETRY_DELAY (15 → 30 → 60).
    """
    headers = getattr(getattr(err, "response", None), "headers", None)
    if headers:
        try:
            gia_tri = headers.get("retry-after") or headers.get("Retry-After")
        except AttributeError:
            gia_tri = None
        if gia_tri:
            try:
                return max(0.0, float(gia_tri))
            except (TypeError, ValueError):
                pass

    khop = re.search(r"(?:retry(?:Delay)?[\"'\s:]*in\s*|retryDelay[\"'\s:]*)"
                     r"(\d+(?:\.\d+)?)s", str(err), re.IGNORECASE)
    if khop:
        return float(khop.group(1))

    return DEFAULT_RETRY_DELAY * (2 ** lan_thu)


def _generate(gemini_client, *, model: str, system_prompt: str, text: str) -> str:
    """Một lượt phân loại, có throttle + retry 429/5xx. RAISE nếu hết retry.

    Cố tình KHÔNG nuốt lỗi hạ tầng: nuốt rồi trả `[]` sẽ khiến graph_builder ghi
    `ontology_mapped = true` cho Component chưa hề được map, và cơ chế idempotency
    bỏ qua nó vĩnh viễn ở lần chạy sau.
    """
    from google.genai import types

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=0.0,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )

    for lan_thu in range(MAX_RETRIES + 1):
        _throttle()
        try:
            response = gemini_client.models.generate_content(
                model=model, contents=text, config=config
            )
            return (response.text or "").strip()
        except Exception as err:                    # noqa: BLE001 — lọc bằng helper
            # Lỗi logic (400/403/404) hoặc đã hết lượt → để nó nổ ra ngoài.
            if not _la_loi_tam_thoi(err) or lan_thu == MAX_RETRIES:
                raise
            cho = _retry_delay(err, lan_thu)
            logger.warning(
                "Gemini lỗi hạ tầng (%s) — thử lại lần %d/%d sau %.1fs",
                type(err).__name__, lan_thu + 1, MAX_RETRIES, cho,
            )
            time.sleep(cho)

    raise RuntimeError("không thể tới đây: vòng retry luôn return hoặc raise")


def _build_concepts_text(core_data: dict) -> str:
    lines = []
    for c in core_data.get("concepts", []):
        lines.append(f"- ID: '{c['id']}' | Ý nghĩa: {c['name']}")
    return "\n".join(lines)


def map_component_to_concepts(
    client: Any | None,
    text: str,
    core_data: dict,
) -> list[str]:
    """Phân loại text của component vào danh sách concept_ids.

    Args:
        client: Client google-genai dựng sẵn (tùy chọn). None → tự khởi tạo từ
            env. Client Anthropic của call site cũ được BỎ QUA (module này chạy
            Gemini) — giữ tham số để `graph_builder` không phải đổi signature.
        text: Nội dung của Component / TextUnit.
        core_data: Dữ liệu từ data/ontology/core_v1.json.

    Returns:
        Danh sách các concept_id hợp lệ. Trả `[]` khi LLM trả về nội dung không
        parse được thành JSON list — đó là lỗi *nội dung*, map lại cũng vậy.

    Raises:
        Lỗi gọi API (429/5xx sau khi hết retry, hoặc lỗi logic 400/403) được
        NÉM RA cho caller. Nuốt nó sẽ khiến graph_builder đánh dấu Component là
        "đã map" trong khi chưa map được gì.
    """
    valid_concept_ids = {c["id"] for c in core_data.get("concepts", [])}
    if not valid_concept_ids:
        return []

    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
        concepts_text=_build_concepts_text(core_data)
    )

    gemini_client = client if _is_genai_client(client) else _get_gemini_client()
    raw = _generate(
        gemini_client,
        model=_planner_model(),
        system_prompt=system_prompt,
        text=text,
    )

    try:
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

    # CHỈ lỗi nội dung mới trả `[]`. Lỗi API đã được `_generate` ném ra trước đó
    # — không có `except Exception` bao trùm ở đây (xem docstring Raises).
    except json.JSONDecodeError as e:
        logger.warning(f"Lỗi parse JSON từ LLM: {raw!r} — {e}")
        return []
