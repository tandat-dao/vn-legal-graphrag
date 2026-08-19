"""
Tests cho src/retrieval/context_assembler.py và answer_generator.py — TASK-13.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from src.retrieval.context_assembler import (
    _estimate_tokens,
    _format_citation_label,
    assemble_context,
    build_messages,
    build_prompt,
    fetch_texts,
)
from src.retrieval.answer_generator import generate_answer, parse_citations
from src.retrieval.semantic_filter import ScoredTextUnit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_unit(
    text_unit_id: str,
    norm_id: str,
    component_id: str,
    tier: int,
    rrf_score: float = 0.03,
    jurisdiction: str = "toan-quoc",
    theme: str = "dat-dai",
) -> ScoredTextUnit:
    return ScoredTextUnit(
        text_unit_id=text_unit_id,
        rrf_score=rrf_score,
        norm_id=norm_id,
        component_id=component_id,
        jurisdiction=jurisdiction,
        tier=tier,
        theme=theme,
        valid_from="2025-01-01",
        valid_to=None,
    )


def _mock_neo4j(text_map: dict[str, dict]) -> MagicMock:
    """Mock Neo4j driver trả về text_map theo id."""
    rows = [
        {"id": tid, "text": v["text"], "context_path": v["context_path"], "norm_id": v["norm_id"]}
        for tid, v in text_map.items()
    ]
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)
    session.run.return_value.data.return_value = rows
    driver = MagicMock()
    driver.session.return_value = session
    return driver


def _mock_llm_client(response_text: str) -> MagicMock:
    content = MagicMock()
    content.text = response_text
    message = MagicMock()
    message.content = [content]
    client = MagicMock()
    client.messages.create.return_value = message
    return client


# ---------------------------------------------------------------------------
# 1. Tests cho _format_citation_label
# ---------------------------------------------------------------------------

class TestFormatCitationLabel:
    def test_full_path(self):
        label = _format_citation_label(
            ["luat-dat-dai-2024", "Điều 116", "Khoản 1"], "luat-dat-dai-2024"
        )
        assert "Điều 116" in label
        assert "Khoản 1" in label
        assert "luat-dat-dai-2024" in label

    def test_empty_path_uses_norm_id(self):
        label = _format_citation_label([], "nghi-dinh-102-2024-nd-cp")
        assert "nghi-dinh-102-2024-nd-cp" in label

    def test_only_norm_id_in_path(self):
        label = _format_citation_label(["luat-dat-dai-2024"], "luat-dat-dai-2024")
        assert "luat-dat-dai-2024" in label


# ---------------------------------------------------------------------------
# 2. Tests cho _estimate_tokens
# ---------------------------------------------------------------------------

class TestEstimateTokens:
    def test_empty_string(self):
        assert _estimate_tokens("") == 1

    def test_proportional(self):
        short = _estimate_tokens("abc")
        long = _estimate_tokens("abc" * 100)
        assert long > short

    def test_3000_token_budget(self):
        # ~3000 tokens ≈ 10500 chars
        text = "a" * 10500
        tokens = _estimate_tokens(text)
        assert abs(tokens - 3000) < 100


# ---------------------------------------------------------------------------
# 3. Tests cho assemble_context
# ---------------------------------------------------------------------------

class TestAssembleContext:
    def test_respects_rrf_order_not_tier(self):
        """assemble_context tôn trọng thứ tự RRF (đã tích hợp tier multiplier +
        graph boost), KHÔNG sort lại theo tier.

        Trước đây sort theo tier 1→4 đã phá hoại tier multiplier/graph boost
        ở hybrid_search và đẩy Tier 4 (NQ địa phương) khỏi token budget.
        Tier vẫn được expose qua header `[Tier X | Hiệu lực: ...]` để LLM
        áp dụng lex superior khi mâu thuẫn (xem prompt build_prompt).
        """
        units = [
            _make_unit("0000000000000004", "quyet-dinh-tp-hcm", "comp-4", tier=4, rrf_score=0.05),
            _make_unit("0000000000000001", "luat-dat-dai-2024", "comp-1", tier=1, rrf_score=0.03),
            _make_unit("0000000000000002", "nghi-dinh-102", "comp-2", tier=2, rrf_score=0.04),
        ]
        text_map = {
            "0000000000000001": {"text": "Nội dung Luật.", "context_path": ["luat-dat-dai-2024", "Điều 116"], "norm_id": "luat-dat-dai-2024"},
            "0000000000000002": {"text": "Nội dung NĐ.", "context_path": ["nghi-dinh-102", "Điều 3"], "norm_id": "nghi-dinh-102"},
            "0000000000000004": {"text": "Nội dung QĐ TP.HCM.", "context_path": ["quyet-dinh-tp-hcm", "Điều 1"], "norm_id": "quyet-dinh-tp-hcm"},
        }
        driver = _mock_neo4j(text_map)

        context = assemble_context(units, driver, max_tokens=3000)

        # RRF order: 0.05 (T4) > 0.04 (T2) > 0.03 (T1)
        pos_tier4 = context.find("Nội dung QĐ TP.HCM")
        pos_tier2 = context.find("Nội dung NĐ")
        pos_tier1 = context.find("Nội dung Luật")
        assert pos_tier4 < pos_tier2 < pos_tier1, (
            f"Sort không tôn trọng RRF: T4@{pos_tier4} T2@{pos_tier2} T1@{pos_tier1}"
        )

        # Header phải chứa tier metadata để LLM tự suy luận lex superior
        assert "[Tier 1" in context
        assert "[Tier 2" in context
        assert "[Tier 4" in context

    def test_dod_2_token_budget(self):
        """DoD: max_tokens=100 cắt bỏ đủ để tổng text < budget."""
        units = [
            _make_unit(f"00000000000000{i:02d}", f"norm-{i}", f"comp-{i}", tier=1)
            for i in range(10)
        ]
        # Mỗi text ~400 chars (~114 tokens) — với budget 100, chỉ giữ 1 block
        text_map = {
            f"00000000000000{i:02d}": {
                "text": "x" * 400,
                "context_path": [f"norm-{i}", f"Điều {i}"],
                "norm_id": f"norm-{i}",
            }
            for i in range(10)
        }
        driver = _mock_neo4j(text_map)

        context = assemble_context(units, driver, max_tokens=100)

        # Với budget 100 tokens (~350 chars), chỉ 0-1 block được giữ
        total_chars = len(context)
        assert total_chars < 100 * 3.5 * 2  # generous upper bound

    def test_empty_units_returns_empty(self):
        driver = _mock_neo4j({})
        result = assemble_context([], driver)
        assert result == ""

    def test_context_contains_text(self):
        units = [_make_unit("0000000000000001", "luat", "comp-1", tier=1)]
        text_map = {
            "0000000000000001": {
                "text": "Điều kiện chuyển mục đích.",
                "context_path": ["luat", "Điều 1"],
                "norm_id": "luat",
            }
        }
        driver = _mock_neo4j(text_map)
        context = assemble_context(units, driver)
        assert "Điều kiện chuyển mục đích" in context

    def test_rrf_tiebreak_within_same_tier(self):
        """Cùng tier: rrf_score cao hơn xuất hiện trước."""
        units = [
            _make_unit("0000000000000001", "luat-a", "comp-1", tier=1, rrf_score=0.02),
            _make_unit("0000000000000002", "luat-b", "comp-2", tier=1, rrf_score=0.05),
        ]
        text_map = {
            "0000000000000001": {"text": "Text A thấp hơn.", "context_path": ["luat-a", "Điều 1"], "norm_id": "luat-a"},
            "0000000000000002": {"text": "Text B cao hơn.", "context_path": ["luat-b", "Điều 1"], "norm_id": "luat-b"},
        }
        driver = _mock_neo4j(text_map)
        context = assemble_context(units, driver)
        assert context.find("Text B cao hơn") < context.find("Text A thấp hơn")


# ---------------------------------------------------------------------------
# 4. Tests cho build_prompt
# ---------------------------------------------------------------------------

class TestBuildPrompt:
    def test_contains_question(self):
        prompt = build_prompt("Phí CMĐSDĐ là bao nhiêu?", "context...")
        assert "Phí CMĐSDĐ là bao nhiêu?" in prompt

    def test_contains_context(self):
        prompt = build_prompt("câu hỏi", "NỘI DUNG CONTEXT ĐẶC BIỆT")
        assert "NỘI DUNG CONTEXT ĐẶC BIỆT" in prompt

    def test_citation_format_mentioned(self):
        prompt = build_prompt("câu hỏi", "context")
        assert "Điều" in prompt and "Văn bản" in prompt

    def test_returns_string(self):
        assert isinstance(build_prompt("q", "c"), str)


# ---------------------------------------------------------------------------
# 5. Tests cho parse_citations
# ---------------------------------------------------------------------------

class TestParseCitations:
    def test_dod_citation_format(self):
        """DoD: extract citation với format {dieu, khoan, van_ban}."""
        raw = "Theo quy định [Điều 116, Khoản 1, Văn bản luat-dat-dai-2024], điều kiện..."
        citations = parse_citations(raw)
        assert len(citations) == 1
        assert citations[0]["dieu"] == "116"
        assert citations[0]["khoan"] == "1"
        assert citations[0]["van_ban"] == "luat-dat-dai-2024"

    def test_citation_without_khoan(self):
        raw = "Căn cứ [Điều 57, Văn bản luat-dat-dai-2024], quy định..."
        citations = parse_citations(raw)
        assert len(citations) == 1
        assert citations[0]["dieu"] == "57"
        assert citations[0]["khoan"] is None
        assert "luat-dat-dai" in citations[0]["van_ban"]

    def test_multiple_citations(self):
        raw = (
            "Thứ nhất [Điều 1, Văn bản van-ban-a]. "
            "Thứ hai [Điều 2, Khoản 3, Văn bản van-ban-b]."
        )
        citations = parse_citations(raw)
        assert len(citations) == 2

    def test_no_citations(self):
        raw = "Không có trích dẫn nào trong câu này."
        assert parse_citations(raw) == []

    def test_empty_string(self):
        assert parse_citations("") == []

    def test_citation_with_diem(self):
        """Citation [Điều X, Khoản Y, Điểm Z, Văn bản W] phải parse đúng."""
        raw = "Theo [Điều 137, Khoản 1, Điểm b, Văn bản luat-dat-dai-2024], quy định..."
        citations = parse_citations(raw)
        assert len(citations) == 1
        assert citations[0]["dieu"] == "137"
        assert citations[0]["khoan"] == "1"
        assert citations[0]["diem"] == "b"
        assert citations[0]["van_ban"] == "luat-dat-dai-2024"
        assert citations[0]["loai"] == "dieu"

    def test_citation_with_diem_and_tiet(self):
        """Citation đầy đủ 4 cấp Điều/Khoản/Điểm/Tiết."""
        raw = "Quy định [Điều 5, Khoản 2, Điểm a, Tiết 1, Văn bản nd-50-2026]"
        citations = parse_citations(raw)
        assert len(citations) == 1
        assert citations[0]["dieu"] == "5"
        assert citations[0]["khoan"] == "2"
        assert citations[0]["diem"] == "a"
        assert citations[0]["tiet"] == "1"
        assert citations[0]["van_ban"] == "nd-50-2026"

    def test_citation_phu_luc(self):
        """Citation [Phụ lục X, Văn bản Y]."""
        raw = "Theo [Phụ lục I, Văn bản nq-22-2024-dong-nai], biểu phí..."
        citations = parse_citations(raw)
        assert len(citations) == 1
        assert citations[0]["loai"] == "phu_luc"
        assert citations[0]["dieu"] == "I"
        assert citations[0]["khoan"] is None
        assert citations[0]["van_ban"] == "nq-22-2024-dong-nai"

    def test_citation_phu_luc_with_khoan(self):
        """Citation [Phụ lục X, Khoản Y, Văn bản Z]."""
        raw = "[Phụ lục 16, Khoản 2, Văn bản qd-52-2016-tp-hcm]"
        citations = parse_citations(raw)
        assert len(citations) == 1
        assert citations[0]["loai"] == "phu_luc"
        assert citations[0]["dieu"] == "16"
        assert citations[0]["khoan"] == "2"

    def test_mixed_formats_in_one_text(self):
        """Mix nhiều định dạng trong cùng 1 đoạn text."""
        raw = (
            "[Điều 1, Văn bản a]. "
            "[Điều 2, Khoản 3, Văn bản b]. "
            "[Điều 137, Khoản 1, Điểm b, Văn bản c]. "
            "[Phụ lục I, Văn bản d]."
        )
        citations = parse_citations(raw)
        assert len(citations) == 4
        assert citations[2]["diem"] == "b"
        assert citations[3]["loai"] == "phu_luc"

    def test_backward_compat_old_format(self):
        """Format cũ phải vẫn parse được + có field mới (None/loai='dieu')."""
        raw = "[Điều 116, Khoản 1, Văn bản luat-dat-dai-2024]"
        citations = parse_citations(raw)
        assert len(citations) == 1
        assert citations[0]["dieu"] == "116"
        assert citations[0]["khoan"] == "1"
        assert citations[0]["diem"] is None
        assert citations[0]["tiet"] is None
        assert citations[0]["loai"] == "dieu"


# ---------------------------------------------------------------------------
# 6. Tests cho generate_answer
# ---------------------------------------------------------------------------

class TestGenerateAnswer:
    def test_dod_returns_answer_and_citations(self):
        """DoD: generate_answer trả về dict có answer + ít nhất 1 citation."""
        raw = (
            "Theo quy định [Điều 116, Khoản 1, Văn bản luat-dat-dai-2024], "
            "điều kiện chuyển mục đích sử dụng đất là..."
        )
        client = _mock_llm_client(raw)
        result = generate_answer("Điều kiện CMĐSDĐ?", "context...", client)

        assert "answer" in result
        assert "citations" in result
        assert len(result["citations"]) >= 1
        assert result["citations"][0]["dieu"] == "116"

    def test_context_used_flag(self):
        client = _mock_llm_client("câu trả lời [Điều 1, Văn bản x].")
        result = generate_answer("câu hỏi", "context có nội dung", client)
        assert result["context_used"] is True

    def test_empty_context_flag(self):
        client = _mock_llm_client("không có context")
        result = generate_answer("câu hỏi", "", client)
        assert result["context_used"] is False

    def test_answer_is_string(self):
        client = _mock_llm_client("câu trả lời")
        result = generate_answer("câu hỏi", "context", client)
        assert isinstance(result["answer"], str)

    def test_llm_called_with_prompt(self):
        """LLM được gọi với câu hỏi và context trong prompt."""
        client = _mock_llm_client("trả lời")
        generate_answer("CÂU HỎI ĐẶC BIỆT", "CONTEXT ĐẶC BIỆT", client)
        call_kwargs = client.messages.create.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs.args[0] if call_kwargs.args else []
        content = str(call_kwargs)
        assert "CÂU HỎI ĐẶC BIỆT" in content
        assert "CONTEXT ĐẶC BIỆT" in content


# ---------------------------------------------------------------------------
# Cấp ngày hiện tại cho lời nhắc
#
# Lời nhắc nhắc tới "thời điểm câu hỏi" ở nhiều chỗ nhưng không chỗ nào nói thời
# điểm đó là khi nào, nên mô hình suy từ tri thức huấn luyện và viết "sắp có
# hiệu lực" cho mốc đã qua. Tham số `ngay_hom_nay` cấp ngày để nó khỏi đoán.
#
# Mặc định TẮT là điều kiện bắt buộc: mọi mẻ đánh giá đã công bố được sinh bằng
# lời nhắc không có khối này, và khóa bộ nhớ đệm băm trên toàn bộ lời nhắc — chèn
# thêm một dòng là mọi kết quả cũ trượt cache và không tái lập được.
# ---------------------------------------------------------------------------

def test_mac_dinh_khong_chen_ngay():
    """Không truyền ngày → lời nhắc không được đổi một ký tự nào."""
    for mode in ("general", "irac"):
        system, user = build_messages("câu hỏi thử", "ngữ cảnh thử", mode)
        assert "THỜI ĐIỂM HIỆN TẠI" not in system
        assert "THỜI ĐIỂM HIỆN TẠI" not in user


def test_chen_ngay_khi_duoc_truyen():
    system, _ = build_messages("câu hỏi thử", "ngữ cảnh thử", "general",
                               ngay_hom_nay="19/08/2026")
    assert "THỜI ĐIỂM HIỆN TẠI: hôm nay là ngày 19/08/2026." in system
    # Phải nói rõ chiều so sánh, nếu không mô hình vẫn có thể viết sai thì
    assert "sắp có hiệu lực" in system


def test_ngay_rong_coi_nhu_khong_truyen():
    """Chuỗi rỗng từ biến môi trường chưa đặt không được sinh khối méo."""
    a, _ = build_messages("q", "c", "general")
    for gia_tri in ("", None):
        b, _ = build_messages("q", "c", "general", ngay_hom_nay=gia_tri)
        assert a == b


def test_ngay_lam_doi_loi_nhac_nen_doi_khoa_cache():
    """Bật ngày PHẢI đổi lời nhắc — nếu không, câu trả lời cũ sẽ bị dùng lại."""
    a, _ = build_messages("q", "c", "general")
    b, _ = build_messages("q", "c", "general", ngay_hom_nay="19/08/2026")
    assert a != b
