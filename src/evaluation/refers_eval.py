"""
Refers Eval — đo tác động của bao đóng dẫn chiếu [:REFERS_TO] lên TRUY HỒI.

Vì sao không đo qua bộ sinh: câu trả lời của Gemini KHÔNG tất định (D-24 đã ghi
một ca "thắng" hoá ra chỉ là dao động của mô hình). So sánh 4 chế độ qua F1
trích dẫn trên tập nhỏ sẽ lẫn tác dụng thật với nhiễu.

Thay vào đó đo thứ đứng TRƯỚC bộ sinh và tất định: **tỉ lệ điều khoản đáp án
lọt vào ngữ cảnh**. Đây là TRẦN của mọi thứ bộ sinh có thể trích dẫn — nếu bao
đóng dẫn chiếu không nâng được trần này thì nó không thể giúp, khỏi cần chạy
sinh. Nếu nâng được thì mới đáng chạy tiếp.

Bốn chế độ so cùng một lượt (Giai đoạn 1+2 tính MỘT LẦN, dùng chung):
    off    — hành vi hiện tại
    khoan  — chỉ dẫn chiếu đích danh khoản
    all    — cả dẫn chiếu cấp Điều
    rrf    — ĐỐI CHỨNG: thêm cùng số đơn vị nhưng chọn theo RRF

Chạy (trỏ vào BẢN SAO, không đụng CSDL demo):
    NEO4J_URI=bolt://localhost:7688 python -m src.evaluation.refers_eval \
        --test-set data/evaluation/test_set_v2.json --sample 30
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from src.evaluation.metrics import cit_matches
from src.evaluation.retrieval_eval import (
    _build_clients,
    _chunk_to_citation,
    _fetch_chunk_meta,
)
from src.retrieval.query_planner import plan_query
from src.retrieval.semantic_filter import hybrid_search
from src.retrieval.subgraph_extractor import extract_subgraph

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Bộ biến thể so sánh: tên → (refers_mode, per_norm_mode).
# "off" LUÔN phải đứng đầu — mọi Δ đều tính so với nó.
BO_BIEN_THE: dict[str, list[tuple[str, str | None, str | None]]] = {
    # Việc 1 — bao đóng dẫn chiếu, kèm nhánh đối chứng "rrf" để tách bạch
    # "nhờ dẫn chiếu" với "nhờ được thêm ngữ cảnh".
    "refers": [
        ("off", None, None),
        ("khoan", "khoan", None),
        ("all", "all", None),
        ("rrf(đối chứng)", "rrf", None),
    ],
    # Việc 2 — ngân sách chiều sâu theo đồ thị, và phối hợp với việc 1.
    "budget": [
        ("off", None, None),
        ("ngân sách", None, "graph"),
        ("khoan", "khoan", None),
        ("khoan+ngân sách", "khoan", "graph"),
    ],
}


def _do_bao_phu(units: list[dict], gt: list[dict], meta: dict, level: str) -> float:
    """Tỉ lệ trích dẫn đáp án có mặt trong tập đơn vị đã chọn."""
    if not gt:
        return 0.0
    cits = []
    for u in units:
        m = meta.get(u["text_unit_id"], {})
        cits.append(
            _chunk_to_citation(m.get("norm_id") or u.get("norm_id", ""),
                               m.get("context_path", []))
        )
    trung = sum(1 for g in gt if any(cit_matches(c, g, level) for c in cits))
    return trung / len(gt)


def chay(test_set: list[dict], top_k: int = 25,
         bien_the: list[tuple[str, str | None, str | None]] | None = None) -> list[dict]:
    bien_the = bien_the or BO_BIEN_THE["refers"]
    neo4j, qdrant, llm, model = _build_clients()
    rows: list[dict] = []
    try:
        for i, item in enumerate(test_set, 1):
            if item.get("gap_type") == "negative":
                continue
            gt = item.get("ground_truth_citations", [])
            if not gt:
                continue
            q = item["question"]

            # Giai đoạn 1+2 KHÔNG phụ thuộc chế độ → tính một lần, dùng chung.
            plan = dict(plan_query(q, llm, neo4j_driver=neo4j))
            plan["jurisdiction"] = item.get("jurisdiction") or plan.get("jurisdiction")
            norm_ids, graph_comp_ids = extract_subgraph(q, plan, neo4j, qdrant, model)
            if not norm_ids:
                continue

            row = {"id": item["id"], "gap_type": item.get("gap_type")}
            for ten, rmode, pmode in bien_the:
                units = hybrid_search(
                    q, norm_ids, qdrant, model, top_k=top_k,
                    graph_component_ids=graph_comp_ids, neo4j_driver=neo4j,
                    procedure_id=plan.get("procedure"), refers_mode=rmode,
                    per_norm_mode=pmode,
                )
                meta = _fetch_chunk_meta([u["text_unit_id"] for u in units], neo4j)
                row[ten] = {
                    "n": len(units),
                    "khoan": _do_bao_phu(units, gt, meta, "khoan"),
                    "dieu": _do_bao_phu(units, gt, meta, "dieu"),
                }
            rows.append(row)
            print(
                f"[{i}/{len(test_set)}] {item['id']}  "
                + "  ".join(f"{t}={row[t]['khoan']:.2f}({row[t]['n']})"
                            for t, _, _ in bien_the),
                flush=True,
            )
    finally:
        neo4j.close()
    return rows


def tong_hop(rows: list[dict], bien_the) -> None:
    if not rows:
        print("Không có câu nào chạy được.")
        return
    tens = [t for t, _, _ in bien_the]
    print(f"\n{'='*70}")
    print(f"ĐỘ BAO PHỦ ĐIỀU KHOẢN ĐÁP ÁN TRONG NGỮ CẢNH — {len(rows)} câu")
    print(f"{'='*70}")
    print(f"{'biến thể':<20}{'cấp Khoản':>12}{'cấp Điều':>12}{'số đơn vị':>12}{'Δ Khoản':>10}")
    goc = None
    for ten in tens:
        kh = sum(r[ten]["khoan"] for r in rows) / len(rows)
        di = sum(r[ten]["dieu"] for r in rows) / len(rows)
        n = sum(r[ten]["n"] for r in rows) / len(rows)
        delta = "" if goc is None else f"{kh - goc:+.3f}"
        if goc is None:
            goc = kh
        print(f"{ten:<20}{kh:>12.3f}{di:>12.3f}{n:>12.1f}{delta:>10}")

    # Đếm câu thắng/thua so với off — quan trọng hơn trung bình khi N nhỏ
    print(f"\n{'so với off':<20}{'thắng':>8}{'thua':>8}{'hoà':>8}")
    for ten in tens[1:]:
        t = sum(1 for r in rows if r[ten]["khoan"] > r["off"]["khoan"])
        th = sum(1 for r in rows if r[ten]["khoan"] < r["off"]["khoan"])
        print(f"{ten:<20}{t:>8}{th:>8}{len(rows)-t-th:>8}")

    # Tách theo gap để biết cơ chế ăn vào loại câu hỏi nào
    gaps = sorted({r.get("gap_type") or "—" for r in rows})
    if len(gaps) > 1:
        print(f"\n{'theo gap (Δ Khoản so với off)':<28}" + "".join(f"{t:>17}" for t in tens[1:]))
        for g in gaps:
            sub = [r for r in rows if (r.get("gap_type") or "—") == g]
            base = sum(r["off"]["khoan"] for r in sub) / len(sub)
            cells = "".join(
                f"{sum(r[t]['khoan'] for r in sub)/len(sub) - base:>+17.3f}" for t in tens[1:]
            )
            print(f"  {g:<26}" + cells + f"   (n={len(sub)})")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Đo tác động REFERS_TO lên độ bao phủ truy hồi ($0, tất định)"
    )
    ap.add_argument("--test-set", required=True, type=Path)
    ap.add_argument("--sample", type=int, default=0, help="Lấy ngẫu nhiên N câu")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--limit", type=int, default=0, help="N câu đầu")
    ap.add_argument("--top-k", type=int, default=25)
    ap.add_argument("--out", type=Path, default=None, help="Ghi kết quả JSON")
    ap.add_argument("--bo", default="refers", choices=list(BO_BIEN_THE),
                    help="Bộ biến thể: refers (việc 1) | budget (việc 2)")
    args = ap.parse_args()

    if not args.test_set.exists():
        print(f"❌ không thấy test set: {args.test_set}", file=sys.stderr)
        return 2
    ts = json.loads(args.test_set.read_text(encoding="utf-8"))
    if args.sample > 0:
        import random
        ts = random.Random(args.seed).sample(ts, min(args.sample, len(ts)))
        print(f"Lấy mẫu {len(ts)} câu (seed={args.seed})")
    if args.limit > 0:
        ts = ts[: args.limit]

    bien_the = BO_BIEN_THE[args.bo]
    rows = chay(ts, top_k=args.top_k, bien_the=bien_the)
    tong_hop(rows, bien_the)
    if args.out:
        args.out.write_text(json.dumps(rows, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        print(f"\nĐã ghi {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
