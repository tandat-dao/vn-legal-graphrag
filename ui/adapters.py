"""Adapter `live` | `replay` cho UI demo — Task 3 (`docs/UI_DEMO_SPEC.md`).

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
import unicodedata
from pathlib import Path
from typing import AsyncIterator

from ui.trace import TraceEvent, link_citations, parse_context

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
# LiveAdapter — Task 4 (khung sẵn, chưa nối pipeline)
# ---------------------------------------------------------------------------

class LiveAdapter(BaseAdapter):
    """Gọi `src.pipeline.run_pipeline()` nguyên bản — Task 4 (gộp với `ui/record.py`).

    Chưa triển khai ở Task 3: máy A có Neo4j/Qdrant RỖNG nên không test được.
    Khi làm Task 4 phải giữ đúng mục 2.2 (khởi tạo client + BGE-M3 MỘT LẦN lúc
    startup) và mục 2.3 (mỗi request một `TraceCollector` qua `gan_collector()`).
    """

    mode = "live"

    def __init__(self, **_):
        raise NotImplementedError(
            "LiveAdapter thuộc Task 4 — chưa triển khai. Chạy DEMO_MODE=replay."
        )
