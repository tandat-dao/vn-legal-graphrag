"""
Build Reproducibility Report — aggregate metrics across N runs same code state.

Output:
  - Mean, std, min, max cho mỗi metric (F1 Khoản/Điều, NormR, Latency,
    Faithfulness existence/support/faithful)
  - Per-Q variance: identify câu có F1 swing lớn (cao σ) — LLM stochastic
    candidates
  - Confidence interval 95% (giả định normal): mean ± 1.96 × (σ/√n)

Usage:
    python -m src.evaluation.build_reproducibility_report run1.json run2.json run3.json
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path


def _safe_float(x, default=None):
    if x is None:
        return default
    try:
        f = float(x)
        return default if math.isnan(f) else f
    except (TypeError, ValueError):
        return default


def _agg_stats(values: list[float]) -> dict:
    """Tính mean, std, min, max, CI95 cho list values."""
    values = [v for v in values if v is not None]
    if not values:
        return {"mean": None, "std": None, "min": None, "max": None, "n": 0}
    n = len(values)
    mean = statistics.mean(values)
    std = statistics.stdev(values) if n > 1 else 0.0
    ci95_half = 1.96 * std / math.sqrt(n) if n > 1 else 0.0
    return {
        "mean": mean, "std": std, "min": min(values), "max": max(values),
        "n": n, "ci95_half": ci95_half,
    }


def _extract_per_run_metrics(run_path: Path) -> dict:
    """Aggregate metrics từ 1 run JSON."""
    data = json.loads(run_path.read_text(encoding="utf-8"))
    results = data["results"]
    n = len(results)
    f1 = statistics.mean(r["citation_score"]["f1"] for r in results)
    f1_dieu = statistics.mean(
        _safe_float(r.get("citation_score_dieu", {}).get("f1"), 0) for r in results
    )
    nr = statistics.mean(r["norm_recall"] for r in results)
    lat = statistics.mean(r["elapsed_seconds"] for r in results)

    # Faithfulness (if available)
    faith_existence = None
    faith_support = None
    faith_faithful = None
    faith_data = [r.get("faithfulness") for r in results if r.get("faithfulness")]
    if faith_data:
        faith_existence = statistics.mean(f["existence_rate"] for f in faith_data)
        # support_rate có thể là NaN khi tier=1
        sup_vals = [
            _safe_float(f["support_rate"], None) for f in faith_data
            if _safe_float(f["support_rate"], None) is not None
        ]
        faith_support = statistics.mean(sup_vals) if sup_vals else None
        faith_faithful = statistics.mean(f["faithful_rate"] for f in faith_data)

    return {
        "path": str(run_path.name),
        "n_questions": n,
        "f1_khoan": f1,
        "f1_dieu": f1_dieu,
        "norm_recall": nr,
        "latency_s": lat,
        "faith_existence": faith_existence,
        "faith_support": faith_support,
        "faith_faithful": faith_faithful,
    }


def build_report(run_paths: list[Path]) -> str:
    """Build markdown report."""
    per_run = [_extract_per_run_metrics(p) for p in run_paths]

    lines = ["# Reproducibility Report — N={} runs same code state".format(len(per_run)), ""]
    lines.append("Mục đích: đo variance của metrics across N runs cùng code state +"
                 " --no-llm-cache → claim 'F1 = mean ± σ' thay vì single-run.")
    lines.append("")
    lines.append("## Per-run aggregate")
    lines.append("")
    lines.append("| Run | F1 Khoản | F1 Điều | NormR | Latency (s) | Faith existence | Faith support | Faith faithful |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for i, r in enumerate(per_run, 1):
        ex = f"{r['faith_existence']:.3f}" if r['faith_existence'] is not None else "—"
        sup = f"{r['faith_support']:.3f}" if r['faith_support'] is not None else "—"
        fa = f"{r['faith_faithful']:.3f}" if r['faith_faithful'] is not None else "—"
        lines.append(
            f"| {i}. `{r['path']}` "
            f"| {r['f1_khoan']:.3f} | {r['f1_dieu']:.3f} | {r['norm_recall']:.3f} "
            f"| {r['latency_s']:.2f} | {ex} | {sup} | {fa} |"
        )
    lines.append("")

    # Aggregate stats
    lines.append("## Aggregate (mean ± σ, 95% CI)")
    lines.append("")
    metrics = [
        ("F1 Khoản", "f1_khoan"),
        ("F1 Điều", "f1_dieu"),
        ("Norm Recall", "norm_recall"),
        ("Latency (s)", "latency_s"),
        ("Faith existence", "faith_existence"),
        ("Faith support", "faith_support"),
        ("Faith faithful", "faith_faithful"),
    ]
    lines.append("| Metric | Mean | σ | Min | Max | 95% CI |")
    lines.append("|---|---:|---:|---:|---:|---|")
    for label, key in metrics:
        vals = [r[key] for r in per_run if r[key] is not None]
        s = _agg_stats(vals)
        if s["n"] == 0:
            lines.append(f"| {label} | — | — | — | — | — |")
            continue
        ci_str = (f"[{s['mean'] - s['ci95_half']:.3f}, "
                  f"{s['mean'] + s['ci95_half']:.3f}]"
                  if s["n"] > 1 else "—")
        lines.append(
            f"| {label} | **{s['mean']:.3f}** | {s['std']:.3f} "
            f"| {s['min']:.3f} | {s['max']:.3f} | {ci_str} |"
        )

    # Per-Q variance — identify stochastic-prone cases
    lines.append("")
    lines.append("## Per-question F1 variance (top 10 σ desc)")
    lines.append("")
    all_results = []
    for p in run_paths:
        data = json.loads(p.read_text(encoding="utf-8"))
        all_results.append({r["id"]: r["citation_score"]["f1"] for r in data["results"]})
    ids = sorted(all_results[0].keys())
    per_q_stats = []
    for qid in ids:
        f1_vals = [r[qid] for r in all_results if qid in r]
        if len(f1_vals) > 1:
            std = statistics.stdev(f1_vals)
            per_q_stats.append((qid, statistics.mean(f1_vals), std, min(f1_vals), max(f1_vals), f1_vals))
    per_q_stats.sort(key=lambda x: -x[2])  # sort by std desc
    lines.append("| ID | Mean F1 | σ | Min | Max | Values |")
    lines.append("|---|---:|---:|---:|---:|---|")
    for qid, m, s, mn, mx, vals in per_q_stats[:10]:
        vals_str = ", ".join(f"{v:.2f}" for v in vals)
        lines.append(f"| {qid} | {m:.3f} | **{s:.3f}** | {mn:.3f} | {mx:.3f} | {vals_str} |")

    lines.append("")
    lines.append("**Interpretation**:")
    lines.append("- σ thấp ≈ 0 → câu deterministic (LLM stochastic không ảnh hưởng)")
    lines.append("- σ cao → câu có F1 swing across runs → cần cẩn thận khi attribute"
                 " regression cho code change vs LLM noise")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    paths = [Path(p) for p in sys.argv[1:]]
    for p in paths:
        if not p.exists():
            print(f"❌ {p} không tồn tại", file=sys.stderr)
            sys.exit(2)
    md = build_report(paths)
    print(md)


if __name__ == "__main__":
    main()
