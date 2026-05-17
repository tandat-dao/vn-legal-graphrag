"""Unit tests cho parse_sections (Schema B — loose sections)."""
from src.retrieval.answer_generator import parse_sections


def test_full_3_sections():
    text = """## TRẢ LỜI
Đây là câu trả lời chính.
[Điều 121, Văn bản luat-dat-dai-2024]

## CẢNH BÁO LEX
- NĐ 102/2024 đã được sửa bởi NĐ 226/2025

## PHẠM VI
Trong phạm vi corpus
"""
    s = parse_sections(text)
    assert "câu trả lời chính" in s["tra_loi"]
    assert "NĐ 102/2024" in s["canh_bao_lex"]
    assert s["pham_vi"] == "Trong phạm vi corpus"


def test_missing_canh_bao_lex():
    text = """## TRẢ LỜI
Câu trả lời.

## PHẠM VI
Trong phạm vi corpus
"""
    s = parse_sections(text)
    assert s["tra_loi"] == "Câu trả lời."
    assert s["canh_bao_lex"] == ""
    assert s["pham_vi"] == "Trong phạm vi corpus"


def test_negative_refuse():
    text = """## TRẢ LỜI
Câu hỏi không thuộc phạm vi.

## CẢNH BÁO LEX
Không có

## PHẠM VI
Ngoài phạm vi corpus — phí công chứng thuộc Luật Công chứng
"""
    s = parse_sections(text)
    assert s["canh_bao_lex"] == "Không có"
    assert "Ngoài phạm vi" in s["pham_vi"]


def test_no_sections_at_all():
    """Câu trả lời không tuân thủ format → mọi field rỗng."""
    s = parse_sections("Just plain text without any section headers.")
    assert s == {"tra_loi": "", "canh_bao_lex": "", "pham_vi": ""}


def test_case_insensitive_header():
    text = """## trả lời
Lowercase header OK.

## Cảnh báo lex
Không có

## phạm vi
Trong phạm vi corpus
"""
    s = parse_sections(text)
    assert "Lowercase" in s["tra_loi"]
    assert s["canh_bao_lex"] == "Không có"


def test_sections_in_wrong_order():
    """Parser robust với thứ tự sai (LLM đôi khi đảo)."""
    text = """## PHẠM VI
Trong phạm vi corpus

## TRẢ LỜI
Body here.

## CẢNH BÁO LEX
Không có
"""
    s = parse_sections(text)
    assert s["pham_vi"] == "Trong phạm vi corpus"
    assert s["tra_loi"] == "Body here."
    assert s["canh_bao_lex"] == "Không có"
