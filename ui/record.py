"""Ghi fixture cho chế độ PHÁT LẠI — Task 4 (`ui/docs/UI_DEMO_SPEC.md` mục 4.2).

**CHẠY Ở MÁY B** (máy có Neo4j + Qdrant đã ingest + LLM credentials). Máy A chỉ
`git pull` lấy `ui/fixtures/*.json` về rồi trình diễn bằng `DEMO_MODE=replay`.

    python -m ui.record "Hạn mức giao đất ở cho cá nhân tại TP.HCM tối đa là bao nhiêu?"
    python -m ui.record            # tự lấy ui/docs/DEMO_QUESTIONS.md

Cờ `--jurisdiction` / `--mode` / `--verify` / `--llm-mode` **phải khớp** với cờ
sẽ dùng lúc demo: chúng đi thẳng vào `run_pipeline`, đổi cờ là đổi kết quả.

Vì sao dùng chính `LiveAdapter` chứ không tự gọi `run_pipeline`: chuỗi event
trong fixture phải giống hệt lúc chạy live (spec Task 4). `LiveAdapter.chay_ghi()`
và `LiveAdapter.ask()` dùng chung `_chay_pipeline()` + chung event `question`,
nên không có hai đường code sinh ra hai dạng trace khác nhau.

Fixture ghi ra CHỈ chứa event log; đuôi `context`/`generate`/`verify`/`done`
được `ReplayAdapter` dựng lại từ `result` bằng `su_kien_ket_qua()` — ghi cả hai
sẽ làm replay phát trùng.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Console Windows mặc định cp1252 → `--help` (chữ có dấu) ném UnicodeEncodeError
# trước cả khi chạy. Ép UTF-8 giống `src/utils/connection_check.py`.
for _luong in (sys.stdout, sys.stderr):
    if getattr(_luong, "encoding", "").lower() != "utf-8":
        try:
            _luong.reconfigure(encoding="utf-8")
        except Exception:                           # noqa: BLE001
            pass

from dotenv import load_dotenv                      # noqa: E402

from ui.adapters import FIXTURES_DIR, LiveAdapter, doc_cau_hoi_goi_y, slug_cau_hoi

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def doc_danh_sach_cau_hoi(dau_vao: str) -> list[str]:
    """Một câu hỏi trực tiếp, hoặc đường dẫn tệp danh sách câu hỏi.

    Coi là tệp khi đường dẫn tồn tại — không đoán theo đuôi `.txt`, vì một câu
    hỏi thật không bao giờ trùng tên một tệp đang tồn tại.
    """
    p = Path(dau_vao)
    if p.is_file():
        cau = doc_cau_hoi_goi_y(p)
        if not cau:
            raise SystemExit(f"Tệp {p} không có dòng câu hỏi nào (bỏ dòng trống và dòng '#').")
        return cau
    return [dau_vao.strip()]


def ghi_fixture(
    adapter: LiveAdapter,
    question: str,
    out_dir: Path,
    params: dict,
    ghi_de: bool = False,
) -> Path | None:
    """Chạy một câu qua `LiveAdapter.chay_ghi()` rồi ghi JSON fixture."""
    dich = out_dir / f"{slug_cau_hoi(question)}.json"
    if dich.exists() and not ghi_de:
        logger.info(f"Bỏ qua (đã có, dùng --overwrite để ghi đè): {dich.name}")
        return None

    logger.info(f"Đang chạy live: {question}")
    events, result = adapter.chay_ghi(question, **params)

    fixture = {
        "question": question,
        "recorded_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "live",
        "params": {
            "force_jurisdiction": params.get("jurisdiction"),
            "response_mode": params.get("response_mode"),
            "verify": bool(params.get("verify")),
            "verify_tier": params.get("verify_tier"),
            "llm_mode": params.get("llm_mode") or adapter.llm_mode,
        },
        "events": events,
        "result": result,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    dich.write_text(
        json.dumps(fixture, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(
        f"Đã ghi {dich.name} — {len(events)} event, "
        f"{len(result.get('citations') or [])} citation, "
        f"{result.get('elapsed_seconds', 0):.1f}s"
    )
    return dich


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ui.record",
        description="Ghi fixture cho chế độ PHÁT LẠI của UI demo (chạy ở máy B).",
    )
    parser.add_argument(
        "dau_vao",
        help="Một câu hỏi, hoặc đường dẫn tệp danh sách câu hỏi "
             "(bỏ trống = ui/docs/DEMO_QUESTIONS.md).",
    )
    parser.add_argument("--jurisdiction", choices=["toan-quoc", "tp-hcm", "dong-nai"],
                        default=None, help="Ép jurisdiction — phải khớp lúc demo.")
    parser.add_argument("--mode", choices=["general", "irac"], default=None,
                        help="response_mode; bỏ trống = để planner tự quyết.")
    parser.add_argument("--verify", action="store_true",
                        help="Bật Verifier agent (D-18).")
    parser.add_argument("--verify-tier", type=int, default=1, choices=[0, 1, 2])
    parser.add_argument("--llm-mode", default=None,
                        choices=["claude", "claude-fallback", "gemini", "gemini-fallback"],
                        help="Mặc định lấy LLM_MODE trong .env (hoặc 'claude').")
    parser.add_argument("--llm-cache-dir", default=None,
                        help="Mặc định data/evaluation/.llm_cache (khớp src/demo.py).")
    parser.add_argument("--no-llm-cache", action="store_true",
                        help="Không dùng cache — ép gọi LLM tươi.")
    parser.add_argument("--out-dir", default=str(FIXTURES_DIR),
                        help="Thư mục ghi fixture (mặc định ui/fixtures/).")
    parser.add_argument("--overwrite", action="store_true",
                        help="Ghi đè fixture đã có.")
    args = parser.parse_args(argv)

    cau_hoi = doc_danh_sach_cau_hoi(args.dau_vao)
    logger.info(f"Sẽ ghi {len(cau_hoi)} câu hỏi.")

    try:
        adapter = LiveAdapter(
            llm_mode=args.llm_mode,
            llm_cache_dir=args.llm_cache_dir,
            no_llm_cache=args.no_llm_cache,
            verify_tier=args.verify_tier,
        )
    except Exception as e:                          # noqa: BLE001
        logger.error(
            f"Không khởi tạo được LiveAdapter: {type(e).__name__}: {e}\n"
            "Kiểm tra: docker compose ps (Neo4j + Qdrant), và credentials trong .env. "
            "Lệnh này PHẢI chạy ở máy B — máy A không có DB."
        )
        return 1

    params = {
        "jurisdiction": args.jurisdiction,
        "response_mode": args.mode,
        "verify": args.verify,
        "verify_tier": args.verify_tier,
        "llm_mode": args.llm_mode,
    }
    out_dir = Path(args.out_dir)
    n_ghi = n_loi = 0
    try:
        for q in cau_hoi:
            try:
                if ghi_fixture(adapter, q, out_dir, params, ghi_de=args.overwrite):
                    n_ghi += 1
            except Exception as e:                  # noqa: BLE001 — một câu hỏng không dừng cả mẻ
                n_loi += 1
                logger.error(f"Lỗi khi ghi câu {q!r}: {type(e).__name__}: {e}")
    finally:
        adapter.dong()

    logger.info(f"Xong: ghi {n_ghi} fixture, {n_loi} câu lỗi, thư mục {out_dir}.")
    return 1 if n_loi and not n_ghi else 0


if __name__ == "__main__":
    sys.exit(main())
