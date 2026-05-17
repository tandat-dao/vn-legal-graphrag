"""
Validate test set — TASK-15
Kiểm tra file test_set.json (hoặc một file partial) theo schema và DoD của TASK-15.

Usage:
    python src/evaluation/validate_test_set.py data/evaluation/test_set.json
    python src/evaluation/validate_test_set.py data/evaluation/test_set_dat_dai.json --partial

`--partial` bỏ qua các check đếm tổng (≥30 câu, ≥10 đất đai, ...) — dùng khi từng
thành viên validate file riêng. Khi merge cuối cùng thì chạy không có flag.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

VALID_THEMES = {"dat-dai", "ho-tich", "nuoi-con-nuoi"}
VALID_JURISDICTIONS = {"toan-quoc", "tp-hcm", "dong-nai"}
VALID_GAPS = {"gap1", "gap2", "gap3", "negative"}
VALID_DIFFICULTY = {"easy", "medium", "hard"}

REQUIRED_FIELDS = {
    "id", "question", "theme", "jurisdiction", "gap_type",
    "difficulty", "ground_truth_answer", "ground_truth_citations",
}

ID_RE = re.compile(r"^Q\d{3}$")

# Map van_ban id prefix -> tier (dùng cho check Gap 3 đa tier)
TIER_PREFIX = {
    "luat-": 1,
    "nghi-quyet-": 1,  # NQ QH = tier 1; NQ HĐND = tier 4 — phân biệt bằng hậu tố
    "nghi-dinh-": 2,
    "phap-lenh-": 2,
    "thong-tu-": 3,
    "quyet-dinh-": 4,
}


def _infer_tier(van_ban_id: str) -> int | None:
    """Suy ra tier từ id văn bản. NQ HĐND tỉnh (kết thúc bằng -nq-hdnd-*) = tier 4."""
    if van_ban_id.startswith("nghi-quyet-") and "nq-hdnd" in van_ban_id:
        return 4
    for prefix, tier in TIER_PREFIX.items():
        if van_ban_id.startswith(prefix):
            return tier
    return None


def validate_item(item: dict, idx: int) -> list[str]:
    errors = []
    prefix = f"[{idx}] id={item.get('id', '?')}"

    missing = REQUIRED_FIELDS - set(item.keys())
    if missing:
        errors.append(f"{prefix}: thiếu field {sorted(missing)}")
        return errors  # không tiếp tục nếu missing required

    if not ID_RE.match(item["id"]):
        errors.append(f"{prefix}: id sai format (mong đợi Q\\d{{3}})")
    if item["theme"] not in VALID_THEMES:
        errors.append(f"{prefix}: theme '{item['theme']}' không hợp lệ")
    if item["jurisdiction"] not in VALID_JURISDICTIONS:
        errors.append(f"{prefix}: jurisdiction '{item['jurisdiction']}' không hợp lệ")
    if item["gap_type"] not in VALID_GAPS:
        errors.append(f"{prefix}: gap_type '{item['gap_type']}' không hợp lệ")
    if item["difficulty"] not in VALID_DIFFICULTY:
        errors.append(f"{prefix}: difficulty '{item['difficulty']}' không hợp lệ")

    cits = item["ground_truth_citations"]
    if not isinstance(cits, list):
        errors.append(f"{prefix}: ground_truth_citations phải là list")
    else:
        if item["gap_type"] != "negative" and len(cits) == 0:
            errors.append(f"{prefix}: câu non-negative phải có ≥ 1 citation")
        if item["gap_type"] == "negative" and len(cits) != 0:
            errors.append(f"{prefix}: câu negative phải có citations rỗng")
        for j, c in enumerate(cits):
            if not isinstance(c, dict):
                errors.append(f"{prefix}: citation[{j}] không phải dict")
                continue
            if "dieu" not in c or "van_ban" not in c:
                errors.append(f"{prefix}: citation[{j}] thiếu dieu hoặc van_ban")

    return errors


def validate_distribution(items: list[dict]) -> list[str]:
    """Kiểm tra phân bổ theo DoD của TASK-15. Chỉ chạy khi không partial."""
    errors = []
    n = len(items)
    if n < 30:
        errors.append(f"Tổng số câu = {n}, cần ≥ 30")

    theme_count = Counter(it["theme"] for it in items)
    dd = theme_count.get("dat-dai", 0)
    ht_ncn = theme_count.get("ho-tich", 0) + theme_count.get("nuoi-con-nuoi", 0)
    if dd < 10:
        errors.append(f"theme=dat-dai có {dd} câu, cần ≥ 10")
    if ht_ncn < 10:
        errors.append(f"theme=ho-tich + nuoi-con-nuoi có {ht_ncn} câu, cần ≥ 10")

    gap_count = Counter(it["gap_type"] for it in items)
    if gap_count.get("negative", 0) < 5:
        errors.append(f"gap_type=negative có {gap_count.get('negative', 0)} câu, cần ≥ 5")

    # Gap 2: cần ≥ 3 câu, có cả TP.HCM và Đồng Nai
    gap2 = [it for it in items if it["gap_type"] == "gap2"]
    if len(gap2) < 3:
        errors.append(f"gap_type=gap2 có {len(gap2)} câu, cần ≥ 3")
    gap2_juris = {it["jurisdiction"] for it in gap2}
    if not {"tp-hcm", "dong-nai"}.issubset(gap2_juris):
        errors.append(
            f"gap_type=gap2 phải có cả tp-hcm và dong-nai, hiện có {sorted(gap2_juris)}"
        )

    # Gap 3: cần ≥ 3 câu, mỗi câu có ≥ 2 văn bản khác tier
    gap3 = [it for it in items if it["gap_type"] == "gap3"]
    if len(gap3) < 3:
        errors.append(f"gap_type=gap3 có {len(gap3)} câu, cần ≥ 3")
    for it in gap3:
        tiers = set()
        unknown = []
        for c in it["ground_truth_citations"]:
            t = _infer_tier(c["van_ban"])
            if t is None:
                unknown.append(c["van_ban"])
            else:
                tiers.add(t)
        if len(tiers) < 2:
            errors.append(
                f"id={it['id']} (gap3) chỉ có {len(tiers)} tier khác nhau "
                f"(tiers={sorted(tiers)}, unknown_prefix={unknown}), cần ≥ 2"
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate test set JSON cho TASK-15")
    parser.add_argument("path", type=Path, help="Đường dẫn file test_set.json")
    parser.add_argument(
        "--partial",
        action="store_true",
        help="Bỏ qua check phân bổ tổng (dùng cho file từng thành viên)",
    )
    args = parser.parse_args()

    if not args.path.exists():
        print(f"❌ File không tồn tại: {args.path}", file=sys.stderr)
        return 2

    try:
        items = json.loads(args.path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"❌ JSON không hợp lệ: {e}", file=sys.stderr)
        return 2

    if not isinstance(items, list):
        print("❌ Root phải là array", file=sys.stderr)
        return 2

    all_errors: list[str] = []
    ids = []
    for i, item in enumerate(items):
        all_errors.extend(validate_item(item, i))
        if isinstance(item, dict) and "id" in item:
            ids.append(item["id"])

    dup = [i for i, c in Counter(ids).items() if c > 1]
    if dup:
        all_errors.append(f"id bị trùng: {dup}")

    if not args.partial:
        all_errors.extend(validate_distribution(items))

    if all_errors:
        print(f"❌ FAIL — {len(all_errors)} lỗi:")
        for e in all_errors:
            print(f"  - {e}")
        return 1

    mode = "partial" if args.partial else "full DoD"
    print(f"✅ PASS — {len(items)} câu hỏi, kiểm tra {mode}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
