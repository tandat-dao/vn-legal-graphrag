"""Launcher cho UI demo — có cờ `--devmode`.

    python -m ui.run --port 8000
    python -m ui.run --port 8000 --devmode      # giả lập `live` bằng fixture
    python -m ui.run --port 8000 --mode live    # ép mode lúc khởi động

Vì sao cần tệp này: `uvicorn ui.server:app --devmode` KHÔNG chạy được — `uvicorn`
chỉ nhận cờ của chính nó và sẽ báo `no such option: --devmode`. Launcher này nhận
cờ, đặt biến môi trường tương ứng, rồi gọi `uvicorn.run()`.

Tương đương không cần launcher:

    DEMO_DEVMODE=1 uvicorn ui.server:app --port 8000        # bash
    $env:DEMO_DEVMODE="1"; uvicorn ui.server:app --port 8000 # PowerShell
"""
from __future__ import annotations

import argparse
import os
import sys

# Console Windows mặc định cp1252 → `--help` (chữ có dấu) ném UnicodeEncodeError.
for _luong in (sys.stdout, sys.stderr):
    if getattr(_luong, "encoding", "").lower() != "utf-8":
        try:
            _luong.reconfigure(encoding="utf-8")
        except Exception:                           # noqa: BLE001
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ui.run",
        description="Chạy UI demo GraphRAG (bọc uvicorn để thêm cờ --devmode).",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--mode", choices=["replay", "live"], default=None,
                        help="Mode lúc khởi động; mặc định lấy DEMO_MODE trong .env.")
    parser.add_argument(
        "--devmode", action="store_true",
        help="GIẢ LẬP `live` bằng fixture — xem giao diện chế độ live trên máy "
             "KHÔNG có Neo4j/Qdrant/LLM. Dữ liệu vẫn là fixture, KHÔNG phải chạy "
             "thật; trang sẽ hiện một dải đỏ thường trực. Tuyệt đối không bật khi bảo vệ.",
    )
    parser.add_argument("--reload", action="store_true",
                        help="Tự nạp lại khi sửa code (chỉ dùng lúc phát triển).")
    args = parser.parse_args(argv)

    # Kiểm dependency TRƯỚC khi in banner: in "CHẾ ĐỘ DEV" rồi mới đổ traceback
    # khiến người dùng tưởng đã bật được, chỉ là server chết vì lý do khác.
    try:
        import uvicorn
    except ImportError:
        print(
            "Thiếu gói `uvicorn` trong môi trường Python đang chạy:\n"
            f"  {sys.executable}\n\n"
            "Cách sửa (chạy đúng trong venv đang bật):\n"
            "  python -m pip install fastapi uvicorn\n"
            "hoặc cài đủ theo khai báo của repo:\n"
            "  python -m pip install -r requirements.txt\n\n"
            "Lưu ý: chỉ chạy UI ở chế độ replay/devmode thì `fastapi` + `uvicorn` là đủ; "
            "`sentence-transformers` (kéo theo torch, ~2 GB) chỉ cần cho `live` thật.",
            file=sys.stderr,
        )
        return 1

    if args.devmode:
        os.environ["DEMO_DEVMODE"] = "1"
        # Bật devmode mà vẫn ở replay thì chẳng thấy gì khác — vào thẳng live giả.
        os.environ.setdefault("DEMO_MODE", "live")
        print("=" * 68)
        print("  CHẾ ĐỘ DEV — giao diện chạy như `live` nhưng DỮ LIỆU LÀ FIXTURE.")
        print("  Không gọi Neo4j/Qdrant/LLM. KHÔNG dùng khi bảo vệ.")
        print("=" * 68)
    if args.mode:
        os.environ["DEMO_MODE"] = args.mode

    uvicorn.run("ui.server:app", host=args.host, port=args.port, reload=args.reload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
