"""
Human eval (E2c) — chấm chất lượng câu trả lời + validate LLM-judge qua kappa.

Quy trình chủ–tớ (docs/E2C_RUBRIC.md, D-22 §E2c):
  1. select_sample: chọn 1 MẪU chung ~N câu (seed cố định, phân tầng theo gap).
  2. build_blind_sheets: sinh phiếu chấm MÙ (đáp án ẩn danh + xáo trộn) — mọi người
     chấm CÙNG mẫu; nhóm A (pháp lý) điền A1–A4, nhóm B (người dùng) điền B1–B2.
  3. Người chấm điền điểm → export JSON.
  4. kappa_report: đo đồng thuận NGƯỜI↔NGƯỜI và NGƯỜI↔MÁY (LLM-judge).
     Kappa cao → tin máy → mở rộng ra toàn bộ. Kappa thấp → không dùng máy (finding).

Kappa: chiều thang 1–5 (ordinal) dùng QUADRATIC WEIGHTED kappa; chiều nhị phân
(Hallucination) dùng Cohen kappa. ≥3 người chấm → trung bình pairwise.

Module KHÔNG cần chạy eval trước để test được phần toán (kappa/sample) — CLI sinh
phiếu cần result files (sau khi chạy eval).
"""
from __future__ import annotations

import argparse
import html
import json
import random
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

# Chiều chấm theo rubric
GROUP_A_ORDINAL = ["A1_factual", "A2_complete", "A3_citation"]
GROUP_A_BINARY = ["A4_halluc"]
GROUP_B_ORDINAL = ["B1_clarity", "B2_useful"]
DIM_LABELS = {
    "A1_factual": "A1 Đúng pháp luật (1–5)",
    "A2_complete": "A2 Đầy đủ (1–5)",
    "A3_citation": "A3 Chính xác trích dẫn (1–5)",
    "A4_halluc": "A4 Bịa đặt (0/1)",
    "B1_clarity": "B1 Rõ ràng (1–5)",
    "B2_useful": "B2 Hữu ích (1–5)",
}


# ---------------------------------------------------------------------------
# Kappa (lõi khoa học — cổng validation)
# ---------------------------------------------------------------------------

def cohen_kappa(a: list, b: list) -> float:
    """Cohen's kappa nominal/nhị phân trên 2 list nhãn cùng độ dài."""
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum((ca[k] / n) * (cb[k] / n) for k in set(ca) | set(cb))
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def quadratic_weighted_kappa(a: list, b: list, min_r: int = 1, max_r: int = 5) -> float:
    """QWK cho thang ordinal — phạt lỗi theo bình phương khoảng cách."""
    n = len(a)
    if n == 0:
        return float("nan")
    R = max_r - min_r + 1
    idx = lambda v: int(round(v)) - min_r
    O = [[0.0] * R for _ in range(R)]
    for x, y in zip(a, b):
        O[idx(x)][idx(y)] += 1
    row = [sum(O[i]) for i in range(R)]
    col = [sum(O[i][j] for i in range(R)) for j in range(R)]
    W = [[((i - j) ** 2) / ((R - 1) ** 2) for j in range(R)] for i in range(R)]
    num = sum(W[i][j] * O[i][j] for i in range(R) for j in range(R))
    den = sum(W[i][j] * row[i] * col[j] / n for i in range(R) for j in range(R))
    return 1.0 if den == 0 else 1 - num / den


def pairwise_kappa(ratings: dict[str, dict[str, float]], ordinal: bool) -> dict:
    """Đồng thuận giữa ≥2 người chấm trên 1 chiều.

    ratings: {rater_name: {instance_id: score}}. Chỉ dùng instance mà CẢ 2 người
    cùng chấm. ≥3 người → trung bình pairwise kappa.
    Trả về {pairs: {..}, mean_kappa, n_raters}.
    """
    raters = sorted(ratings)
    kappa_fn = quadratic_weighted_kappa if ordinal else cohen_kappa
    pairs = {}
    for r1, r2 in combinations(raters, 2):
        common = sorted(set(ratings[r1]) & set(ratings[r2]))
        if not common:
            continue
        a = [ratings[r1][i] for i in common]
        b = [ratings[r2][i] for i in common]
        pairs[f"{r1}↔{r2}"] = round(kappa_fn(a, b), 3)
    mean = round(sum(pairs.values()) / len(pairs), 3) if pairs else float("nan")
    return {"pairs": pairs, "mean_kappa": mean, "n_raters": len(raters)}


def interpret_kappa(k: float) -> str:
    """Nhãn Landis & Koch."""
    if k != k:  # nan
        return "N/A"
    if k < 0:
        return "kém hơn ngẫu nhiên"
    if k < 0.20:
        return "rất thấp (slight)"
    if k < 0.40:
        return "thấp (fair)"
    if k < 0.60:
        return "trung bình (moderate)"
    if k < 0.80:
        return "cao (substantial)"
    return "rất cao (almost perfect)"


def kappa_report(rater_scores: dict[str, dict[str, dict]], dims: list[str]) -> dict:
    """Tính kappa mỗi chiều từ {rater: {instance_id: {dim: score}}}.

    Dùng cho cả người↔người (truyền các rater người) và người↔máy (thêm rater 'judge').
    """
    report = {}
    for dim in dims:
        ordinal = dim not in GROUP_A_BINARY
        ratings = {
            r: {iid: s[dim] for iid, s in inst.items() if dim in s and s[dim] is not None}
            for r, inst in rater_scores.items()
        }
        ratings = {r: v for r, v in ratings.items() if v}
        res = pairwise_kappa(ratings, ordinal)
        res["interpret"] = interpret_kappa(res["mean_kappa"])
        report[dim] = res
    return report


# ---------------------------------------------------------------------------
# Chọn mẫu chung (seed cố định, phân tầng theo gap)
# ---------------------------------------------------------------------------

def _load_results(paths: list[Path]) -> dict[str, list[dict]]:
    """Đọc nhiều result file → {system: [items]}."""
    by_system = {}
    for p in paths:
        d = json.loads(p.read_text(encoding="utf-8"))
        items = d["results"] if isinstance(d, dict) and "results" in d else d
        sysname = d.get("system") if isinstance(d, dict) else None
        sysname = sysname or (items[0].get("system") if items else p.stem)
        by_system[sysname] = items
    return by_system


def select_sample(by_system: dict[str, list[dict]], n: int, seed: int = 42) -> list[str]:
    """Chọn n qid phân tầng theo gap_type (seed cố định). Chung cho mọi người chấm."""
    any_sys = next(iter(by_system.values()))
    by_gap: dict[str, list[str]] = defaultdict(list)
    for it in any_sys:
        by_gap[it["gap_type"]].append(it["id"])
    rng = random.Random(seed)
    gaps = sorted(by_gap)
    per = max(1, n // len(gaps))
    chosen: list[str] = []
    for g in gaps:
        ids = sorted(by_gap[g])
        rng.shuffle(ids)
        chosen.extend(ids[:per])
    # bù/cắt cho đủ n
    rng.shuffle(chosen)
    return sorted(chosen[:n])


# ---------------------------------------------------------------------------
# Sinh phiếu chấm MÙ (đáp án ẩn danh + xáo trộn)
# ---------------------------------------------------------------------------

def build_instances(sample_ids: list[str], by_system: dict[str, list[dict]],
                    seed: int = 42) -> tuple[list[dict], dict]:
    """Trả về (instances, key). instance = 1 (câu, đáp án ẩn danh). key ánh xạ về system.

    instance_id = '<qid>#<slot>'. Xáo trộn slot theo seed để chấm mù.
    """
    idx = {s: {it["id"]: it for it in items} for s, items in by_system.items()}
    systems = sorted(by_system)
    rng = random.Random(seed)
    instances, key = [], {}
    for qid in sample_ids:
        base = next((idx[s][qid] for s in systems if qid in idx[s]), None)
        if base is None:
            continue
        slots = systems[:]
        rng.shuffle(slots)
        for slot, sysname in enumerate(slots, 1):
            it = idx[sysname].get(qid)
            if it is None:
                continue
            iid = f"{qid}#{slot}"
            instances.append({
                "iid": iid, "qid": qid, "question": base["question"],
                "gap_type": base["gap_type"], "answer": it["answer"],
            })
            key[iid] = {"qid": qid, "system": sysname}
    return instances, key


def _sheet_html(instances: list[dict], group: str) -> str:
    dims = (GROUP_A_ORDINAL + GROUP_A_BINARY) if group == "A" else GROUP_B_ORDINAL
    cards = []
    for ins in instances:
        inputs = []
        for d in dims:
            if d in GROUP_A_BINARY:
                opts = ('<label><input type=radio name="{iid}_{d}" value=1> 1 Có bịa</label>'
                        '<label><input type=radio name="{iid}_{d}" value=0> 0 Không</label>')
            else:
                opts = "".join(
                    f'<label><input type=radio name="{{iid}}_{{d}}" value={v}>{v}</label>'
                    for v in range(1, 6))
            inputs.append(f'<div class=dim><span>{html.escape(DIM_LABELS[d])}</span>'
                          + opts.format(iid=ins["iid"], d=d) + "</div>")
        cards.append(f'''<div class=card data-iid="{ins['iid']}">
  <div class=hd><b>{ins['iid']}</b> <span class=g>{ins['gap_type']}</span></div>
  <div class=q>❓ {html.escape(ins['question'])}</div>
  <div class=a>{html.escape(ins['answer'])}</div>
  {''.join(inputs)}
  <input class=cmt type=text placeholder="ghi chú (nếu cần)">
</div>''')
    who = "PHÁP LÝ (A1–A4)" if group == "A" else "NGƯỜI DÙNG (B1–B2)"
    return f'''<!DOCTYPE html><html lang=vi><head><meta charset=utf-8>
<title>Phiếu chấm E2c — nhóm {group}</title><style>
 body{{font-family:-apple-system,Segoe UI,sans-serif;max-width:900px;margin:0 auto;padding:16px;background:#fafafa}}
 .bar{{position:sticky;top:0;background:#fff;border:1px solid #ddd;border-radius:8px;padding:10px;margin-bottom:12px}}
 .card{{background:#fff;border:1px solid #e3e3e3;border-radius:8px;padding:12px;margin-bottom:10px}}
 .hd .g{{color:#888;font-size:12px}} .q{{font-weight:600;margin:6px 0}}
 .a{{background:#f0f6ff;border-radius:6px;padding:8px;white-space:pre-wrap;font-size:14px;margin-bottom:8px}}
 .dim{{display:flex;gap:8px;align-items:center;font-size:13px;margin:3px 0}} .dim span{{width:200px}}
 .dim label{{cursor:pointer}} .cmt{{width:100%;margin-top:6px;padding:3px}}
</style></head><body>
<div class=bar><b>Phiếu chấm MÙ — nhóm {who}</b> · <input id=who placeholder="tên người chấm" style=padding:3px>
 · <button id=exp>⬇︎ Xuất điểm (JSON)</button> · <span id=prog></span></div>
{''.join(cards)}
<script>
const G="{group}", DIMS={json.dumps(dims)};
const store=JSON.parse(localStorage.getItem("e2c_"+G)||"{{}}");
function save(){{localStorage.setItem("e2c_"+G,JSON.stringify(store));
  document.getElementById('prog').textContent=Object.keys(store).length+" instance đã chấm";}}
document.querySelectorAll('.card').forEach(c=>{{
  const iid=c.dataset.iid; const s=store[iid]||{{}};
  DIMS.forEach(d=>{{if(s[d]!=null){{const el=c.querySelector(`input[name="${{iid}}_${{d}}"][value="${{s[d]}}"]`);if(el)el.checked=true;}}}});
  if(s._cmt)c.querySelector('.cmt').value=s._cmt;
  c.addEventListener('change',()=>collect(c)); c.addEventListener('input',()=>collect(c));
}});
function collect(c){{const iid=c.dataset.iid;const o=store[iid]||{{}};
  DIMS.forEach(d=>{{const el=c.querySelector(`input[name="${{iid}}_${{d}}"]:checked`);if(el)o[d]=Number(el.value);}});
  o._cmt=c.querySelector('.cmt').value; store[iid]=o; save();}}
document.getElementById('exp').onclick=()=>{{
  const who=document.getElementById('who').value||"anon";
  const blob=new Blob([JSON.stringify({{rater:who,group:G,scores:store}},null,2)],{{type:'application/json'}});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`E2C_diem_${{G}}_${{who}}.json`;a.click();}};
save();
</script></body></html>'''


def build_blind_sheets(sample_ids, by_system, out_dir: Path, seed: int = 42) -> dict:
    """Sinh 2 phiếu (nhóm A + nhóm B) trên CÙNG mẫu + lưu key giải ẩn danh."""
    instances, key = build_instances(sample_ids, by_system, seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    for g in ("A", "B"):
        (out_dir / f"E2C_PHIEU_{g}.html").write_text(_sheet_html(instances, g), encoding="utf-8")
    (out_dir / "E2C_KEY.json").write_text(json.dumps(key, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
    return {"n_instances": len(instances), "n_questions": len(sample_ids),
            "systems": sorted(by_system)}


# ---------------------------------------------------------------------------
# LLM-judge (máy chấm — validate qua kappa với người)
# ---------------------------------------------------------------------------

def build_judge_prompt(question: str, answer: str, group: str,
                       gt_answer: str = "", gt_cits: list | None = None) -> tuple[str, str]:
    if group == "A":
        system = (
            "Bạn là giám khảo pháp lý. Chấm câu trả lời của một hệ thống so với ĐÁP ÁN "
            "CHUẨN (ground truth) theo 4 tiêu chí, trả về JSON: "
            '{"A1_factual":1-5,"A2_complete":1-5,"A3_citation":1-5,"A4_halluc":0|1}. '
            "A1 đúng pháp luật, A2 đầy đủ, A3 chính xác trích dẫn, A4=1 nếu có bịa "
            "điều/khoản/văn bản không tồn tại. CHỈ trả JSON, không giải thích.")
        user = (f"CÂU HỎI: {question}\n\nĐÁP ÁN CHUẨN: {gt_answer}\n"
                f"TRÍCH DẪN CHUẨN: {json.dumps(gt_cits or [], ensure_ascii=False)}\n\n"
                f"CÂU TRẢ LỜI CẦN CHẤM: {answer}")
    else:
        system = (
            "Bạn đóng vai NGƯỜI DÂN đi hỏi thủ tục (không chuyên luật). Chấm câu trả lời "
            'theo 2 tiêu chí, trả về JSON: {"B1_clarity":1-5,"B2_useful":1-5}. '
            "B1 rõ ràng dễ hiểu, B2 hữu ích/biết phải làm gì. CHỈ trả JSON.")
        user = f"CÂU HỎI: {question}\n\nCÂU TRẢ LỜI: {answer}"
    return system, user


def _parse_judge_json(text: str) -> dict:
    import re
    m = re.search(r"\{[^}]*\}", text, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


def judge_instance(ins: dict, group: str, llm_client, gt_by_qid: dict) -> dict:
    gt = gt_by_qid.get(ins["qid"], {})
    system, user = build_judge_prompt(
        ins["question"], ins["answer"], group,
        gt.get("ground_truth_answer", ""), gt.get("ground_truth_citations", []))
    msg = llm_client.messages.create(
        model="claude-haiku-4-5-20251001", max_tokens=200, temperature=0.0,
        system=system, messages=[{"role": "user", "content": user}])
    return _parse_judge_json(msg.content[0].text)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cmd_sheets(args):
    by_system = _load_results([Path(p) for p in args.results])
    sample = select_sample(by_system, args.n, args.seed)
    info = build_blind_sheets(sample, by_system, Path(args.out_dir), args.seed)
    print(f"✅ Sinh phiếu: {info['n_questions']} câu × {len(info['systems'])} hệ "
          f"= {info['n_instances']} instance. Hệ: {info['systems']}")
    print(f"   → {args.out_dir}/E2C_PHIEU_A.html, E2C_PHIEU_B.html, E2C_KEY.json")


def _cmd_kappa(args):
    """Đọc các file điểm người (+ tùy chọn judge) → báo cáo kappa mỗi chiều."""
    rater_scores: dict[str, dict[str, dict]] = {}
    group = None
    for p in args.scores:
        d = json.loads(Path(p).read_text(encoding="utf-8"))
        rater_scores[d["rater"]] = {iid: {k: v for k, v in s.items() if not k.startswith("_")}
                                    for iid, s in d["scores"].items()}
        group = group or d.get("group")
    dims = (GROUP_A_ORDINAL + GROUP_A_BINARY) if group == "A" else GROUP_B_ORDINAL
    rep = kappa_report(rater_scores, dims)
    print(f"── Kappa nhóm {group} ({len(rater_scores)} người chấm) ──")
    for dim, r in rep.items():
        print(f"  {DIM_LABELS[dim]:<32} mean κ={r['mean_kappa']}  [{r['interpret']}]  {r['pairs']}")


def main() -> int:
    ap = argparse.ArgumentParser(description="E2c human eval — phiếu chấm + kappa")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s1 = sub.add_parser("sheets", help="Sinh phiếu chấm mù từ result files")
    s1.add_argument("--results", nargs="+", required=True, help="results_<system>_*.json")
    s1.add_argument("--n", type=int, default=25)
    s1.add_argument("--seed", type=int, default=42)
    s1.add_argument("--out-dir", default="data/evaluation/e2c")
    s1.set_defaults(func=_cmd_sheets)
    s2 = sub.add_parser("kappa", help="Tính kappa từ các file điểm đã chấm")
    s2.add_argument("--scores", nargs="+", required=True, help="E2C_diem_*.json")
    s2.set_defaults(func=_cmd_kappa)
    args = ap.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
