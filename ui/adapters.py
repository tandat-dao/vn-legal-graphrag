"""Adapter `live` | `replay` cho UI demo — Task 3 (`ui/docs/UI_DEMO_SPEC.md`).

Hai adapter cùng một interface `ask()` → `AsyncIterator[TraceEvent]`. Frontend
CHỈ biết dòng TraceEvent, không biết mode nào đang chạy (spec mục 4.1).

`ReplayAdapter` (Task 3, làm ở máy A — không cần DB): phát lại fixture do
`ui/record.py` sinh ở máy B.
`LiveAdapter` (Task 4): gọi `src.pipeline.run_pipeline()` NGUYÊN BẢN.

Chuỗi event của một request:
    1. `question` / `result`  — echo input (nguồn: chính request)
    2. …các event log của pipeline (nguồn: log record thật)
    3. `context` / `result`   — bảng block parse từ `PipelineResult["context"]`
    4. `generate` / `result`  — answer + citation đã nối block
    5. `done` / `done`        — tổng kết
Bước 3–5 do `su_kien_ket_qua()` dựng — dùng CHUNG cho cả hai adapter để chuỗi
event khi replay giống hệt lúc chạy live.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import threading
import unicodedata
from pathlib import Path
from typing import AsyncIterator

from ui.trace import TraceEvent, gan_collector, link_citations, parse_context

logger = logging.getLogger(__name__)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

# Một câu chạy thật mất ~22s → chia thời gian phát lại cho hệ số này.
DEFAULT_REPLAY_SPEED = 4.0
# Chặn trên cho mỗi khoảng nghỉ: fixture lỗi (t nhảy vọt) không được treo demo.
_MAX_SLEEP = 5.0


# ---------------------------------------------------------------------------
# Chuẩn hóa câu hỏi để tra fixture
# ---------------------------------------------------------------------------

_DAU_CAU_RE = re.compile(r"[^\w\s]", re.UNICODE)


def chuan_hoa_cau_hoi(question: str) -> str:
    """Khóa tra fixture: lowercase, bỏ dấu câu, gộp khoảng trắng.

    GIỮ dấu tiếng Việt (chỉ chuẩn hóa NFC) — bỏ dấu sẽ làm "hạn mức" và
    "hàn mức" trùng khóa.
    """
    text = unicodedata.normalize("NFC", question or "").lower()
    text = _DAU_CAU_RE.sub(" ", text)
    return " ".join(text.split())


def slug_cau_hoi(question: str, max_len: int = 60) -> str:
    """Tên file fixture từ câu hỏi (bỏ dấu tiếng Việt cho an toàn hệ tệp)."""
    text = unicodedata.normalize("NFD", question or "").lower()
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:max_len].strip("-") or "cau-hoi"


# ---------------------------------------------------------------------------
# Event dựng từ PipelineResult (dùng chung live + replay)
# ---------------------------------------------------------------------------

def su_kien_ket_qua(result: dict, seq_bat_dau: int, t: float) -> list[TraceEvent]:
    """Dựng các event `result` cuối luồng từ một `PipelineResult`.

    Mọi trường đều lấy từ `PipelineResult` thật — KHÔNG bịa. Riêng bảng block
    là parse lại từ `result["context"]` (spec mục 3.1: `PipelineResult` không
    chứa `ScoredTextUnit`, nên KHÔNG có rrf per-block và KHÔNG biết pass nào
    sinh ra block nào).
    """
    result = result or {}
    blocks = parse_context(result.get("context") or "")
    citations = result.get("citations") or []
    events: list[TraceEvent] = []

    def _them(step: str, kind: str, data: dict) -> None:
        events.append(TraceEvent(
            seq=seq_bat_dau + len(events), t=round(t, 3),
            step=step, kind=kind, raw="", data=data,
        ))

    _them("context", "result", {
        "blocks": blocks,
        "n_blocks": len(blocks),
        "context_tokens": result.get("context_tokens"),
        "top_k_count": result.get("top_k_count"),
        "context_used": result.get("context_used"),
    })
    _them("generate", "result", {
        "answer": result.get("answer") or "",
        "citations": citations,
        "citation_links": link_citations(citations, blocks),
        "response_mode": result.get("response_mode"),
    })
    _them("verify", "result", {"verifier": result.get("verifier")})
    _them("done", "done", {
        "elapsed_seconds": result.get("elapsed_seconds"),
        "n_citations": len(citations),
        "lccids_count": result.get("lccids_count"),
        "query_plan": result.get("query_plan"),
    })
    return events


def su_kien_loi(thong_bao: str, seq: int = 0, t: float = 0.0,
                data: dict | None = None) -> TraceEvent:
    """Event lỗi — thông báo tiếng Việt, hiển thị thẳng cho người trình bày."""
    return TraceEvent(
        seq=seq, t=round(t, 3), step="done", kind="error",
        raw=thong_bao, data={"thong_bao": thong_bao, **(data or {})},
    )


# ---------------------------------------------------------------------------
# Adapter cơ sở
# ---------------------------------------------------------------------------

class BaseAdapter:
    """Interface chung: `ask()` phát dòng TraceEvent cho một câu hỏi."""

    mode: str = "base"

    def cau_hoi_co_san(self) -> list[str]:
        """Danh sách câu hỏi gợi ý cho frontend ([] nếu không giới hạn)."""
        return []

    async def ask(self, question: str, **params) -> AsyncIterator[TraceEvent]:
        raise NotImplementedError

    def dong(self) -> None:
        """Dọn tài nguyên lúc tắt server (LiveAdapter đóng driver)."""


# ---------------------------------------------------------------------------
# ReplayAdapter
# ---------------------------------------------------------------------------

class ReplayAdapter(BaseAdapter):
    """Phát lại fixture — chạy được ở máy A, không cần Neo4j/Qdrant/LLM."""

    mode = "replay"

    def __init__(
        self,
        fixtures_dir: Path | str | None = None,
        speed: float | None = None,
    ):
        self.fixtures_dir = Path(fixtures_dir or FIXTURES_DIR)
        self.speed = speed if speed is not None else _doc_speed()
        self._fixtures: dict[str, dict] = {}
        self.nap_fixtures()

    # -- nạp fixture -------------------------------------------------------

    def nap_fixtures(self) -> int:
        """Đọc lại toàn bộ `ui/fixtures/*.json`. Trả về số fixture hợp lệ."""
        self._fixtures = {}
        if not self.fixtures_dir.is_dir():
            logger.warning(f"Không có thư mục fixture: {self.fixtures_dir}")
            return 0
        for path in sorted(self.fixtures_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as e:
                logger.warning(f"Fixture hỏng, bỏ qua {path.name}: {e}")
                continue
            question = (data.get("question") or "").strip()
            if not question:
                logger.warning(f"Fixture {path.name} thiếu 'question' — bỏ qua.")
                continue
            data["_file"] = path.name
            self._fixtures[chuan_hoa_cau_hoi(question)] = data
        logger.info(f"ReplayAdapter: nạp {len(self._fixtures)} fixture từ {self.fixtures_dir}")
        return len(self._fixtures)

    def cau_hoi_co_san(self) -> list[str]:
        return [f["question"] for f in self._fixtures.values()]

    def thong_tin_fixtures(self) -> list[dict]:
        return [
            {
                "question": f["question"], "file": f.get("_file"),
                "mode": f.get("mode"), "tam": bool(f.get("tam")),
                "recorded_at": f.get("recorded_at"), "ghi_chu": f.get("ghi_chu"),
            }
            for f in self._fixtures.values()
        ]

    def tim_fixture(self, question: str) -> dict | None:
        return self._fixtures.get(chuan_hoa_cau_hoi(question))

    # -- phát lại ----------------------------------------------------------

    async def ask(self, question: str, **params) -> AsyncIterator[TraceEvent]:
        fixture = self.tim_fixture(question)
        if fixture is None:
            co_san = self.cau_hoi_co_san()
            yield su_kien_loi(
                "Chưa có fixture cho câu hỏi này. Chế độ PHÁT LẠI chỉ chạy được "
                "những câu đã ghi sẵn ở máy B bằng `python -m ui.record`. "
                + (
                    "Các câu đang có: " + " | ".join(co_san)
                    if co_san else
                    f"Hiện chưa có fixture nào trong {self.fixtures_dir}."
                ),
                data={"cau_hoi_co_san": co_san, "loai": "khong-co-fixture"},
            )
            return

        events: list[dict] = fixture.get("events") or []
        result: dict = fixture.get("result") or {}
        # `speed` theo request (nút chỉnh tốc độ ở Task 5) đè `REPLAY_SPEED`.
        try:
            speed = float(params.get("speed") or self.speed)
        except (TypeError, ValueError):
            speed = self.speed
        speed = max(speed, 0.1)

        # Fixture viết tay tạm (Task 3) phải tự khai báo để UI cảnh báo — không
        # được để người xem tưởng đây là một lượt chạy thật.
        canh_bao_tam = {}
        if fixture.get("tam"):
            canh_bao_tam = {
                "fixture_tam": True,
                "fixture_ghi_chu": fixture.get("ghi_chu") or "",
                "fixture_file": fixture.get("_file"),
            }

        t_truoc = 0.0
        seq = 0
        for raw_event in events:
            cho = (float(raw_event.get("t") or 0.0) - t_truoc) / speed
            if cho > 0:
                await asyncio.sleep(min(cho, _MAX_SLEEP))
            t_truoc = float(raw_event.get("t") or t_truoc)
            data = dict(raw_event.get("data") or {})
            if seq == 0 and canh_bao_tam:
                data.update(canh_bao_tam)
            event = TraceEvent(
                seq=seq,
                t=round(t_truoc, 3),
                step=raw_event.get("step") or "question",
                kind=raw_event.get("kind") or "log",
                raw=raw_event.get("raw") or "",
                data=data,
            )
            seq += 1
            yield event

        # Event kết quả dựng từ `result` — cùng hàm với LiveAdapter.
        for event in su_kien_ket_qua(result, seq, t_truoc):
            yield event


def _doc_speed() -> float:
    try:
        return float(os.getenv("REPLAY_SPEED", DEFAULT_REPLAY_SPEED))
    except ValueError:
        return DEFAULT_REPLAY_SPEED


# ---------------------------------------------------------------------------
# LiveAdapter — Task 4
# ---------------------------------------------------------------------------

# Khớp `--llm-cache-dir` của `src/demo.py` (KHÔNG phải `data/llm_cache`).
DEFAULT_LLM_CACHE_DIR = Path("data/evaluation/.llm_cache")

# Nhịp rót event từ queue của collector ra SSE trong lúc pipeline chạy ở thread.
_NHIP_ROT = 0.05


class LiveAdapter(BaseAdapter):
    """Gọi `src.pipeline.run_pipeline()` NGUYÊN BẢN (spec mục 1.2).

    Hai ràng buộc bắt buộc của spec:

    * **Mục 2.2 — client khởi tạo MỘT LẦN.** `__init__` gọi
      `src.pipeline._build_clients()` (Neo4j driver + Qdrant client + LLM client
      + BGE-M3) rồi truyền vào `run_pipeline` qua keyword ở mỗi request.
      `load_model()` mất hàng chục giây; để `run_pipeline` tự khởi tạo là phá
      buổi demo. Vì vậy adapter phải được dựng trong FastAPI lifespan.
    * **Mục 2.3 — mỗi request một `TraceCollector`.** Dùng `gan_collector()`
      (context manager tự `removeHandler` trong `finally`), KHÔNG dùng chung
      một collector rồi `reset()`.

    `ask()` (streaming, cho `/api/ask`) và `chay_ghi()` (đồng bộ, cho
    `ui/record.py`) dùng CHUNG `_chay_pipeline()` và chung event `question` —
    nên chuỗi event ghi vào fixture giống hệt lúc chạy live.
    """

    mode = "live"

    def __init__(
        self,
        llm_mode: str | None = None,
        llm_cache_dir: Path | str | None = None,
        no_llm_cache: bool = False,
        top_k: int | None = None,
        max_tokens: int | None = None,
        verify_tier: int = 1,
        clients: tuple | None = None,
    ):
        from src.pipeline import _build_clients

        self.llm_mode = (llm_mode or os.getenv("LLM_MODE") or "claude").strip()
        self.llm_cache_dir = (
            None if no_llm_cache
            else Path(llm_cache_dir or DEFAULT_LLM_CACHE_DIR)
        )
        self.top_k = top_k
        self.max_tokens = max_tokens
        self.verify_tier = verify_tier

        # `clients` chỉ để test tiêm client giả — chạy thật luôn đi qua
        # `_build_clients` để đúng đường code của `src/`.
        if clients is None:
            logger.info(f"LiveAdapter: khởi tạo client (llm_mode={self.llm_mode})…")
            clients = _build_clients(self.llm_mode)
            logger.info("LiveAdapter: client + BGE-M3 đã sẵn sàng.")
        (self.neo4j_driver, self.qdrant_client,
         self.anthropic_client, self.model) = clients

        # Chốt chặn thứ hai sau lock của `server.py`: không cho hai lượt
        # `run_pipeline` chồng nhau kể cả khi client ngắt kết nối giữa chừng
        # làm generator SSE đóng sớm và nhả lock cấp module (spec mục 2.3).
        self._khoa_pipeline = threading.Lock()

    # -- vòng đời ----------------------------------------------------------

    def dong(self) -> None:
        """Đóng Neo4j driver lúc tắt server."""
        try:
            if self.neo4j_driver is not None:
                self.neo4j_driver.close()
        except Exception as e:                      # noqa: BLE001 — tắt máy, đừng sập
            logger.warning(f"Lỗi khi đóng Neo4j driver: {e}")

    def cau_hoi_co_san(self) -> list[str]:
        """Live không giới hạn câu hỏi; gợi ý lấy từ `demo_questions.txt` nếu có."""
        return doc_cau_hoi_goi_y()

    # -- chạy pipeline -----------------------------------------------------

    def _tham_so(self, params: dict) -> dict:
        """Gom keyword cho `run_pipeline` — bỏ hẳn key None để giữ mặc định của `src/`."""
        kw = {
            "neo4j_driver": self.neo4j_driver,
            "qdrant_client": self.qdrant_client,
            "anthropic_client": self.anthropic_client,
            "model": self.model,
            "force_jurisdiction": params.get("jurisdiction"),
            "response_mode": params.get("response_mode"),
            "verify": bool(params.get("verify")),
            "verify_tier": params.get("verify_tier", self.verify_tier),
            "llm_mode": params.get("llm_mode") or self.llm_mode,
            "llm_cache_dir": self.llm_cache_dir,
        }
        if self.top_k is not None:
            kw["top_k"] = self.top_k
        if self.max_tokens is not None:
            kw["max_tokens"] = self.max_tokens
        return kw

    def _du_lieu_cau_hoi(self, question: str, params: dict) -> dict:
        """Data của event `question` — echo input, dùng chung ask() và chay_ghi()."""
        return {
            "question": question,
            "force_jurisdiction": params.get("jurisdiction"),
            "response_mode": params.get("response_mode"),
            "verify": bool(params.get("verify")),
            "llm_mode": params.get("llm_mode") or self.llm_mode,
        }

    def _chay_pipeline(self, question: str, params: dict) -> dict:
        """Gọi `run_pipeline` nguyên bản (chạy trong thread riêng)."""
        from src.pipeline import run_pipeline
        return run_pipeline(question, **self._tham_so(params))

    # -- đường đồng bộ: dùng cho ui/record.py ------------------------------

    def chay_ghi(self, question: str, **params) -> tuple[list[TraceEvent], dict]:
        """Chạy một câu ĐỒNG BỘ → `(events log, PipelineResult)`.

        `ui/record.py` dùng hàm này. Trả về **chỉ event log** (không có đuôi
        `context`/`generate`/`verify`/`done`) vì `ReplayAdapter` dựng lại đuôi
        đó từ `result` bằng `su_kien_ket_qua()` — ghi cả hai sẽ phát trùng.
        """
        if not self._khoa_pipeline.acquire(blocking=False):
            raise RuntimeError("Một lượt run_pipeline khác đang chạy.")
        try:
            with gan_collector() as collector:
                collector.push("question", "result", data=self._du_lieu_cau_hoi(question, params))
                result = self._chay_pipeline(question, params)
                return collector.drain(), result
        finally:
            self._khoa_pipeline.release()

    # -- đường streaming: dùng cho /api/ask --------------------------------

    async def ask(self, question: str, **params) -> AsyncIterator[TraceEvent]:
        if not self._khoa_pipeline.acquire(blocking=False):
            yield su_kien_loi(
                "Pipeline vẫn đang chạy câu trước (có thể do lượt trước bị ngắt "
                "giữa chừng). Đợi vài giây rồi hỏi lại, hoặc chuyển sang chế độ "
                "PHÁT LẠI để trình bày tiếp.",
                data={"loai": "dang-ban"},
            )
            return

        da_giao_thread = False
        seq_cuoi = -1
        t_cuoi = 0.0
        try:
            with gan_collector() as collector:
                # `push()` đã ĐẨY event vào queue rồi — chỉ đẩy, KHÔNG yield ở
                # đây, nếu không vòng drain bên dưới sẽ phát lại lần thứ hai
                # (seq lặp 0,0 → frontend dựng hai thẻ bước 1).
                collector.push(
                    "question", "result", data=self._du_lieu_cau_hoi(question, params))

                viec = asyncio.ensure_future(
                    asyncio.to_thread(self._chay_pipeline_roi_nha, question, params))
                # Nhường MỘT vòng lặp để task kịp `submit` vào executor. Nếu
                # không, client đóng kết nối ngay sau event đầu sẽ hủy task
                # trước khi thread khởi động → `_chay_pipeline_roi_nha` không
                # bao giờ chạy → khóa kẹt vĩnh viễn, mọi câu sau báo "đang bận".
                await asyncio.sleep(0)
                da_giao_thread = True

                # Rót event ra SSE trong lúc pipeline còn chạy ở thread khác.
                while not viec.done():
                    for ev in collector.drain():
                        seq_cuoi, t_cuoi = ev["seq"], ev["t"]
                        yield ev
                    await asyncio.sleep(_NHIP_ROT)
                for ev in collector.drain():        # vét nốt phần còn lại
                    seq_cuoi, t_cuoi = ev["seq"], ev["t"]
                    yield ev

                try:
                    result = viec.result()
                except Exception as e:              # noqa: BLE001 — demo không được sập
                    yield _loi_pipeline(e, seq_cuoi + 1, t_cuoi)
                    return

            for ev in su_kien_ket_qua(result, seq_cuoi + 1, t_cuoi):
                yield ev
        finally:
            if not da_giao_thread:
                self._khoa_pipeline.release()

    def _chay_pipeline_roi_nha(self, question: str, params: dict) -> dict:
        """Bọc `_chay_pipeline` để LUÔN nhả khóa, kể cả khi SSE đã đóng sớm."""
        try:
            return self._chay_pipeline(question, params)
        finally:
            self._khoa_pipeline.release()


def _loi_pipeline(e: Exception, seq: int, t: float) -> TraceEvent:
    """Đổi exception của pipeline thành event lỗi tiếng Việt.

    Tách riêng `APIStatusError` (429/529 hay gặp — xem cách `src/demo.py` xử lý)
    vì cách chữa khác hẳn lỗi hạ tầng: chờ vài phút hoặc đổi `llm_mode`.
    """
    ten = type(e).__name__
    status = getattr(e, "status_code", None)
    if status is not None:
        thong_bao = (
            f"LLM trả lỗi {status} ({ten}). Câu đã chạy trước đó vẫn dùng được "
            "nhờ cache; câu mới thì phụ thuộc API. Cách xử lý: đợi vài phút và "
            "hỏi lại, đổi `--llm-mode` (claude-fallback / gemini-fallback), hoặc "
            "chuyển sang chế độ PHÁT LẠI để trình bày tiếp."
        )
        loai = "loi-llm"
    else:
        thong_bao = (
            f"Pipeline gặp lỗi: {ten}: {e}. Kiểm tra Neo4j/Qdrant còn chạy không "
            "(`docker compose ps`). Nếu không chữa nhanh được, chuyển sang chế độ "
            "PHÁT LẠI để trình bày tiếp."
        )
        loai = "loi-pipeline"
    logger.exception("LiveAdapter: pipeline lỗi")
    return su_kien_loi(thong_bao, seq=seq, t=t, data={"loai": loai, "exception": ten})


# ---------------------------------------------------------------------------
# Câu hỏi gợi ý cho chế độ live
# ---------------------------------------------------------------------------

DEMO_QUESTIONS_FILE = Path("data/evaluation/demo_questions.txt")


def doc_cau_hoi_goi_y(path: Path | str | None = None) -> list[str]:
    """Đọc `demo_questions.txt` — bỏ dòng trống và dòng bắt đầu bằng `#`.

    Cùng quy tắc với `ui/record.py` để danh sách gợi ý lúc `live` trùng đúng
    danh sách câu đã ghi fixture cho `replay`.
    """
    p = Path(path or DEMO_QUESTIONS_FILE)
    if not p.is_file():
        return []
    try:
        dong = p.read_text(encoding="utf-8").splitlines()
    except OSError as e:
        logger.warning(f"Không đọc được {p}: {e}")
        return []
    return [d.strip() for d in dong if d.strip() and not d.strip().startswith("#")]
