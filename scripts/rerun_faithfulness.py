"""Chấm lại faithfulness Tier 2 trên các file results CÓ SẴN, dùng judge Gemini Flash.

    # xem trước: đếm số lần gọi API + ước phí, KHÔNG gọi API
    python scripts/rerun_faithfulness.py data/evaluation/results_graphrag_final1_*.json --dry-run

    # chạy thật trên vài file chỉ định
    python scripts/rerun_faithfulness.py data/evaluation/results_graphrag_final1_*.json

    # thử nhanh 5 câu đầu mỗi file
    python scripts/rerun_faithfulness.py <file...> --limit 5

Đọc `context` / `answer` / `pred_citations` đã lưu trong results (KHÔNG chạy lại
pipeline, không đụng Neo4j/Qdrant), gọi `evaluate_faithfulness(tier2=True)` và ghi
ra file MỚI `faithfulness_flash_<timestamp>.json`. File results gốc KHÔNG bị sửa.

Vì sao cần: judge Tier 2 trước đây là Claude Haiku; dự án chuyển sang thuần Gemini
nên số Tier 2 cũ và mới không so trực tiếp được. Script này chấm lại bằng judge mới
trên cùng dữ liệu để có bộ số nhất quán — và cho phép so judge-cũ vs judge-mới trên
từng câu (`faithfulness_cu` trong output) như một phép đo agreement giữa hai judge.

Ba điểm cẩn trọng đã xử lý:
  • Câu KHÔNG có `context` (một số run cũ không lưu) bị BỎ QUA, không chấm 0 —
    thiếu dữ liệu không phải là bằng chứng hallucination.
  • `_judge_citation` nuốt exception và trả `supported=False`. Nếu gặp 429 thì cả
    mẻ sẽ bị chấm trượt ÂM THẦM. Script bọc client bằng proxy có throttle + retry
    (dùng lại `_la_loi_tam_thoi` / `_retry_delay` của ontology_mapper) và ĐẾM
    RIÊNG số `judge_error` còn sót để báo động thay vì để lẫn vào tỉ lệ.
  • Mặc định KHÔNG chạy toàn bộ 39 file (≈5000 lượt gọi) — phải chỉ định file,
    hoặc dùng --all một cách có ý thức.
"""
from __future__ import annotations

import argparse
import glob
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

for _luong in (sys.stdout, sys.stderr):
    if getattr(_luong, "encoding", "").lower() != "utf-8":
        try:
            _luong.reconfigure(encoding="utf-8")
        except Exception:                           # noqa: BLE001
            pass

GOC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC))

from dotenv import load_dotenv                      # noqa: E402

load_dotenv(GOC / ".env")

from src.evaluation.faithfulness import evaluate_faithfulness   # noqa: E402
from src.ingestion.ontology_mapper import _la_loi_tam_thoi, _retry_delay  # noqa: E402
from src.utils.gemini_fallback import _build_gemini_client      # noqa: E402

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
logger = logging.getLogger("rerun_faithfulness")

MAX_RETRIES = 3
THROTTLE_SEC = float(os.getenv("JUDGE_THROTTLE_SEC", "0.5"))

# Dừng sớm nếu N lượt judge ĐẦU TIÊN đều lỗi: gần như chắc chắn là sai cấu hình
# (model không có trên kênh đang dùng, thiếu quyền…) chứ không phải hallucination.
# Không có chốt này, một tên model sai sẽ đốt 20 phút để sinh ra bảng support toàn 0.
NGUONG_LOI_LIEN_TIEP = 8

# Giá Gemini 2.5 Flash (USD/1M token) — chỉ để ƯỚC phí trong --dry-run.
GIA_INPUT = 0.30
GIA_OUTPUT = 2.50
# Đo thực tế trên prompt judge (system + snippet + chunk[:1500]) và output+thinking.
TOKEN_INPUT_UOC = 900
TOKEN_OUTPUT_UOC = 400


class ClientCoRetry:
    """Bọc client google-genai: throttle + retry 429/5xx/mất kết nối.

    `faithfulness._judge_citation` bắt mọi exception và trả `supported=False`,
    nên lỗi hạ tầng phải được xử lý TRƯỚC khi tới đó — nếu không, một đợt 429 sẽ
    biến thành "support_rate thấp" mà không ai biết.
    """

    def __init__(self, inner):
        self._inner = inner
        self.models = type("_Models", (), {"generate_content": self._gen})()
        self.so_retry = 0
        self.so_call = 0
        self._last_ts: float | None = None

    def _gen(self, **kwargs):
        for lan_thu in range(MAX_RETRIES + 1):
            if self._last_ts is not None:
                con_lai = THROTTLE_SEC - (time.monotonic() - self._last_ts)
                if con_lai > 0:
                    time.sleep(con_lai)
            self._last_ts = time.monotonic()
            try:
                self.so_call += 1
                return self._inner.models.generate_content(**kwargs)
            except Exception as err:                # noqa: BLE001 — lọc bằng helper
                if not _la_loi_tam_thoi(err) or lan_thu == MAX_RETRIES:
                    raise
                self.so_retry += 1
                cho = _retry_delay(err, lan_thu)
                logger.warning("judge lỗi hạ tầng (%s) — thử lại sau %.1fs",
                               type(err).__name__, cho)
                time.sleep(cho)


def _cau_du_dieu_kien(rec: dict) -> bool:
    return bool((rec.get("context") or "").strip()) and bool(rec.get("pred_citations"))


def _tom_tat_cu(rec: dict) -> dict | None:
    """Số faithfulness của judge CŨ (Claude) nếu file có lưu — để đối chiếu."""
    f = rec.get("faithfulness")
    if not isinstance(f, dict):
        return None
    return {k: f.get(k) for k in
            ("existence_rate", "support_rate", "faithful_rate",
             "citations_total", "citations_existing", "citations_supported")}


def _kiem_ke(duong_dan: list[str], limit: int | None) -> list[dict]:
    ke = []
    for p in duong_dan:
        try:
            d = json.loads(Path(p).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"  ⚠️  Bỏ qua {p}: {e}")
            continue
        res = d.get("results", [])
        if limit:
            res = res[:limit]
        du = [r for r in res if _cau_du_dieu_kien(r)]
        ke.append({
            "path": p, "system": d.get("system"), "timestamp": d.get("timestamp"),
            "n_records": len(res), "n_du": len(du),
            "n_thieu_context": sum(1 for r in res if not (r.get("context") or "").strip()),
            "n_khong_citation": sum(1 for r in res if not r.get("pred_citations")),
            "n_citation": sum(len(r["pred_citations"]) for r in du),
            "records": res,
        })
    return ke


def _in_kiem_ke(ke: list[dict]) -> tuple[int, int]:
    print(f"\n{'file':52} {'hệ':>10} {'N':>4} {'đủ':>4} {'∅ctx':>5} {'∅cit':>5} {'#cit':>5}")
    tong_du = tong_cit = 0
    for k in ke:
        print(f"{Path(k['path']).name[:52]:52} {str(k['system'])[:10]:>10} "
              f"{k['n_records']:>4} {k['n_du']:>4} {k['n_thieu_context']:>5} "
              f"{k['n_khong_citation']:>5} {k['n_citation']:>5}")
        tong_du += k["n_du"]
        tong_cit += k["n_citation"]
    print(f"\nTổng: {tong_du} câu đủ điều kiện Tier 2, {tong_cit} citation.")
    print("Judge chỉ gọi cho citation TỒN TẠI trong context (Tier 1 pass), "
          "nên số lượt gọi thật ≤ số citation trên.")
    phi = (tong_cit * TOKEN_INPUT_UOC * GIA_INPUT
           + tong_cit * TOKEN_OUTPUT_UOC * GIA_OUTPUT) / 1e6
    print(f"Ước phí tối đa: ~${phi:.2f} (giả định {TOKEN_INPUT_UOC} token vào / "
          f"{TOKEN_OUTPUT_UOC} token ra mỗi lượt).")
    return tong_du, tong_cit


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", help="đường dẫn results_*.json (chấp nhận glob)")
    ap.add_argument("--files", dest="files_flag", nargs="+", default=[],
                    metavar="FILE", help="dạng cờ của tham số vị trí trên")
    ap.add_argument("--all", action="store_true",
                    help="chạy TẤT CẢ data/evaluation/results_*.json (tốn kém — cân nhắc)")
    ap.add_argument("--dry-run", action="store_true", help="chỉ kiểm kê + ước phí")
    ap.add_argument("--limit", type=int, help="chỉ lấy N câu đầu mỗi file (thử nhanh)")
    ap.add_argument("--out-dir", default="data/evaluation", help="thư mục ghi kết quả")
    args = ap.parse_args()

    duong_dan: list[str] = []
    for f in list(args.files) + list(args.files_flag):
        duong_dan.extend(sorted(glob.glob(f)) or [f])
    if args.all:
        duong_dan = sorted(glob.glob(str(GOC / "data/evaluation/results_*.json")))
    if not duong_dan:
        ap.error("Chưa chỉ định file. Dùng đường dẫn cụ thể, hoặc --all nếu thực sự "
                 "muốn chấm lại toàn bộ.")

    ke = _kiem_ke(duong_dan, args.limit)
    tong_du, tong_cit = _in_kiem_ke(ke)
    if args.dry_run:
        print("\n[dry-run] Không gọi API, không ghi file.")
        return 0
    if tong_du == 0:
        print("\nKhông có câu nào đủ (cần CẢ context lẫn pred_citations). Dừng.")
        return 1

    client = ClientCoRetry(_build_gemini_client(os.getenv("GEMINI_API_KEY")))
    from src.evaluation.faithfulness import _judge_model
    print(f"\nJudge: {_judge_model()} | "
          f"{'Vertex ADC' if os.getenv('GEMINI_USE_VERTEX','').lower()=='true' else 'Developer API'}")

    ket_qua_files = []
    t0 = time.monotonic()
    n_cit_tong = n_ton_tai = n_support = n_loi = 0
    ty_le_cau = []

    for k in ke:
        print(f"\n── {Path(k['path']).name} ({k['n_du']} câu) ──")
        per_q = []
        for i, rec in enumerate(k["records"], 1):
            if not _cau_du_dieu_kien(rec):
                per_q.append({"id": rec.get("id"), "bo_qua": (
                    "thiếu context" if not (rec.get("context") or "").strip()
                    else "không có citation")})
                continue
            f = evaluate_faithfulness(
                citations=rec["pred_citations"], answer=rec.get("answer", ""),
                context=rec["context"], llm_client=client, tier2=True,
            )
            loi = sum(1 for c in f["per_citation"]
                      if str(c.get("reason", "")).startswith("judge_error"))
            n_cit_tong += f["citations_total"]
            n_ton_tai += f["citations_existing"]
            n_support += f["citations_supported"]
            n_loi += loi
            ty_le_cau.append(f["faithful_rate"])
            per_q.append({
                "id": rec.get("id"), "gap_type": rec.get("gap_type"),
                "existence_rate": f["existence_rate"], "support_rate": f["support_rate"],
                "faithful_rate": f["faithful_rate"],
                "citations_total": f["citations_total"],
                "citations_existing": f["citations_existing"],
                "citations_supported": f["citations_supported"],
                "judge_error": loi,
                "per_citation": f["per_citation"],
                "faithfulness_cu": _tom_tat_cu(rec),
            })
            print(f"  [{i}/{len(k['records'])}] {rec.get('id')}: "
                  f"exist={f['existence_rate']:.2f} support={f['support_rate']:.2f}"
                  + (f" ⚠️ {loi} judge_error" if loi else ""))

            # Fail-fast: mọi lượt judge từ đầu tới giờ đều lỗi → dừng, đừng đốt thêm.
            if n_loi >= NGUONG_LOI_LIEN_TIEP and n_loi == n_ton_tai:
                loi_dau = next((c.get("reason") for c in f["per_citation"]
                                if str(c.get("reason", "")).startswith("judge_error")), "")
                print(f"\n❌ DỪNG SỚM: {n_loi}/{n_ton_tai} lượt judge đầu tiên đều lỗi — "
                      f"gần như chắc chắn sai cấu hình, không phải chất lượng câu trả lời.\n"
                      f"   Lỗi đầu tiên: {str(loi_dau)[:300]}\n"
                      f"   Kiểm tra: model `{_judge_model()}` có tồn tại trên kênh đang dùng "
                      f"({'Vertex' if os.getenv('GEMINI_USE_VERTEX','').lower()=='true' else 'Developer API'}) không?")
                return 2
        ket_qua_files.append({"path": k["path"], "system": k["system"],
                              "timestamp_goc": k["timestamp"], "per_question": per_q})

    elapsed = time.monotonic() - t0
    micro_exist = n_ton_tai / n_cit_tong if n_cit_tong else float("nan")
    micro_support = n_support / n_ton_tai if n_ton_tai else float("nan")
    micro_faith = n_support / n_cit_tong if n_cit_tong else float("nan")
    macro_faith = sum(ty_le_cau) / len(ty_le_cau) if ty_le_cau else float("nan")

    summary = {
        "judge_model": _judge_model(),
        "vertex": os.getenv("GEMINI_USE_VERTEX", "false"),
        "so_file": len(ket_qua_files), "so_cau_da_cham": len(ty_le_cau),
        "citations_total": n_cit_tong, "citations_existing": n_ton_tai,
        "citations_supported": n_support, "judge_error": n_loi,
        "existence_rate_micro": micro_exist, "support_rate_micro": micro_support,
        "faithful_rate_micro": micro_faith, "faithful_rate_macro": macro_faith,
        "so_lan_goi_api": client.so_call, "so_lan_retry": client.so_retry,
        "elapsed_s": round(elapsed, 1),
    }

    Path(args.out_dir).mkdir(parents=True, exist_ok=True)
    out = Path(args.out_dir) / f"faithfulness_flash_{datetime.now():%Y%m%d-%H%M%S}.json"
    out.write_text(json.dumps({"summary": summary, "files": ket_qua_files},
                              ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 62)
    print("TỔNG HỢP (micro — tính trên từng citation)")
    print("=" * 62)
    print(f"  existence_rate  = {micro_exist:.4f}  ({n_ton_tai}/{n_cit_tong})")
    print(f"  support_rate    = {micro_support:.4f}  ({n_support}/{n_ton_tai})")
    print(f"  faithful_rate   = {micro_faith:.4f}  ({n_support}/{n_cit_tong})")
    print(f"  faithful_rate (macro theo câu) = {macro_faith:.4f}")
    print(f"\n  API: {client.so_call} lượt gọi, {client.so_retry} lần retry, "
          f"{elapsed/60:.1f} phút")
    if n_loi:
        print(f"  ⚠️  {n_loi} citation bị judge_error SAU khi hết retry — chúng bị "
              f"tính là UNSUPPORTED, làm support_rate thấp GIẢ TẠO. Nên chạy lại.")
    print(f"\nĐã ghi: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
