"""
Error analysis (E3) — phân loại lỗi hệ thống thành taxonomy hành động được.

"F1=0.55" không cho biết SỬA GÌ. E3 mổ phần sai thành các loại có nguyên nhân
khác nhau (docs/EVALUATION_ARCHITECTURE.md §E3):

  retrieval-fail   : GT citation KHÔNG có trong context đã retrieve → hệ không thể
                     trích (lỗi ở retrieval — cần cải thiện Stage 1/2).
  generation-fail  : GT citation CÓ trong context nhưng hệ KHÔNG trích / trích sai
                     (lỗi ở generation — cần cải thiện prompt/model).
  over-cite        : hệ trích citation KHÔNG có trong GT (mất precision). Cần người
                     soi: over-cite THẬT (thừa) hay GT-ARTIFACT (hệ đúng, GT thiếu —
                     chính finding D-19). Script FLAG để [A] review, không tự quyết.
  negative-fail    : câu negative (đáng từ chối) mà hệ vẫn trích dẫn → trả lời bừa.

Đọc result file (sau eval). Tách van_ban có trong context bằng cách dò slug trong
label context ("... (van_ban_slug)"). Tái dùng metrics.cit_matches.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from src.evaluation.metrics import cit_matches


def _matched_gt_flags(pred: list[dict], gt: list[dict], level: str) -> list[bool]:
    """[bool] theo GT: True nếu GT thứ i được ÍT NHẤT 1 pred khớp (greedy 1-1)."""
    used = [False] * len(gt)
    for p in pred:
        for i, g in enumerate(gt):
            if not used[i] and cit_matches(p, g, level):
                used[i] = True
                break
    return used


def _pred_unmatched(pred: list[dict], gt: list[dict], level: str) -> list[dict]:
    """Các pred KHÔNG khớp GT nào (over-cite)."""
    gt_used = [False] * len(gt)
    over = []
    for p in pred:
        hit = False
        for i, g in enumerate(gt):
            if not gt_used[i] and cit_matches(p, g, level):
                gt_used[i] = True
                hit = True
                break
        if not hit:
            over.append(p)
    return over


def classify_question(item: dict, level: str = "khoan") -> dict:
    """Phân loại lỗi 1 câu. Trả về dict các nhóm citation lỗi."""
    pred = item.get("pred_citations", []) or []
    gt = item.get("ground_truth_citations", []) or []
    context = item.get("context", "") or ""

    if item.get("gap_type") == "negative":
        # Đúng = không trích (từ chối). Sai = có trích.
        return {
            "kind": "negative",
            "negative_fail": pred,           # trích khi đáng từ chối
            "ok": len(pred) == 0,
        }

    used = _matched_gt_flags(pred, gt, level)
    missed = [gt[i] for i in range(len(gt)) if not used[i]]
    # Tách missed: văn bản có trong context chưa?
    retrieval_fail = [c for c in missed if str(c.get("van_ban")) not in context]
    generation_fail = [c for c in missed if str(c.get("van_ban")) in context]
    over_cite = _pred_unmatched(pred, gt, level)
    return {
        "kind": "normal",
        "retrieval_fail": retrieval_fail,
        "generation_fail": generation_fail,
        "over_cite": over_cite,
        "n_gt": len(gt), "n_matched": sum(used),
    }


def analyze(results: list[dict], level: str = "khoan") -> dict:
    """Tổng hợp taxonomy trên list result. Trả về counts + per-gap + flag over-cite."""
    tax = Counter()
    per_gap = defaultdict(Counter)
    over_flags = []       # để [A] review over-cite vs GT-artifact
    retrieval_examples = []

    for it in results:
        c = classify_question(it, level)
        g = it.get("gap_type", "?")
        if c["kind"] == "negative":
            if not c["ok"]:
                tax["negative_fail"] += 1
                per_gap[g]["negative_fail"] += 1
            continue
        nrf, ngf, nov = len(c["retrieval_fail"]), len(c["generation_fail"]), len(c["over_cite"])
        tax["retrieval_fail"] += nrf
        tax["generation_fail"] += ngf
        tax["over_cite"] += nov
        per_gap[g]["retrieval_fail"] += nrf
        per_gap[g]["generation_fail"] += ngf
        per_gap[g]["over_cite"] += nov
        if nov:
            over_flags.append({"id": it.get("id"), "question": it.get("question", "")[:80],
                               "over_cite": c["over_cite"]})
        if nrf:
            retrieval_examples.append({"id": it.get("id"),
                                       "missed": c["retrieval_fail"]})

    return {
        "taxonomy": dict(tax),
        "per_gap": {g: dict(v) for g, v in sorted(per_gap.items())},
        "n_over_cite_questions": len(over_flags),
        "over_cite_flags": over_flags,          # → người review: over-cite hay GT-artifact?
        "retrieval_fail_examples": retrieval_examples,
    }


def _load(path: Path) -> list[dict]:
    d = json.loads(path.read_text(encoding="utf-8"))
    return d["results"] if isinstance(d, dict) and "results" in d else d


def main() -> int:
    ap = argparse.ArgumentParser(description="E3 error analysis — taxonomy lỗi hệ thống")
    ap.add_argument("results", help="results_<system>_*.json")
    ap.add_argument("--level", default="khoan", choices=["khoan", "dieu"])
    ap.add_argument("--flags", action="store_true", help="In chi tiết over-cite cần review")
    args = ap.parse_args()

    rep = analyze(_load(Path(args.results)), args.level)
    print(f"── Error taxonomy (level={args.level}) ──")
    for k, v in sorted(rep["taxonomy"].items(), key=lambda x: -x[1]):
        print(f"  {k:<18} {v}")
    print("\n── Per-gap ──")
    for g, v in rep["per_gap"].items():
        print(f"  {g:<10} {dict(v)}")
    print(f"\n{rep['n_over_cite_questions']} câu có over-cite → cần [A] soi "
          "(over-cite thật vs GT-artifact, D-19).")
    if args.flags:
        for f in rep["over_cite_flags"]:
            print(f"  [{f['id']}] {f['question']}")
            for c in f["over_cite"]:
                print(f"       thừa: {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
