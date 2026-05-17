"""
Metrics — TASK-17
Tính các metric để so sánh GraphRAG vs Naive RAG baseline.

Metric set (Phase 4):
  - Citation Accuracy: precision / recall / F1 trên (dieu, khoan, van_ban) tuple
  - Norm-level Recall: % văn bản (van_ban) trong ground truth có trong citations dự đoán
  - Negative Handling: câu negative trả về citations rỗng đúng không
  - Latency: thống kê elapsed_seconds

Hàm thuần (không I/O) — runner.py gọi và aggregate.
"""
from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from typing import TypedDict


class CitationScore(TypedDict):
    precision: float
    recall: float
    f1: float
    pred_count: int
    gt_count: int
    match_count: int


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def _norm_str(v) -> str | None:
    """Chuẩn hoá string để so khớp: strip + lowercase. None nếu rỗng."""
    if v is None:
        return None
    s = str(v).strip().lower()
    return s or None


def _citation_key(c: dict, level: str = "khoan") -> tuple:
    """Chuyển citation dict thành tuple key để so sánh.

    level:
      - 'van_ban': chỉ (van_ban,) — coarse, chỉ kiểm văn bản
      - 'dieu':    (dieu, van_ban) — kiểm Điều
      - 'khoan':   (dieu, khoan, van_ban) — default, tương đương cấp CTV
      - 'diem':    (dieu, khoan, diem, van_ban) — strict
    """
    vb = _norm_str(c.get("van_ban"))
    dieu = _norm_str(c.get("dieu"))
    khoan = _norm_str(c.get("khoan"))
    diem = _norm_str(c.get("diem"))
    if level == "van_ban":
        return (vb,)
    if level == "dieu":
        return (dieu, vb)
    if level == "khoan":
        return (dieu, khoan, vb)
    if level == "diem":
        return (dieu, khoan, diem, vb)
    raise ValueError(f"level không hợp lệ: {level}")


# ---------------------------------------------------------------------------
# Citation accuracy (per question)
# ---------------------------------------------------------------------------

def citation_score(
    pred: list[dict],
    gt: list[dict],
    level: str = "khoan",
) -> CitationScore:
    """Tính precision/recall/F1 cho citations của một câu hỏi.

    Dùng multiset (Counter) — duplicates được đếm. Match là intersection của hai
    multiset ở cấp `level`.

    Trường hợp đặc biệt:
      - gt rỗng, pred rỗng: precision=recall=f1=1.0 (correct refuse)
      - gt rỗng, pred khác rỗng: precision=0, recall=1 (theo convention), f1=0
        — câu negative bịa citation → penalize qua precision
      - gt khác rỗng, pred rỗng: precision=1 (theo convention), recall=0, f1=0
    """
    pred_keys = Counter(_citation_key(c, level) for c in pred)
    gt_keys = Counter(_citation_key(c, level) for c in gt)

    if not pred_keys and not gt_keys:
        return CitationScore(precision=1.0, recall=1.0, f1=1.0, pred_count=0, gt_count=0, match_count=0)

    intersection = pred_keys & gt_keys  # multiset intersection
    match = sum(intersection.values())
    # Precision: pred rỗng → 1.0 (không bịa) nếu gt cũng rỗng, else 0.0 (gt có mà không trả).
    # Recall: gt rỗng → 1.0 (không có gì để recall — không phạt qua recall, mà phạt qua precision).
    p = match / sum(pred_keys.values()) if pred_keys else (1.0 if not gt_keys else 0.0)
    r = match / sum(gt_keys.values()) if gt_keys else 1.0
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    return CitationScore(
        precision=p,
        recall=r,
        f1=f1,
        pred_count=sum(pred_keys.values()),
        gt_count=sum(gt_keys.values()),
        match_count=match,
    )


def norm_recall(pred: list[dict], gt: list[dict]) -> float:
    """% văn bản (norm_id) trong ground truth được hệ thống có dẫn (cấp coarse).

    Trả 1.0 nếu gt rỗng và pred rỗng (negative correct); 0.0 nếu gt rỗng và pred khác rỗng;
    nếu gt khác rỗng: |gt_van_ban ∩ pred_van_ban| / |gt_van_ban|.
    """
    gt_norms = {_norm_str(c.get("van_ban")) for c in gt if c.get("van_ban")}
    pred_norms = {_norm_str(c.get("van_ban")) for c in pred if c.get("van_ban")}
    if not gt_norms:
        return 1.0 if not pred_norms else 0.0
    return len(gt_norms & pred_norms) / len(gt_norms)


def negative_correct(pred: list[dict], gt_type: str) -> bool:
    """Câu negative → pass nếu pred citations rỗng (hệ thống từ chối đúng)."""
    if gt_type != "negative":
        return False  # không áp dụng
    return len(pred) == 0


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate(per_question: list[dict]) -> dict:
    """Tổng hợp metric từ list các per-question result.

    per_question item phải có:
      - id, gap_type, theme, jurisdiction
      - citation_score: {precision, recall, f1, ...}
      - norm_recall: float
      - elapsed_seconds: float
      - negative_correct: bool | None  (None nếu không phải negative)
    """
    if not per_question:
        return {"count": 0}

    def _mean(xs):
        xs = [x for x in xs if x is not None]
        return statistics.mean(xs) if xs else 0.0

    overall = {
        "count": len(per_question),
        # Cấp Khoản (strict): citation đúng (dieu, khoan, van_ban)
        "precision_mean": _mean(q["citation_score"]["precision"] for q in per_question),
        "recall_mean": _mean(q["citation_score"]["recall"] for q in per_question),
        "f1_mean": _mean(q["citation_score"]["f1"] for q in per_question),
        # Cấp Điều (looser): citation đúng (dieu, van_ban) — đo định tuyến văn bản
        "precision_dieu_mean": _mean(q.get("citation_score_dieu", {}).get("precision") for q in per_question),
        "recall_dieu_mean": _mean(q.get("citation_score_dieu", {}).get("recall") for q in per_question),
        "f1_dieu_mean": _mean(q.get("citation_score_dieu", {}).get("f1") for q in per_question),
        # Norm + latency
        "norm_recall_mean": _mean(q["norm_recall"] for q in per_question),
        "latency_mean_s": _mean(q["elapsed_seconds"] for q in per_question),
        "latency_p95_s": (
            sorted(q["elapsed_seconds"] for q in per_question)[int(0.95 * (len(per_question) - 1))]
            if per_question else 0.0
        ),
    }

    # Negative-only subset
    negs = [q for q in per_question if q["gap_type"] == "negative"]
    if negs:
        overall["negative_count"] = len(negs)
        overall["negative_correct_rate"] = sum(1 for q in negs if q["negative_correct"]) / len(negs)

    # Per-gap breakdown
    by_gap = defaultdict(list)
    for q in per_question:
        by_gap[q["gap_type"]].append(q)
    overall["by_gap"] = {
        gap: {
            "count": len(qs),
            "f1": _mean(q["citation_score"]["f1"] for q in qs),
            "f1_dieu": _mean(q.get("citation_score_dieu", {}).get("f1") for q in qs),
            "norm_recall": _mean(q["norm_recall"] for q in qs),
        }
        for gap, qs in sorted(by_gap.items())
    }

    # Per-theme breakdown
    by_theme = defaultdict(list)
    for q in per_question:
        by_theme[q["theme"]].append(q)
    overall["by_theme"] = {
        theme: {
            "count": len(qs),
            "f1": _mean(q["citation_score"]["f1"] for q in qs),
            "norm_recall": _mean(q["norm_recall"] for q in qs),
        }
        for theme, qs in sorted(by_theme.items())
    }

    return overall


# ---------------------------------------------------------------------------
# Markdown reporter
# ---------------------------------------------------------------------------

def render_summary_md(
    graphrag_agg: dict,
    baseline_agg: dict,
    *,
    test_set_file: str,
    timestamp: str,
) -> str:
    """Render bảng so sánh markdown cho 2 hệ thống."""
    def _f(v, fmt=".3f"):
        return f"{v:{fmt}}" if isinstance(v, (int, float)) else str(v)

    lines = [
        f"# Metrics Summary — TASK-17",
        f"",
        f"- Test set: `{test_set_file}`",
        f"- Run timestamp: {timestamp}",
        f"- Số câu hỏi: {graphrag_agg.get('count', 0)}",
        f"",
        f"## Overall",
        f"",
        f"| Metric | GraphRAG | Baseline | Δ (G-B) |",
        f"|---|---:|---:|---:|",
    ]
    for key, label in [
        ("precision_mean", "Citation Precision (Khoản)"),
        ("recall_mean", "Citation Recall (Khoản)"),
        ("f1_mean", "Citation F1 (Khoản — strict)"),
        ("precision_dieu_mean", "Citation Precision (Điều)"),
        ("recall_dieu_mean", "Citation Recall (Điều)"),
        ("f1_dieu_mean", "Citation F1 (Điều — đo định tuyến văn bản)"),
        ("norm_recall_mean", "Norm-level Recall (Văn bản)"),
        ("latency_mean_s", "Latency mean (s)"),
        ("latency_p95_s", "Latency p95 (s)"),
    ]:
        g = graphrag_agg.get(key, 0)
        b = baseline_agg.get(key, 0)
        delta = g - b if isinstance(g, (int, float)) and isinstance(b, (int, float)) else "-"
        lines.append(f"| {label} | {_f(g)} | {_f(b)} | {_f(delta)} |")

    if "negative_correct_rate" in graphrag_agg or "negative_correct_rate" in baseline_agg:
        g = graphrag_agg.get("negative_correct_rate", 0)
        b = baseline_agg.get("negative_correct_rate", 0)
        n = graphrag_agg.get("negative_count", 0)
        lines.append(f"| Negative correct rate ({n} câu) | {_f(g)} | {_f(b)} | {_f(g - b)} |")

    lines += ["", "## Theo gap_type", "", "| Gap | N | G F1(Kh) | B F1(Kh) | G F1(Đ) | B F1(Đ) | G NormR | B NormR |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    gaps = sorted(set(graphrag_agg.get("by_gap", {}).keys()) | set(baseline_agg.get("by_gap", {}).keys()))
    for gap in gaps:
        g = graphrag_agg.get("by_gap", {}).get(gap, {})
        b = baseline_agg.get("by_gap", {}).get(gap, {})
        n = g.get("count", b.get("count", 0))
        lines.append(
            f"| {gap} | {n} "
            f"| {_f(g.get('f1', 0))} | {_f(b.get('f1', 0))} "
            f"| {_f(g.get('f1_dieu', 0))} | {_f(b.get('f1_dieu', 0))} "
            f"| {_f(g.get('norm_recall', 0))} | {_f(b.get('norm_recall', 0))} |"
        )

    lines += ["", "## Theo theme", "", "| Theme | N | G F1 | B F1 | G NormRecall | B NormRecall |", "|---|---:|---:|---:|---:|---:|"]
    themes = sorted(set(graphrag_agg.get("by_theme", {}).keys()) | set(baseline_agg.get("by_theme", {}).keys()))
    for theme in themes:
        g = graphrag_agg.get("by_theme", {}).get(theme, {})
        b = baseline_agg.get("by_theme", {}).get(theme, {})
        n = g.get("count", b.get("count", 0))
        lines.append(
            f"| {theme} | {n} | {_f(g.get('f1', 0))} | {_f(b.get('f1', 0))} "
            f"| {_f(g.get('norm_recall', 0))} | {_f(b.get('norm_recall', 0))} |"
        )

    lines.append("")
    return "\n".join(lines)
