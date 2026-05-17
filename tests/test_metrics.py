"""Unit tests cho src/evaluation/metrics.py (TASK-17)."""
from src.evaluation.metrics import (
    aggregate,
    citation_score,
    negative_correct,
    norm_recall,
)


def _c(dieu, khoan=None, van_ban="x", diem=None):
    return {"dieu": dieu, "khoan": khoan, "diem": diem, "van_ban": van_ban}


def test_perfect_match():
    gt = [_c("3", "1", "qd-69"), _c("3", "2", "qd-69")]
    pred = [_c("3", "1", "qd-69"), _c("3", "2", "qd-69")]
    s = citation_score(pred, gt)
    assert s["precision"] == 1.0 and s["recall"] == 1.0 and s["f1"] == 1.0


def test_partial_match():
    gt = [_c("3", "1", "a"), _c("3", "2", "a"), _c("3", "3", "a")]
    pred = [_c("3", "1", "a"), _c("3", "2", "a")]  # miss 1, no extras
    s = citation_score(pred, gt)
    assert s["precision"] == 1.0
    assert abs(s["recall"] - 2 / 3) < 1e-6
    assert abs(s["f1"] - 0.8) < 1e-6


def test_gt_khoan_none_wildcard():
    """GT cite cấp Điều (khoan=None) — pred trả về Khoản cụ thể vẫn match (semantic)."""
    gt = [_c("6", None, "nq87")]  # designer chỉ cite Đ6
    pred = [_c("6", "1", "nq87"), _c("6", "2", "nq87")]  # pipeline trả Đ6.1, Đ6.2
    s = citation_score(pred, gt, level="khoan")
    # 1 match (greedy 1-1), 2 pred, 1 gt
    assert s["precision"] == 0.5
    assert s["recall"] == 1.0
    assert abs(s["f1"] - 2/3) < 1e-6


def test_gt_khoan_none_wrong_dieu():
    """GT (Đ6, None) — pred (Đ5, 1) KHÔNG match (khác Điều)."""
    gt = [_c("6", None, "x")]
    pred = [_c("5", "1", "x"), _c("7", None, "x")]
    s = citation_score(pred, gt, level="khoan")
    assert s["match_count"] == 0
    assert s["recall"] == 0.0


def test_extra_predictions():
    gt = [_c("3", "1", "a")]
    pred = [_c("3", "1", "a"), _c("9", "9", "b")]
    s = citation_score(pred, gt)
    assert s["precision"] == 0.5 and s["recall"] == 1.0


def test_case_insensitive_van_ban():
    gt = [_c("3", "1", "Luat-DD")]
    pred = [_c("3", "1", "luat-dd")]
    s = citation_score(pred, gt)
    assert s["f1"] == 1.0


def test_negative_both_empty():
    s = citation_score([], [])
    assert s["precision"] == 1.0 and s["recall"] == 1.0 and s["f1"] == 1.0


def test_negative_pred_not_empty():
    # GT rỗng (negative question), system bịa citation → precision=0
    s = citation_score([_c("1", "1", "x")], [])
    assert s["precision"] == 0.0 and s["recall"] == 1.0 and s["f1"] == 0.0


def test_norm_recall():
    gt = [_c("3", "1", "a"), _c("4", "1", "b"), _c("5", "1", "c")]
    pred = [_c("99", "99", "a"), _c("88", "88", "b")]  # Điều sai nhưng văn bản đúng
    # 2/3 văn bản gt được cover
    assert abs(norm_recall(pred, gt) - 2 / 3) < 1e-6


def test_negative_correct():
    assert negative_correct([], "negative") is True
    assert negative_correct([_c("1", "1", "x")], "negative") is False
    assert negative_correct([], "gap1") is False


def test_aggregate_basic():
    per_q = [
        {
            "id": "Q01", "gap_type": "gap1", "theme": "dat-dai", "jurisdiction": "toan-quoc",
            "citation_score": {"precision": 1.0, "recall": 1.0, "f1": 1.0},
            "norm_recall": 1.0, "elapsed_seconds": 5.0, "negative_correct": None,
        },
        {
            "id": "Q02", "gap_type": "gap2", "theme": "dat-dai", "jurisdiction": "tp-hcm",
            "citation_score": {"precision": 0.5, "recall": 1.0, "f1": 0.67},
            "norm_recall": 1.0, "elapsed_seconds": 10.0, "negative_correct": None,
        },
        {
            "id": "Q03", "gap_type": "negative", "theme": "dat-dai", "jurisdiction": "toan-quoc",
            "citation_score": {"precision": 1.0, "recall": 1.0, "f1": 1.0},
            "norm_recall": 1.0, "elapsed_seconds": 3.0, "negative_correct": True,
        },
    ]
    agg = aggregate(per_q)
    assert agg["count"] == 3
    assert abs(agg["precision_mean"] - (1.0 + 0.5 + 1.0) / 3) < 1e-6
    assert agg["negative_count"] == 1
    assert agg["negative_correct_rate"] == 1.0
    assert "gap1" in agg["by_gap"] and "gap2" in agg["by_gap"]
    assert agg["by_theme"]["dat-dai"]["count"] == 3
