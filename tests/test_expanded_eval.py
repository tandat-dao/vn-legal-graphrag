"""
Unit tests cho expanded_eval — offline ($0), thuần hàm thống kê + behavior.
"""
import math

from src.evaluation.expanded_eval import (
    _bootstrap_ci, _wilcoxon_p, _win_loss_tie, _paired_deltas,
    _citation_behavior, _group_means, _overall,
)


# ---------------------------------------------------------------------------
# Helpers tạo per-question giả
# ---------------------------------------------------------------------------

def _q(qid, f1k, f1d=None, nr=1.0, gap="gap1", juris="toan-quoc",
       pred=1, gt=1, match=1, lat=10.0):
    f1d = f1k if f1d is None else f1d
    p = match / pred if pred else 1.0
    r = match / gt if gt else 1.0
    return {
        "id": qid, "gap_type": gap, "jurisdiction": juris, "theme": "dat-dai",
        "citation_score": {"f1": f1k, "precision": p, "recall": r,
                           "pred_count": pred, "gt_count": gt, "match_count": match},
        "citation_score_dieu": {"f1": f1d},
        "norm_recall": nr, "elapsed_seconds": lat,
    }


# ---------------------------------------------------------------------------
# Bootstrap CI: deterministic + bao quanh mean
# ---------------------------------------------------------------------------

def test_bootstrap_deterministic():
    d = [0.1, 0.2, 0.3, -0.1, 0.5]
    a = _bootstrap_ci(d, iters=2000, seed=7)
    b = _bootstrap_ci(d, iters=2000, seed=7)
    assert a == b                          # cùng seed → cùng kết quả
    assert math.isclose(a[0], sum(d) / len(d))  # mean khớp
    assert a[1] <= a[0] <= a[2]            # lo <= mean <= hi


def test_bootstrap_empty():
    assert _bootstrap_ci([]) == (0.0, 0.0, 0.0)


def test_ci_excludes_zero_for_all_positive():
    _, lo, hi = _bootstrap_ci([0.3, 0.4, 0.5, 0.35], iters=2000, seed=1)
    assert lo > 0  # mọi delta dương → CI nằm trên 0


# ---------------------------------------------------------------------------
# Wilcoxon + win/loss/tie
# ---------------------------------------------------------------------------

def test_wilcoxon_all_zero_is_nan():
    assert math.isnan(_wilcoxon_p([0.0, 0.0, 0.0]))


def test_wilcoxon_clear_signal_significant():
    p = _wilcoxon_p([0.3, 0.4, 0.5, 0.2, 0.6, 0.35, 0.45])
    assert p < 0.05


def test_win_loss_tie():
    assert _win_loss_tie([0.1, -0.2, 0.0, 0.3, 0.0]) == (2, 1, 2)


# ---------------------------------------------------------------------------
# Paired deltas: bỏ negative, align theo id
# ---------------------------------------------------------------------------

def test_paired_deltas_excludes_negative_and_aligns():
    g = {"Q1": _q("Q1", 0.8), "Q2": _q("Q2", 0.5, gap="negative"), "Q3": _q("Q3", 0.6)}
    b = {"Q1": _q("Q1", 0.4), "Q3": _q("Q3", 0.1), "Q9": _q("Q9", 0.0)}
    deltas, ids = _paired_deltas(g, b, lambda q: q["citation_score"]["f1"])
    assert ids == ["Q1", "Q3"]                  # Q2 negative bỏ, Q9 không chung
    assert deltas == [0.8 - 0.4, 0.6 - 0.1]


# ---------------------------------------------------------------------------
# Citation behavior
# ---------------------------------------------------------------------------

def test_citation_behavior_over_cite_detect():
    res = [
        _q("Q1", 0.5, pred=4, gt=2, match=2),   # 2 pred thừa → over-cite
        _q("Q2", 1.0, pred=2, gt=2, match=2),   # khớp đủ → không over
        _q("Q3", 0.5, gap="negative", pred=0, gt=0, match=0),  # bỏ
    ]
    beh = _citation_behavior(res)
    assert beh["n"] == 2
    assert beh["over_cite_rate"] == 0.5
    assert beh["pr_gap"] == beh["mean_recall"] - beh["mean_precision"]


# ---------------------------------------------------------------------------
# Group means + overall bỏ negative cho F1
# ---------------------------------------------------------------------------

def test_group_means_by_gap():
    res = [_q("Q1", 0.8, gap="gap2"), _q("Q2", 0.4, gap="gap2"), _q("Q3", 1.0, gap="gap4")]
    g = _group_means(res, "gap_type")
    assert g["gap2"]["n"] == 2 and math.isclose(g["gap2"]["f1_khoan"], 0.6)
    assert g["gap4"]["n"] == 1


def test_overall_excludes_negative_from_f1():
    res = [_q("Q1", 0.8), _q("Q2", 0.0, gap="negative")]
    ov = _overall(res)
    assert math.isclose(ov["f1_khoan"], 0.8)   # chỉ Q1
