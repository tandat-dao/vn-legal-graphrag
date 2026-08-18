"""
Unit tests cho Verifier agent — TẤT CẢ mock, KHÔNG gọi API ($0).

Tier 2 dùng MagicMock cho anthropic client (không có request mạng nào).
"""
from unittest.mock import MagicMock

from src.retrieval.verifier import verify_citations, VALID_VERIFY_TIERS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Context giả lập đúng format header của assemble_context:
#   --- [Tier X | Hiệu lực: ...] Điều Y. ..., Khoản Z. (van-ban-id) ---
_CONTEXT = (
    "--- [Tier 1 | Hiệu lực: 2025-01-01] Điều 116. Căn cứ, Khoản 5. "
    "(luat-dat-dai-2024) ---\n"
    "Căn cứ cho phép chuyển mục đích sử dụng đất là kế hoạch sử dụng đất.\n\n"
    "--- [Tier 2 | Hiệu lực: 2024-08-01] Điều 13. Trình tự (nghi-dinh-102-2024-nd-cp) ---\n"
    "Trình tự thủ tục chuyển mục đích sử dụng đất.\n"
)


def _cit(dieu=None, khoan=None, van_ban=None, loai="dieu"):
    return {"dieu": dieu, "khoan": khoan, "diem": None, "tiet": None,
            "van_ban": van_ban, "loai": loai}


# Citation có trong context
_GROUNDED = _cit(dieu="116", khoan="5", van_ban="luat-dat-dai-2024")
# Citation KHÔNG có trong context (Điều 999 không tồn tại)
_UNGROUNDED = _cit(dieu="999", van_ban="luat-dat-dai-2024")
# Citation có trong context (norm khác)
_GROUNDED_2 = _cit(dieu="13", van_ban="nghi-dinh-102-2024-nd-cp")


def _mock_judge_client(verdict: str):
    """Client kiểu Anthropic giả: messages.create trả JSON verdict cố định.

    `spec=["messages"]` là CẦN THIẾT: `_judge_citation` phân biệt client
    google-genai với client `.messages.create` bằng duck-typing, mà MagicMock
    trần thì bịa ra cả `.models.generate_content` → bị nhận nhầm là client genai.
    """
    client = MagicMock(spec=["messages"])
    msg = MagicMock()
    block = MagicMock()
    block.text = f'{{"verdict": "{verdict}", "reason": "mock"}}'
    msg.content = [block]
    client.messages.create.return_value = msg
    return client


# ---------------------------------------------------------------------------
# Tier 0 + edge cases
# ---------------------------------------------------------------------------

def test_tier0_noop_keeps_all():
    cits = [_GROUNDED, _UNGROUNDED]
    r = verify_citations("q", _CONTEXT, "ans", cits, tier=0)
    assert r["filtered_citations"] == cits
    assert r["n_dropped"] == 0
    assert r["tier"] == 0


def test_empty_citations_noop():
    r = verify_citations("q", _CONTEXT, "ans", [], tier=1)
    assert r["filtered_citations"] == []
    assert r["n_input"] == 0
    assert r["n_kept"] == 0


def test_invalid_tier_falls_back_to_1():
    r = verify_citations("q", _CONTEXT, "ans", [_GROUNDED], tier=99)
    # tier 99 không hợp lệ → coi như tier 1, grounded citation được giữ
    assert r["n_kept"] == 1
    assert r["tier"] == 1


# ---------------------------------------------------------------------------
# Tier 1 — grounding prune (deterministic, $0)
# ---------------------------------------------------------------------------

def test_tier1_drops_ungrounded_keeps_grounded():
    cits = [_GROUNDED, _UNGROUNDED, _GROUNDED_2]
    r = verify_citations("q", _CONTEXT, "ans", cits, tier=1)
    assert r["n_input"] == 3
    assert r["n_kept"] == 2
    assert r["n_dropped"] == 1
    assert _UNGROUNDED not in r["filtered_citations"]
    assert _GROUNDED in r["filtered_citations"]
    assert _GROUNDED_2 in r["filtered_citations"]


def test_tier1_all_grounded_keeps_all():
    cits = [_GROUNDED, _GROUNDED_2]
    r = verify_citations("q", _CONTEXT, "ans", cits, tier=1)
    assert r["n_dropped"] == 0
    assert r["n_kept"] == 2


def test_tier1_preserves_order():
    cits = [_GROUNDED_2, _GROUNDED]  # thứ tự đảo
    r = verify_citations("q", _CONTEXT, "ans", cits, tier=1)
    assert r["filtered_citations"] == [_GROUNDED_2, _GROUNDED]


def test_tier1_no_api_call_when_client_passed():
    """Tier 1 KHÔNG được gọi LLM dù có truyền client."""
    client = _mock_judge_client("SUPPORTED")
    verify_citations("q", _CONTEXT, "ans", [_GROUNDED], tier=1, llm_client=client)
    client.messages.create.assert_not_called()


# ---------------------------------------------------------------------------
# Tier 2 — grounding + LLM support judge (mock)
# ---------------------------------------------------------------------------

def test_tier2_supported_keeps():
    client = _mock_judge_client("SUPPORTED")
    r = verify_citations("q", _CONTEXT, "ans [Điều 116, Khoản 5, Văn bản luat-dat-dai-2024]",
                         [_GROUNDED], tier=2, llm_client=client)
    assert r["tier"] == 2
    assert r["n_kept"] == 1
    assert r["n_dropped"] == 0
    assert r["verdicts"][0]["supported"] is True


def test_tier2_unsupported_flags_by_default():
    """UNSUPPORTED mặc định chỉ 'flag' (giữ lại) — bảo thủ chống over-prune."""
    client = _mock_judge_client("UNSUPPORTED")
    r = verify_citations("q", _CONTEXT, "ans [Điều 116, Khoản 5, Văn bản luat-dat-dai-2024]",
                         [_GROUNDED], tier=2, llm_client=client)
    assert r["n_flagged"] == 1
    assert r["n_dropped"] == 0
    assert r["n_kept"] == 1  # flagged vẫn được giữ
    assert _GROUNDED in r["filtered_citations"]


def test_tier2_unsupported_drops_when_aggressive():
    client = _mock_judge_client("UNSUPPORTED")
    r = verify_citations("q", _CONTEXT, "ans [Điều 116, Khoản 5, Văn bản luat-dat-dai-2024]",
                         [_GROUNDED], tier=2, llm_client=client, drop_unsupported=True)
    assert r["n_dropped"] == 1
    assert r["n_kept"] == 0


def test_tier2_ungrounded_dropped_before_judge():
    """Citation ungrounded bị drop ở Lớp 1 → KHÔNG tốn judge call."""
    client = _mock_judge_client("SUPPORTED")
    r = verify_citations("q", _CONTEXT, "ans", [_UNGROUNDED], tier=2, llm_client=client)
    assert r["n_dropped"] == 1
    client.messages.create.assert_not_called()


def test_tier2_without_client_falls_back_to_tier1():
    """Yêu cầu tier 2 nhưng thiếu client → fallback tier 1 ($0), không crash."""
    r = verify_citations("q", _CONTEXT, "ans", [_GROUNDED, _UNGROUNDED],
                         tier=2, llm_client=None)
    assert r["tier"] == 1
    assert r["n_kept"] == 1
    assert r["n_dropped"] == 1


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

def test_valid_tiers_constant():
    assert VALID_VERIFY_TIERS == (0, 1, 2)
