"""
Unit tests cho faithfulness helpers — TẤT CẢ offline, KHÔNG gọi API ($0).

Tập trung vào regression cho bug snippet Phụ lục (_extract_answer_snippet) phát
hiện khi chạy verifier Tier 2 trên Q008.
"""
from src.evaluation.faithfulness import _extract_answer_snippet, _citation_in_context


def _cit(dieu=None, khoan=None, van_ban=None, loai="dieu"):
    return {"dieu": dieu, "khoan": khoan, "diem": None, "tiet": None,
            "van_ban": van_ban, "loai": loai}


# ---------------------------------------------------------------------------
# _extract_answer_snippet — Điều (đã hoạt động từ trước)
# ---------------------------------------------------------------------------

def test_snippet_finds_dieu_citation_beyond_fallback():
    """Citation Điều nằm SAU 400 ký tự đầu → snippet vẫn phải định vị đúng (không fallback)."""
    pad = "A" * 500
    ans = f"{pad} Nội dung quan trọng [Điều 116, Khoản 5, Văn bản luat-dat-dai-2024] kết thúc."
    c = _cit(dieu="116", khoan="5", van_ban="luat-dat-dai-2024")
    snip = _extract_answer_snippet(c, ans)
    assert "Điều 116" in snip
    assert "luat-dat-dai-2024" in snip
    assert snip != ans[:400]  # không phải fallback 400 ký tự đầu


# ---------------------------------------------------------------------------
# _extract_answer_snippet — Phụ lục (BUG FIX: trước đây luôn fallback)
# ---------------------------------------------------------------------------

def test_snippet_finds_phu_luc_citation():
    """REGRESSION: citation Phụ lục phải được định vị, không rơi vào fallback 400 ký tự."""
    pad = "B" * 500
    ans = (f"{pad} Phí cấp lần đầu được quy định tại "
           f"[Phụ lục I, Văn bản nghi-quyet-22-2024-nq-hdnd-dong-nai] như sau.")
    c = _cit(dieu="I", van_ban="nghi-quyet-22-2024-nq-hdnd-dong-nai", loai="phu_luc")
    snip = _extract_answer_snippet(c, ans)
    assert "Phụ lục I" in snip
    assert "nghi-quyet-22-2024-nq-hdnd-dong-nai" in snip
    assert snip != ans[:400]  # đã KHÔNG còn fallback (trước fix sẽ == ans[:400])


def test_snippet_phu_luc_default_number():
    """Phụ lục không số (dieu='_default') vẫn định vị được [Phụ lục, ...]."""
    pad = "C" * 500
    ans = f"{pad} Theo [Phụ lục, Khoản 2, Văn bản nghi-quyet-87-2025-nq-hdnd-tp-hcm] thì..."
    c = _cit(dieu="_default", khoan="2", van_ban="nghi-quyet-87-2025-nq-hdnd-tp-hcm", loai="phu_luc")
    snip = _extract_answer_snippet(c, ans)
    assert "Phụ lục" in snip
    assert "nghi-quyet-87-2025-nq-hdnd-tp-hcm" in snip


def test_snippet_fallback_when_not_found():
    """Không tìm thấy citation → fallback 2*window ký tự đầu (không crash)."""
    ans = "Đoạn văn không chứa citation nào." * 20
    c = _cit(dieu="999", van_ban="khong-ton-tai")
    snip = _extract_answer_snippet(c, ans)
    assert snip == ans[:400]


# ---------------------------------------------------------------------------
# _citation_in_context — sanity Phụ lục (grounding dùng cho verifier Tier 1)
# ---------------------------------------------------------------------------

def test_citation_in_context_phu_luc():
    ctx = ("--- [Tier 4 | Hiệu lực: 2024-01-01] Phụ lục I. Biểu phí "
           "(nghi-quyet-22-2024-nq-hdnd-dong-nai) ---\nNội dung biểu phí.")
    assert _citation_in_context(
        _cit(dieu="I", van_ban="nghi-quyet-22-2024-nq-hdnd-dong-nai", loai="phu_luc"), ctx)
    # Phụ lục khác số → không match
    assert not _citation_in_context(
        _cit(dieu="II", van_ban="nghi-quyet-22-2024-nq-hdnd-dong-nai", loai="phu_luc"), ctx)


# ---------------------------------------------------------------------------
# Judge Tier 2 — chuyển sang Gemini Flash, vẫn nhận client kiểu Anthropic
# ---------------------------------------------------------------------------

import os  # noqa: E402
import sys  # noqa: E402
from types import ModuleType, SimpleNamespace  # noqa: E402

import pytest  # noqa: E402

from src.evaluation import faithfulness as fa  # noqa: E402


@pytest.fixture(autouse=True)
def _stub_genai_types(monkeypatch):
    """Cho phép chạy khi máy chưa cài google-genai (chỉ cần `types`)."""
    try:
        from google.genai import types  # noqa: F401
        return
    except ImportError:
        pass
    fake_types = ModuleType("google.genai.types")
    fake_types.GenerateContentConfig = lambda **kw: SimpleNamespace(**kw)
    fake_genai = ModuleType("google.genai")
    fake_genai.types = fake_types
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)
    monkeypatch.setitem(sys.modules, "google.genai.types", fake_types)


class _GenaiClientGia:
    """Client google-genai giả — đường judge mới."""

    def __init__(self, text):
        self.calls = []
        self.models = SimpleNamespace(generate_content=self._gen)

    def _gen(self, **kw):
        self.calls.append(kw)
        return SimpleNamespace(text=self._text)

    _text = ""


class _MessagesClientGia:
    """Client kiểu Anthropic (.messages.create) — đường verifier D-18."""

    def __init__(self, text):
        self.calls = []
        self._text = text
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        self.calls.append(kw)
        return SimpleNamespace(content=[SimpleNamespace(text=self._text)])


def _genai(text):
    c = _GenaiClientGia(text)
    c._text = text
    return c


def test_judge_model_mac_dinh_la_gemini_flash(monkeypatch):
    monkeypatch.delenv("FAITHFULNESS_JUDGE_MODEL", raising=False)
    assert fa._judge_model() == "gemini-2.5-flash"
    assert "claude" not in fa.DEFAULT_JUDGE_MODEL.lower()


def test_judge_model_doc_tu_env(monkeypatch):
    monkeypatch.setenv("FAITHFULNESS_JUDGE_MODEL", "gemini-3.6-flash")
    assert fa._judge_model() == "gemini-3.6-flash"


def test_judge_qua_client_genai(monkeypatch):
    monkeypatch.setenv("FAITHFULNESS_JUDGE_MODEL", "gemini-2.5-flash")
    client = _genai('{"verdict": "SUPPORTED", "reason": "khớp"}')
    kq = fa._judge_citation(_cit("13", "1", "nd-49"), "answer", "chunk", client)
    assert kq["supported"] is True
    kw = client.calls[0]
    assert kw["model"] == "gemini-2.5-flash"
    assert kw["config"].temperature == 0.0
    # thinking model: budget phải đủ lớn, không dùng 200 kiểu Claude
    assert kw["config"].max_output_tokens == fa.JUDGE_MAX_OUTPUT_TOKENS


def test_judge_qua_client_messages_van_chay(monkeypatch):
    """Verifier Tier 2 (D-18) truyền GeminiClient/.messages.create — không được vỡ."""
    client = _MessagesClientGia('{"verdict": "UNSUPPORTED", "reason": "sai số"}')
    kq = fa._judge_citation(_cit("13", "1", "nd-49"), "answer", "chunk", client)
    assert kq["supported"] is False
    assert client.calls[0]["temperature"] == 0.0


def test_judge_loi_api_khong_lam_vo_eval():
    class _Vo:
        models = SimpleNamespace(generate_content=lambda **kw: (_ for _ in ()).throw(RuntimeError("429")))
    kq = fa._judge_citation(_cit("13", "1", "nd-49"), "a", "c", _Vo())
    assert kq["supported"] is False and "judge_error" in kq["reason"]
