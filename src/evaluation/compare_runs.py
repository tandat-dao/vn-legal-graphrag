"""
Compare 2 evaluation runs — old (canonical) vs new (after fix).

Usage:
    python -m src.evaluation.compare_runs OLD_RESULTS_JSON NEW_RESULTS_JSON

In ra:
  - Aggregate diff (F1 Khoản/Điều, NormR, latency, negative)
  - Per-Q diff sắp xếp theo |ΔF1| desc
  - Phân loại: improvements / regressions / unchanged
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return statistics.mean(xs) if xs else 0.0


def compare(old_path: Path, new_path: Path) -> str:
    old = json.loads(old_path.read_text(encoding="utf-8"))
    new = json.loads(new_path.read_text(encoding="utf-8"))
    old_by_id = {r["id"]: r for r in old["results"]}
    new_by_id = {r["id"]: r for r in new["results"]}

    common_ids = sorted(set(old_by_id) & set(new_by_id))

    lines = []
    lines.append(f"# Comparison: {old_path.name} → {new_path.name}")
    lines.append("")
    lines.append(f"**System:** {new.get('system')}  ")
    lines.append(f"**N câu chung:** {len(common_ids)}  ")
    lines.append(f"**Test set:** `{new.get('test_set')}`")
    lines.append("")

    # Aggregate
    old_f1 = _mean(old_by_id[i]["citation_score"]["f1"] for i in common_ids)
    new_f1 = _mean(new_by_id[i]["citation_score"]["f1"] for i in common_ids)
    old_f1d = _mean(old_by_id[i].get("citation_score_dieu", {}).get("f1") for i in common_ids)
    new_f1d = _mean(new_by_id[i].get("citation_score_dieu", {}).get("f1") for i in common_ids)
    old_nr = _mean(old_by_id[i]["norm_recall"] for i in common_ids)
    new_nr = _mean(new_by_id[i]["norm_recall"] for i in common_ids)
    old_lat = _mean(old_by_id[i]["elapsed_seconds"] for i in common_ids)
    new_lat = _mean(new_by_id[i]["elapsed_seconds"] for i in common_ids)

    lines.append("## Aggregate")
    lines.append("")
    lines.append("| Metric | Old | New | Δ |")
    lines.append("|---|---:|---:|---:|")
    lines.append(f"| F1 Khoản | {old_f1:.3f} | {new_f1:.3f} | {new_f1-old_f1:+.3f} |")
    lines.append(f"| F1 Điều | {old_f1d:.3f} | {new_f1d:.3f} | {new_f1d-old_f1d:+.3f} |")
    lines.append(f"| Norm Recall | {old_nr:.3f} | {new_nr:.3f} | {new_nr-old_nr:+.3f} |")
    lines.append(f"| Latency mean (s) | {old_lat:.2f} | {new_lat:.2f} | {new_lat-old_lat:+.2f} |")
    lines.append("")

    # Per-Q with diff
    rows = []
    for qid in common_ids:
        o, n = old_by_id[qid], new_by_id[qid]
        of1, nf1 = o["citation_score"]["f1"], n["citation_score"]["f1"]
        onr, nnr = o["norm_recall"], n["norm_recall"]
        rows.append({
            "id": qid, "gap": o.get("gap_type"),
            "old_f1": of1, "new_f1": nf1, "df1": nf1 - of1,
            "old_nr": onr, "new_nr": nnr, "dnr": nnr - onr,
            "old_pred": len(o["pred_citations"]), "new_pred": len(n["pred_citations"]),
        })

    improvements = [r for r in rows if r["df1"] > 0.05]
    regressions = [r for r in rows if r["df1"] < -0.05]
    unchanged = [r for r in rows if abs(r["df1"]) <= 0.05]

    lines.append(f"## Improvements ({len(improvements)} câu, ΔF1 > 0.05)")
    lines.append("")
    if improvements:
        lines.append("| ID | gap | old F1 | new F1 | ΔF1 | old NR | new NR | ΔNR | preds |")
        lines.append("|---|---|---:|---:|---:|---:|---:|---:|---|")
        for r in sorted(improvements, key=lambda x: -x["df1"]):
            lines.append(f"| {r['id']} | {r['gap']} | {r['old_f1']:.2f} | {r['new_f1']:.2f} | "
                         f"**{r['df1']:+.2f}** | {r['old_nr']:.2f} | {r['new_nr']:.2f} | "
                         f"{r['dnr']:+.2f} | {r['old_pred']}→{r['new_pred']} |")
    else:
        lines.append("_(không có)_")
    lines.append("")

    lines.append(f"## Regressions ({len(regressions)} câu, ΔF1 < -0.05)")
    lines.append("")
    if regressions:
        lines.append("| ID | gap | old F1 | new F1 | ΔF1 | old NR | new NR | ΔNR | preds |")
        lines.append("|---|---|---:|---:|---:|---:|---:|---:|---|")
        for r in sorted(regressions, key=lambda x: x["df1"]):
            lines.append(f"| {r['id']} | {r['gap']} | {r['old_f1']:.2f} | {r['new_f1']:.2f} | "
                         f"**{r['df1']:+.2f}** | {r['old_nr']:.2f} | {r['new_nr']:.2f} | "
                         f"{r['dnr']:+.2f} | {r['old_pred']}→{r['new_pred']} |")
    else:
        lines.append("_(không có)_")
    lines.append("")

    lines.append(f"## Unchanged ({len(unchanged)} câu, |ΔF1| ≤ 0.05)")
    lines.append("")
    lines.append(f"_(IDs: {', '.join(r['id'] for r in unchanged)})_")
    return "\n".join(lines)


def main():
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    print(compare(Path(sys.argv[1]), Path(sys.argv[2])))


if __name__ == "__main__":
    main()
