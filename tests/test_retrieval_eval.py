"""
Unit tests cho retrieval-metric harness — offline ($0), không DB/API.
Chỉ test các hàm thuần: _chunk_to_citation, _recall_at_k, _mrr.
"""
from src.evaluation.retrieval_eval import _chunk_to_citation, _recall_at_k, _mrr


# ---------------------------------------------------------------------------
# _chunk_to_citation: parse context_path → {van_ban, dieu, khoan, loai}
# ---------------------------------------------------------------------------

def test_parse_dieu_khoan():
    c = _chunk_to_citation("luat-dat-dai-2024",
                           ["luat-dat-dai-2024", "Điều 116. Căn cứ", "Khoản 5."])
    assert c == {"van_ban": "luat-dat-dai-2024", "dieu": "116", "khoan": "5", "loai": "dieu"}


def test_parse_dieu_only():
    c = _chunk_to_citation("nd-102", ["nd-102", "Điều 13. Trình tự"])
    assert c["dieu"] == "13" and c["khoan"] is None and c["loai"] == "dieu"


def test_parse_phu_luc_numbered():
    c = _chunk_to_citation("nq-22", ["nq-22", "Phụ lục I. Biểu phí"])
    assert c["loai"] == "phu_luc" and c["dieu"] == "I"


def test_parse_phu_luc_default():
    c = _chunk_to_citation("nq-87", ["nq-87", "Phụ lục"])
    assert c["loai"] == "phu_luc" and c["dieu"] == "_default"


def test_parse_empty_context_path():
    c = _chunk_to_citation("norm-x", [])
    assert c["van_ban"] == "norm-x" and c["dieu"] is None


# ---------------------------------------------------------------------------
# Recall@k + MRR (dùng cit_matches làm semantic match)
# ---------------------------------------------------------------------------

_GT = [{"van_ban": "luat-dat-dai-2024", "dieu": "116", "khoan": "5"}]


def test_recall_hit_within_k():
    cands = [
        {"van_ban": "x", "dieu": "1", "khoan": None},
        {"van_ban": "luat-dat-dai-2024", "dieu": "116", "khoan": "5"},  # rank 2
    ]
    assert _recall_at_k(cands, _GT, "khoan", 5) == 1.0
    assert _recall_at_k(cands, _GT, "khoan", 1) == 0.0  # rank1 không khớp


def test_recall_multi_gt_coverage():
    gt = [{"van_ban": "A", "dieu": "1"}, {"van_ban": "B", "dieu": "2"}]
    cands = [{"van_ban": "A", "dieu": "1"}]  # chỉ phủ 1/2 GT
    assert _recall_at_k(cands, gt, "dieu", 5) == 0.5


def test_mrr_first_hit_rank():
    cands = [
        {"van_ban": "x", "dieu": "1"},
        {"van_ban": "y", "dieu": "2"},
        {"van_ban": "luat-dat-dai-2024", "dieu": "116", "khoan": "5"},  # rank 3
    ]
    assert _mrr(cands, _GT, "khoan") == 1.0 / 3


def test_mrr_no_hit():
    cands = [{"van_ban": "x", "dieu": "1"}]
    assert _mrr(cands, _GT, "khoan") == 0.0


def test_dieu_level_ignores_khoan():
    """level='dieu': chỉ cần van_ban+dieu khớp (bỏ qua khoan)."""
    cands = [{"van_ban": "luat-dat-dai-2024", "dieu": "116", "khoan": "9"}]  # khoan sai
    assert _recall_at_k(cands, _GT, "dieu", 5) == 1.0   # vẫn khớp ở cấp Điều
    assert _recall_at_k(cands, _GT, "khoan", 5) == 0.0  # nhưng không ở cấp Khoản
