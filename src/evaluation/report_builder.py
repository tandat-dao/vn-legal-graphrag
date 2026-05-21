"""
Human-readable report builder cho evaluation.

Sinh ra một file Markdown duy nhất tổng hợp:
  1. Bảng tổng quan các hệ thống (F1, NormRecall, latency, negative)
  2. Bảng so sánh nhanh theo từng câu
  3. Per-question detail: câu hỏi + ground truth + answer text + citations
     có đánh dấu ✅/❌ của TỪNG hệ thống.

Extensible: nhận `results_by_system: dict[str, list[dict]]` — thêm hệ thống mới
(VD "hybrid_v2", "rerank_v1") chỉ cần truyền thêm key, không sửa builder.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from src.evaluation.metrics import aggregate, cit_matches


# ---------------------------------------------------------------------------
# Citation matching — DELEGATE cho metrics.cit_matches để đảm bảo F1 và ✅/❌
# trong report là một định nghĩa khớp duy nhất.
# ---------------------------------------------------------------------------

# Cấp match dùng cho hiển thị ✅/❌. Cố tình KHỚP cấp dùng trong citation_score()
# của runner (level='khoan' — cấp CTV). Nếu sau này runner đổi sang cấp Điều,
# sửa hằng này cùng lúc.
_REPORT_MATCH_LEVEL = "khoan"


def _cit_matches_gt(pred: dict, gt_list: list[dict]) -> dict | None:
    """Trả về GT citation đầu tiên khớp với pred theo `metrics.cit_matches`."""
    for g in gt_list:
        if cit_matches(pred, g, level=_REPORT_MATCH_LEVEL):
            return g
    return None


def _fmt_cit(c: dict) -> str:
    """Hiển thị citation gọn: 'Điều 3 Khoản 1 Điểm a — van-ban-id'."""
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
    vb = c.get("van_ban") or "(không rõ văn bản)"
    return f"{loc} — `{vb}`"


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

_SYS_DISPLAY = {
    "graphrag": "GraphRAG",
    "baseline": "Baseline (Naive RAG)",
}


def _sys_label(name: str) -> str:
    return _SYS_DISPLAY.get(name, name)


def _gap_display(gap: str) -> str:
    return {
        "gap1": "Gap 1 — Đa lĩnh vực",
        "gap2": "Gap 2 — Đa địa phương",
        "gap3": "Gap 3 — Đa tầng văn bản",
        "negative": "Negative — Ngoài phạm vi",
    }.get(gap, gap)


def _trunc(s: str, n: int = 70) -> str:
    s = s.replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def _emoji_f1(f1: float) -> str:
    if f1 >= 0.8:
        return "✅"
    if f1 >= 0.4:
        return "⚠️"
    return "❌"


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _render_overview(aggs: dict[str, dict]) -> str:
    """Bảng overall + per-gap cho tất cả hệ thống."""
    lines = ["## 1. Tổng quan các hệ thống", ""]

    # Header
    header = "| Hệ thống | F1 Khoản | F1 Điều | Norm Recall | Latency TB (s) | Latency P95 (s) |"
    sep = "|---|---|---|---|---|---|"
    rows = [header, sep]
    for sys_name, agg in aggs.items():
        rows.append(
            f"| {_sys_label(sys_name)} "
            f"| {agg.get('f1_mean', 0):.3f} "
            f"| {agg.get('f1_dieu_mean', 0):.3f} "
            f"| {agg.get('norm_recall_mean', 0):.3f} "
            f"| {agg.get('latency_mean_s', 0):.2f} "
            f"| {agg.get('latency_p95_s', 0):.2f} |"
        )
    lines.extend(rows)

    # Negative subset
    neg_systems = {s: a for s, a in aggs.items() if "negative_correct_rate" in a}
    if neg_systems:
        lines.append("")
        lines.append("**Negative handling (câu ngoài phạm vi):**")
        lines.append("")
        lines.append("| Hệ thống | Số câu negative | Tỉ lệ trả lời đúng (rỗng citations) |")
        lines.append("|---|---|---|")
        for sys_name, agg in neg_systems.items():
            lines.append(
                f"| {_sys_label(sys_name)} "
                f"| {agg['negative_count']} "
                f"| {agg['negative_correct_rate']:.0%} |"
            )

    # Per-gap breakdown
    all_gaps: list[str] = []
    for agg in aggs.values():
        for g in agg.get("by_gap", {}).keys():
            if g not in all_gaps:
                all_gaps.append(g)
    if all_gaps:
        lines.append("")
        lines.append("### Phân loại theo Gap (F1 Khoản)")
        lines.append("")
        head_sys = " | ".join(_sys_label(s) for s in aggs.keys())
        lines.append(f"| Gap | # câu | {head_sys} |")
        lines.append("|---|---|" + "---|" * len(aggs))
        for gap in all_gaps:
            # count: lấy từ hệ thống đầu tiên có gap đó
            count = next(
                (agg["by_gap"][gap]["count"] for agg in aggs.values() if gap in agg.get("by_gap", {})),
                0,
            )
            cells = [
                f"{agg.get('by_gap', {}).get(gap, {}).get('f1', 0):.3f}"
                if gap in agg.get("by_gap", {}) else "—"
                for agg in aggs.values()
            ]
            lines.append(f"| {_gap_display(gap)} | {count} | {' | '.join(cells)} |")

    return "\n".join(lines)


def _render_comparison_table(
    test_set: list[dict],
    results_by_system: dict[str, list[dict]],
) -> str:
    """Bảng 1 hàng / 1 câu, mỗi hệ thống 1 cột F1+emoji."""
    lines = ["## 2. So sánh nhanh theo câu", ""]
    sys_names = list(results_by_system.keys())
    # Index per-system result by id
    idx = {s: {r["id"]: r for r in rs} for s, rs in results_by_system.items()}

    head_sys = " | ".join(f"{_sys_label(s)} F1" for s in sys_names)
    lines.append(f"| ID | Câu hỏi | Gap | {head_sys} |")
    lines.append("|---|---|---|" + "---|" * len(sys_names))

    for item in test_set:
        qid = item["id"]
        q_short = _trunc(item["question"], 65)
        cells = []
        for s in sys_names:
            r = idx[s].get(qid)
            if not r:
                cells.append("—")
                continue
            f1 = r.get("citation_score", {}).get("f1", 0)
            cells.append(f"{f1:.2f} {_emoji_f1(f1)}")
        lines.append(
            f"| {qid} | {q_short} | {item.get('gap_type', '?')} | {' | '.join(cells)} |"
        )

    lines.append("")
    lines.append("> ✅ F1 ≥ 0.8 | ⚠️ 0.4–0.8 | ❌ < 0.4")
    return "\n".join(lines)


def _render_pred_citations(pred: list[dict], gt: list[dict]) -> str:
    """List citations dự đoán với ✅ nếu khớp GT, ❌ nếu không."""
    if not pred:
        return "_(không có citation nào)_"
    lines = []
    for c in pred:
        mark = "✅" if _cit_matches_gt(c, gt) else "❌"
        lines.append(f"- {mark} {_fmt_cit(c)}")
    return "\n".join(lines)


def _render_gt_citations(gt: list[dict], pred: list[dict]) -> str:
    """List ground-truth citations với ✅ nếu có ít nhất 1 pred khớp, ❌ nếu bị miss."""
    if not gt:
        return "_(không có — đây là câu negative hoặc tự do)_"
    lines = []
    for g in gt:
        # Reverse: GT này có được pred nào cover không?
        hit = any(_cit_matches_gt(p, [g]) for p in pred)
        mark = "✅" if hit else "❌"
        lines.append(f"- {mark} {_fmt_cit(g)}")
    return "\n".join(lines)


def _render_per_question(
    test_set: list[dict],
    results_by_system: dict[str, list[dict]],
) -> str:
    """Section chi tiết per-question."""
    lines = ["## 3. Chi tiết từng câu", ""]
    idx = {s: {r["id"]: r for r in rs} for s, rs in results_by_system.items()}

    for item in test_set:
        qid = item["id"]
        gt_cits = item.get("ground_truth_citations", [])

        lines.append("---")
        lines.append("")
        lines.append(f"### {qid} — {item['question']}")
        lines.append("")
        lines.append(
            f"**Loại:** {_gap_display(item.get('gap_type', '?'))} "
            f"· **Độ khó:** {item.get('difficulty', '?')} "
            f"· **Theme:** {item.get('theme', '?')} "
            f"· **Jurisdiction:** {item.get('jurisdiction', '?')}"
        )
        lines.append("")

        gt_answer = item.get("ground_truth_answer")
        if gt_answer:
            lines.append("**Đáp án mong muốn (ground truth):**")
            lines.append("")
            lines.append("> " + gt_answer.replace("\n", "\n> "))
            lines.append("")

        # Hiển thị GT citations với ✅/❌ tính tổng hợp giữa các hệ thống không có nghĩa —
        # nên show riêng từng hệ thống bên dưới. Ở đây chỉ liệt kê GT.
        lines.append(f"**Citations mong muốn ({len(gt_cits)}):**")
        if gt_cits:
            for g in gt_cits:
                lines.append(f"- {_fmt_cit(g)}")
        else:
            lines.append("- _(không có — đây là câu negative hoặc không yêu cầu trích dẫn)_")
        lines.append("")

        notes = item.get("notes")
        if notes:
            lines.append(f"**Ghi chú test set:** {notes}")
            lines.append("")

        # Per-system
        for sys_name in results_by_system.keys():
            r = idx[sys_name].get(qid)
            if not r:
                lines.append(f"#### → {_sys_label(sys_name)}: _(không có kết quả)_")
                lines.append("")
                continue

            cs = r.get("citation_score", {})
            cs_dieu = r.get("citation_score_dieu", {})
            f1 = cs.get("f1", 0)
            f1_dieu = cs_dieu.get("f1", 0)
            nr = r.get("norm_recall", 0)
            elapsed = r.get("elapsed_seconds", 0)

            lines.append(
                f"#### → {_sys_label(sys_name)} "
                f"({_emoji_f1(f1)} F1 Khoản={f1:.2f}, "
                f"F1 Điều={f1_dieu:.2f}, NormR={nr:.2f}, {elapsed:.1f}s)"
            )
            lines.append("")

            answer = r.get("answer", "").strip()
            if answer:
                lines.append("<details><summary><strong>Câu trả lời</strong> (bấm để mở/đóng)</summary>")
                lines.append("")
                # Indent answer as blockquote-style? Use details fenced. Keep markdown rendering.
                lines.append(answer)
                lines.append("")
                lines.append("</details>")
            else:
                lines.append("_(không có câu trả lời)_")
            lines.append("")

            lines.append(f"**Citations dự đoán ({len(r.get('pred_citations', []))}):**")
            lines.append(_render_pred_citations(r.get("pred_citations", []), gt_cits))
            lines.append("")

            # GT-side coverage
            if gt_cits:
                lines.append("**Đối chiếu ngược (GT có được cover không?):**")
                lines.append(_render_gt_citations(gt_cits, r.get("pred_citations", [])))
                lines.append("")

            if r.get("confirmation_needed"):
                lines.append("> ⚠️ Hệ thống yêu cầu xác nhận (Confirmation Loop) — câu hỏi thiếu thông tin.")
                lines.append("")
            if r.get("confirmation_retried"):
                lines.append("> ℹ️ Đã retry sau khi tự bổ sung jurisdiction từ test set.")
                lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------

def build_human_report(
    test_set: list[dict],
    results_by_system: dict[str, list[dict]],
    out_path: Path,
    *,
    timestamp: str | None = None,
    test_set_file: str | None = None,
    run_config: dict[str, Any] | None = None,
) -> Path:
    """Sinh report markdown human-readable.

    Args:
        test_set: List item từ test_set_*.json (question + GT).
        results_by_system: Map system_name → per-question results đã có metric.
                           VD {"graphrag": [...], "baseline": [...], "hybrid_v2": [...]}
        out_path: Đường dẫn file .md output.
        timestamp: Hiển thị trong header. Mặc định: now().
        test_set_file: Path test set hiển thị trong header (informational).
        run_config: Dict các flag cấu hình chạy ảnh hưởng kết quả (VD
                    force_jurisdiction, bypass_completeness, llm_cache, top_k...).
                    Hiển thị trong "Cấu hình run" để người đọc biết kết quả đã được
                    sinh dưới điều kiện nào — đảm bảo tính khoa học/reproducibility.

    Returns:
        out_path đã ghi.
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    aggs = {s: aggregate(rs) for s, rs in results_by_system.items()}

    sys_list = ", ".join(_sys_label(s) for s in results_by_system.keys())
    header = [
        f"# Báo cáo Đánh giá — {timestamp}",
        "",
        f"**Test set:** `{test_set_file or '(không rõ)'}`  ",
        f"**Tổng số câu:** {len(test_set)}  ",
        f"**Hệ thống tham gia:** {sys_list}",
        "",
        "> File này được sinh tự động bởi `src/evaluation/report_builder.py` sau mỗi lần "
        "chạy `run_evaluation.py`. Mục đích: cho người đọc (không phải developer) đánh giá "
        "định tính câu trả lời + so sánh các hệ thống cạnh nhau.",
        "",
    ]

    if run_config:
        header.append("**Cấu hình run (ảnh hưởng kết quả — đảm bảo tính reproducible):**")
        header.append("")
        for k, v in run_config.items():
            header.append(f"- `{k}` = `{v}`")
        header.append("")

    body = "\n\n".join([
        _render_overview(aggs),
        _render_comparison_table(test_set, results_by_system),
        _render_per_question(test_set, results_by_system),
    ])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(header) + body + "\n", encoding="utf-8")
    return out_path
