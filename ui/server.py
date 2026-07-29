"""FastAPI server cho UI demo — Task 3 (`docs/UI_DEMO_SPEC.md`).

Chạy:  uvicorn ui.server:app --port 8000
Mode:  DEMO_MODE=replay (mặc định, không cần DB) | live (Task 4)

Đồng thời (spec mục 2.3 — BẮT BUỘC):
  - `/api/ask` được serialize bằng lock cấp module, thử lấy kiểu KHÔNG CHỜ:
    request đến khi đang bận → trả event `kind="error"` "đang xử lý câu trước",
    KHÔNG xếp hàng.
  - Mỗi request một `TraceCollector` riêng (`ui.trace.gan_collector`) — việc này
    nằm trong `LiveAdapter` (Task 4); `ReplayAdapter` không đụng logger.
  - Frontend đọc stream bằng `fetch()` + `getReader()`, KHÔNG dùng `EventSource`.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ui.adapters import BaseAdapter, ReplayAdapter, su_kien_loi
from ui.corpus import get_component_text, load_corpus, norm_graph
from ui.trace import TraceEvent

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"

# Lock cấp module: chỉ một câu hỏi được xử lý tại một thời điểm (mục 2.3).
_KHOA_ASK = threading.Lock()


# ---------------------------------------------------------------------------
# Adapter theo DEMO_MODE
# ---------------------------------------------------------------------------

_adapter: BaseAdapter | None = None


def tao_adapter() -> BaseAdapter:
    """Khởi tạo adapter theo `DEMO_MODE`; lỗi ở `live` thì lùi về `replay`."""
    mode = (os.getenv("DEMO_MODE") or "replay").strip().lower()
    if mode == "live":
        from ui.adapters import LiveAdapter
        try:
            return LiveAdapter()
        except NotImplementedError as e:
            logger.warning(f"{e} — lùi về replay.")
        except Exception as e:
            logger.error(f"Không khởi tạo được LiveAdapter ({e}) — lùi về replay.")
    return ReplayAdapter()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Khởi tạo adapter + nạp corpus MỘT LẦN lúc startup (spec mục 2.2)."""
    global _adapter
    _adapter = tao_adapter()
    load_corpus()   # để request đầu tiên không phải chờ đọc 32 file
    logger.info(f"UI sẵn sàng — mode={_adapter.mode}")
    try:
        yield
    finally:
        if _adapter is not None:
            _adapter.dong()


app = FastAPI(
    title="GraphRAG Pháp luật VN — Demo bảo vệ",
    docs_url=None, redoc_url=None, lifespan=lifespan,
)

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def lay_adapter() -> BaseAdapter:
    global _adapter
    if _adapter is None:
        _adapter = tao_adapter()
    return _adapter


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@app.get("/")
def trang_chu() -> FileResponse:
    index = STATIC_DIR / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=500, detail="Thiếu ui/static/index.html")
    return FileResponse(index)


@app.get("/api/mode")
def api_mode() -> dict:
    adapter = lay_adapter()
    return {
        "mode": adapter.mode,
        "questions": adapter.cau_hoi_co_san(),
        "replay_speed": getattr(adapter, "speed", None),
        "dang_ban": _KHOA_ASK.locked(),
        "fixtures": (adapter.thong_tin_fixtures()
                     if hasattr(adapter, "thong_tin_fixtures") else []),
    }


class HoiRequest(BaseModel):
    question: str
    jurisdiction: str | None = None
    response_mode: str | None = None   # None | "general" | "irac"
    verify: bool = False
    speed: float | None = None         # chỉ có tác dụng ở replay


def _khung_sse(event: TraceEvent | dict) -> str:
    """Một khung SSE: `data: {json}\\n\\n`."""
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@app.post("/api/ask")
async def api_ask(payload: HoiRequest) -> StreamingResponse:
    adapter = lay_adapter()
    question = (payload.question or "").strip()

    async def phat() -> AsyncIterator[str]:
        # Lấy lock KHÔNG CHỜ ngay trong generator để acquire/release luôn cùng
        # một vòng đời — client ngắt giữa chừng thì `finally` vẫn nhả lock.
        if not _KHOA_ASK.acquire(blocking=False):
            yield _khung_sse(su_kien_loi(
                "Hệ thống đang xử lý câu hỏi trước — vui lòng đợi câu đó chạy xong "
                "rồi hỏi tiếp (mỗi lần chỉ chạy một câu để trace không bị trộn).",
                data={"loai": "dang-ban"},
            ))
            return
        try:
            if not question:
                yield _khung_sse(su_kien_loi("Chưa nhập câu hỏi."))
                return
            async for event in adapter.ask(
                question,
                jurisdiction=payload.jurisdiction,
                response_mode=payload.response_mode,
                verify=payload.verify,
                speed=payload.speed,
            ):
                yield _khung_sse(event)
        except Exception as e:                      # noqa: BLE001 — demo không được sập
            logger.exception("Lỗi khi xử lý câu hỏi")
            yield _khung_sse(su_kien_loi(
                f"Pipeline gặp lỗi: {e}. Có thể chuyển sang chế độ PHÁT LẠI "
                "(DEMO_MODE=replay) để tiếp tục trình bày.",
                data={"loai": "loi-pipeline"},
            ))
        finally:
            _KHOA_ASK.release()

    return StreamingResponse(
        phat(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/norm-graph")
def api_norm_graph() -> dict:
    return norm_graph()


@app.get("/api/text")
def api_text(
    norm_id: str = Query(...),
    dieu: str = Query(...),
    khoan: str | None = Query(None),
    diem: str | None = Query(None),
) -> dict:
    corpus = load_corpus()
    norm = corpus.get(norm_id)
    text = get_component_text(norm_id, dieu, khoan, diem)
    return {
        "norm_id": norm_id,
        "dieu": dieu,
        "khoan": khoan,
        "diem": diem,
        "tim_thay": text is not None,
        "text": text,
        "norm": None if norm is None else {
            "title": norm["title"], "so_hieu": norm["so_hieu"],
            "tier": norm["tier"], "valid_from": norm["valid_from"],
            "valid_to": norm["valid_to"], "source_url": norm["source_url"],
        },
    }
