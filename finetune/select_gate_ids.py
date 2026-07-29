"""TASK-FT-03 — chọn 15 câu phân tầng cho gate, ghi ra finetune/data/gate_ids.json.

Kế hoạch §TASK-FT-03 quy trình (1): "3 mỗi nhóm thách thức + 3 bẫy phủ định".

Hai ràng buộc:

  1. **Bẫy phủ định chỉ lấy từ 4 câu ĐÃ QUA MÔ HÌNH SINH** (V005, V105, V114, V117).
     10 câu còn lại (V106–V113, V115, V116) là hằng số sao chép — `pipeline.py:223`
     return trước `generate_answer` nên Gemini chưa từng được gọi; đưa vào gate chỉ
     tốn chỗ mà không đo được gì về mô hình cục bộ.

  2. **Chọn TẤT ĐỊNH**, không random: cùng đầu vào → cùng 15 id. Quy tắc tham lam
     ưu tiên phủ `theme` trước, rồi `difficulty`, phá hoà bằng id tăng dần.

Đây KHÔNG phải selection-on-test (§9.5): không chọn giữa các mô hình, chỉ chạy sớm
15 trong số 137 câu mà hàng "cục bộ chưa tinh chỉnh" đằng nào cũng phải chạy đủ.

Chạy:  python -m finetune.select_gate_ids
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "data/evaluation/results_graphrag_20260710-085236.json"
OUT_PATH = REPO / "finetune/data/gate_ids.json"

GROUPS = ("gap1", "gap2", "gap3", "gap4", "negative")
PER_GROUP = 3


def pick(candidates: list[dict], k: int) -> list[dict]:
    """Tham lam: phủ theme trước, rồi difficulty, phá hoà bằng id tăng dần."""
    remaining = sorted(candidates, key=lambda x: x["id"])
    chosen: list[dict] = []
    themes: set = set()
    diffs: set = set()
    while remaining and len(chosen) < k:
        # ưu tiên 1: thêm theme mới; ưu tiên 2: thêm difficulty mới; cuối: id nhỏ nhất
        best = min(
            remaining,
            key=lambda x: (x["theme"] in themes, x["difficulty"] in diffs, x["id"]),
        )
        chosen.append(best)
        themes.add(best["theme"])
        diffs.add(best["difficulty"])
        remaining.remove(best)
    return chosen


def main() -> int:
    items = json.loads(SOURCE.read_text(encoding="utf-8"))["results"]

    selected: list[dict] = []
    per_group_note: dict[str, str] = {}

    for g in GROUPS:
        pool = [x for x in items if x["gap_type"] == g]
        # Ràng buộc (1): chỉ câu thực sự đi qua mô hình sinh.
        sent = [x for x in pool if x["top_k_count"] > 0]
        skipped = len(pool) - len(sent)
        per_group_note[g] = (
            f"pool {len(pool)} câu, {len(sent)} câu qua mô hình sinh"
            + (f", bỏ {skipped} câu hằng số (top_k_count=0)" if skipped else "")
        )
        got = pick(sent, PER_GROUP)
        assert len(got) == PER_GROUP, f"{g}: chỉ chọn được {len(got)}/{PER_GROUP}"
        for x in got:
            selected.append({
                "id": x["id"],
                "gap_type": x["gap_type"],
                "theme": x["theme"],
                "difficulty": x["difficulty"],
                "jurisdiction": x["jurisdiction"],
                "top_k_count": x["top_k_count"],
                "gt_nonempty": bool(x["ground_truth_citations"]),
                "n_gt_citations": len(x["ground_truth_citations"]),
                "context_chars": len(x["context"]),
                "question": x["question"],
            })

    gt_nonempty = [s for s in selected if s["gt_nonempty"]]

    payload = {
        "_mo_ta": "TASK-FT-03 — 15 câu phân tầng cho gate. Sinh bởi finetune/select_gate_ids.py.",
        "_nguon": str(SOURCE.relative_to(REPO)).replace("\\", "/"),
        "_quy_tac_chon": (
            "3 câu mỗi nhóm gap1/gap2/gap3/gap4 + 3 bẫy phủ định. Tất định: tham lam "
            "phủ theme trước, rồi difficulty, phá hoà bằng id tăng dần. Bẫy phủ định "
            "CHỈ lấy từ 4 câu đã qua mô hình sinh (V005/V105/V114/V117); 10 câu "
            "V106-V113/V115/V116 là hằng số sao chép, không đo được gì."
        ),
        "_khong_phai_selection_on_test": (
            "Không chọn giữa các mô hình (§9.5 chốt Qwen3-4B-Instruct-2507) — đây chỉ "
            "là chạy sớm 15 trong 137 câu mà hàng 'cục bộ chưa tinh chỉnh' đằng nào "
            "cũng phải chạy đủ."
        ),
        "_mau_so_format_ok": (
            f"{len(gt_nonempty)}/{len(selected)} câu có ground_truth_citations khác "
            f"rỗng → format_ok_rate tính trên {len(gt_nonempty)} câu, KHÔNG phải "
            f"{len(selected)}. 3 câu bẫy phủ định có GT rỗng nên bị loại khỏi mẫu số."
        ),
        "ghi_chu_tung_nhom": per_group_note,
        "ids": [s["id"] for s in selected],
        "ids_csv": ",".join(s["id"] for s in selected),
        "chi_tiet": selected,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Đã chọn {len(selected)} câu:")
    for s in selected:
        print(f"  {s['id']}  {s['gap_type']:8s} {str(s['theme']):14s} "
              f"{s['difficulty']:6s} ctx={s['context_chars']:6d}ch "
              f"GT={'có' if s['gt_nonempty'] else 'RỖNG'}")
    print(f"\nmẫu số format_ok = {len(gt_nonempty)} (không phải {len(selected)})")
    print(f"--ids {payload['ids_csv']}")
    print(f"Đã ghi {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
