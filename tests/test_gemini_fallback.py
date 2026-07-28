"""Test Gemini fallback — toàn bộ mock, KHÔNG gọi API thật ($0).

Kiểm: (1) Claude OK → không đụng Gemini; (2) Claude lỗi hạ tầng → fallback Gemini;
(3) Claude lỗi logic (400) → re-raise; (4) factory gate đúng; (5) helpers dịch request.
"""
from __future__ import annotations

from types import SimpleNamespace

import anthropic
import pytest

from src.utils.gemini_fallback import (
    FallbackGeminiClient,
    FallbackLLMClient,
    GeminiClient,
    _extract_system_text,
    _extract_user_text,
    _gemini_model_for,
    _should_fallback,
    _should_fallback_gemini,
)
from src.utils.llm_config import make_llm_client


# --- Fakes ----------------------------------------------------------------

class _FakeAPIError(anthropic.APIError):
    """APIError giả với status_code đặt sẵn, không cần request/response thật."""
    def __init__(self, status_code):
        self.status_code = status_code
        self.message = f"fake {status_code}"


class _Msgs:
    def __init__(self, exc):
        self._exc = exc
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self._exc is not None:
            raise self._exc
        return SimpleNamespace(content=[SimpleNamespace(text="CLAUDE_OK")])


class _FakeAnthropic:
    def __init__(self, exc=None):
        self.messages = _Msgs(exc)


# --- Hành vi fallback -----------------------------------------------------

def test_claude_ok_khong_dung_gemini(monkeypatch):
    client = FallbackLLMClient(_FakeAnthropic(None), "fake-key")
    gemini_called = []
    monkeypatch.setattr(client, "_call_gemini",
                        lambda **kw: gemini_called.append(1) or "GEMINI")
    resp = client.messages.create(model="m", messages=[{"role": "user", "content": "u"}])
    assert resp.content[0].text == "CLAUDE_OK"
    assert gemini_called == []   # Gemini KHÔNG được gọi khi Claude OK


def test_claude_overload_fallback_gemini(monkeypatch):
    client = FallbackLLMClient(_FakeAnthropic(_FakeAPIError(529)), "fake-key")
    monkeypatch.setattr(client, "_call_gemini", lambda **kw: "GEMINI_OK")
    resp = client.messages.create(
        model="claude-haiku-4-5",
        system="sys",
        messages=[{"role": "user", "content": "u"}],
    )
    assert resp.content[0].text == "GEMINI_OK"   # đã chuyển sang Gemini


def test_claude_500_fallback(monkeypatch):
    client = FallbackLLMClient(_FakeAnthropic(_FakeAPIError(500)), "k")
    monkeypatch.setattr(client, "_call_gemini", lambda **kw: "G")
    resp = client.messages.create(model="m", messages=[{"role": "user", "content": "u"}])
    assert resp.content[0].text == "G"


def test_claude_400_khong_fallback_re_raise(monkeypatch):
    """Lỗi logic 400 = bug của ta, Gemini không cứu được → re-raise, KHÔNG fallback."""
    client = FallbackLLMClient(_FakeAnthropic(_FakeAPIError(400)), "k")
    monkeypatch.setattr(client, "_call_gemini", lambda **kw: "G")
    with pytest.raises(anthropic.APIError):
        client.messages.create(model="m", messages=[{"role": "user", "content": "u"}])


# --- _should_fallback -----------------------------------------------------

@pytest.mark.parametrize("status,expected", [
    (429, True), (500, True), (503, True), (529, True),
    (400, False), (401, False), (404, False),
])
def test_should_fallback_theo_status(status, expected):
    assert _should_fallback(_FakeAPIError(status)) is expected


def test_should_fallback_connection_error():
    err = anthropic.APIConnectionError(request=None)
    assert _should_fallback(err) is True


# --- Factory gate ---------------------------------------------------------

def test_factory_mode_claude_tra_anthropic_thuan(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    client = make_llm_client(mode="claude")
    assert isinstance(client, anthropic.Anthropic)
    assert not isinstance(client, FallbackLLMClient)


def test_factory_mode_fallback_thieu_gemini_degrade(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_USE_VERTEX", raising=False)
    client = make_llm_client(mode="claude-fallback")
    assert isinstance(client, anthropic.Anthropic)   # degrade về Claude thuần


def test_factory_mode_fallback_co_gemini_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_API_KEY", "gem-key")
    client = make_llm_client(mode="claude-fallback")
    assert isinstance(client, FallbackLLMClient)


def test_factory_mode_fallback_vertex_khong_can_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_USE_VERTEX", "true")   # vertex dùng ADC, không cần api_key
    client = make_llm_client(mode="claude-fallback")
    assert isinstance(client, FallbackLLMClient)


def test_factory_mode_gemini_end_to_end(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "gem-key")
    client = make_llm_client(mode="gemini")
    assert isinstance(client, GeminiClient)


def test_factory_mode_invalid_fallback_claude(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    client = make_llm_client(mode="khong-hop-le")
    assert isinstance(client, anthropic.Anthropic)


def test_factory_mode_gemini_fallback_co_vertex(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_USE_VERTEX", "true")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    client = make_llm_client(mode="gemini-fallback")
    assert isinstance(client, FallbackGeminiClient)


def test_factory_mode_gemini_fallback_thieu_gemini_degrade(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_USE_VERTEX", raising=False)
    client = make_llm_client(mode="gemini-fallback")
    assert isinstance(client, anthropic.Anthropic)   # degrade về Claude thuần


# --- FallbackGeminiClient: Gemini chính → Claude dự phòng ------------------

class _FakeGoogleError(Exception):
    """Lỗi google-genai giả với .code (HTTP status) như APIError thật."""
    def __init__(self, code, message=""):
        self.code = code
        super().__init__(message or f"fake {code}")


def test_gemini_ok_khong_dung_claude(monkeypatch):
    import src.utils.gemini_fallback as gf
    monkeypatch.setattr(gf, "_build_gemini_client", lambda key: object())
    monkeypatch.setattr(gf, "_gemini_complete", lambda c, **kw: "GEMINI_OK")
    client = FallbackGeminiClient("gem-key", _FakeAnthropic(None))
    resp = client.messages.create(model="m", messages=[{"role": "user", "content": "u"}])
    assert resp.content[0].text == "GEMINI_OK"
    assert client._anthropic.messages.calls == 0   # Claude KHÔNG bị gọi khi Gemini OK


def test_gemini_429_fallback_claude(monkeypatch):
    """Gemini 429 RESOURCE_EXHAUSTED (hết quota) → chuyển sang Claude."""
    import src.utils.gemini_fallback as gf
    monkeypatch.setattr(gf, "_build_gemini_client", lambda key: object())
    def _boom(c, **kw):
        raise _FakeGoogleError(429, "RESOURCE_EXHAUSTED")
    monkeypatch.setattr(gf, "_gemini_complete", _boom)
    client = FallbackGeminiClient("gem-key", _FakeAnthropic(None))
    resp = client.messages.create(model="claude-sonnet-4-6",
                                  messages=[{"role": "user", "content": "u"}])
    assert resp.content[0].text == "CLAUDE_OK"   # đã chuyển sang Claude
    assert client._anthropic.messages.calls == 1


def test_gemini_500_fallback_claude(monkeypatch):
    import src.utils.gemini_fallback as gf
    monkeypatch.setattr(gf, "_build_gemini_client", lambda key: object())
    def _boom(c, **kw):
        raise _FakeGoogleError(503, "UNAVAILABLE")
    monkeypatch.setattr(gf, "_gemini_complete", _boom)
    client = FallbackGeminiClient("k", _FakeAnthropic(None))
    resp = client.messages.create(model="m", messages=[{"role": "user", "content": "u"}])
    assert resp.content[0].text == "CLAUDE_OK"


def test_gemini_400_khong_fallback_re_raise(monkeypatch):
    """Lỗi logic 400 INVALID_ARGUMENT = bug của ta → re-raise, KHÔNG fallback."""
    import src.utils.gemini_fallback as gf
    monkeypatch.setattr(gf, "_build_gemini_client", lambda key: object())
    def _boom(c, **kw):
        raise _FakeGoogleError(400, "INVALID_ARGUMENT")
    monkeypatch.setattr(gf, "_gemini_complete", _boom)
    client = FallbackGeminiClient("k", _FakeAnthropic(None))
    with pytest.raises(_FakeGoogleError):
        client.messages.create(model="m", messages=[{"role": "user", "content": "u"}])
    assert client._anthropic.messages.calls == 0


@pytest.mark.parametrize("code,expected", [
    (429, True), (500, True), (503, True), (529, True),
    (400, False), (401, False), (403, False), (404, False),
])
def test_should_fallback_gemini_theo_code(code, expected):
    assert _should_fallback_gemini(_FakeGoogleError(code)) is expected


@pytest.mark.parametrize("msg,expected", [
    ("RESOURCE_EXHAUSTED: quota", True),
    ("503 UNAVAILABLE", True),
    ("INTERNAL error", True),
    ("400 INVALID_ARGUMENT", False),
    ("PERMISSION_DENIED", False),
])
def test_should_fallback_gemini_theo_message(msg, expected):
    """Lỗi không có .code (vd connection) → dò theo message."""
    assert _should_fallback_gemini(Exception(msg)) is expected


def test_gemini_client_always_gemini(monkeypatch):
    """GeminiClient.messages.create luôn gọi Gemini (mock _gemini_complete)."""
    import src.utils.gemini_fallback as gf
    monkeypatch.setattr(gf, "_build_gemini_client", lambda key: object())
    monkeypatch.setattr(gf, "_gemini_complete", lambda c, **kw: "GEMINI_E2E")
    client = GeminiClient("gem-key")
    resp = client.messages.create(model="m", messages=[{"role": "user", "content": "u"}])
    assert resp.content[0].text == "GEMINI_E2E"


# --- Helpers dịch request -------------------------------------------------

def test_extract_system_text_list_co_cache_control():
    system = [{"type": "text", "text": "RULES", "cache_control": {"type": "ephemeral"}}]
    assert _extract_system_text(system) == "RULES"


def test_extract_system_text_str_va_none():
    assert _extract_system_text("abc") == "abc"
    assert _extract_system_text(None) == ""


def test_extract_user_text():
    msgs = [{"role": "user", "content": "câu hỏi"}]
    assert _extract_user_text(msgs) == "câu hỏi"


def test_gemini_model_mapping(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL_PLANNER", "flash-planner")
    monkeypatch.setenv("GEMINI_MODEL_GENERATOR", "pro-gen")
    assert _gemini_model_for("claude-haiku-4-5") == "flash-planner"
    assert _gemini_model_for("claude-sonnet-4-6") == "pro-gen"
