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
import re
import sys
from pathlib import Path

from src.evaluation.metrics import cit_matches
from src.evaluation.retrieval_eval import (
    _build_clients,
    _chunk_to_citation,
    _fetch_chunk_meta,
)
from src.pipeline import CONTEXT_MAX_TOKENS
from src.retrieval.context_assembler import assemble_context_chi_tiet
from src.retrieval.query_planner import plan_query
from src.retrieval.semantic_filter import hybrid_search
from src.retrieval.subgraph_extractor import extract_subgraph

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Bộ biến thể so sánh: tên → (refers_mode, budget_mode).
# "off" LUÔN phải đứng đầu — mọi Δ đều tính so với nó.
BO_BIEN_THE: dict[str, list[tuple]] = {
    # Việc 1 — bao đóng dẫn chiếu, kèm nhánh đối chứng "rrf" để tách bạch
    # "nhờ dẫn chiếu" với "nhờ được thêm ngữ cảnh".
    "refers": [
        ("off", None, None, 6000, None),
        ("khoan", "khoan", None, 6000, None),
        ("all", "all", None, 6000, None),
        ("rrf(đối chứng)", "rrf", None, 6000, None),
    ],
    # Việc 2 — ngân sách theo đồ thị (đã cho kết quả âm, giữ để tái lập).
    "budget": [
        ("off", None, None, 6000, None),
        ("ngân sách", None, "graph", 6000, None),
        ("khoan", "khoan", None, 6000, None),
        ("khoan+ngân sách", "khoan", "graph", 6000, None),
    ],
    # Việc 2 vòng 2 — nhắm đúng ràng buộc đang chặn (trần TẦNG), và thử tiêu
    # thẳng phần ngân sách bỏ trống. Đo cho thấy ứng viên thừa mứa (trung vị
    # 2772) nhưng 0/38 câu lấy đủ 25 vì trần khoá.
    "budget2": [
        ("off", None, None, 6000, None),
        ("nới trần văn bản", None, "norm", 6000, None),
        ("nới trần tầng", None, "tier", 6000, None),
        ("tiêu hết ngân sách", None, "fill", 6000, None),
    ],
    # Vòng 4 — nới chính NGƯỠNG TOKEN. Đo cho thấy trần top_k/per_norm/per_tier
    # đều nằm TRÊN một nút thắt chặt hơn ở phía dưới: assemble_context cắt theo
    # CONTEXT_MAX_TOKENS=6000 và cắt đúng các đơn vị điểm RRF thấp — tức đúng
    # phần mà mọi cơ chế nạp thêm vừa đưa vào. 6000 là con số đặt từ thời tính
    # tiền theo Claude; Gemini 2.5 Pro chịu tới 1 triệu token.
    "token": [
        ("off (6000)", None, None, 6000, None),
        ("off + 12000", None, None, 12000, None),
        ("khoan + 12000", "khoan", None, 12000, None),
        ("khoan+tiêu hết + 12000", "khoan", "fill", 12000, None),
    ],
    # Vòng 5 — tìm điểm BÃO HOÀ của ngưỡng token. Độ bao phủ tăng đơn điệu theo
    # lượng ngữ cảnh nên "nới thêm" luôn trông đẹp; điều cần biết là nới tới đâu
    # thì hết thứ để lấy. Nếu 18000 không hơn 12000 thì 12000 đã vét hết.
    "token-bao-hoa": [
        ("khoan+fill 6000", "khoan", "fill", 6000, None),
        ("khoan+fill 12000", "khoan", "fill", 12000, None),
        ("khoan+fill 18000", "khoan", "fill", 18000, None),
        ("khoan+fill 30000", "khoan", "fill", 30000, None),
    ],
    # Vòng 6 — lever cuối cùng. Đo cho thấy 87% trích dẫn còn thiếu thuộc văn bản
    # ĐÃ truy hồi đúng, chỉ là điều khoản thua các điều khoản khác cùng văn bản.
    # Cross-encoder xếp lại BÊN TRONG văn bản — không lặp lại thất bại D-20 vì
    # thứ tự giữa các văn bản giữ nguyên.
    "rerank": [
        ("mốc (khoan+fill 12k)", "khoan", "fill", 12000, None),
        ("+ xếp lại trong norm", "khoan", "fill", 12000, "trong-norm"),
        ("chỉ xếp lại (ko fill)", "khoan", None, 12000, "trong-norm"),
        ("xếp lại, ko dẫn chiếu", None, None, 12000, "trong-norm"),
    ],
    # Vòng 3 — phép so QUYẾT ĐỊNH: biến thể tốt nhất của mỗi việc, và cả hai
    # cùng lúc. Dùng để chốt cấu hình cuối.
    "ket-hop": [
        ("off", None, None, 6000, None),
        ("khoan", "khoan", None, 6000, None),
        ("tiêu hết ngân sách", None, "fill", 6000, None),
        ("khoan+tiêu hết", "khoan", "fill", 6000, None),
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
         bien_the: list[tuple] | None = None,
         summary_type: str = "summary") -> list[dict]:
    bien_the = bien_the or BO_BIEN_THE["refers"]
    neo4j, qdrant, llm, model = _build_clients()
    # Cross-encoder ~600MB, chạy CPU (D-20: MPS treo) → tải MỘT LẦN, dùng lại.
    rr_model = None
    if any(v[4] for v in bien_the):
        from src.retrieval.reranker import load_reranker
        print("Đang tải cross-encoder (CPU, ~600MB)...", flush=True)
        rr_model = load_reranker()
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
            norm_ids, graph_comp_ids = extract_subgraph(
                q, plan, neo4j, qdrant, model, summary_type=summary_type)
            if not norm_ids:
                continue

            row = {"id": item["id"], "gap_type": item.get("gap_type")}
            for ten, rmode, pmode, mtok, rrmode in bien_the:
                units = hybrid_search(
                    q, norm_ids, qdrant, model, top_k=top_k,
                    graph_component_ids=graph_comp_ids, neo4j_driver=neo4j,
                    procedure_id=plan.get("procedure"), refers_mode=rmode,
                    budget_mode=pmode, rerank_mode=rrmode, rerank_model=rr_model,
                )
                meta = _fetch_chunk_meta([u["text_unit_id"] for u in units], neo4j)
                # Đơn vị THỰC SỰ lọt vào ngữ cảnh sau khi cắt theo ngưỡng token.
                # Đây mới là thứ bộ sinh nhìn thấy — các cơ chế nạp thêm đều gán
                # điểm RRF thấp nên nằm cuối và bị cắt trước.
                ctx, giu = assemble_context_chi_tiet(
                    units, neo4j, max_tokens=mtok)
                row[ten] = {
                    "n": len(units),
                    "n_ctx": len(giu),
                    "token": int(len(ctx) / 3.5),
                    "khoan": _do_bao_phu(giu, gt, meta, "khoan"),
                    "dieu": _do_bao_phu(giu, gt, meta, "dieu"),
                    "khoan_chon": _do_bao_phu(units, gt, meta, "khoan"),
                }
            rows.append(row)
            print(
                f"[{i}/{len(test_set)}] {item['id']}  "
                + "  ".join(f"{t}={row[t]['khoan']:.2f}({row[t]['n']})"
                            for t, *_ in bien_the),
                flush=True,
            )
    finally:
        neo4j.close()
    return rows


def tong_hop(rows: list[dict], bien_the) -> None:
    if not rows:
        print("Không có câu nào chạy được.")
        return
    tens = [t for t, *_ in bien_the]
    print(f"\n{'='*70}")
    print(f"ĐỘ BAO PHỦ ĐIỀU KHOẢN ĐÁP ÁN TRONG NGỮ CẢNH — {len(rows)} câu")
    print(f"{'='*70}")
    print("Cột 'cấp Khoản' đo trên đơn vị THỰC SỰ lọt vào ngữ cảnh (sau cắt token).")
    print(f"\n{'biến thể':<20}{'cấp Khoản':>11}{'Δ':>9}{'(nếu ko cắt)':>14}"
          f"{'cấp Điều':>10}{'chọn':>7}{'lọt':>7}{'token':>8}{'bị cắt':>8}")
    goc = None
    for ten in tens:
        kh = sum(r[ten]["khoan"] for r in rows) / len(rows)
        di = sum(r[ten]["dieu"] for r in rows) / len(rows)
        n = sum(r[ten]["n"] for r in rows) / len(rows)
        nc = sum(r[ten]["n_ctx"] for r in rows) / len(rows)
        tk = sum(r[ten]["token"] for r in rows) / len(rows)
        cat = sum(1 for r in rows if r[ten]["n_ctx"] < r[ten]["n"])
        delta = "" if goc is None else f"{kh - goc:+.3f}"
        if goc is None:
            goc = kh
        kc = sum(r[ten]["khoan_chon"] for r in rows) / len(rows)
        print(f"{ten:<20}{kh:>11.3f}{delta:>9}{kc:>14.3f}"
              f"{di:>10.3f}{n:>7.1f}{nc:>7.1f}{tk:>8.0f}{cat:>8}")
    print("  '(nếu ko cắt)' = đo trên đơn vị được CHỌN. Chênh với cột đầu chính"
          " là phần bị ngưỡng token nuốt mất.")

    # Đếm câu thắng/thua so với MỐC (biến thể đầu tiên, không cứng tên "off")
    moc = tens[0]
    print(f"\n{'so với ' + moc:<24}{'thắng':>8}{'thua':>8}{'hoà':>8}")
    for ten in tens[1:]:
        t = sum(1 for r in rows if r[ten]["khoan"] > r[moc]["khoan"])
        th = sum(1 for r in rows if r[ten]["khoan"] < r[moc]["khoan"])
        print(f"{ten:<24}{t:>8}{th:>8}{len(rows)-t-th:>8}")

    # Tách theo gap để biết cơ chế ăn vào loại câu hỏi nào
    gaps = sorted({r.get("gap_type") or "—" for r in rows})
    if len(gaps) > 1:
        print(f"\n{'theo gap (Δ Khoản so với off)':<28}" + "".join(f"{t:>17}" for t in tens[1:]))
        for g in gaps:
            sub = [r for r in rows if (r.get("gap_type") or "—") == g]
            base = sum(r[tens[0]]["khoan"] for r in sub) / len(sub)
            cells = "".join(
                f"{sum(r[t]['khoan'] for r in sub)/len(sub) - base:>+17.3f}"
                for t in tens[1:]
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
    ap.add_argument("--summary-type", default="summary",
                    choices=["summary", "summary_auto"],
                    help="Nguồn tóm tắt cho Giai đoạn 1: summary (người viết, mặc "
                         "định) | summary_auto (máy sinh — việc 4, đo độ nhạy).")
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
    rows = chay(ts, top_k=args.top_k, bien_the=bien_the,
                summary_type=args.summary_type)
    tong_hop(rows, bien_the)
    if args.out:
        args.out.write_text(json.dumps(rows, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        print(f"\nĐã ghi {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
