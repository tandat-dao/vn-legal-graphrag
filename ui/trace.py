"""Trace collector + parser cho UI demo — Task 2 (`docs/UI_DEMO_SPEC.md` mục 6).

Ba nhóm chức năng, tất cả đều thuần đọc — KHÔNG gọi LLM, KHÔNG sửa `src/`:

1. `TraceCollector` — `logging.Handler` gắn vào logger `"src"`, biến mỗi log
   record thành `TraceEvent` có cấu trúc rồi đẩy vào `queue.Queue` để SSE rót ra.
2. `parse_message()` — phân loại một dòng log thành `(step, data)` bằng regex
   (mục 5.1 của spec).
3. `parse_context()` / `link_citations()` — parse chuỗi context do
   `assemble_context()` ghép (mục 5.2) và nối citation → block (mục 5.3).

Nguyên tắc bất biến (spec mục 4.1): `raw` LUÔN được giữ nguyên. Regex không
khớp thì vẫn phát event với `data={}` — thà hiện thô còn hơn mất thông tin.
KHÔNG lọc theo danh sách keyword như `src/demo.py` (danh sách đó có mục chết và
sẽ mục ruỗng thêm khi `src/` đổi).
"""
from __future__ import annotations

import ast
import logging
import queue
import re
import threading
import time
from contextlib import contextmanager
from typing import Any, Callable, Iterator, TypedDict

logger = logging.getLogger(__name__)

# Bảy bước hiển thị + các bước phụ; đồng bộ với spec mục 4.1.
STEPS = (
    "question", "plan", "temporal", "stage1", "stage2", "stage3",
    "hybrid", "context", "generate", "verify", "done",
)

# Loại event.
KINDS = ("log", "result", "error", "done")


class TraceEvent(TypedDict):
    seq: int          # số thứ tự tăng dần
    t: float          # giây kể từ lúc bắt đầu request
    step: str         # ∈ STEPS
    kind: str         # ∈ KINDS
    raw: str          # message log gốc — luôn giữ để đối chiếu
    data: dict        # dict đã parse ({} nếu không parse được)


class ContextBlock(TypedDict):
    index: int
    label: str                 # nhãn gốc trong header `--- ... ---`
    tier: int | None
    valid_from: str | None
    valid_to: str | None
    het_hieu_luc: bool
    vi_tri: str                # "Điều 3. ..., Khoản 1." ("" nếu label chỉ là slug)
    norm_id: str
    amendments: list[dict]     # {amending_norm, amending_loc, effective_date, content_summary}
    text: str                  # nguyên văn (đã bỏ block cảnh báo sửa đổi)
    raw: str                   # toàn bộ block gốc


# ---------------------------------------------------------------------------
# Helper chuyển chuỗi Python repr → giá trị
# ---------------------------------------------------------------------------

def _lit(text: str | None, default: Any = None) -> Any:
    """`ast.literal_eval` phòng vệ — trả `default` khi chuỗi không hợp lệ."""
    if text is None:
        return default
    try:
        return ast.literal_eval(text.strip())
    except (ValueError, SyntaxError):
        return default


def _none(text: str | None) -> str | None:
    """'None' (Python repr trong log) → None; chuỗi rỗng → None."""
    if text is None:
        return None
    text = text.strip()
    if not text or text == "None":
        return None
    return text


def _int(text: str | None, default: int | None = None) -> int | None:
    try:
        return int(str(text).strip())
    except (TypeError, ValueError):
        return default


def _float(text: str | None, default: float | None = None) -> float | None:
    try:
        return float(str(text).strip())
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Stage 1 — ghép scores với norm_ids
# ---------------------------------------------------------------------------

def pair_stage1(
    scores: list[float],
    norm_ids: list[str],
    threshold: float | None,
) -> list[dict]:
    """Ghép `scores` (toàn bộ top-n theo rank) với `norm_ids` (đã lọc ≥ ngưỡng).

    Qdrant trả kết quả sắp giảm dần theo score nên tập vượt ngưỡng luôn là
    PREFIX của danh sách rank → norm_ids[i] ứng với scores[i]. Dùng độ dài
    `norm_ids` để xác định ranh giới thay vì so sánh lại `score >= threshold`
    (score trong log đã làm tròn 3 chữ số, so lại có thể lệch ở ca sát ngưỡng).

    Ca fallback của `stage1_norm_ids` (không norm nào vượt ngưỡng → giữ top-1):
    rank 0 vẫn `chon=True` nhưng `duoi_nguong=True`.

    Returns:
        list {rank, score, norm_id, chon, duoi_nguong} theo thứ tự rank.
    """
    k = len(norm_ids)
    out: list[dict] = []
    for rank, score in enumerate(scores):
        chon = rank < k
        out.append({
            "rank": rank,
            "score": score,
            "norm_id": norm_ids[rank] if chon else None,
            "chon": chon,
            "duoi_nguong": threshold is not None and score < threshold,
        })
    # Log Stage 1 [no-theme] không có scores → vẫn liệt kê norm_ids đã chọn.
    for rank in range(len(scores), k):
        out.append({
            "rank": rank, "score": None, "norm_id": norm_ids[rank],
            "chon": True, "duoi_nguong": False,
        })
    return out


# ---------------------------------------------------------------------------
# Bảng regex phân loại log record (nguyên văn format từ `src/`, spec mục 5.1)
# ---------------------------------------------------------------------------

_Builder = Callable[[re.Match], dict]

_PATTERNS: list[tuple[re.Pattern, str, _Builder]] = [
    # --- Query planner ---------------------------------------------------
    (
        re.compile(r"^run_pipeline: plan_query cho '(?P<q>.*)'$"),
        "plan",
        lambda m: {"question_preview": m.group("q")},
    ),
    (
        re.compile(r"^plan_query: cache HIT \((?P<key>[^)]*)\) — \$0 API$"),
        "plan",
        lambda m: {"cache_hit": True, "cache_key": m.group("key")},
    ),
    (
        re.compile(
            r"^plan_query: backfill theme='(?P<theme>[^']*)' từ norm refs "
            r"tokens=(?P<tokens>.*) ids=(?P<ids>.*)$"
        ),
        "plan",
        lambda m: {
            "backfill_theme": m.group("theme"),
            "tokens": _lit(m.group("tokens"), []),
            "ids": _lit(m.group("ids"), []),
        },
    ),
    (
        re.compile(
            r"^plan_query \| theme=(?P<theme>\S*) procedure=(?P<proc>\S*) "
            r"jurisdiction=(?P<juris>\S*) temporal=(?P<temporal>\S*) "
            r"temporal_ctx=(?P<ctx>\S+)$"
        ),
        "plan",
        lambda m: {
            "theme": _none(m.group("theme")),
            "procedure": _none(m.group("proc")),
            "jurisdiction": _none(m.group("juris")),
            "temporal": _none(m.group("temporal")),
            "has_temporal_context": m.group("ctx") == "True",
        },
    ),
    (
        re.compile(r"^run_pipeline: plan=(?P<theme>.*?)/(?P<juris>.*)$"),
        "plan",
        lambda m: {
            "theme": _none(m.group("theme")),
            "jurisdiction": _none(m.group("juris")),
        },
    ),
    (
        re.compile(r"^run_pipeline: response_mode='(?P<mode>[^']*)'$"),
        "plan",
        lambda m: {"response_mode": m.group("mode")},
    ),
    (
        re.compile(r"^run_pipeline: force_jurisdiction='(?P<j>[^']*)' áp dụng$"),
        "plan",
        lambda m: {"force_jurisdiction": m.group("j"), "ap_dung": True},
    ),
    # --- Temporal --------------------------------------------------------
    (
        re.compile(
            r"^run_pipeline: TEMPORAL MODE — anchor='(?P<anchor>[^']*)' "
            r"status='(?P<status>[^']*)' → (?P<reason>.+)$"
        ),
        "temporal",
        lambda m: {
            "temporal_anchor": _none(m.group("anchor")),
            "case_status": _none(m.group("status")),
            "reason": m.group("reason").strip(),
            "temporal": _temporal_tu_reason(m.group("reason")),
            "broad": "broad" in m.group("reason") or "span-regime" in m.group("reason"),
        },
    ),
    # --- Stage 1 ---------------------------------------------------------
    (
        re.compile(
            r"^Stage 1: top-(?P<top_n>\d+) scores=(?P<scores>\[.*?\]), "
            r"threshold=(?P<threshold>[\d.]+) → (?P<n>\d+) norm_ids = (?P<ids>\[.*\])$"
        ),
        "stage1",
        lambda m: _stage1_data(
            top_n=_int(m.group("top_n")),
            scores=_lit(m.group("scores"), []),
            threshold=_float(m.group("threshold")),
            norm_ids=_lit(m.group("ids"), []),
            no_theme=False,
        ),
    ),
    (
        re.compile(r"^Stage 1 \[no-theme\]: (?P<n>\d+) norm_ids = (?P<ids>\[.*\])$"),
        "stage1",
        lambda m: _stage1_data(
            top_n=None, scores=[], threshold=None,
            norm_ids=_lit(m.group("ids"), []), no_theme=True,
        ),
    ),
    # --- Stage 2 ---------------------------------------------------------
    # CẢNH BÁO CHO FRONTEND: `norm_ids` ở đây KHÔNG có thứ hạng. `stage2_norm_ids`
    # dựng kết quả bằng `list({row["norm_id"] for row in rows})` → thứ tự phụ
    # thuộc hash randomization, đổi theo từng process. Hiển thị dạng TẬP HỢP
    # (sắp theo tier hoặc alphabet), TUYỆT ĐỐI không đánh số 1., 2., 3. như thể
    # là mức độ liên quan. (Stage 1 thì ngược lại — có score, có rank thật.)
    (
        re.compile(
            r"^Stage 2 \(norm_ids\): (?P<n>\d+) norms "
            r"\(jurisdiction=(?P<juris>[^,]*), temporal=(?P<temporal>.*?)\): "
            r"(?P<ids>\[.*\])$"
        ),
        "stage2",
        lambda m: {
            "n_norms": _int(m.group("n")),
            "jurisdiction": _none(m.group("juris")),
            "temporal": _none(m.group("temporal")),
            "norm_ids": _lit(m.group("ids"), []),
        },
    ),
    (
        re.compile(
            r"^Stage 2: (?P<n>\d+) component_ids từ (?P<m>\d+) norms "
            r"\(jurisdiction=(?P<juris>[^,]*), temporal=(?P<temporal>[^,]*), "
            r"cap=(?P<cap>[^/]*)/norm\)$"
        ),
        "stage2",
        lambda m: {
            "n_components": _int(m.group("n")),
            "n_norms": _int(m.group("m")),
            "jurisdiction": _none(m.group("juris")),
            "temporal": _none(m.group("temporal")),
            "cap_per_norm": _int(m.group("cap")),
        },
    ),
    (
        re.compile(
            r"^Stage 2: norm '(?P<norm>[^']*)' có (?P<n>\d+) components → "
            r"capped xuống (?P<cap>\d+)$"
        ),
        "stage2",
        lambda m: {
            "norm_id": m.group("norm"),
            "n_components": _int(m.group("n")),
            "cap": _int(m.group("cap")),
        },
    ),
    (
        re.compile(r"^extract_subgraph \[dense-only\]: (?P<rest>.*)$"),
        "stage2",
        lambda m: {"dense_only": True},
    ),
    (
        re.compile(r"^run_pipeline: extract_subgraph$"),
        "stage2",
        lambda m: {},
    ),
    # --- Stage 3 ---------------------------------------------------------
    (
        re.compile(
            r"^Stage 3: (?P<n>\d+) graph_component_ids mapped for procedure "
            r"(?P<proc>.*)$"
        ),
        "stage3",
        lambda m: {
            "n_components": _int(m.group("n")),
            "procedure": _none(m.group("proc")),
        },
    ),
    (
        re.compile(
            r"^run_pipeline: (?P<n>\d+) norm_ids, (?P<m>\d+) graph_comp_ids "
            r"từ Stage 2\+3$"
        ),
        "stage3",
        lambda m: {
            "n_norm_ids": _int(m.group("n")),
            "n_graph_comp_ids": _int(m.group("m")),
        },
    ),
    # --- Hybrid search ---------------------------------------------------
    (
        re.compile(
            r"^hybrid_search Path -1 \(struct cite\): cites=(?P<cites>.*) → "
            r"(?P<comps>\d+) comps → (?P<tus>\d+) text_units$"
        ),
        "hybrid",
        lambda m: {
            "struct_cites": _lit(m.group("cites"), []),
            "n_components": _int(m.group("comps")),
            "n_text_units": _int(m.group("tus")),
        },
    ),
    (
        re.compile(
            r"^hybrid_search: dense=(?P<d>\d+), keyword=(?P<k>\d+), "
            r"graph=(?P<g>\d+) candidates$"
        ),
        "hybrid",
        lambda m: {
            "dense": _int(m.group("d")),
            "keyword": _int(m.group("k")),
            "graph": _int(m.group("g")),
        },
    ),
    (
        re.compile(
            r"^hybrid_search: rarity stats — (?P<n>\d+) norms, (?P<m>\d+) "
            r"components mapped, (?P<k>\d+) required concepts$"
        ),
        "hybrid",
        lambda m: {
            "n_norms": _int(m.group("n")),
            "n_components_mapped": _int(m.group("m")),
            "n_required_concepts": _int(m.group("k")),
        },
    ),
    (
        re.compile(r"^hybrid_search: tất cả các path đều rỗng$"),
        "hybrid",
        lambda m: {"rong": True},
    ),
    (
        re.compile(
            r"^hybrid_search: top-(?P<topk>\d+) \| "
            r"pass-1\(struct-cite\)=(?P<p_struct>\d+), "
            r"pass-0\.5\(label-keyword\)=(?P<p_label>\d+), "
            r"pass0\(dense-floor\)=(?P<p_dense>\d+), "
            r"pass1\(rrf-breadth\)=(?P<p_breadth>\d+), "
            r"pass2\(depth\)=(?P<p_depth>\d+) \| "
            r"caps: per_norm=(?P<per_norm>\d+), per_tier=(?P<per_tier>\{.*?\}) \| "
            r"best rrf=(?P<best>[\d.]+) \| "
            r"tier_dist=(?P<tier_dist>\{.*?\}) \| norm_dist=(?P<norm_dist>\{.*\})$"
        ),
        "hybrid",
        lambda m: {
            "top_k": _int(m.group("topk")),
            "passes": {
                "struct_cite": _int(m.group("p_struct")),
                "label_keyword": _int(m.group("p_label")),
                "dense_floor": _int(m.group("p_dense")),
                "rrf_breadth": _int(m.group("p_breadth")),
                "depth": _int(m.group("p_depth")),
            },
            "caps": {
                "per_norm": _int(m.group("per_norm")),
                "per_tier": _lit(m.group("per_tier"), {}),
            },
            "best_rrf": _float(m.group("best")),
            "tier_dist": _lit(m.group("tier_dist"), {}),
            "norm_dist": _lit(m.group("norm_dist"), {}),
        },
    ),
    (
        re.compile(r"^run_pipeline: (?P<n>\d+) scored units$"),
        "hybrid",
        lambda m: {"n_scored_units": _int(m.group("n"))},
    ),
    (
        re.compile(r"^run_pipeline: hybrid_search$"),
        "hybrid",
        lambda m: {},
    ),
    # --- Context assembly ------------------------------------------------
    (
        re.compile(
            r"^assemble_context: dừng tại (?P<n>\d+) blocks "
            r"\((?P<used>\d+)/(?P<max>\d+) tokens\)$"
        ),
        "context",
        lambda m: {
            "n_blocks": _int(m.group("n")),
            "tokens": _int(m.group("used")),
            "max_tokens": _int(m.group("max")),
            "bi_cat": True,
        },
    ),
    (
        re.compile(r"^assemble_context: (?P<n>\d+) blocks, ~(?P<tokens>\d+) tokens$"),
        "context",
        lambda m: {
            "n_blocks": _int(m.group("n")),
            "tokens": _int(m.group("tokens")),
        },
    ),
    (
        re.compile(r"^run_pipeline: assemble_context$"),
        "context",
        lambda m: {},
    ),
    # --- Answer generation -----------------------------------------------
    (
        re.compile(r"^generate_answer: cache HIT \((?P<key>[^)]*)\) — \$0 API$"),
        "generate",
        lambda m: {"cache_hit": True, "cache_key": m.group("key")},
    ),
    (
        re.compile(
            r"^generate_answer: (?P<chars>\d+) chars, (?P<cits>\d+) citations, "
            r"sections=(?P<sections>\{.*\})$"
        ),
        "generate",
        lambda m: {
            "n_chars": _int(m.group("chars")),
            "n_citations": _int(m.group("cits")),
            "sections": _lit(m.group("sections"), {}),
            "cache_hit": False,
        },
    ),
    (
        re.compile(r"^run_pipeline: generate_answer$"),
        "generate",
        lambda m: {},
    ),
    (
        re.compile(r"^generate_answer: context rỗng.*$"),
        "generate",
        lambda m: {"context_rong": True},
    ),
    # --- Verifier --------------------------------------------------------
    (
        re.compile(
            r"^run_pipeline: verifier tier=(?P<tier>\d+) (?P<n_in>\d+)→"
            r"(?P<n_kept>\d+) citations \(drop (?P<drop>\d+), flag (?P<flag>\d+)\)$"
        ),
        "verify",
        lambda m: {
            "tier": _int(m.group("tier")),
            "n_input": _int(m.group("n_in")),
            "n_kept": _int(m.group("n_kept")),
            "n_dropped": _int(m.group("drop")),
            "n_flagged": _int(m.group("flag")),
        },
    ),
    (
        re.compile(
            r"^verify_citations: tier=(?P<tier>\d+) in=(?P<n_in>\d+) "
            r"kept=(?P<n_kept>\d+) dropped=(?P<drop>\d+) flagged=(?P<flag>\d+)$"
        ),
        "verify",
        lambda m: {
            "tier": _int(m.group("tier")),
            "n_input": _int(m.group("n_in")),
            "n_kept": _int(m.group("n_kept")),
            "n_dropped": _int(m.group("drop")),
            "n_flagged": _int(m.group("flag")),
        },
    ),
    # --- Hoàn thành ------------------------------------------------------
    (
        re.compile(
            r"^run_pipeline: hoàn thành trong (?P<sec>[\d.]+)s — "
            r"(?P<n>\d+) citations$"
        ),
        "done",
        lambda m: {
            "elapsed_seconds": _float(m.group("sec")),
            "n_citations": _int(m.group("n")),
        },
    ),
]

# Suy `step` từ tên logger khi không regex nào khớp (spec mục 5.1).
_LOGGER_STEPS: list[tuple[str, str]] = [
    ("query_planner", "plan"),
    ("subgraph_extractor", "stage2"),
    ("semantic_filter", "hybrid"),
    ("reranker", "hybrid"),
    ("context_assembler", "context"),
    ("answer_generator", "generate"),
    ("verifier", "verify"),
]


def _temporal_tu_reason(reason: str) -> str | None:
    """Rút ngày ISO đã resolve từ phần lý do: 'strict date=2024-12-31'."""
    m = re.search(r"date=(\d{4}-\d{2}-\d{2})", reason)
    return m.group(1) if m else None


def _stage1_data(
    *,
    top_n: int | None,
    scores: list,
    threshold: float | None,
    norm_ids: list,
    no_theme: bool,
) -> dict:
    scores = [s for s in scores if isinstance(s, (int, float))]
    norm_ids = [str(n) for n in norm_ids]
    return {
        "top_n": top_n,
        "scores": scores,
        "threshold": threshold,
        "norm_ids": norm_ids,
        "n_norms": len(norm_ids),
        "no_theme": no_theme,
        "ranked": pair_stage1(scores, norm_ids, threshold),
    }


def parse_message(name: str, msg: str) -> tuple[str | None, dict]:
    """Phân loại một dòng log thành `(step, data)`.

    Args:
        name: tên logger (`record.name`), VD 'src.retrieval.semantic_filter'.
        msg: message đã format (`record.getMessage()`).

    Returns:
        (step, data). `step is None` nghĩa là không nhận dạng được cả regex lẫn
        tên logger → caller nên gán bước hiện hành (`TraceCollector` làm việc
        này). `data` rỗng khi không parse được, nhưng event vẫn phải phát ra
        kèm `raw` — không được im lặng bỏ.
    """
    text = (msg or "").strip()
    for pattern, step, build in _PATTERNS:
        m = pattern.match(text)
        if m:
            try:
                return step, build(m)
            except Exception as e:  # regex khớp nhưng dữ liệu lạ — vẫn phát event
                logger.debug(f"parse_message: dựng data lỗi ({e}) cho {text!r}")
                return step, {}

    for needle, step in _LOGGER_STEPS:
        if needle in (name or ""):
            return step, {}

    return None, {}


# ---------------------------------------------------------------------------
# TraceCollector
# ---------------------------------------------------------------------------

class TraceCollector(logging.Handler):
    """`logging.Handler` biến log record của `src` thành `TraceEvent` trong queue.

    **MỖI REQUEST MỘT COLLECTOR** — dùng `gan_collector()` để tự động
    `removeHandler` trong `finally` (spec mục 2.3):

        with gan_collector() as collector:
            ...  # chạy pipeline, đọc collector.queue

    KHÔNG dùng chung một collector cho nhiều request rồi `reset()`:
    `logging.getLogger("src")` là toàn cục theo process nên hai request chồng
    nhau sẽ trộn event vào cùng queue, và `reset()` của request sau làm `t` của
    request trước âm, `seq` nhảy lùi. Quên `removeHandler` thì handler tích lũy
    → event nhân bản. `/api/ask` còn phải được serialize bằng lock cấp module.

    Pipeline chạy trong thread riêng, generator SSE đọc `collector.queue`.
    """

    def __init__(self, event_queue: "queue.Queue[TraceEvent]" | None = None,
                 level: int = logging.INFO):
        super().__init__(level=level)
        self.queue: "queue.Queue[TraceEvent]" = event_queue or queue.Queue()
        self._lock = threading.Lock()
        self._seq = 0
        self._t0 = time.perf_counter()
        self._step = "question"   # bước hiện hành, dùng khi không nhận dạng được

    # -- vòng đời request --------------------------------------------------

    def reset(self) -> None:
        """Đặt lại mốc thời gian + số thứ tự.

        CHỈ dùng khi collector chưa gắn vào logger (VD test). Với request thật,
        tạo collector mới qua `gan_collector()` thay vì reset — xem docstring lớp.
        """
        with self._lock:
            self._seq = 0
            self._t0 = time.perf_counter()
            self._step = "question"

    def elapsed(self) -> float:
        return time.perf_counter() - self._t0

    # -- phát event --------------------------------------------------------

    def push(
        self,
        step: str,
        kind: str = "log",
        data: dict | None = None,
        raw: str = "",
    ) -> TraceEvent:
        """Phát một event thủ công (bước `question`, `result`, `error`, `done`)."""
        with self._lock:
            seq = self._seq
            self._seq += 1
            if step in STEPS:
                self._step = step
            t = time.perf_counter() - self._t0
        event = TraceEvent(
            seq=seq,
            t=round(t, 3),
            step=step,
            kind=kind if kind in KINDS else "log",
            raw=raw,
            data=data or {},
        )
        self.queue.put(event)
        return event

    def emit(self, record: logging.LogRecord) -> None:
        """Bắt MỌI record INFO của logger `src` → TraceEvent."""
        try:
            msg = record.getMessage()
            step, data = parse_message(record.name, msg)
            if step is None:
                step = self._step   # không nhận dạng được → gắn vào bước hiện hành
            self.push(step, kind="log", data=data, raw=msg)
        except Exception:
            self.handleError(record)

    def drain(self) -> list[TraceEvent]:
        """Lấy hết event đang có trong queue (không chặn)."""
        events: list[TraceEvent] = []
        while True:
            try:
                events.append(self.queue.get_nowait())
            except queue.Empty:
                return events


@contextmanager
def gan_collector(
    logger_name: str = "src",
    level: int = logging.INFO,
) -> "Iterator[TraceCollector]":
    """Gắn một `TraceCollector` MỚI vào logger cho ĐÚNG một request.

    Luôn `removeHandler` + trả lại mức log cũ trong `finally`, kể cả khi pipeline
    ném exception hay client ngắt kết nối giữa chừng (spec mục 2.3).
    """
    collector = TraceCollector()
    log = logging.getLogger(logger_name)
    muc_cu = log.level
    log.setLevel(min(level, muc_cu) if muc_cu else level)
    log.addHandler(collector)
    try:
        yield collector
    finally:
        log.removeHandler(collector)
        log.setLevel(muc_cu)


# ---------------------------------------------------------------------------
# Parse context string (spec mục 5.2)
# ---------------------------------------------------------------------------

_HEADER_RE = re.compile(r"^---\s(?P<label>.*?)\s---$", re.MULTILINE)
_META_RE = re.compile(r"^\[(?P<meta>[^\]]*)\]\s*(?P<base>.*)$", re.DOTALL)
_TIER_RE = re.compile(r"Tier\s+(\d+)")
_HIEU_LUC_RE = re.compile(
    r"Hiệu lực:\s*(?P<tu>\d{4}-\d{2}-\d{2})"
    r"(?:\s*→\s*(?P<den>\d{4}-\d{2}-\d{2}))?"
)
_BASE_RE = re.compile(r"^(?P<vi_tri>.+)\s\((?P<norm>[^()]+)\)$")
_AMEND_HEADER = "[AMENDMENT WARNING"
_AMEND_ITEM_RE = re.compile(
    r"^\s+-\s+(?P<norm>.+?)\s\((?P<loc>.*?),\s*hiệu lực\s+(?P<date>.*?)\):\s?(?P<summary>.*)$"
)

VALID_TO_SENTINEL = "9999-12-31"   # còn hiệu lực → không in mũi tên


def parse_label(label: str) -> dict:
    """Parse nhãn block context (3 dạng, xem spec mục 5.2).

        [Tier 4 | Hiệu lực: 2024-09-30] Điều 3, Khoản 1 (quyet-dinh-69-...)
        [Tier 1 | Hiệu lực: 2014-07-01 → 2025-01-01 (HẾT HIỆU LỰC)] Điều 95 (luat-dat-dai-2013)
        luat-dat-dai-2024
    """
    label = (label or "").strip()
    tier: int | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    het_hieu_luc = False

    base = label
    m = _META_RE.match(label)
    if m:
        meta, base = m.group("meta"), m.group("base").strip()
        mt = _TIER_RE.search(meta)
        if mt:
            tier = _int(mt.group(1))
        mh = _HIEU_LUC_RE.search(meta)
        if mh:
            valid_from = mh.group("tu")
            den = mh.group("den")
            if den and den != VALID_TO_SENTINEL:
                valid_to = den
        het_hieu_luc = "HẾT HIỆU LỰC" in meta

    mb = _BASE_RE.match(base)
    if mb:
        vi_tri = mb.group("vi_tri").strip()
        norm_id = mb.group("norm").strip()
    else:
        # `context_path` rỗng → nhãn chỉ là norm slug, không có vị trí.
        vi_tri = ""
        norm_id = base.strip()

    return {
        "label": label,
        "tier": tier,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "het_hieu_luc": het_hieu_luc,
        "vi_tri": vi_tri,
        "norm_id": norm_id,
    }


def _parse_amendments(body: str) -> tuple[list[dict], str]:
    """Tách block cảnh báo sửa đổi ở đầu body → (amendments, nguyên văn còn lại)."""
    lines = body.split("\n")
    if not lines or not lines[0].lstrip().startswith(_AMEND_HEADER):
        return [], body

    amendments: list[dict] = []
    i = 1
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        m = _AMEND_ITEM_RE.match(line)
        if m:
            amendments.append({
                "amending_norm": m.group("norm").strip(),
                "amending_loc": m.group("loc").strip(),
                "effective_date": m.group("date").strip(),
                "content_summary": m.group("summary").strip(),
            })
            i += 1
            continue
        # Dòng thụt lề tiếp theo = phần nối của content_summary xuống dòng.
        if line.startswith(" ") and amendments:
            amendments[-1]["content_summary"] = (
                f"{amendments[-1]['content_summary']} {line.strip()}".strip()
            )
            i += 1
            continue
        break   # dòng không thụt lề đầu tiên → bắt đầu nguyên văn

    return amendments, "\n".join(lines[i:]).strip()


def parse_context(context_str: str) -> list[ContextBlock]:
    """Parse chuỗi context do `assemble_context()` ghép → list ContextBlock.

    Thứ tự block giữ nguyên = thứ tự rrf giảm dần (spec mục 3.1). KHÔNG suy ra
    rrf_score hay pass của từng block — `PipelineResult` không chứa dữ liệu đó.
    """
    if not context_str or not context_str.strip():
        return []

    blocks: list[ContextBlock] = []
    matches = list(_HEADER_RE.finditer(context_str))
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(context_str)
        body = context_str[start:end].strip("\n")
        amendments, text = _parse_amendments(body)
        info = parse_label(m.group("label"))
        blocks.append(ContextBlock(
            index=i,
            label=info["label"],
            tier=info["tier"],
            valid_from=info["valid_from"],
            valid_to=info["valid_to"],
            het_hieu_luc=info["het_hieu_luc"],
            vi_tri=info["vi_tri"],
            norm_id=info["norm_id"],
            amendments=amendments,
            text=text.strip(),
            raw=context_str[m.start():end].strip(),
        ))
    return blocks


# ---------------------------------------------------------------------------
# Nối citation → block (spec mục 5.3)
# ---------------------------------------------------------------------------

_VT_DIEU_RE = re.compile(r"(?:^|,\s*)Điều\s+(?P<so>[^.\s,]+)\.?", re.IGNORECASE)
_VT_PHU_LUC_RE = re.compile(r"(?:^|,\s*)Phụ\s*lục\s*(?P<so>[^.\s,\-]*)", re.IGNORECASE)
_VT_KHOAN_RE = re.compile(r"(?:^|,\s*)Khoản\s+(?P<so>[^.\s,]+)\.?", re.IGNORECASE)
_VT_DIEM_RE = re.compile(r"(?:^|,\s*)Điểm\s+(?P<so>[^.\s,]+)\.?", re.IGNORECASE)
_VT_TIET_RE = re.compile(r"(?:^|,\s*)Tiết\s+(?P<so>[^.\s,]+)\.?", re.IGNORECASE)

PHU_LUC_DEFAULT = "_default"   # sentinel Phụ lục không đánh số (parse_citations)


def _chuan(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split()).strip().rstrip(".").lower()
    return text or None


def parse_vi_tri(vi_tri: str) -> dict:
    """Tách vị trí pháp lý trong nhãn block → {loai, dieu, khoan, diem, tiet}.

    Lưu ý 1: tiêu đề Điều có thể chứa dấu phẩy ("Điều 1. Quy định hạn mức ... hộ
    gia đình, cá nhân ..., Khoản 1., Điểm b.") nên KHÔNG tách bằng `split(', ')`
    mà dò từng nhãn cấp bằng regex.

    Lưu ý 2: nhãn được ghép `", ".join(context_path[1:])` → cấp sâu LUÔN nằm ở
    CUỐI. Với Khoản/Điểm/Tiết phải lấy match CUỐI, vì tiêu đề Điều của văn bản
    sửa đổi hay chứa sẵn chuỗi dạng ", Khoản X" ("Điều 1. Sửa đổi Điều 5,
    Khoản 3 của Nghị định…, Khoản 2." — corpus có nhiều VB sửa đổi: NĐ 226 sửa
    NĐ 112, NQ 254 sửa Luật ĐĐ). Cấp Điều/Phụ lục ngược lại: lấy match ĐẦU vì
    nó luôn là phần tử đầu của context_path.
    """
    text = vi_tri or ""
    loai = "dieu"
    so: str | None = None

    m = _VT_DIEU_RE.search(text)
    if m:
        so = m.group("so")
    else:
        m = _VT_PHU_LUC_RE.search(text)
        if m:
            loai = "phu_luc"
            so = m.group("so") or PHU_LUC_DEFAULT

    def _grab(pattern: re.Pattern) -> str | None:
        matches = list(pattern.finditer(text))
        return matches[-1].group("so") if matches else None

    return {
        "loai": loai if so is not None else None,
        "dieu": _chuan(so),
        "khoan": _chuan(_grab(_VT_KHOAN_RE)),
        "diem": _chuan(_grab(_VT_DIEM_RE)),
        "tiet": _chuan(_grab(_VT_TIET_RE)),
    }


_CAP_CON = ("khoan", "diem", "tiet")
_TEN_CAP = {"dieu": "Điều", "phu_luc": "Phụ lục", "khoan": "Khoản",
            "diem": "Điểm", "tiet": "Tiết"}


def _cap_sau_nhat(vt: dict) -> str:
    """Tên cấp sâu nhất mà block thật sự có ('Khoản', 'Điểm'…)."""
    ten = _TEN_CAP.get(vt.get("loai") or "dieu", "Điều")
    for cap in _CAP_CON:
        if vt.get(cap) is not None:
            ten = _TEN_CAP[cap]
    return ten


def _chu_thich_gan_dung(citation: dict, vt: dict) -> str:
    """Nêu ĐÚNG cấp bị lệch giữa citation và block, thay vì câu chung chung.

    Hai kiểu lệch quan sát được trên dữ liệu thật:
      - citation nêu sâu hơn block (Điểm a trong khi block dừng ở Khoản 1);
      - citation nêu cùng cấp nhưng khác số (Khoản 9 vs Khoản 3).
    """
    for cap in _CAP_CON:
        c_val = _chuan(citation.get(cap))
        if c_val is None or c_val == vt.get(cap):
            continue
        ten = _TEN_CAP[cap]
        goc = str(citation.get(cap)).strip()
        if vt.get(cap) is None:
            return (
                f"khớp gần đúng — context chỉ tới cấp {_cap_sau_nhat(vt)}, "
                f"citation nêu {ten} {goc}"
            )
        return (
            f"khớp gần đúng — context ở {ten} {vt[cap]}, citation nêu {ten} {goc}"
        )
    return "khớp gần đúng"


def _so_khop(citation: dict, vt: dict) -> tuple[int, int, bool] | None:
    """So một citation với vị trí của một block.

    Returns:
        (n_khop, n_du, khop_het) hoặc None nếu khác loại/khác Điều (không nối được).
        - n_khop: số cấp citation nêu ra mà block khớp (luôn ≥ 1 vì đã khớp Điều).
        - n_du: số cấp block có mà citation không nêu — dùng ưu tiên block
          nông hơn khi citation chỉ nêu tới Điều.
        - khop_het: mọi cấp citation nêu ra đều khớp → 'chinh-xac'.
    """
    c_loai = "phu_luc" if citation.get("loai") == "phu_luc" else "dieu"
    if vt["loai"] != c_loai or vt["dieu"] is None:
        return None

    c_dieu = _chuan(citation.get("dieu"))
    if c_loai == "phu_luc":
        # '_default' = Phụ lục không đánh số → khớp mọi Phụ lục của văn bản đó.
        if c_dieu not in (None, PHU_LUC_DEFAULT) and c_dieu != vt["dieu"]:
            return None
    elif c_dieu != vt["dieu"]:
        return None

    n_khop = 1          # đã khớp cấp Điều / Phụ lục
    n_yeu_cau = 1
    for cap in _CAP_CON:
        c_val = _chuan(citation.get(cap))
        if c_val is None:
            continue    # citation không nêu cấp này
        n_yeu_cau += 1
        if c_val == vt[cap]:
            n_khop += 1

    n_du = sum(
        1 for cap in _CAP_CON
        if vt[cap] is not None and _chuan(citation.get(cap)) is None
    )
    return n_khop, n_du, n_khop == n_yeu_cau


def link_citations(citations: list[dict], blocks: list[ContextBlock]) -> list[dict]:
    """Nối mỗi citation với block context tương ứng (khớp lỏng, spec mục 5.3).

    Returns:
        list dict {citation, block_index, khop, chu_thich} theo đúng thứ tự
        `citations`. `khop` ∈ 'chinh-xac' | 'gan-dung' | 'khong-tim-thay'.
        Citation không khớp block nào là TÍN HIỆU THẬT (LLM cite ngoài context),
        không phải bug cần che.
    """
    vi_tri_blocks = [
        (b, parse_vi_tri(b.get("vi_tri", "")), _chuan(b.get("norm_id")))
        for b in blocks
    ]

    ket_qua: list[dict] = []
    for c in citations or []:
        van_ban = _chuan(c.get("van_ban"))
        best_index: int | None = None
        best_key: tuple[int, int] | None = None
        best_khop_het = False
        best_vt: dict | None = None

        for block, vt, norm_id in vi_tri_blocks:
            if van_ban is None or norm_id != van_ban:
                continue
            ket = _so_khop(c, vt)
            if ket is None:
                continue
            n_khop, n_du, khop_het = ket
            # Ưu tiên: khớp sâu nhất → block ít cấp thừa nhất → block đứng trước
            # (thứ tự block = rrf giảm dần).
            key = (n_khop, -n_du)
            if best_key is None or key > best_key:
                best_key, best_index = key, block["index"]
                best_khop_het, best_vt = khop_het, vt

        if best_index is None:
            khop, chu_thich = "khong-tim-thay", "không tìm thấy trong context"
        elif best_khop_het:
            khop, chu_thich = "chinh-xac", "khớp đúng vị trí trong context"
        else:
            khop, chu_thich = "gan-dung", _chu_thich_gan_dung(c, best_vt or {})

        ket_qua.append({
            "citation": c,
            "block_index": best_index,
            "khop": khop,
            "chu_thich": chu_thich,
        })
    return ket_qua
