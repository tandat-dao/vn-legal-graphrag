"""
Tests cho src/retrieval/semantic_filter.py — TASK-12.

Chiến lược: mock Qdrant + encode_text để chạy offline.
"""
import math
from unittest.mock import MagicMock, patch

import pytest

from src.retrieval.semantic_filter import (
    ScoredTextUnit,
    _keyword_score,
    _qdrant_id_to_hex,
    _rrf_score,
    _slugify_tokens,
    hybrid_search,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_point(
    hex_id: str,
    norm_id: str,
    component_id: str,
    score: float = 0.8,
    jurisdiction: str = "toan-quoc",
    tier: int = 2,
    theme: str = "dat-dai",
) -> MagicMock:
    point = MagicMock()
    point.id = int(hex_id, 16)
    point.score = score
    point.payload = {
        "content_type": "text_unit",
        "norm_id": norm_id,
        "component_id": component_id,
        "jurisdiction": jurisdiction,
        "tier": tier,
        "theme": theme,
        "valid_from": "2025-01-01",
        "valid_to": None,
    }
    return point


def _mock_qdrant(points: list, scroll_points: list | None = None) -> MagicMock:
    result = MagicMock()
    result.points = points
    client = MagicMock()
    client.query_points.return_value = result
    # scroll trả về tuple (list[point], next_offset)
    client.scroll.return_value = (scroll_points if scroll_points is not None else points, None)
    return client


def _mock_model() -> MagicMock:
    return MagicMock()


# ---------------------------------------------------------------------------
# 1. Unit tests cho _slugify_tokens
# ---------------------------------------------------------------------------

class TestSlugifyTokens:
    def test_vietnamese_accents_removed(self):
        tokens = _slugify_tokens("Nghị định 102")
        assert "nghi" in tokens
        assert "dinh" in tokens
        assert "102" in tokens

    def test_citation_number_parsed(self):
        tokens = _slugify_tokens("Nghị định 102/2024/NĐ-CP")
        assert "nghi" in tokens
        assert "102" in tokens
        assert "2024" in tokens
        assert "nd" in tokens
        assert "cp" in tokens

    def test_single_char_excluded(self):
        tokens = _slugify_tokens("a b c đất đai")
        assert "a" not in tokens
        assert "b" not in tokens

    def test_empty_string(self):
        assert _slugify_tokens("") == set()

    def test_slug_style_input(self):
        tokens = _slugify_tokens("nghi-dinh-102-2024-nd-cp")
        assert "nghi" in tokens
        assert "102" in tokens
        assert "nd" in tokens


# ---------------------------------------------------------------------------
# 2. Unit tests cho _keyword_score
# ---------------------------------------------------------------------------

class TestKeywordScore:
    def test_exact_norm_id_match(self):
        query_tokens = _slugify_tokens("Nghị định 102/2024/NĐ-CP")
        payload = {"norm_id": "nghi-dinh-102-2024-nd-cp", "component_id": "abc"}
        score = _keyword_score(query_tokens, payload)
        assert score > 0.5

    def test_no_match(self):
        query_tokens = _slugify_tokens("đăng ký khai sinh")
        payload = {"norm_id": "nghi-dinh-102-2024-nd-cp", "component_id": "xyz"}
        score = _keyword_score(query_tokens, payload)
        assert score == 0.0

    def test_empty_query_tokens(self):
        score = _keyword_score(set(), {"norm_id": "anything"})
        assert score == 0.0

    def test_partial_match(self):
        query_tokens = {"102", "2024", "unknown"}
        payload = {"norm_id": "nghi-dinh-102-2024-nd-cp", "component_id": ""}
        score = _keyword_score(query_tokens, payload)
        assert 0.0 < score < 1.0


# ---------------------------------------------------------------------------
# 3. Unit tests cho _rrf_score
# ---------------------------------------------------------------------------

class TestRrfScore:
    def test_best_rank_highest_score(self):
        # rank 0 beats rank 1
        assert _rrf_score(0, 0) > _rrf_score(1, 1)

    def test_symmetric(self):
        assert _rrf_score(2, 5) == _rrf_score(5, 2)

    def test_positive(self):
        assert _rrf_score(10, 10) > 0

    def test_formula(self):
        k = 60
        expected = 1.0 / (k + 3) + 1.0 / (k + 7)
        assert abs(_rrf_score(3, 7) - expected) < 1e-9


# ---------------------------------------------------------------------------
# 4. Unit tests cho _qdrant_id_to_hex
# ---------------------------------------------------------------------------

class TestQdrantIdToHex:
    def test_round_trip(self):
        original = "a1b2c3d4e5f6a7b8"
        qdrant_id = int(original, 16)
        recovered = _qdrant_id_to_hex(qdrant_id)
        assert recovered == original

    def test_zero_padded(self):
        # ID nhỏ phải được pad thành 16 chars
        recovered = _qdrant_id_to_hex(255)
        assert len(recovered) == 16
        assert recovered == "00000000000000ff"


# ---------------------------------------------------------------------------
# 4. Tests cho hybrid_search
# ---------------------------------------------------------------------------

class TestHybridSearch:
    @patch("src.retrieval.semantic_filter.encode_text", return_value=[0.1] * 1024)
    def test_dod_1_returns_top_k(self, mock_encode):
        """DoD: top_k=5 trả về đúng 5 kết quả (hoặc ít hơn nếu không đủ)."""
        points = [
            _make_point(f"000000000000000{i}", f"norm-{i}", f"comp-{i}", score=0.9 - i * 0.05)
            for i in range(7)
        ]
        client = _mock_qdrant(points)
        model = _mock_model()
        norm_ids = [f"norm-{i}" for i in range(7)]

        results = hybrid_search("câu hỏi đất đai", norm_ids, client, model, top_k=5)

        assert len(results) == 5

    @patch("src.retrieval.semantic_filter.encode_text", return_value=[0.1] * 1024)
    def test_dod_1_returns_fewer_if_not_enough(self, mock_encode):
        """top_k=10 nhưng chỉ có 3 kết quả → trả về 3."""
        points = [
            _make_point(f"000000000000000{i}", f"norm-{i}", f"comp-{i}")
            for i in range(3)
        ]
        client = _mock_qdrant(points)
        model = _mock_model()

        results = hybrid_search("câu hỏi", ["norm-0", "norm-1", "norm-2"], client, model, top_k=10)

        assert len(results) == 3

    @patch("src.retrieval.semantic_filter.encode_text", return_value=[0.1] * 1024)
    def test_dod_2_norm_ids_filter_passed_to_qdrant(self, mock_encode):
        """Payload filter norm_id IN norm_ids được truyền vào Qdrant."""
        client = _mock_qdrant([])
        model = _mock_model()
        norm_ids = ["luat-dat-dai-2024", "nghi-dinh-102-2024-nd-cp"]

        hybrid_search("câu hỏi", norm_ids, client, model)

        assert client.query_points.called
        call_kwargs = client.query_points.call_args
        query_filter = call_kwargs.kwargs.get("query_filter")
        assert query_filter is not None

    @patch("src.retrieval.semantic_filter.encode_text", return_value=[0.1] * 1024)
    def test_dod_3_keyword_boost_for_norm_id(self, mock_encode):
        """DoD: query chứa số hiệu NĐ 102/2024 → TextUnit có norm_id='nghi-dinh-102-2024-nd-cp'
        được boost lên top-1 dù dense score thấp hơn."""
        points = [
            # Dense score cao hơn nhưng không khớp số hiệu
            _make_point("0000000000000001", "luat-dat-dai-2024", "comp-1", score=0.95,
                        jurisdiction="toan-quoc", tier=1),
            # Dense score thấp hơn nhưng khớp số hiệu NĐ 102 chính xác
            _make_point("0000000000000002", "nghi-dinh-102-2024-nd-cp", "comp-2", score=0.80,
                        jurisdiction="toan-quoc", tier=2),
            _make_point("0000000000000003", "nghi-dinh-50-2026-nd-cp", "comp-3", score=0.75,
                        jurisdiction="toan-quoc", tier=2),
        ]
        client = _mock_qdrant(points)
        model = _mock_model()

        results = hybrid_search(
            "Nghị định 102/2024/NĐ-CP quy định gì",
            ["luat-dat-dai-2024", "nghi-dinh-102-2024-nd-cp", "nghi-dinh-50-2026-nd-cp"],
            client,
            model,
            top_k=3,
        )

        assert len(results) == 3
        # norm_id có "102-2024-nd-cp" phải được rank cao hơn nhờ keyword boost
        norm_ids_ranked = [r["norm_id"] for r in results]
        assert norm_ids_ranked[0] == "nghi-dinh-102-2024-nd-cp"

    @patch("src.retrieval.semantic_filter.encode_text", return_value=[0.1] * 1024)
    def test_empty_norm_ids_returns_empty(self, mock_encode):
        """Nếu norm_ids rỗng → trả về [] ngay, không gọi Qdrant."""
        client = _mock_qdrant([])
        model = _mock_model()

        results = hybrid_search("câu hỏi", [], client, model)

        assert results == []
        client.query_points.assert_not_called()

    @patch("src.retrieval.semantic_filter.encode_text", return_value=[0.1] * 1024)
    def test_scored_text_unit_fields(self, mock_encode):
        """ScoredTextUnit có đủ các trường cần thiết."""
        hex_id = "a1b2c3d4e5f6a7b8"
        points = [_make_point(hex_id, "luat-dat-dai-2024", "comp-abc",
                              jurisdiction="tp-hcm", tier=1, theme="dat-dai")]
        client = _mock_qdrant(points)
        model = _mock_model()

        results = hybrid_search("đất đai", ["luat-dat-dai-2024"], client, model, top_k=1)

        assert len(results) == 1
        r = results[0]
        assert r["text_unit_id"] == hex_id
        assert r["norm_id"] == "luat-dat-dai-2024"
        assert r["component_id"] == "comp-abc"
        assert r["jurisdiction"] == "tp-hcm"
        assert r["tier"] == 1
        assert r["theme"] == "dat-dai"
        assert isinstance(r["rrf_score"], float)
        assert r["rrf_score"] > 0

    @patch("src.retrieval.semantic_filter.encode_text", return_value=[0.1] * 1024)
    def test_results_sorted_by_rrf_desc(self, mock_encode):
        """Kết quả sắp xếp theo rrf_score giảm dần."""
        points = [
            _make_point(f"000000000000000{i}", f"norm-{i}", f"comp-{i}",
                        score=0.9 - i * 0.1)
            for i in range(5)
        ]
        client = _mock_qdrant(points)
        model = _mock_model()

        results = hybrid_search("câu hỏi", [f"norm-{i}" for i in range(5)], client, model)

        scores = [r["rrf_score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    @patch("src.retrieval.semantic_filter.encode_text", return_value=[0.1] * 1024)
    def test_dense_pool_larger_than_top_k(self, mock_encode):
        """Qdrant được gọi với limit = 2 * top_k (dense pool)."""
        client = _mock_qdrant([])
        model = _mock_model()

        hybrid_search("câu hỏi", ["luat-dat-dai-2024"], client, model, top_k=5)

        call_kwargs = client.query_points.call_args
        limit = call_kwargs.kwargs.get("limit")
        assert limit >= 10  # ít nhất 2 * top_k
