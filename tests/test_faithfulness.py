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
