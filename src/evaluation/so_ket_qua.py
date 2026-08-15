"""So hai mẻ sinh — ghép theo id, tách câu dương / câu âm.

Khác `compare_runs.py` (diff A/B chi tiết từng câu), module này cho SỐ TỔNG
có nhánh đối chứng: Δ kèm khoảng tin cậy bootstrap ghép cặp, tách theo gap,
và các đại lượng giải thích over-cite (precision/recall/số trích dẫn TB).

    python -m src.evaluation.so_ket_qua <moc.json> <caitien.json>
"""
import json, sys, statistics, random


def doc(p):
    d = json.load(open(p))
    return {x["id"]: x for x in (d["results"] if isinstance(d, dict) else d)}


def g(x, k):
    v = x[k]
    return v["f1"] if isinstance(v, dict) else v


def pr(x, k):
    v = x[k]
    return (v.get("precision"), v.get("recall")) if isinstance(v, dict) else (None, None)


def boot(pairs, n=10000, seed=42):
    rnd = random.Random(seed)
    ds = [b - a for a, b in pairs]
    out = []
    for _ in range(n):
        s = [rnd.choice(ds) for _ in ds]
        out.append(sum(s) / len(s))
    out.sort()
    return out[int(0.025 * n)], out[int(0.975 * n)]


a, b = doc(sys.argv[1]), doc(sys.argv[2])
ids = sorted(set(a) & set(b))
pos = [i for i in ids if a[i]["gap_type"] != "negative"]
neg = [i for i in ids if a[i]["gap_type"] == "negative"]

print("ghép được %d câu (%d dương / %d âm)\n" % (len(ids), len(pos), len(neg)))
for k, ten in (("citation_score", "F1 Khoản"), ("citation_score_dieu", "F1 Điều"),
               ("norm_recall", "NormR")):
    va = sum(g(a[i], k) for i in pos) / len(pos)
    vb = sum(g(b[i], k) for i in pos) / len(pos)
    w = sum(1 for i in pos if g(b[i], k) > g(a[i], k))
    l = sum(1 for i in pos if g(b[i], k) < g(a[i], k))
    line = "%-10s %.3f -> %.3f  Δ=%+.3f  T%d/B%d" % (ten, va, vb, vb - va, w, l)
    if k == "citation_score":
        lo, hi = boot([(g(a[i], k), g(b[i], k)) for i in pos])
        line += "  CI95=[%+.3f, %+.3f]" % (lo, hi)
    print(line)

pa = [pr(a[i], "citation_score") for i in pos]
pb = [pr(b[i], "citation_score") for i in pos]
if pa[0][0] is not None:
    print("\nprecision %.3f -> %.3f | recall %.3f -> %.3f" % (
        sum(x[0] for x in pa) / len(pa), sum(x[0] for x in pb) / len(pb),
        sum(x[1] for x in pa) / len(pa), sum(x[1] for x in pb) / len(pb)))
print("trích dẫn TB %.2f -> %.2f" % (
    sum(len(a[i]["pred_citations"]) for i in pos) / len(pos),
    sum(len(b[i]["pred_citations"]) for i in pos) / len(pos)))
if neg:
    print("câu âm đúng %d/%d -> %d/%d" % (
        sum(1 for i in neg if a[i].get("negative_correct")), len(neg),
        sum(1 for i in neg if b[i].get("negative_correct")), len(neg)))

print("\n-- theo gap --")
gaps = sorted({a[i]["gap_type"] for i in pos})
for gp in gaps:
    s = [i for i in pos if a[i]["gap_type"] == gp]
    va = sum(g(a[i], "citation_score") for i in s) / len(s)
    vb = sum(g(b[i], "citation_score") for i in s) / len(s)
    print("%-8s n=%2d  %.3f -> %.3f  Δ=%+.3f" % (gp, len(s), va, vb, vb - va))

print("\n-- câu đổi nhiều nhất --")
dd = sorted(pos, key=lambda i: g(b[i], "citation_score") - g(a[i], "citation_score"))
for i in dd[:4] + dd[-4:]:
    print("%s %-6s %.2f -> %.2f  (%+.2f)" % (
        i, a[i]["gap_type"], g(a[i], "citation_score"),
        g(b[i], "citation_score"),
        g(b[i], "citation_score") - g(a[i], "citation_score")))
