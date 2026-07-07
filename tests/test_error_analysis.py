"""Tests cho E3 error_analysis — phân loại retrieval/generation/over-cite/negative."""
from src.evaluation.error_analysis import analyze, classify_question


def _item(**kw):
    base = dict(id="V1", gap_type="gap3", question="q",
                ground_truth_citations=[], pred_citations=[], context="")
    base.update(kw)
    return base


class TestClassify:
    def test_retrieval_fail(self):
        # GT van_ban 'X' KHÔNG có trong context → retrieval-fail
        it = _item(ground_truth_citations=[{"dieu": "5", "khoan": "1", "van_ban": "X"}],
                   pred_citations=[], context="--- Điều 9 (Y) ---\n...")
        c = classify_question(it)
        assert len(c["retrieval_fail"]) == 1
        assert len(c["generation_fail"]) == 0

    def test_generation_fail(self):
        # GT van_ban 'X' CÓ trong context nhưng hệ không trích → generation-fail
        it = _item(ground_truth_citations=[{"dieu": "5", "khoan": "1", "van_ban": "X"}],
                   pred_citations=[], context="--- Điều 5, Khoản 1 (X) ---\n...")
        c = classify_question(it)
        assert len(c["generation_fail"]) == 1
        assert len(c["retrieval_fail"]) == 0

    def test_over_cite(self):
        it = _item(ground_truth_citations=[{"dieu": "5", "van_ban": "X"}],
                   pred_citations=[{"dieu": "5", "van_ban": "X"},
                                   {"dieu": "9", "van_ban": "Z"}],
                   context="--- Điều 5 (X) ---")
        c = classify_question(it)
        assert len(c["over_cite"]) == 1
        assert c["over_cite"][0]["van_ban"] == "Z"
        assert c["n_matched"] == 1

    def test_perfect_no_errors(self):
        it = _item(ground_truth_citations=[{"dieu": "5", "van_ban": "X"}],
                   pred_citations=[{"dieu": "5", "van_ban": "X"}],
                   context="--- Điều 5 (X) ---")
        c = classify_question(it)
        assert not c["retrieval_fail"] and not c["generation_fail"] and not c["over_cite"]

    def test_negative_ok_when_no_citations(self):
        it = _item(gap_type="negative", pred_citations=[])
        c = classify_question(it)
        assert c["kind"] == "negative" and c["ok"] is True

    def test_negative_fail_when_cites(self):
        it = _item(gap_type="negative",
                   pred_citations=[{"dieu": "5", "van_ban": "X"}])
        c = classify_question(it)
        assert c["ok"] is False and len(c["negative_fail"]) == 1


class TestAnalyze:
    def test_aggregate_and_flags(self):
        results = [
            _item(id="V1", gap_type="gap3",
                  ground_truth_citations=[{"dieu": "5", "van_ban": "X"}],
                  pred_citations=[], context="no match"),          # retrieval-fail
            _item(id="V2", gap_type="gap2",
                  ground_truth_citations=[{"dieu": "5", "van_ban": "X"}],
                  pred_citations=[{"dieu": "5", "van_ban": "X"},
                                  {"dieu": "9", "van_ban": "Z"}],
                  context="--- Điều 5 (X) ---"),                    # over-cite
            _item(id="V3", gap_type="negative",
                  pred_citations=[{"dieu": "1", "van_ban": "W"}]),  # negative-fail
        ]
        rep = analyze(results)
        assert rep["taxonomy"]["retrieval_fail"] == 1
        assert rep["taxonomy"]["over_cite"] == 1
        assert rep["taxonomy"]["negative_fail"] == 1
        assert rep["n_over_cite_questions"] == 1
        assert rep["per_gap"]["gap3"]["retrieval_fail"] == 1
