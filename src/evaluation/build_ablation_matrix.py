"""
Build Ablation Matrix table — table tổng hợp impact của từng fix layer.

Mục đích cho thesis Experiments chapter: 1 bảng duy nhất show cumulative
F1/NormR/latency qua 4 fix layers, so sánh với Baseline + canonical.

Sources (kết quả đã có trong data/evaluation/):
  - Baseline (Naive RAG):       results_baseline_20260519-204426.json
  - v2.3 canonical:             results_graphrag_20260519-161509.json
  - v2.3 + dedupe (reuse):      results_graphrag_reused_20260519-195317.json
  - v2.4 (+prompt TEMPORAL #4): results_graphrag_20260519-204426.json
  - v2.5 (+Dense Floor):        results_graphrag_20260519-212405.json
  - v2.6 (+Pass -1):            results_graphrag_20260520-merged_pass-neg1.json

Output: markdown + LaTeX-ready table cho thesis.
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

DATA_DIR = Path("data/evaluation")

CONFIGS = [
    ("Baseline (Naive RAG)", "results_baseline_20260519-204426.json", "baseline"),
    ("v2.3 GraphRAG canonical", "results_graphrag_20260519-161509.json", "v2.3"),
    ("+ parse_citations dedupe", "results_graphrag_reused_20260519-195317.json", "v2.3+dedupe"),
    ("+ Prompt TEMPORAL #4", "results_graphrag_20260519-204426.json", "v2.4"),
    ("+ Dense Floor (Pass 0)", "results_graphrag_20260519-212405.json", "v2.5"),
    ("+ Structured Cite (Pass -1) [N=3 mean]", "results_graphrag_20260520-205113.json", "v2.6"),
]

# Repro N=3 cho v2.6 — list các runs cùng code state
V26_REPRO_RUNS = [
    "results_graphrag_20260520-205113.json",
    "results_graphrag_20260520-210859.json",
    "results_graphrag_20260520-211930.json",
]


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return statistics.mean(xs) if xs else 0.0


def _aggregate(results: list[dict]) -> dict:
    """Compute aggregate metrics cho 1 run."""
    if not results:
        return {}
    f1 = _mean(r["citation_score"]["f1"] for r in results)
    f1_dieu = _mean(r.get("citation_score_dieu", {}).get("f1") for r in results)
    nr = _mean(r["norm_recall"] for r in results)
    lat = _mean(r["elapsed_seconds"] for r in results)
    neg = [r for r in results if r["gap_type"] == "negative"]
    neg_rate = sum(1 for r in neg if r["negative_correct"]) / len(neg) if neg else 1.0
    # Per-gap
    by_gap = {}
    for r in results:
        gap = r["gap_type"]
        by_gap.setdefault(gap, []).append(r["citation_score"]["f1"])
    gap_f1 = {g: _mean(xs) for g, xs in by_gap.items()}
    return {
        "n": len(results),
        "f1_khoan": f1, "f1_dieu": f1_dieu, "norm_recall": nr,
        "latency_s": lat, "negative_rate": neg_rate,
        "gap_f1": gap_f1,
    }


def _aggregate_repro_n3(filenames: list[str]) -> dict:
    """Compute mean across N runs cho v2.6 final config."""
    import math, statistics
    aggs = []
    for fname in filenames:
        path = DATA_DIR / fname
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        aggs.append(_aggregate(data["results"]))
    if not aggs:
        return {}
    def _safe_mean(key):
        vals = [a[key] for a in aggs if a.get(key) is not None]
        return statistics.mean(vals) if vals else 0.0
    def _safe_std(key):
        vals = [a[key] for a in aggs if a.get(key) is not None]
        return statistics.stdev(vals) if len(vals) > 1 else 0.0
    return {
        "n": aggs[0]["n"],
        "f1_khoan": _safe_mean("f1_khoan"),
        "f1_khoan_std": _safe_std("f1_khoan"),
        "f1_dieu": _safe_mean("f1_dieu"),
        "norm_recall": _safe_mean("norm_recall"),
        "latency_s": _safe_mean("latency_s"),
        "negative_rate": _safe_mean("negative_rate"),
        "gap_f1": {
            g: statistics.mean([a["gap_f1"].get(g, 0) for a in aggs])
            for g in set().union(*(a.get("gap_f1", {}).keys() for a in aggs))
        },
        "n_runs": len(aggs),
    }


def build_table() -> str:
    """Build markdown table."""
    rows = []
    baseline_f1 = None
    canonical_f1 = None
    prev_f1 = None

    lines = []
    lines.append("# Ablation Matrix — Cumulative Fix Impact (26 câu Đất đai)")
    lines.append("")
    lines.append("Bảng tổng hợp impact của từng fix layer, đo trên cùng test set"
                 " (`test_set_dat_dai.json`), cùng embedding (BGE-M3), cùng LLM"
                 " (Claude Sonnet 4.6), cùng eval-mode (force_jurisdiction)."
                 " **Chỉ khác retrieval/parsing logic**.")
    lines.append("")
    lines.append("**Reproducibility note**: v2.6 final config có N=3 runs cùng"
                 " code state với `--no-llm-cache` để measure variance. Các config"
                 " trước (v2.3-v2.5) là N=1 — variance không đo nhưng cùng order"
                 " of magnitude (xem REPRODUCIBILITY_REPORT_20260520.md).")
    lines.append("")
    lines.append("## Aggregate metrics")
    lines.append("")
    lines.append("| # | Configuration | F1 Khoản | F1 Điều | NormR | Latency (s) | Neg. correct | Δ vs Baseline | Δ vs Prev |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")

    aggregates = []
    for label, fname, key in CONFIGS:
        path = DATA_DIR / fname
        if not path.exists():
            lines.append(f"| ? | {label} | _(file missing: {fname})_ | | | | | | |")
            continue
        # v2.6 dùng N=3 reproducibility mean thay vì single run
        if key == "v2.6":
            agg = _aggregate_repro_n3(V26_REPRO_RUNS)
        else:
            data = json.loads(path.read_text(encoding="utf-8"))
            agg = _aggregate(data["results"])
        aggregates.append((label, agg))

        if baseline_f1 is None:
            baseline_f1 = agg["f1_khoan"]
        delta_baseline = (
            f"+{(agg['f1_khoan'] - baseline_f1) / baseline_f1 * 100:.1f}%"
            if baseline_f1 and label != "Baseline (Naive RAG)" else "—"
        )
        delta_prev = (
            f"+{(agg['f1_khoan'] - prev_f1):.3f}"
            if prev_f1 is not None else "—"
        )
        if label == "v2.3 GraphRAG canonical":
            canonical_f1 = agg["f1_khoan"]

        std_suffix = f" ±{agg.get('f1_khoan_std', 0):.3f}" if agg.get("f1_khoan_std") else ""
        lines.append(
            f"| {len(aggregates)} | {label} "
            f"| **{agg['f1_khoan']:.3f}**{std_suffix} | {agg['f1_dieu']:.3f} | {agg['norm_recall']:.3f} "
            f"| {agg['latency_s']:.2f} | {agg['negative_rate']:.0%} "
            f"| {delta_baseline} | {delta_prev} |"
        )
        prev_f1 = agg["f1_khoan"]

    lines.append("")
    if baseline_f1 and canonical_f1 and aggregates:
        final_f1 = aggregates[-1][1]["f1_khoan"]
        lines.append(f"**Headline**:")
        lines.append(f"- Baseline → v2.6 GraphRAG: F1 **{baseline_f1:.3f} → {final_f1:.3f}** "
                     f"(+{(final_f1 - baseline_f1) / baseline_f1 * 100:.1f}%)")
        lines.append(f"- v2.3 canonical → v2.6 (4 fix layers cumulative): F1 **{canonical_f1:.3f} → {final_f1:.3f}** "
                     f"(+{(final_f1 - canonical_f1) / canonical_f1 * 100:.1f}%)")
        lines.append("")
        lines.append("> **Latency note**: v2.3 canonical 2.85s là **cache artifact** (cache hit từ debugging session). v2.4+ runs với `--no-llm-cache` cho số real ~22-28s. Khi viết thesis dùng số v2.4+ làm honest latency.")
        lines.append("")

    # Per-Gap breakdown
    lines.append("## Per-Gap F1 Khoản")
    lines.append("")
    all_gaps = sorted({g for _, a in aggregates for g in a.get("gap_f1", {}).keys()})
    header = "| Configuration | " + " | ".join(f"{g} (n)" for g in all_gaps) + " |"
    sep = "|---|" + "|".join("---:" for _ in all_gaps) + "|"
    lines.append(header)
    lines.append(sep)
    # First row: count per gap (from first non-baseline config)
    n_per_gap = {}
    for r in json.loads((DATA_DIR / CONFIGS[1][1]).read_text(encoding="utf-8"))["results"]:
        g = r["gap_type"]
        n_per_gap[g] = n_per_gap.get(g, 0) + 1
    lines.append(
        "| _(n câu)_ | " + " | ".join(f"_{n_per_gap.get(g, 0)}_" for g in all_gaps) + " |"
    )
    for label, agg in aggregates:
        row_cells = [f"{agg['gap_f1'].get(g, 0):.3f}" for g in all_gaps]
        lines.append(f"| {label} | " + " | ".join(row_cells) + " |")

    return "\n".join(lines)


if __name__ == "__main__":
    md = build_table()
    out = DATA_DIR / "ABLATION_MATRIX.md"
    out.write_text(md, encoding="utf-8")
    print(f"Written: {out}")
    print()
    print(md)
