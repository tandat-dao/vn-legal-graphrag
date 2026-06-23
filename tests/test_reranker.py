"""
Unit tests cho cross-encoder reranker — mock model, KHÔNG tải model, $0 / offline.
"""
from src.retrieval.reranker import rerank, RERANKER_MODEL


class _MockReranker:
    """Giả CrossEncoder: predict trả list điểm cố định theo thứ tự input."""
    def __init__(self, scores):
        self._scores = scores
        self.calls = []

    def predict(self, pairs):
        self.calls.append(pairs)
        return list(self._scores)


def _cand(cid, text):
    return {"id": cid, "text": text, "norm_id": f"norm-{cid}"}


def test_rerank_reorders_by_score_desc():
    cands = [_cand("a", "x"), _cand("b", "y"), _cand("c", "z")]
    m = _MockReranker([0.1, 0.9, 0.5])  # b cao nhất, rồi c, rồi a
    out = rerank("q", cands, model=m)
    assert [c["id"] for c in out] == ["b", "c", "a"]


def test_rerank_annotates_score_and_keeps_metadata():
    cands = [_cand("a", "x"), _cand("b", "y")]
    out = rerank("q", cands, model=_MockReranker([0.3, 0.7]))
    assert out[0]["id"] == "b" and out[0]["rerank_score"] == 0.7
    assert out[0]["norm_id"] == "norm-b"   # metadata giữ nguyên


def test_rerank_top_k_truncates():
    cands = [_cand(str(i), "t") for i in range(5)]
    out = rerank("q", cands, model=_MockReranker([0.5, 0.1, 0.9, 0.2, 0.7]), top_k=2)
    assert len(out) == 2
    assert [c["id"] for c in out] == ["2", "4"]   # 0.9, 0.7


def test_rerank_empty_returns_empty():
    assert rerank("q", [], model=_MockReranker([])) == []


def test_rerank_builds_query_text_pairs():
    cands = [_cand("a", "alpha"), _cand("b", "beta")]
    m = _MockReranker([0.2, 0.8])
    rerank("câu hỏi", cands, model=m)
    assert m.calls[0] == [["câu hỏi", "alpha"], ["câu hỏi", "beta"]]


def test_rerank_stable_on_tie():
    """Hòa điểm → giữ thứ tự gốc (sort ổn định)."""
    cands = [_cand("a", "x"), _cand("b", "y"), _cand("c", "z")]
    out = rerank("q", cands, model=_MockReranker([0.5, 0.5, 0.5]))
    assert [c["id"] for c in out] == ["a", "b", "c"]


def test_default_model_constant():
    assert RERANKER_MODEL == "BAAI/bge-reranker-v2-m3"
