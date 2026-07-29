"""TASK-FT-01 phần A — Đo ngân sách token THẬT cho việc phát lại.

Đo TỔNG thật, không chỉ context:

    tổng = system_prompt(mode) + khung user_prompt + question + context

Cả bốn thành phần đều sinh ra từ `src.retrieval.context_assembler.build_messages`
— tức chuỗi y hệt cái mà mô hình sinh đã nhận ở mẻ 10/07. Không quy đổi ước lượng
ký-tự-sang-token; tokenize bằng tokenizer thật của từng mô hình ứng viên.

Hai cách tính tổng, báo cáo cả hai:
  - `raw`  = len(tok(system)) + len(tok(user)) — ngân sách NỘI DUNG thuần.
  - `chat` = len(tok.apply_chat_template([system, user], add_generation_prompt=True))
             — thêm token đánh dấu vai trò; đây là con số FT-02/FT-05 phải dùng.

Cũng đo token của `answer` Gemini đã sinh → cần để chốt cửa sổ, vì cửa sổ phải
chứa CẢ prompt LẪN phần sinh ra.

Chỉ ĐỌC. Không GPU, không gọi API mô hình (chỉ tải file tokenizer từ HuggingFace).

Chạy:  python -m finetune.measure_token_budget
"""
from __future__ import annotations

import json
import statistics
import sys
import warnings
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
warnings.filterwarnings("ignore")

from src.retrieval.context_assembler import build_messages  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
INPUTS = {
    "graphrag": REPO / "data/evaluation/results_graphrag_20260710-085236.json",
    "baseline": REPO / "data/evaluation/results_baseline_20260710-085236.json",
}
MODE_MAP_PATH = REPO / "finetune/data/mode_map.json"
OUT_JSON = REPO / "finetune/reports/token_budget.json"

# Ứng viên: tokenizer ungated, tải được không cần đăng nhập.
# Việc CHỐT mô hình thuộc TASK-FT-03; ở đây chỉ cần bracket khoảng token.
CANDIDATES = [
    # (nhãn, repo HuggingFace, ghi chú)
    ("Qwen2.5-7B-Instruct", "Qwen/Qwen2.5-7B-Instruct", "BPE 151k, cửa sổ gốc 32k"),
    ("Llama-3.1-8B-Instruct", "NousResearch/Meta-Llama-3.1-8B-Instruct", "BPE 128k, cửa sổ 128k"),
    ("Phi-3.5-mini-instruct", "microsoft/Phi-3.5-mini-instruct", "SentencePiece 32k, cửa sổ 128k"),
    ("VinaLlama-7B-chat", "vilm/vinallama-7b-chat", "SP 46k mở rộng tiếng Việt, Llama-2 base"),
]


def percentiles(xs: list[int]) -> dict:
    """p50/p90/p95/max + mean. Dùng nội suy tuyến tính (statistics.quantiles)."""
    if not xs:
        return {}
    s = sorted(xs)
    if len(s) == 1:
        return {"n": 1, "mean": s[0], "p50": s[0], "p90": s[0], "p95": s[0], "max": s[0]}

    def q(p: float) -> int:
        # vị trí p (0..1) theo nội suy tuyến tính trên mẫu đã sắp xếp
        k = p * (len(s) - 1)
        lo, hi = int(k), min(int(k) + 1, len(s) - 1)
        return int(round(s[lo] + (s[hi] - s[lo]) * (k - lo)))

    return {
        "n": len(s),
        "mean": int(round(statistics.mean(s))),
        "p50": q(0.50),
        "p90": q(0.90),
        "p95": q(0.95),
        "max": s[-1],
    }


def load_tokenizers() -> list[tuple[str, str, object, bool]]:
    """Trả (nhãn, ghi_chú, tokenizer, có_chat_template)."""
    from transformers import AutoTokenizer

    out = []
    for label, repo, note in CANDIDATES:
        try:
            tok = AutoTokenizer.from_pretrained(repo)
        except Exception as e:  # gated / mạng / thiếu file
            print(f"  BỎ QUA {label}: {type(e).__name__} {str(e)[:80]}")
            continue
        has_tpl = getattr(tok, "chat_template", None) is not None
        out.append((label, note, tok, has_tpl))
        print(f"  nạp {label:24s} vocab={tok.vocab_size:<7} chat_template={'có' if has_tpl else 'KHÔNG'}")
    return out


def n_tokens(tok, text: str) -> int:
    return len(tok(text, add_special_tokens=False)["input_ids"])


def n_tokens_chat(tok, system: str, user: str, has_tpl: bool) -> int | None:
    """Đếm token sau khi áp chat template. None nếu tokenizer không có template."""
    if not has_tpl:
        return None
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    try:
        ids = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True)
    except Exception:
        # Vài template không nhận role "system" → gộp system vào user.
        try:
            ids = tok.apply_chat_template(
                [{"role": "user", "content": system + "\n\n" + user}],
                add_generation_prompt=True, tokenize=True,
            )
        except Exception:
            return None
    return len(ids)


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="TASK-FT-01A — đo ngân sách token")
    ap.add_argument("--models", default="", help="Lọc ứng viên theo nhãn, cách bởi dấu phẩy (rỗng = tất cả)")
    ap.add_argument("--dump-raw", action="store_true", help="Ghi giá trị token thô từng câu vào JSON")
    ap.add_argument("--out", type=Path, default=OUT_JSON)
    ap.add_argument("--thresholds", default="8192,12288,16384,32768",
                    help="Các cửa sổ cần đếm số câu vượt quá")
    args = ap.parse_args()

    keep = {s.strip() for s in args.models.split(",") if s.strip()}
    thresholds = [int(x) for x in args.thresholds.split(",")]

    mode_data = json.loads(MODE_MAP_PATH.read_text(encoding="utf-8"))

    print("Nạp tokenizer (chỉ tokenizer, không nạp weights):")
    toks = [t for t in load_tokenizers() if not keep or t[0] in keep]
    if not toks:
        print("Không nạp được tokenizer nào — dừng.")
        return 1

    report: dict = {
        "_mo_ta": "TASK-FT-01A — ngân sách token thật (system + khung user + question + context).",
        "_nguon": {k: str(v.relative_to(REPO)).replace("\\", "/") for k, v in INPUTS.items()},
        "_ung_vien": {lbl: note for lbl, note, _, _ in toks},
        "do": {},
    }

    for system_name, path in INPUTS.items():
        items = json.loads(path.read_text(encoding="utf-8"))["results"]
        mode_map = mode_data["he_thong"][system_name]["mode_map"]

        # Nhóm câu THỰC SỰ đi qua mô hình sinh. 10 câu top_k_count==0 của graphrag
        # được sao chép hằng số (kế hoạch §9.1) → không tốn token nào.
        sent = [it for it in items if it["top_k_count"] > 0]

        report["do"][system_name] = {
            "n_tong": len(items),
            "n_thuc_su_gui_mo_hinh": len(sent),
            "theo_mo_hinh": {},
        }

        for label, _note, tok, has_tpl in toks:
            raws, chats, answers, systems_only, contexts_only = [], [], [], [], []
            per_item: dict[str, dict] = {}
            # system_prompt chỉ có 2 biến thể (general / irac) → tokenize 1 lần mỗi mode.
            # Không cache thì 11k ký tự bị tokenize lại 137 lần cho mỗi tokenizer.
            sys_cache: dict[str, tuple[str, int]] = {}
            tpl_overhead: int | None = None

            for it in sent:
                mode = mode_map[it["id"]]
                if mode not in sys_cache:
                    s_p, _ = build_messages("", "", mode)
                    sys_cache[mode] = (s_p, n_tokens(tok, s_p))
                sys_p, n_sys = sys_cache[mode]

                _, usr_p = build_messages(it["question"], it["context"], mode)
                n_usr = n_tokens(tok, usr_p)
                n_ctx = n_tokens(tok, it["context"])
                n_ans = n_tokens(tok, it["answer"])
                raw = n_sys + n_usr

                # Overhead của chat template đo MỘT LẦN rồi kiểm chứng lại trên câu thứ hai:
                # template chỉ bọc nội dung bằng token đánh dấu vai trò, không phụ thuộc độ dài.
                if has_tpl and tpl_overhead is None:
                    c = n_tokens_chat(tok, sys_p, usr_p, has_tpl)
                    if c is not None:
                        tpl_overhead = c - raw
                chat = raw + tpl_overhead if tpl_overhead is not None else None

                raws.append(raw)
                systems_only.append(n_sys)
                contexts_only.append(n_ctx)
                answers.append(n_ans)
                if chat is not None:
                    chats.append(chat)
                if args.dump_raw:
                    per_item[it["id"]] = {
                        "mode": mode, "system": n_sys, "user": n_usr, "context": n_ctx,
                        "answer": n_ans, "tong_raw": raw, "tong_chat": chat,
                    }

            # Kiểm chứng mô hình cộng: overhead phải bất biến theo độ dài nội dung.
            if has_tpl and tpl_overhead is not None and len(sent) > 1:
                s_p, n_s = sys_cache[mode_map[sent[-1]["id"]]]
                _, u_p = build_messages(sent[-1]["question"], sent[-1]["context"],
                                        mode_map[sent[-1]["id"]])
                real = n_tokens_chat(tok, s_p, u_p, has_tpl)
                assert real == n_s + n_tokens(tok, u_p) + tpl_overhead, (
                    f"{label}: overhead chat template KHÔNG bất biến — không dùng được mô hình cộng"
                )

            entry = {
                "tong_raw": percentiles(raws),
                "tong_chat": percentiles(chats) if chats else None,
                "chi_system": percentiles(systems_only),
                "chi_context": percentiles(contexts_only),
                "answer_gemini": percentiles(answers),
            }
            base = entry["tong_chat"] or entry["tong_raw"]
            entry["overhead_chat_template"] = tpl_overhead
            entry["cua_so_toi_thieu_max"] = base["max"] + entry["answer_gemini"]["max"]
            entry["cua_so_toi_thieu_p95"] = base["p95"] + entry["answer_gemini"]["p95"]

            # Số câu KHÔNG vừa cửa sổ W, tính cả phần sinh ra (prompt + answer thực tế).
            need = [(chats[i] if chats else raws[i]) + answers[i] for i in range(len(raws))]
            entry["so_cau_vuot_cua_so"] = {
                str(w): sum(1 for x in need if x > w) for w in thresholds
            }
            if args.dump_raw:
                entry["per_item"] = per_item
            report["do"][system_name]["theo_mo_hinh"][label] = entry

            print(f"[{system_name:8s}] {label:24s} "
                  f"tong_chat p50={base['p50']:6d} p95={base['p95']:6d} max={base['max']:6d} "
                  f"| answer max={entry['answer_gemini']['max']:5d} "
                  f"| cửa sổ tối thiểu={entry['cua_so_toi_thieu_max']:6d} "
                  f"| vượt: {entry['so_cau_vuot_cua_so']}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nĐã ghi {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
