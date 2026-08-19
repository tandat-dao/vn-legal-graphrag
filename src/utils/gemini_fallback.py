"""Gemini fallback — dự phòng khi Anthropic API sập (chủ yếu cho DEMO bảo vệ).

Vấn đề: demo lúc bảo vệ phụ thuộc Claude API. Nếu Anthropic outage đúng giờ →
demo chết. Lớp này bọc Anthropic client bằng một wrapper TRONG SUỐT: gọi Claude
trước; nếu lỗi API (529/timeout/connection) SAU khi đã hết 8 retry → tự dịch
request sang Gemini và trả về response GIẢ DẠNG Anthropic (`.content[0].text`).

Nguyên tắc thiết kế:
  • TRONG SUỐT: call site vẫn gọi `client.messages.create(...)` như cũ — không
    đổi một dòng nào ở answer_generator / query_planner.
  • OPT-IN, mặc định TẮT: eval LUÔN chạy thuần Claude. Nếu Claude chớp tắt giữa
    eval mà tự đổi Gemini → CORRUPT số liệu luận văn. Chỉ demo path bật fallback.
  • CHỈ fallback khi lỗi hạ tầng (5xx/429/connection), KHÔNG fallback lỗi logic
    (400 BadRequest = bug của ta, Gemini không cứu được) → re-raise.
  • LOG TO khi fallback nổ → lúc demo biết đã chuyển provider.

Khi Claude chạy bình thường (mọi eval run), hành vi GIỐNG HỆT không có lớp này.
Gemini chỉ kích hoạt khi Claude thật sự sập → đúng tinh thần "dự phòng", không
đụng vào hệ thống đã đánh giá.
"""
from __future__ import annotations

import logging
import os
from types import SimpleNamespace
from typing import Any

import anthropic

logger = logging.getLogger(__name__)

# Model Gemini mặc định (free tier). Có thể override qua env. Tên model thay đổi
# theo thời gian → để cấu hình được thay vì hardcode cứng trong logic.
_DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"


def _gemini_model_for(anthropic_model: str) -> str:
    """Ánh xạ model Claude → model Gemini tương ứng (planner nhẹ vs generator mạnh)."""
    if "haiku" in (anthropic_model or "").lower():
        return os.getenv("GEMINI_MODEL_PLANNER", _DEFAULT_GEMINI_MODEL)
    return os.getenv("GEMINI_MODEL_GENERATOR", _DEFAULT_GEMINI_MODEL)


def _extract_system_text(system: Any) -> str:
    """Lấy text hệ thống từ kwarg `system` — chấp nhận str hoặc list[dict] (dạng
    Anthropic có cache_control). Bỏ qua cache_control (đặc thù Anthropic)."""
    if system is None:
        return ""
    if isinstance(system, str):
        return system
    if isinstance(system, list):
        parts = []
        for block in system:
            if isinstance(block, dict):
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(p for p in parts if p)
    return str(system)


def _extract_user_text(messages: Any) -> str:
    """Gộp nội dung các message role=user thành 1 chuỗi cho Gemini."""
    if not messages:
        return ""
    parts = []
    for m in messages:
        if not isinstance(m, dict) or m.get("role") != "user":
            continue
        content = m.get("content", "")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    parts.append(block)
    return "\n".join(p for p in parts if p)


def _should_fallback(err: anthropic.APIError) -> bool:
    """True nếu lỗi là hạ tầng (đáng fallback); False nếu lỗi logic (re-raise).

    Fallback: connection error, rate limit (429), server error (5xx, kể cả 529).
    KHÔNG fallback: 4xx client error khác (400 bad request = bug của ta).
    """
    if isinstance(err, anthropic.APIConnectionError):
        return True
    status = getattr(err, "status_code", None)
    if status is None:
        # APIError không rõ status → bảo thủ, vẫn thử fallback cho demo
        return True
    return status == 429 or status >= 500


def _should_fallback_gemini(err: Exception) -> bool:
    """True nếu lỗi Gemini là hạ tầng (đáng fallback sang Claude); False nếu lỗi logic.

    Đối xứng `_should_fallback` nhưng cho google-genai. Fallback: 429 RESOURCE_EXHAUSTED
    (hết quota Vertex — CHÍNH sự cố đã cắn mẻ eval), 5xx (UNAVAILABLE/INTERNAL), connection.
    KHÔNG fallback: 400 INVALID_ARGUMENT / 401/403 PERMISSION_DENIED (bug/cấu hình của ta —
    Claude không cứu được, re-raise để lộ lỗi thật thay vì nuốt).
    """
    status = getattr(err, "code", None)
    if not isinstance(status, int):
        status = getattr(err, "status_code", None)
    if isinstance(status, int):
        return status == 429 or status >= 500
    msg = str(err).upper()
    # Loại trừ lỗi logic trước (không fallback)
    if any(m in msg for m in ("INVALID_ARGUMENT", "PERMISSION_DENIED", "UNAUTHENTICATED",
                              "NOT_FOUND", " 400", " 401", " 403", " 404")):
        return False
    infra = ("RESOURCE_EXHAUSTED", "429", "UNAVAILABLE", "INTERNAL", "DEADLINE",
             "503", "500", "502", "504", "TIMEOUT", "CONNECTION")
    return any(m in msg for m in infra)


class _Messages:
    """Giả lập namespace `client.messages` với method `.create()`."""

    def __init__(self, parent: "FallbackLLMClient") -> None:
        self._parent = parent

    def create(self, **kwargs: Any) -> Any:
        return self._parent._create(**kwargs)


class FallbackLLMClient:
    """Wrapper trong suốt: thử Anthropic, lỗi hạ tầng → Gemini.

    Dùng được ở mọi chỗ đang nhận `anthropic.Anthropic` vì expose cùng interface
    `client.messages.create(...)` và trả về object có `.content[0].text`.
    """

    def __init__(self, anthropic_client: anthropic.Anthropic, gemini_api_key: str) -> None:
        self._anthropic = anthropic_client
        self._gemini_api_key = gemini_api_key
        self._gemini_client = None  # lazy init khi fallback nổ
        self.messages = _Messages(self)

    def _create(self, **kwargs: Any) -> Any:
        try:
            return self._anthropic.messages.create(**kwargs)
        except anthropic.APIError as err:
            if not _should_fallback(err):
                logger.error("Claude lỗi logic (không fallback): %s", err)
                raise
            logger.warning(
                "⚠️  Claude API thất bại (%s) → CHUYỂN SANG GEMINI fallback", err
            )
            text = self._call_gemini(
                model=kwargs.get("model", ""),
                system_text=_extract_system_text(kwargs.get("system")),
                user_text=_extract_user_text(kwargs.get("messages")),
                max_tokens=kwargs.get("max_tokens"),
                temperature=kwargs.get("temperature", 0.0),
            )
            # Mimic shape response Anthropic để call site đọc message.content[0].text
            return SimpleNamespace(content=[SimpleNamespace(text=text)])

    def _call_gemini(self, *, model, system_text, user_text, max_tokens, temperature) -> str:
        """Gọi Gemini (lazy-init client). Tách method để test mock dễ."""
        if self._gemini_client is None:
            self._gemini_client = _build_gemini_client(self._gemini_api_key)
        return _gemini_complete(
            self._gemini_client, model=model, system_text=system_text,
            user_text=user_text, max_tokens=max_tokens, temperature=temperature,
        )


# ---------------------------------------------------------------------------
# Lõi gọi Gemini — dùng chung cho fallback (Claude→Gemini) và Gemini-only
# ---------------------------------------------------------------------------

def _build_gemini_client(api_key: str | None):
    """Khởi tạo google-genai client (import lazy). Vertex (ADC) hoặc Developer (api_key).

    GEMINI_USE_VERTEX=true → Vertex AI qua ADC (project+location, KHÔNG api_key — Vertex
    đòi OAuth2/ADC qua `gcloud auth application-default login`; dùng credit Cloud/$300).
    Mặc định false → Developer API (generativelanguage) bằng api_key.
    """
    from google import genai
    from google.genai import types

    # THỜI HẠN CHỜ LÀ BẮT BUỘC. Mặc định của google-genai là chờ vô hạn: đã gặp
    # thật một lượt gọi treo 32 phút, CPU 0%, không lỗi, không trả về. Giữa buổi
    # bảo vệ thì giao diện đứng im vĩnh viễn — và vì mỗi lần chỉ chạy một câu,
    # nó khoá luôn mọi câu sau. Hết hạn thì thành lỗi nhìn thấy được, và mode
    # có dự phòng còn chuyển được sang nhà cung cấp khác.
    # Đơn vị là mili-giây. 180 giây: gemini-2.5-pro sinh câu trả lời dài mất
    # 40–60 giây nên ngưỡng này chỉ cắn khi thật sự treo.
    han_cho_ms = int(os.getenv("GEMINI_TIMEOUT_MS", "180000"))
    tuy_chon = types.HttpOptions(timeout=han_cho_ms)

    if os.getenv("GEMINI_USE_VERTEX", "false").lower() == "true":
        return genai.Client(
            vertexai=True,
            project=os.getenv("GEMINI_VERTEX_PROJECT"),
            location=os.getenv("GEMINI_VERTEX_LOCATION", "us-central1"),
            http_options=tuy_chon,
        )
    return genai.Client(api_key=api_key, http_options=tuy_chon)


def _gemini_complete(gemini_client, *, model, system_text, user_text,
                     max_tokens, temperature) -> str:
    """Một lượt generate qua google-genai, trả về text."""
    from google.genai import types

    gem_model = _gemini_model_for(model)
    # Gemini 2.5/3.x là "thinking" model: thinking tiêu token TRONG max_output_tokens.
    # Nếu chỉ truyền max_tokens Claude-tuned (128 ontology, 256 planner, 3000 generator),
    # thinking ăn vào → output thật bị CẮT CỤT (vd IRAC dài + thinking > 3000 → cụt giữa
    # citation → mất citation). Fix: cộng HEADROOM cho thinking TRÊN độ dài answer mong muốn.
    _ANSWER_FLOOR = 2048   # answer tối thiểu (kể cả call budget nhỏ)
    _THINK_HEADROOM = 4096  # chừa cho thinking
    mot = max(max_tokens or 0, _ANSWER_FLOOR) + _THINK_HEADROOM
    logger.info("Gemini call: model=%s max_out=%d", gem_model, mot)
    response = gemini_client.models.generate_content(
        model=gem_model,
        contents=user_text,
        config=types.GenerateContentConfig(
            system_instruction=system_text or None,
            temperature=temperature or 0.0,
            max_output_tokens=mot,
        ),
    )
    return (response.text or "").strip()


class GeminiClient:
    """Client Gemini-only — luôn gọi Gemini (KHÔNG đụng Claude). Mode "gemini" end-to-end.

    Expose cùng interface `client.messages.create(...)` → object có `.content[0].text`,
    nên thay được `anthropic.Anthropic` ở mọi call site (planner + generator).
    """

    def __init__(self, gemini_api_key: str | None = None) -> None:
        self._gemini_api_key = gemini_api_key
        self._gemini_client = None  # lazy
        self.messages = _Messages(self)

    def _create(self, **kwargs: Any) -> Any:
        if self._gemini_client is None:
            self._gemini_client = _build_gemini_client(self._gemini_api_key)
        text = _gemini_complete(
            self._gemini_client,
            model=kwargs.get("model", ""),
            system_text=_extract_system_text(kwargs.get("system")),
            user_text=_extract_user_text(kwargs.get("messages")),
            max_tokens=kwargs.get("max_tokens"),
            temperature=kwargs.get("temperature", 0.0),
        )
        return SimpleNamespace(content=[SimpleNamespace(text=text)])


class FallbackGeminiClient:
    """Gemini chính + Claude dự phòng — ĐỐI XỨNG `FallbackLLMClient`, cho DEMO chạy Gemini.

    Demo bảo vệ chạy Gemini end-to-end (mode "gemini"). Nếu Gemini lỗi hạ tầng — nhất là
    `429 RESOURCE_EXHAUSTED` (hết quota Vertex, đã từng làm hỏng mẻ eval) — thì demo chết
    vì `GeminiClient` không có dự phòng. Lớp này bọc trong suốt: gọi Gemini trước; lỗi hạ
    tầng → tự chuyển request sang Claude (kwargs vốn đã dạng Anthropic: model là tên Claude,
    system/messages/max_tokens y hệt → truyền thẳng). Lỗi logic (400/403) → re-raise.

    Mặc định TẮT (eval luôn thuần Gemini mode "gemini" để reproducible). Chỉ demo bật.
    """

    def __init__(self, gemini_api_key: str | None,
                 anthropic_client: anthropic.Anthropic) -> None:
        self._gemini_api_key = gemini_api_key
        self._gemini_client = None  # lazy
        self._anthropic = anthropic_client
        self.messages = _Messages(self)

    def _create(self, **kwargs: Any) -> Any:
        try:
            if self._gemini_client is None:
                self._gemini_client = _build_gemini_client(self._gemini_api_key)
            text = _gemini_complete(
                self._gemini_client,
                model=kwargs.get("model", ""),
                system_text=_extract_system_text(kwargs.get("system")),
                user_text=_extract_user_text(kwargs.get("messages")),
                max_tokens=kwargs.get("max_tokens"),
                temperature=kwargs.get("temperature", 0.0),
            )
            return SimpleNamespace(content=[SimpleNamespace(text=text)])
        except Exception as err:  # noqa: BLE001 — google-genai raise nhiều loại; lọc bằng helper
            if not _should_fallback_gemini(err):
                logger.error("Gemini lỗi logic (không fallback): %s", err)
                raise
            logger.warning(
                "⚠️  Gemini API thất bại (%s) → CHUYỂN SANG CLAUDE fallback", err
            )
            return self._anthropic.messages.create(**kwargs)
