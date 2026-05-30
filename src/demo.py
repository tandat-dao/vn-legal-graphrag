"""
Demo CLI — input câu hỏi, output pretty answer + citations cho weekly meeting.

Sử dụng `rich` cho UX đẹp: spinner trong khi pipeline chạy, markdown render
cho answer text, table cho citations, tree view cho pipeline trace.

Usage:
    python -m src.demo "Hạn mức giao đất ở TP.HCM tối đa bao nhiêu?"
    python -m src.demo "..." --trace            # hiện chi tiết pipeline trace
    python -m src.demo "..." --jurisdiction tp-hcm   # force jurisdiction
    python -m src.demo "..." --no-llm-cache     # bypass cache
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

# Single global console — auto-detect color/terminal width
console = Console()


# ---------------------------------------------------------------------------
# Trace log handler
# ---------------------------------------------------------------------------

class _TraceHandler(logging.Handler):
    """Capture log INFO records cho trace display."""
    def __init__(self):
        super().__init__(level=logging.INFO)
        self.records: list[str] = []

    def emit(self, record):
        msg = record.getMessage()
        if any(kw in msg for kw in (
            "plan_query", "Stage 1", "Stage 2", "Stage 3", "hybrid_search",
            "assemble_context", "generate_answer", "run_pipeline", "Pass -",
            "TEMPORAL", "force_jurisdiction"
        )):
            self.records.append(msg)


# ---------------------------------------------------------------------------
# Pretty formatting helpers
# ---------------------------------------------------------------------------

def _fmt_cit_text(c: dict) -> str:
    """Định dạng vị trí citation: 'Điều 3 Khoản 1 Điểm a'."""
    parts = []
    if c.get("dieu"):
        parts.append(f"Điều {c['dieu']}")
    if c.get("khoan"):
        parts.append(f"Khoản {c['khoan']}")
    if c.get("diem"):
        parts.append(f"Điểm {c['diem']}")
    if c.get("tiet"):
        parts.append(f"Tiết {c['tiet']}")
    return " ".join(parts) if parts else "(không rõ vị trí)"


def _build_trace_tree(records: list[str]) -> Tree:
    """Group log records vào Tree theo pipeline stage."""
    tree = Tree("🔍 [bold cyan]PIPELINE TRACE[/bold cyan]")
    # Group theo prefix
    groups = {
        "📋 Query Plan": [],
        "🔎 Stage 1 — Norm seed (Qdrant summary)": [],
        "📊 Stage 2 — Graph traversal": [],
        "🧩 Stage 3 — Procedure mapping": [],
        "⚙️  Hybrid Search (4-pass)": [],
        "📝 Context + Generation": [],
        "🕒 TEMPORAL Layer": [],
    }
    for r in records:
        msg = r.split(":", 1)[-1].strip() if ":" in r else r
        if "plan_query" in msg or "force_jurisdiction" in msg or "backfill" in msg:
            groups["📋 Query Plan"].append(msg)
        elif "Stage 1" in msg:
            groups["🔎 Stage 1 — Norm seed (Qdrant summary)"].append(msg)
        elif "Stage 2" in msg:
            groups["📊 Stage 2 — Graph traversal"].append(msg)
        elif "Stage 3" in msg:
            groups["🧩 Stage 3 — Procedure mapping"].append(msg)
        elif "hybrid_search" in msg or "Pass -" in msg or "Path -" in msg:
            groups["⚙️  Hybrid Search (4-pass)"].append(msg)
        elif "assemble_context" in msg or "generate_answer" in msg:
            groups["📝 Context + Generation"].append(msg)
        elif "TEMPORAL" in msg:
            groups["🕒 TEMPORAL Layer"].append(msg)
        elif "run_pipeline" in msg:
            # Skip overall meta logs
            continue
    for group_name, items in groups.items():
        if not items:
            continue
        branch = tree.add(f"[bold]{group_name}[/bold]")
        for item in items:
            # Truncate long messages
            if len(item) > 130:
                item = item[:127] + "…"
            branch.add(Text(item, style="dim"))
    return tree


def _build_citations_table(citations: list[dict], with_marker: bool = True) -> Table:
    """Build rich Table cho list citations."""
    table = Table(show_header=True, header_style="bold magenta", box=None)
    if with_marker:
        table.add_column("", width=2)
    table.add_column("Vị trí", style="cyan", no_wrap=False)
    table.add_column("Văn bản", style="green")
    for c in citations:
        row = []
        if with_marker:
            row.append("✓")
        row.append(_fmt_cit_text(c))
        row.append(c.get("van_ban", "?"))
        table.add_row(*row)
    return table


def _build_stats_table(result: dict, total_time: float) -> Table:
    """Build stats table."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Metric", style="dim")
    table.add_column("Value")
    table.add_row("LCCIDs (Components)", str(result.get("lccids_count", 0)))
    table.add_row("Top-k retrieved", str(result.get("top_k_count", 0)))
    table.add_row("Context tokens", f"~{result.get('context_tokens', 0)}")
    table.add_row("Context used", "✓" if result.get("context_used") else "✗")
    table.add_row("Tổng thời gian", f"[bold]{total_time:.1f}s[/bold]")
    return table


# ---------------------------------------------------------------------------
# Output rendering
# ---------------------------------------------------------------------------

def _render_result(question: str, result: dict, total_time: float,
                   show_trace: bool, trace_records: list[str]) -> None:
    """Render kết quả với rich panels."""
    # Câu hỏi panel
    console.print()
    console.print(Panel(
        Text(question, style="bold"),
        title="🔍 [bold cyan]CÂU HỎI[/bold cyan]",
        border_style="cyan",
        expand=False,
    ))

    # Confirmation needed case — render markdown để khung hướng dẫn (bullet/ví dụ)
    # hiển thị gọn gàng.
    if result.get("confirmation_needed"):
        console.print()
        console.print(Panel(
            Markdown(result.get("confirmation_prompt", "(không có prompt)")),
            title="⚠️  [bold yellow]HỆ THỐNG YÊU CẦU XÁC NHẬN[/bold yellow]",
            border_style="yellow",
        ))
        return

    # Trace tree (optional)
    if show_trace and trace_records:
        console.print()
        console.print(_build_trace_tree(trace_records))

    # Answer panel — render markdown
    answer = result.get("answer", "(không có câu trả lời)")
    console.print()
    console.print(Panel(
        Markdown(answer),
        title="📝 [bold green]TRẢ LỜI[/bold green]",
        border_style="green",
        padding=(1, 2),
    ))

    # Citations
    citations = result.get("citations", [])
    console.print()
    if citations:
        console.print(Panel(
            _build_citations_table(citations),
            title=f"📚 [bold blue]CITATIONS ({len(citations)})[/bold blue]",
            border_style="blue",
        ))
    else:
        console.print(Panel(
            Text("(không có citation)", style="dim italic"),
            title="📚 [bold blue]CITATIONS (0)[/bold blue]",
            border_style="blue",
        ))

    # Stats
    console.print()
    console.print(Panel(
        _build_stats_table(result, total_time),
        title="📊 [bold magenta]THỐNG KÊ[/bold magenta]",
        border_style="magenta",
    ))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Demo CLI — câu hỏi pháp luật → câu trả lời có citations",
    )
    parser.add_argument("question", help="Câu hỏi tiếng Việt")
    parser.add_argument("--trace", action="store_true",
                        help="Hiện chi tiết pipeline trace (Tree view)")
    parser.add_argument("--jurisdiction", choices=["toan-quoc", "tp-hcm", "dong-nai"],
                        help="Force jurisdiction (bypass Confirmation Loop)")
    parser.add_argument("--bypass-completeness", action="store_true",
                        help="Bypass kiểm tra đầy đủ field")
    parser.add_argument("--no-llm-cache", action="store_true",
                        help="Tắt LLM cache (luôn gọi API)")
    parser.add_argument("--llm-cache-dir", default="data/evaluation/.llm_cache/",
                        help="Thư mục cache LLM")
    parser.add_argument("--mode", choices=["auto", "general", "irac"], default="auto",
                        help="Chế độ trả lời: auto (planner tự chọn), general (gọn), "
                             "irac (tư vấn chi tiết). Mặc định auto.")
    args = parser.parse_args()

    # Setup logging
    trace_handler = _TraceHandler()
    logging.basicConfig(
        level=logging.WARNING,
        format="%(name)s:%(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )
    if args.trace:
        logging.getLogger("src").setLevel(logging.INFO)
        logging.getLogger("src").addHandler(trace_handler)

    # Run pipeline với spinner + graceful 529 handling
    from src.pipeline import run_pipeline
    import anthropic as _anthropic

    cache_dir = None if args.no_llm_cache else Path(args.llm_cache_dir)
    t_start = time.perf_counter()

    with console.status(
        "[bold cyan]Đang xử lý pipeline...[/bold cyan] "
        "(Stage 1/2/3 → Hybrid Search → LLM generation)",
        spinner="dots",
    ):
        try:
            result = run_pipeline(
                args.question,
                force_jurisdiction=args.jurisdiction,
                bypass_completeness=args.bypass_completeness,
                llm_cache_dir=cache_dir,
                response_mode=None if args.mode == "auto" else args.mode,
            )
        except _anthropic.OverloadedError as e:
            elapsed = time.perf_counter() - t_start
            console.print()
            console.print(Panel(
                Text.from_markup(
                    f"[bold red]Anthropic API 529 Overloaded[/bold red]\n\n"
                    f"Lỗi: {e}\n\n"
                    f"[dim]Gợi ý: thử lại sau vài phút. Cache đã được populate cho\n"
                    f"các câu hỏi đã chạy trước đây — chỉ câu mới phụ thuộc API live.[/dim]\n\n"
                    f"Total elapsed: {elapsed:.1f}s"
                ),
                title="⚠️  [bold red]ANTHROPIC API OUTAGE[/bold red]",
                border_style="red",
            ))
            return 1
        except _anthropic.APIStatusError as e:
            console.print()
            console.print(f"[bold red]⚠️  Anthropic API Error:[/bold red] {e}")
            return 1

    elapsed = time.perf_counter() - t_start
    _render_result(args.question, result, elapsed, args.trace, trace_handler.records)
    return 0


if __name__ == "__main__":
    sys.exit(main())
