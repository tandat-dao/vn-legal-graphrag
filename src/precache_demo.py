"""Lớp 1 — Pre-cache câu hỏi demo (chống đạn cho buổi bảo vệ).

Vấn đề: demo phụ thuộc Claude API live. Lớp này CHẠY TRƯỚC các câu demo (dùng
Claude thật) → nạp đầy LLM cache (`.llm_cache`, hash theo prompt). Hôm bảo vệ, các
câu ĐÃ chuẩn bị replay từ cache: $0, tức thì, KHÔNG gọi API → dù Claude sập vẫn chạy.

Reproducibility study đã xác nhận: cache hit = bit-exact, $0. Đây là phòng thủ
chính cho câu hỏi có kịch bản (Gemini fallback chỉ lo câu hỏi ngẫu hứng).

QUAN TRỌNG — tính nhất quán cache:
  Cache key = hash(prompt), mà prompt phụ thuộc CONTEXT retrieve được → phụ thuộc
  trạng thái graph. Vì vậy phải pre-cache SAU khi re-ingest (graph cuối cùng) và
  với ĐÚNG flag (--jurisdiction/--mode) sẽ dùng lúc demo. Đổi graph/flag → cache miss.

Cách dùng:
    # 1 file câu hỏi, mỗi dòng 1 câu (bỏ qua dòng trống / bắt đầu bằng #)
    python -m src.precache_demo data/evaluation/demo_questions.txt
    python -m src.precache_demo data/evaluation/demo_questions.txt --jurisdiction tp-hcm
    # hoặc truyền thẳng câu hỏi
    python -m src.precache_demo --question "Hạn mức đất ở TP.HCM?"

Sau khi chạy, kiểm tra bằng cách chạy lại đúng câu đó qua demo → phải thấy
cache_hit=True (latency ~0.x s).
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_DEFAULT_CACHE_DIR = "data/evaluation/.llm_cache/"

# CÙNG thứ tự ưu tiên với `ui.adapters.DEMO_QUESTIONS_FILES`. Bắt buộc phải
# giống, nếu không sẽ hâm cache cho danh sách này mà demo lại chạy danh sách
# kia — cache trượt im lặng đúng lúc bảo vệ.
_TEP_CAU_HOI = (
    Path("ui/docs/DEMO_QUESTIONS.md"),      # bản có phân nhóm + ghi chú (UI đọc)
    Path("data/evaluation/demo_questions.txt"),
)


def _tep_mac_dinh() -> Path | None:
    for p in _TEP_CAU_HOI:
        if p.exists():
            return p
    return None


def _read_questions(path: Path) -> list[str]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-cache câu hỏi demo (Lớp 1)")
    parser.add_argument("questions_file", nargs="?",
                        help="Tệp câu hỏi, mỗi dòng 1 câu (bỏ dòng # và trống). "
                             "Bỏ trống thì dùng ĐÚNG tệp giao diện đang đọc: "
                             "ui/docs/DEMO_QUESTIONS.md, lùi về "
                             "data/evaluation/demo_questions.txt.")
    parser.add_argument("--question", action="append", default=[],
                        help="Câu hỏi truyền thẳng (lặp được). Thay cho file.")
    parser.add_argument("--jurisdiction", choices=["toan-quoc", "tp-hcm", "dong-nai"],
                        help="PHẢI khớp flag sẽ dùng lúc demo (nếu có).")
    parser.add_argument("--mode", choices=["auto", "general", "irac"], default="auto")
    parser.add_argument("--cache-dir", default=_DEFAULT_CACHE_DIR,
                        help=f"Thư mục LLM cache (mặc định {_DEFAULT_CACHE_DIR}).")
    # Khoá cache = sha256(model | prompt). Hâm bằng nhà cung cấp KHÁC lúc demo
    # thì mọi câu đều trượt cache — phải khớp `LLM_MODE` của giao diện.
    parser.add_argument("--llm-mode",
                        choices=["claude", "claude-fallback", "gemini", "gemini-fallback"],
                        default=os.getenv("LLM_MODE") or "gemini",
                        help="Nhà cung cấp dùng để hâm. PHẢI khớp lúc demo "
                             "(giao diện mặc định gemini).")
    # refers_mode đổi ngữ cảnh -> đổi prompt -> đổi khoá cache. Phải khớp
    # UI_REFERS_MODE, nếu không demo vẫn gọi tươi.
    parser.add_argument("--refers-mode", choices=["khoan", "all", "rrf"],
                        default=os.getenv("UI_REFERS_MODE") or None,
                        help="PHẢI khớp UI_REFERS_MODE lúc demo.")
    # Cả ba cơ chế đều đổi ngữ cảnh -> đổi khoá cache. Thiếu một cái là trượt.
    parser.add_argument("--rerank-mode", choices=["trong-norm"],
                        default=os.getenv("UI_RERANK_MODE") or None,
                        help="PHẢI khớp UI_RERANK_MODE lúc demo.")
    parser.add_argument("--chuyen-tiep", action="store_true",
                        default=(os.getenv("UI_CHUYEN_TIEP") or "").lower() in ("1", "true", "yes"),
                        help="PHẢI khớp UI_CHUYEN_TIEP lúc demo.")
    # Ngày nằm TRONG lời nhắc nên nằm trong khóa cache. Đọc cùng biến môi trường
    # với giao diện để hai bên không thể lệch nhau.
    parser.add_argument("--ngay-hom-nay", default=os.getenv("UI_NGAY_HOM_NAY") or None,
                        help="Ngày dạng DD/MM/YYYY cấp cho lời nhắc. "
                             "PHẢI khớp UI_NGAY_HOM_NAY lúc demo.")
    args = parser.parse_args()

    questions = list(args.question)
    tep = Path(args.questions_file) if args.questions_file else (
        None if args.question else _tep_mac_dinh())
    if tep:
        if not tep.exists():
            print("❌ Không thấy tệp câu hỏi: %s" % tep)
            sys.exit(1)
        questions += _read_questions(tep)
        print("📄 Nguồn câu hỏi: %s" % tep)
    if not questions:
        print("❌ Không có câu hỏi. Truyền file hoặc --question.")
        sys.exit(1)

    # Import muộn để --help không cần DB
    from src.pipeline import run_pipeline

    cache_dir = Path(args.cache_dir)
    print(f"🔁 Pre-cache {len(questions)} câu → {cache_dir}")
    print(f"   jurisdiction={args.jurisdiction} mode={args.mode} "
          f"llm_mode={args.llm_mode} refers={args.refers_mode} "
          f"rerank={args.rerank_mode} chuyen_tiep={args.chuyen_tiep} "
          f"ngay={args.ngay_hom_nay}")
    print(f"   pool={os.getenv('SF_DENSE_POOL_MIN', '50')} "
          f"rarity_alpha={os.getenv('SF_RARITY_ALPHA', '1.5')}")
    print("   ⚠️  Lúc demo PHẢI đặt đúng LLM_MODE và UI_REFERS_MODE như trên, "
          "khác đi là trượt cache.\n")

    ok = 0
    for i, q in enumerate(questions, 1):
        t0 = time.perf_counter()
        try:
            result = run_pipeline(
                q,
                force_jurisdiction=args.jurisdiction,
                llm_cache_dir=cache_dir,
                response_mode=None if args.mode == "auto" else args.mode,
                llm_mode=args.llm_mode,
                **({"refers_mode": args.refers_mode} if args.refers_mode else {}),
                **({"rerank_mode": args.rerank_mode} if args.rerank_mode else {}),
                **({"chuyen_tiep": True} if args.chuyen_tiep else {}),
                **({"ngay_hom_nay": args.ngay_hom_nay} if args.ngay_hom_nay else {}),
            )
            dt = time.perf_counter() - t0
            hit = result.get("cache_hit")
            tag = "♻️  cache-hit" if hit else "✅ cached mới"
            print(f"[{i}/{len(questions)}] {tag} ({dt:.1f}s) — {q[:60]}")
            ok += 1
        except Exception as e:  # noqa: BLE001 — báo lỗi rõ, tiếp câu sau
            print(f"[{i}/{len(questions)}] ❌ LỖI ({type(e).__name__}): {q[:60]}")
            print(f"      → {e}")

    print(f"\n{'=' * 60}")
    print(f"Xong: {ok}/{len(questions)} câu đã vào cache.")
    print("Lúc demo, chạy ĐÚNG câu + ĐÚNG flag → cache_hit=True ($0, không cần API).")
    if ok < len(questions):
        sys.exit(1)


if __name__ == "__main__":
    main()
