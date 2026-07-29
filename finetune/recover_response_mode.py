"""TASK-FT-01 phần B — Khôi phục `response_mode` từ field `answer` đã lưu.

Bối cảnh: mẻ chạy 10/07 dùng `--response-mode auto` → planner tự chọn general/irac
từng câu, nhưng `run_evaluation` KHÔNG chép field đó vào results JSON
(src/evaluation/run_evaluation.py:84 trả về, dict result dòng 258-279 bỏ qua).
Không có planner cache trên máy → nguồn khôi phục duy nhất là chính `answer`.

Hai đường khôi phục, KHÁC NHAU theo hệ thống:

  baseline  → TẤT ĐỊNH, không cần regex.
              src/evaluation/run_evaluation.py:93 ép
              `resolved_mode = "general" if response_mode == "auto" else response_mode`
              → mọi câu baseline chạy mode "general". Không có ngoại lệ.

  graphrag  → suy từ dấu hiệu định dạng.
              src/pipeline.py:179 `response_mode or query_plan["response_mode"] or "general"`
              → mode do planner LLM chọn, không lưu lại.
              Khối prompt irac (src/retrieval/context_assembler.py:264-280) ép đúng
              4 heading H3: Vấn đề / Căn cứ pháp lý / Phân tích / Kết luận.

Chỉ ĐỌC data/evaluation/. Ghi finetune/data/mode_map.json.

Chạy:  python -m finetune.recover_response_mode
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Console Windows mặc định cp1252 → tiếng Việt trong log sẽ crash. Ép UTF-8.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# 4 heading của khối prompt irac — context_assembler.py:268/271/274/277.
# Cho phép H2-H4 và sai lệch khoảng trắng/hoa-thường để KHÔNG bỏ sót biến thể.
_IRAC_HEADINGS = {
    "van_de": re.compile(r"^#{2,4}\s*Vấn\s*đề\s*$", re.MULTILINE | re.IGNORECASE),
    "can_cu": re.compile(r"^#{2,4}\s*Căn\s*cứ\s*pháp\s*lý\s*$", re.MULTILINE | re.IGNORECASE),
    "phan_tich": re.compile(r"^#{2,4}\s*Phân\s*tích\s*$", re.MULTILINE | re.IGNORECASE),
    "ket_luan": re.compile(r"^#{2,4}\s*Kết\s*luận\s*$", re.MULTILINE | re.IGNORECASE),
}

# Dấu hiệu phụ dùng để KIỂM TRA CHÉO, không dùng để phân loại:
# nếu bắt được thứ gì ở đây trong nhóm "general" thì phân loại theo heading là chưa đủ.
_SECONDARY_SIGNALS = {
    "bat_ky_heading": re.compile(r"^#{2,6}\s+\S", re.MULTILINE),
    "bold_van_de": re.compile(r"\*\*\s*Vấn đề", re.IGNORECASE),
    "bold_ket_luan": re.compile(r"\*\*\s*Kết luận", re.IGNORECASE),
    "ket_luan_plain": re.compile(r"^\s*Kết luận\s*:", re.MULTILINE | re.IGNORECASE),
    # Lối thoát của prompt irac khi câu hỏi thiếu tình tiết (context_assembler.py:280)
    "thieu_tinh_tiet": re.compile(
        r"(cần (thêm|cung cấp) thông tin|cung cấp thêm thông tin|để tư vấn cụ thể)",
        re.IGNORECASE,
    ),
}

REPO = Path(__file__).resolve().parents[1]
DEFAULT_INPUTS = {
    "graphrag": REPO / "data/evaluation/results_graphrag_20260710-085236.json",
    "baseline": REPO / "data/evaluation/results_baseline_20260710-085236.json",
}
OUT_PATH = REPO / "finetune/data/mode_map.json"


def count_irac_headings(answer: str) -> int:
    """Số heading irac (0-4) tìm thấy trong câu trả lời."""
    return sum(1 for pat in _IRAC_HEADINGS.values() if pat.search(answer))


def infer_mode(answer: str) -> str:
    """Suy response_mode từ answer. Đủ 4 heading → irac, còn lại → general.

    Ngưỡng 4/4 (không phải >=1) là an toàn: phân bố thực tế hoàn toàn lưỡng cực,
    không có ca 1-3 heading nào để phải phân xử.
    """
    return "irac" if count_irac_headings(answer) == 4 else "general"


def scan(results: list[dict], system: str) -> dict:
    """Phân loại + thu thập số liệu kiểm chứng cho một hệ thống."""
    per_id: dict[str, str] = {}
    hist: dict[int, int] = {}
    irac_ids: list[str] = []
    partial: list[dict] = []
    secondary_in_general: dict[str, list[str]] = {k: [] for k in _SECONDARY_SIGNALS}

    for item in results:
        qid, answer = item["id"], item["answer"]
        n = count_irac_headings(answer)
        hist[n] = hist.get(n, 0) + 1

        if system == "baseline":
            # Tất định theo code, KHÔNG suy từ answer.
            mode = "general"
        else:
            mode = infer_mode(answer)

        per_id[qid] = mode
        if n == 4:
            irac_ids.append(qid)
        elif n > 0:
            partial.append({
                "id": qid,
                "n_heading": n,
                "co": [k for k, p in _IRAC_HEADINGS.items() if p.search(answer)],
            })

        if mode == "general":
            for name, pat in _SECONDARY_SIGNALS.items():
                if pat.search(answer):
                    secondary_in_general[name].append(qid)

    return {
        "per_id": per_id,
        "n": len(results),
        "n_irac": sum(1 for m in per_id.values() if m == "irac"),
        "n_general": sum(1 for m in per_id.values() if m == "general"),
        "histogram_so_heading": dict(sorted(hist.items())),
        "irac_ids": irac_ids,
        "ca_partial": partial,
        "tin_hieu_phu_trong_nhom_general": {k: v for k, v in secondary_in_general.items() if v},
    }


def main() -> int:
    out = {
        "_mo_ta": "TASK-FT-01B — response_mode khôi phục, KHÔNG phải giá trị gốc của planner.",
        "_nguon": {k: str(v.relative_to(REPO)).replace("\\", "/") for k, v in DEFAULT_INPUTS.items()},
        "_phuong_phap": {
            "baseline": "TẤT ĐỊNH: run_evaluation.py:93 ép 'general' cho mọi câu khi --response-mode auto.",
            "graphrag": "SUY LUẬN: đủ 4/4 heading irac (context_assembler.py:264-280) → irac, còn lại → general.",
        },
        "he_thong": {},
    }

    for system, path in DEFAULT_INPUTS.items():
        data = json.loads(path.read_text(encoding="utf-8"))
        info = scan(data["results"], system)
        mode_map = info.pop("per_id")
        out["he_thong"][system] = {"thong_ke": info, "mode_map": mode_map}
        print(f"[{system}] n={info['n']}  irac={info['n_irac']}  general={info['n_general']}")
        print(f"          histogram số heading: {info['histogram_so_heading']}")
        print(f"          ca partial (1-3 heading): {len(info['ca_partial'])}")
        print(f"          tín hiệu phụ lọt vào nhóm general: "
              f"{info['tin_hieu_phu_trong_nhom_general'] or 'không có'}")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nĐã ghi {OUT_PATH.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
