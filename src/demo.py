"""
Demo CLI — input câu hỏi, output pretty answer + citations cho weekly meeting.

Usage:
    python -m src.demo "Hạn mức giao đất ở TP.HCM tối đa bao nhiêu?"
    python -m src.demo "..." --trace            # hiện chi tiết pipeline trace
    python -m src.demo "..." --jurisdiction tp-hcm   # force jurisdiction
    python -m src.demo "..." --no-llm-cache     # bypass cache

Mục đích: weekly report cho giảng viên hướng dẫn — hình dung được hệ thống
xử lý 1 câu hỏi ra sao, không cần đọc JSON dài.
"""
from __future__ import annotations

import argparse
import io
import logging
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Bắt log để parse cho --trace mode
_log_buffer = io.StringIO()


class _TraceHandler(logging.Handler):
    """Capture log INFO records cho trace display."""
    def __init__(self):
        super().__init__(level=logging.INFO)
        self.records: list[str] = []

    def emit(self, record):
        msg = record.getMessage()
        # Chỉ giữ log liên quan retrieval/generation
        if any(kw in msg for kw in (
            "plan_query", "Stage 1", "Stage 2", "Stage 3", "hybrid_search",
            "assemble_context", "generate_answer", "run_pipeline", "Pass -",
            "TEMPORAL", "force_jurisdiction"
        )):
            self.records.append(msg)


# ---------------------------------------------------------------------------
# Pretty formatting
# ---------------------------------------------------------------------------

def _fmt_cit(c: dict) -> str:
    """Định dạng citation gọn: Điều 3 Khoản 1 — văn-bản-id."""
    parts = []
    if c.get("dieu"):
        parts.append(f"Điều {c['dieu']}")
    if c.get("khoan"):
        parts.append(f"Khoản {c['khoan']}")
    if c.get("diem"):
        parts.append(f"Điểm {c['diem']}")
    if c.get("tiet"):
        parts.append(f"Tiết {c['tiet']}")
    loc = " ".join(parts) if parts else "(không rõ vị trí)"
    return f"{loc} — {c.get('van_ban', '?')}"


def _print_trace(records: list[str], total_time: float) -> None:
    """In trace records nhóm theo stage."""
    print()
    print("┌─ 🔍 PIPELINE TRACE ─────────────────────────────────────")
    for r in records:
        # Strip module prefix
        msg = r.split(":", 1)[-1].strip() if ":" in r else r
        # Truncate long lines
        if len(msg) > 110:
            msg = msg[:107] + "..."
        print(f"│  {msg}")
    print(f"└─ ⏱  Tổng: {total_time:.1f}s")
    print()


def _print_result(question: str, result: dict, total_time: float, show_trace: bool, trace_records: list[str]) -> None:
    """In kết quả đẹp cho user."""
    print()
    print("═" * 70)
    print(f"🔍 CÂU HỎI: {question}")
    print("═" * 70)

    if result.get("confirmation_needed"):
        print()
        print("⚠️  HỆ THỐNG YÊU CẦU XÁC NHẬN:")
        print(f"   {result.get('confirmation_prompt', '(không có prompt)')}")
        print()
        if show_trace:
            _print_trace(trace_records, total_time)
        return

    if show_trace:
        _print_trace(trace_records, total_time)

    print()
    print("📝 TRẢ LỜI:")
    print("─" * 70)
    # Indent answer cho dễ đọc
    answer = result.get("answer", "(không có câu trả lời)")
    for line in answer.split("\n"):
        print(f"  {line}")

    print()
    print(f"📚 CITATIONS ({len(result.get('citations', []))}):")
    print("─" * 70)
    if result.get("citations"):
        for c in result["citations"]:
            print(f"  • {_fmt_cit(c)}")
    else:
        print("  (không có citation)")

    print()
    print("📊 THỐNG KÊ:")
    print("─" * 70)
    print(f"  LCCIDs (Components): {result.get('lccids_count', 0)}")
    print(f"  Top-k retrieved:     {result.get('top_k_count', 0)}")
    print(f"  Context tokens:      ~{result.get('context_tokens', 0)}")
    print(f"  Context used:        {'✓' if result.get('context_used') else '✗'}")
    print(f"  Tổng thời gian:      {total_time:.1f}s")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Demo CLI — câu hỏi pháp luật → câu trả lời có citations",
    )
    parser.add_argument("question", help="Câu hỏi tiếng Việt")
    parser.add_argument(
        "--trace", action="store_true",
        help="Hiện chi tiết pipeline trace (Stage 1/2/3 + hybrid + LLM)",
    )
    parser.add_argument(
        "--jurisdiction", choices=["toan-quoc", "tp-hcm", "dong-nai"],
        help="Force jurisdiction (bypass Confirmation Loop)",
    )
    parser.add_argument(
        "--bypass-completeness", action="store_true",
        help="Bypass kiểm tra đầy đủ field (chấp nhận query plan thiếu procedure/theme)",
    )
    parser.add_argument(
        "--no-llm-cache", action="store_true",
        help="Tắt LLM cache (luôn gọi API)",
    )
    parser.add_argument(
        "--llm-cache-dir", default="data/evaluation/.llm_cache/",
        help="Thư mục cache LLM (default: data/evaluation/.llm_cache/)",
    )
    args = parser.parse_args()

    # Setup logging
    trace_handler = _TraceHandler()
    logging.basicConfig(
        level=logging.WARNING,  # default quiet
        format="%(name)s:%(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )
    if args.trace:
        # Bắt INFO logs từ src.* modules
        logging.getLogger("src").setLevel(logging.INFO)
        logging.getLogger("src").addHandler(trace_handler)

    # Run pipeline với graceful 529 handling
    from src.pipeline import run_pipeline
    import anthropic as _anthropic

    cache_dir = None if args.no_llm_cache else Path(args.llm_cache_dir)
    t_start = time.perf_counter()
    try:
        result = run_pipeline(
            args.question,
            force_jurisdiction=args.jurisdiction,
            bypass_completeness=args.bypass_completeness,
            llm_cache_dir=cache_dir,
        )
    except _anthropic.OverloadedError as e:
        elapsed = time.perf_counter() - t_start
        print()
        print("═" * 70)
        print("⚠️  ANTHROPIC API OUTAGE (529 Overloaded)")
        print("═" * 70)
        print(f"Lỗi: {e}")
        print(f"\nGợi ý: thử lại sau vài phút. Cache đã được populate cho")
        print(f"các câu hỏi đã chạy thành công trước đây — chỉ câu mới mới")
        print(f"phụ thuộc API live.")
        print(f"\nTotal elapsed: {elapsed:.1f}s")
        return 1
    except _anthropic.APIStatusError as e:
        elapsed = time.perf_counter() - t_start
        print()
        print(f"⚠️  Anthropic API Error: {e}")
        print(f"Total elapsed: {elapsed:.1f}s")
        return 1
    elapsed = time.perf_counter() - t_start

    _print_result(args.question, result, elapsed, args.trace, trace_handler.records)
    return 0


if __name__ == "__main__":
    sys.exit(main())
