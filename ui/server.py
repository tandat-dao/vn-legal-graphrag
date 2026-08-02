"""FastAPI server cho UI demo — Task 3 (`ui/docs/UI_DEMO_SPEC.md`).

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

import asyncio
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


class _LocTaiNguyenTinh(logging.Filter):
    """Bỏ log truy cập THÀNH CÔNG của `/static/vendor/…` (Task 5).

    15 tệp font + Tailwind + Cytoscape sinh ra một tràng `GET
    /static/vendor/fonts/... 200 OK` mỗi lần tải trang, đẩy hết log thật
    (`LiveAdapter` khởi tạo, đổi mode, lỗi pipeline) ra khỏi màn hình đúng lúc
    cần nhìn nhất.

    CHỈ lọc 2xx/3xx: 404 vendor vẫn phải hiện, vì đó chính là triệu chứng
    "quên copy thư mục vendor" — thứ làm trang trắng khi máy không có mạng.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if not isinstance(args, tuple) or len(args) < 5:
            return True
        duong_dan, ma = args[2], args[4]
        try:
            im_lang = (str(duong_dan).startswith("/static/vendor/")
                       and 200 <= int(ma) < 400)
        except (TypeError, ValueError):
            return True
        return not im_lang


logging.getLogger("uvicorn.access").addFilter(_LocTaiNguyenTinh())

# Lock cấp module: chỉ một câu hỏi được xử lý tại một thời điểm (mục 2.3).
_KHOA_ASK = threading.Lock()


# ---------------------------------------------------------------------------
# Adapter theo DEMO_MODE
# ---------------------------------------------------------------------------

_adapter: BaseAdapter | None = None


def devmode() -> bool:
    """`DEMO_DEVMODE=1` → cho phép GIẢ LẬP `live` bằng fixture (không cần DB).

    Chỉ để dựng giao diện ở máy A. Đọc mỗi lần gọi (không cache) để test đổi
    biến môi trường được.
    """
    return (os.getenv("DEMO_DEVMODE") or "").strip().lower() in {"1", "true", "yes"}


def tao_adapter(mode: str | None = None) -> BaseAdapter:
    """Khởi tạo adapter theo `mode` (mặc định `DEMO_MODE`); lỗi ở `live` → lùi về `replay`."""
    mode = (mode or os.getenv("DEMO_MODE") or "replay").strip().lower()
    if mode == "live":
        if devmode():
            # Dev mode: KHÔNG thử LiveAdapter thật — mục đích là xem giao diện
            # `live` trên máy không có DB, nên phải đoán trước được kết quả.
            from ui.adapters import DevAdapter
            logger.warning(
                "DEMO_DEVMODE bật — dùng DevAdapter: giao diện chạy như `live` "
                "nhưng DỮ LIỆU LÀ FIXTURE. Không dùng khi bảo vệ.")
            return DevAdapter()
        from ui.adapters import LiveAdapter
        try:
            return LiveAdapter()
        except Exception as e:                      # noqa: BLE001 — demo không được sập
            logger.error(f"Không khởi tạo được LiveAdapter ({e}) — lùi về replay.")
    return ReplayAdapter()


# Task 5 — đổi mode lúc đang chạy, KHÔNG restart server.
# `live` cần dựng client + BGE-M3 (hàng chục giây) nên phải chạy ở thread khác,
# nếu không event loop đứng và trình duyệt tưởng server treo.
_KHOA_DOI_MODE = threading.Lock()
_LOI_DOI_MODE: str | None = None    # lý do lần đổi gần nhất thất bại (cho UI)


def _doi_adapter(mode_moi: str) -> BaseAdapter:
    """Dựng adapter mới rồi thay vào chỗ cũ; adapter cũ được `dong()`.

    Chỉ đổi khi adapter mới dựng THÀNH CÔNG — hỏng thì giữ nguyên cái đang chạy,
    vì giữa buổi bảo vệ mất luôn adapter cũ còn tệ hơn không đổi được.
    """
    global _adapter, _LOI_DOI_MODE
    moi = tao_adapter(mode_moi)
    if mode_moi == "live" and moi.mode != "live":
        _LOI_DOI_MODE = (
            "Không dựng được LiveAdapter (Neo4j/Qdrant/LLM chưa sẵn sàng) — "
            "vẫn đang chạy PHÁT LẠI. Kiểm tra `docker compose ps` và .env."
        )
        moi.dong()
        raise RuntimeError(_LOI_DOI_MODE)
    cu, _adapter = _adapter, moi
    _LOI_DOI_MODE = None
    if cu is not None and cu is not moi:
        try:
            cu.dong()
        except Exception as e:                      # noqa: BLE001
            logger.warning(f"Lỗi khi đóng adapter cũ: {e}")
    logger.info(f"Đã đổi mode sang {moi.mode}.")
    return moi


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


def _trang_thai(adapter: BaseAdapter) -> dict:
    return {
        "mode": adapter.mode,
        "questions": adapter.cau_hoi_co_san(),
        "replay_speed": getattr(adapter, "speed", None),
        "dang_ban": _KHOA_ASK.locked(),
        "dang_doi_mode": _KHOA_DOI_MODE.locked(),
        "loi_doi_mode": _LOI_DOI_MODE,
        # `live` sẵn sàng để bấm chuyển hay không (khỏi hiện nút chết).
        "co_the_live": _co_the_live(),
        # Frontend PHẢI hiện dải đỏ khi cờ này bật — xem DevAdapter.
        "devmode": bool(getattr(adapter, "devmode", False)),
        "fixtures": (adapter.thong_tin_fixtures()
                     if hasattr(adapter, "thong_tin_fixtures") else []),
    }


def _co_the_live() -> bool:
    """Có đủ cấu hình để thử `live` không — KHÔNG kết nối, chỉ xem .env."""
    if devmode():
        return True     # dev mode giả lập được, không cần .env
    return bool(os.getenv("NEO4J_URI") and os.getenv("NEO4J_PASSWORD"))


@app.get("/api/mode")
def api_mode() -> dict:
    return _trang_thai(lay_adapter())


class DoiModeRequest(BaseModel):
    mode: str                          # "live" | "replay"


@app.post("/api/mode")
async def api_doi_mode(payload: DoiModeRequest) -> dict:
    """Đổi live ⇄ replay KHÔNG cần restart (Task 5).

    Chặn khi đang có câu chạy dở: thay adapter giữa chừng sẽ cắt luồng SSE đang
    phát và làm trace dở dang trên màn hình.
    """
    mode_moi = (payload.mode or "").strip().lower()
    if mode_moi not in {"live", "replay"}:
        raise HTTPException(status_code=400,
                            detail="mode chỉ nhận 'live' hoặc 'replay'.")

    if _KHOA_ASK.locked():
        raise HTTPException(
            status_code=409,
            detail="Đang xử lý một câu hỏi — đợi câu đó chạy xong rồi hãy đổi chế độ.")
    if not _KHOA_DOI_MODE.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Đang đổi chế độ, đợi một chút.")
    try:
        hien_tai = lay_adapter()
        if hien_tai.mode == mode_moi:
            moi = hien_tai
        else:
            # `live` dựng client + BGE-M3 rất lâu → chạy ở thread khác cho khỏi
            # chặn event loop (các request khác vẫn trả lời được trong lúc chờ).
            try:
                moi = await asyncio.to_thread(_doi_adapter, mode_moi)
            except Exception as e:                  # noqa: BLE001
                raise HTTPException(status_code=503, detail=str(e))
    finally:
        _KHOA_DOI_MODE.release()
    # Dựng trạng thái SAU khi nhả khóa, nếu không `dang_doi_mode` luôn trả về
    # true và UI hiện "đang đổi…" ngay sau lượt đổi vừa thành công.
    return _trang_thai(moi)


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
