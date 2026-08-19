import warnings, logging, json, re
logging.disable(logging.WARNING); warnings.filterwarnings("ignore")
from dotenv import load_dotenv; load_dotenv()
from pathlib import Path
from src.pipeline import run_pipeline, _build_clients

qs = [l.strip() for l in open("ui/docs/DEMO_QUESTIONS.md", encoding="utf-8")
      if l.strip() and not l.startswith("#")]
cl = _build_clients("gemini"); CD = Path("data/evaluation/.llm_cache/")
base = dict(neo4j_driver=cl[0], qdrant_client=cl[1], anthropic_client=cl[2],
            model=cl[3], llm_mode="gemini", llm_cache_dir=CD)
SAU = {"refers_mode": "khoan", "rerank_mode": "trong-norm", "chuyen_tiep": True}
def c(x): return "%s|%s|%s" % (x.get("van_ban"), x.get("dieu"), x.get("khoan"))
HET_HL = ("luat-dat-dai-2013", "quyet-dinh-18-2016", "bo-luat-lao-dong-2012")
out = []
for i, q in enumerate(qs, 1):
    a = run_pipeline(q, **base); b = run_pipeline(q, **base, **SAU)
    sa = [c(x) for x in a["citations"]]; sb = [c(x) for x in b["citations"]]
    rec = {
        "i": i, "q": q,
        "cu_n": len(sa), "moi_n": len(sb),
        "cu_het_hl": sum(1 for x in sa if any(h in x for h in HET_HL)),
        "moi_het_hl": sum(1 for x in sb if any(h in x for h in HET_HL)),
        "khac": set(sa) != set(sb),
        "canh_bao": bool(b.get("canh_bao_thay_doi")),
        "cu_so": len(re.findall(r"\d+\s*m²", a["answer"])),
        "moi_so": len(re.findall(r"\d+\s*m²", b["answer"])),
        "cu_cite": sa, "moi_cite": sb,
    }
    out.append(rec)
    print("[%2d] khác=%-5s | hết-hiệu-lực %d→%d | trích %d→%d | số liệu %d→%d | cảnh báo=%s"
          % (i, rec["khac"], rec["cu_het_hl"], rec["moi_het_hl"], rec["cu_n"], rec["moi_n"],
             rec["cu_so"], rec["moi_so"], "có" if rec["canh_bao"] else "-"))
json.dump(out, open("/tmp/so15.json", "w"), ensure_ascii=False, indent=1)
