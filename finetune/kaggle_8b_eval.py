"""Chạy Qwen3-8B gốc, 2-shot, trên HAI khuôn ngữ cảnh — bổ sung một hàng cho mục 4.7.

    prep   cài wheel llama-cpp-python đã ghim + tải GGUF 8B, ghi lại sha256
    run    hai ô, mỗi ô một `finetune.replay` (GraphRAG rồi Naive RAG)
    table  gom hai file kết quả → finetune/reports/8b_eval.md

Bản rút gọn của `kaggle_ft06.py`: bỏ hai cổng chặn (template/prompt), bỏ đẩy HF, bỏ
`--parallel`. Chỉ MỘT cấu hình sinh nên không có ma trận để so chéo trong nội bộ
script — điểm so sánh nằm ở `ft06b_matrix.md` của lượt 4B.

────────────────────────────────────────────────────────────────────────────────
VÌ SAO CHỈ 2-SHOT
────────────────────────────────────────────────────────────────────────────────
Lượt 4B đã đo: mô hình gốc 0-shot đạt `format_ok` 6.6%, 2-shot đạt 78.1%. Với mô
hình gốc, few-shot không phải biến phụ mà là điều kiện để kết quả có nghĩa — chạy
0-shot cho 8B chỉ tốn giờ GPU để đo lại một thất bại đã biết.

Hai ô dùng lại đúng khuôn 2-shot của lượt 4B: `build_chat_messages` trong `replay.py`
dựng khối minh hoạ từ cùng một nguồn, nên `--n-shot 2` ở đây và ở `ft06b-base-s2` cho
đúng một prompt (chỉ khác ngữ cảnh từng câu). Bằng chứng đã đọc bằng mắt của lượt
trước nằm ở `finetune/reports/ft06_prompt_{graphrag,baseline}_s2.txt` — script này
KHÔNG dựng lại cổng chặn prompt vì khuôn không đổi, chỉ đổi mô hình sinh.

────────────────────────────────────────────────────────────────────────────────
THAM SỐ SINH — giống hệt lượt 4B, KHÔNG được đổi
────────────────────────────────────────────────────────────────────────────────
temperature 0.7 · top_p 0.8 · top_k 20 · min_p 0 · presence_penalty 0 · seed 42 ·
max_new_tokens 2048 · n_ctx 16384 · n_gpu_layers −1 (`gate_base_model.md` §3).

Bảy trong tám giá trị đó ĐÃ là mặc định của `replay.py` → không truyền lại, vì truyền
lại là nhân đôi nguồn chân lý: đổi ở một chỗ mà quên chỗ kia thì cột Δ so hai thứ
khác nhau mà không có dấu hiệu gì.

**NGOẠI LỆ DUY NHẤT — `--presence-penalty 0` PHẢI truyền tường minh.** Mặc định của
`replay.py` là **1.0**, không phải 0.

Đổi bất kỳ giá trị nào ở đây làm cột Δ so với hàng 4B mất nghĩa: hai hàng khi đó khác
nhau ở CẢ mô hình lẫn tham số sinh, không tách được phần nào do đâu.

────────────────────────────────────────────────────────────────────────────────
GHIM GPU
────────────────────────────────────────────────────────────────────────────────
Kaggle cấp T4 x2. Cả hai ô chạy TUẦN TỰ trên `CUDA_VISIBLE_DEVICES=0` — ghim qua env
của subprocess, KHÔNG đặt `os.environ` toàn cục (một ô chỉnh env toàn cục là ô sau
thừa hưởng trạng thái không ai khai báo). 8B Q4_K_M ~5 GB, n_ctx 16384 vẫn vừa 16 GB
của một card; chạy tuần tự nên card thứ hai không rút ngắn được gì, mà lại thêm biến
"ô nào nằm card nào" vào phép so.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

MODELS_DIR = REPO / "finetune/models"
REPORTS_DIR = REPO / "finetune/reports"
RESULTS_DIR = REPO / "finetune/results"

# --- nguồn ngữ cảnh: ĐÚNG hai file của lượt 4B, để Δ chỉ phản ánh mô hình sinh ---
SRC_GRAPHRAG = "data/evaluation/results_graphrag_final1_20260729-022916.json"
SRC_BASELINE = "data/evaluation/results_baseline_20260710-085236.json"

# --- wheel llama-cpp-python: ghim y hệt lượt 4B ---------------------------------
# Bản dựng llama.cpp khác là đổi nền tái lập của MỌI con số, kể cả khi model giống.
WHEEL_REPO = "dangnguyen254/thesis-graphrag-gguf"
WHEEL_FILE = "runtime/llama_cpp_python-0.3.16-cp312-cp312-linux_x86_64.whl"
WHEEL_SHA256 = "a3cb84bddb15c1759a0ece5ec8ef9d10d1419f926c895064d1a91ec517fd0da7"

# --- GGUF 8B --------------------------------------------------------------------
# KHÔNG ghim sha256 sẵn: đây là lần đầu dự án dùng repo này nên chưa có giá trị nào
# để đối chiếu. `prep` TÍNH sha256 rồi ghi vào finetune/reports/8b_artifacts.json —
# lần chạy sau truyền --gguf-sha256 để biến nó thành cổng chặn thật.
GGUF_REPO = "Qwen/Qwen3-8B-GGUF"
GGUF_LOCAL_NAME = "Qwen3-8B-Q4_K_M.gguf"
# Tên file trên Hub khác nhau giữa các repo (Qwen dùng thư mục con, bartowski dùng
# tiền tố) → thử vài biến thể trước khi bỏ cuộc, thay vì chết ở lần gọi đầu.
GGUF_FILE_ALT = [
    "Qwen3-8B-Q4_K_M.gguf",
    "qwen3-8b-q4_k_m.gguf",
    "Q4_K_M/Qwen3-8B-Q4_K_M.gguf",
]

ARTIFACTS_JSON = REPORTS_DIR / "8b_artifacts.json"
BANG_MD = REPORTS_DIR / "8b_eval.md"

TAG = "8b-base-s2"
N_SHOT = 2

# Ô 4B tương ứng — cột đối chiếu ở bảng 2. Chỉ ĐỌC, không chạy lại.
TAG_4B = "ft06b-base-s2"


@dataclass(frozen=True)
class Cell:
    idx: int
    system: str          # "graphrag" | "baseline"

    @property
    def nhan(self) -> str:
        return f"ô {self.idx} · {self.system} · 8B gốc {N_SHOT}-shot"

    @property
    def out_path(self) -> Path:
        # Tên TẤT ĐỊNH (không timestamp): replay.py suy .partial.jsonl từ tên file
        # đầu ra, nên tên có timestamp làm --resume vô dụng ngay lần đứt đầu tiên.
        return RESULTS_DIR / f"results_{self.system}_{TAG}.json"


CELLS = [Cell(1, "graphrag"), Cell(2, "baseline")]
CELL_BY_IDX = {c.idx: c for c in CELLS}


# ---------------------------------------------------------------------------
# Tiện ích
# ---------------------------------------------------------------------------

def _tieu_de(s: str) -> None:
    print(f"\n{'=' * 78}\n{s}\n{'=' * 78}")


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(REPO))
    except ValueError:
        return str(p)


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _hf_token() -> str | None:
    # Notebook nạp token qua kaggle_secrets rồi đặt vào os.environ. KHÔNG hardcode.
    return os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")


def _pip(*args: str) -> int:
    cmd = [sys.executable, "-m", "pip", "install", "-q", *args]
    print("  $", " ".join(cmd))
    return subprocess.run(cmd).returncode


def _tai(repo: str, file: str, revision: str | None = None) -> Path:
    from huggingface_hub import hf_hub_download
    return Path(hf_hub_download(repo_id=repo, filename=file, revision=revision,
                                token=_hf_token()))


def _symlink(src: Path, dst: Path) -> None:
    """Symlink thay vì copy: GGUF ~5 GB, /kaggle/working chỉ có 20 GB."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    try:
        os.symlink(src, dst)
    except OSError:
        try:
            os.link(src, dst)
        except OSError:
            import shutil
            shutil.copy2(src, dst)


def _env_ghim_gpu(dev: int) -> dict[str, str]:
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(dev)
    return env


def _srcs(args) -> dict[str, str]:
    return {"graphrag": args.src_graphrag, "baseline": args.src_baseline}


def _so(x, n: int = 3) -> str:
    return "—" if x is None else f"{x:.{n}f}"


# ---------------------------------------------------------------------------
# prep
# ---------------------------------------------------------------------------

def stage_prep(args) -> int:
    _tieu_de("CHẶNG prep — wheel đã ghim + GGUF Qwen3-8B")

    print("\n[1/4] wheel llama-cpp-python — đối chiếu sha256 TRƯỚC khi cài")
    _pip("huggingface_hub==1.25.1", "hf_xet")
    wheel = _tai(WHEEL_REPO, WHEEL_FILE)
    tinh = sha256_file(wheel)
    if tinh != WHEEL_SHA256:
        print(f"\n❌ sha256 wheel LỆCH.\n   tính được {tinh}\n   đã ghim   {WHEEL_SHA256}\n"
              "   KHÔNG cài — bản dựng llama.cpp khác là đổi nền tái lập của mọi con số,\n"
              "   kể cả khi model và tham số sinh giống hệt.", file=sys.stderr)
        return 1
    print(f"  sha256 KHỚP ({tinh[:12]}…) → cài")
    if _pip(str(wheel)) != 0:
        print("❌ pip install wheel thất bại", file=sys.stderr)
        return 1

    print(f"\n[2/4] GGUF từ {args.gguf_repo}")
    gguf = None
    thu = [args.gguf_file] if args.gguf_file else GGUF_FILE_ALT
    for ten in thu:
        try:
            gguf = _tai(args.gguf_repo, ten, revision=args.gguf_revision)
            print(f"  tải được: {ten}")
            break
        except Exception as e:                       # noqa: BLE001 — thử tên kế tiếp
            print(f"  không lấy được {ten}: {type(e).__name__}")
    if gguf is None:
        print(f"\n❌ Không tải được file GGUF nào trong {thu} từ {args.gguf_repo}.\n"
              "   Mở trang repo xem tên file thật rồi truyền --gguf-file.", file=sys.stderr)
        return 1

    sha = sha256_file(gguf)
    print(f"  kích thước {gguf.stat().st_size / 1e9:.2f} GB")
    print(f"  sha256     {sha}")
    if args.gguf_sha256:
        if sha != args.gguf_sha256:
            print(f"\n❌ sha256 GGUF LỆCH so với giá trị đã ghim ({args.gguf_sha256}).\n"
                  "   File trên Hub đã đổi → DỪNG, đừng chạy tiếp bằng file khác.",
                  file=sys.stderr)
            return 1
        print("  sha256 KHỚP giá trị đã ghim")
    else:
        print("  ⚠️  CHƯA ghim sha256 (lần chạy đầu). Giá trị trên được ghi vào\n"
              "      8b_artifacts.json — lần sau truyền --gguf-sha256 <giá trị> để\n"
              "      biến thành cổng chặn thật, nếu không file Hub đổi mà số liệu\n"
              "      vẫn chạy tiếp trong im lặng.")

    print("\n[3/4] symlink vào finetune/models/")
    _symlink(gguf, MODELS_DIR / GGUF_LOCAL_NAME)
    print(f"  {_rel(MODELS_DIR / GGUF_LOCAL_NAME)} → {gguf}")

    print("\n[4/4] kiểm import finetune.replay (cài đúng module thiếu, tối đa 10 vòng)")
    # `finetune.replay` kéo theo src/retrieval → neo4j, qdrant-client… Cài đúng cái
    # thiếu, KHÔNG `pip install -r requirements.txt` (kéo cả torch/UI, có nguy cơ hạ
    # torch về bản CPU-only và làm hỏng lượt chạy GPU).
    for _ in range(10):
        r = subprocess.run(
            [sys.executable, "-c",
             "from finetune.replay import build_chat_messages; print('OK')"],
            cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if "OK" in (r.stdout or ""):
            print("  IMPORT OK")
            break
        m = re.search(r"No module named '([^']+)'", r.stderr or "")
        if not m:
            print((r.stderr or "")[-1500:])
            print("  ❌ lỗi import KHÔNG phải thiếu module → đọc traceback trên",
                  file=sys.stderr)
            return 1
        thieu = m.group(1).split(".")[0]
        print(f"  thiếu module {thieu} → cài")
        _pip(thieu)
    else:
        print("  ❌ vẫn thiếu module sau 10 vòng", file=sys.stderr)
        return 1

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_JSON.write_text(json.dumps({
        "wheel": {"repo": WHEEL_REPO, "file": WHEEL_FILE, "sha256": WHEEL_SHA256},
        "gguf": {"repo": args.gguf_repo, "file": gguf.name,
                 "revision": args.gguf_revision, "sha256": sha,
                 "size_bytes": gguf.stat().st_size,
                 "local": _rel(MODELS_DIR / GGUF_LOCAL_NAME)},
        # Ghi lại để báo cáo đọc được bộ tham số thật đã chạy, không phải bộ ai đó
        # nhớ lại. Bảy giá trị đầu là mặc định của replay.py, không truyền qua CLI.
        "gen_params": {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0.0,
                       "presence_penalty": 0.0, "seed": 42, "max_new_tokens": 2048,
                       "n_ctx": 16384, "n_gpu_layers": -1},
        "n_shot": N_SHOT,
        "srcs": {"graphrag": args.src_graphrag, "baseline": args.src_baseline},
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  đã ghi {_rel(ARTIFACTS_JSON)}")
    print("\n✅ prep xong")
    return 0


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

def _chay_o(cell: Cell, srcs: dict[str, str], dev: int) -> bool:
    _tieu_de(cell.nhan)
    gguf = MODELS_DIR / GGUF_LOCAL_NAME
    if not gguf.exists():
        print(f"❌ chưa có {_rel(gguf)} — chạy --stage prep trước", file=sys.stderr)
        return False

    cmd = [
        sys.executable, "-m", "finetune.replay",
        # replay.py tự đọc finetune/data/mode_map.json — KHÔNG truyền, và KHÔNG suy
        # lại mode từ nguồn: mode là ĐẦU VÀO của khâu sinh, phải ghim cố định giữa
        # các lượt, nếu không Δ giữa 8B và 4B lẫn cả khác biệt chế độ trả lời.
        "--input", srcs[cell.system],
        "--model", _rel(gguf),
        "--n-shot", str(N_SHOT),
        "--resume",
        "--tag", TAG,
        "--out", _rel(cell.out_path),
        # NGOẠI LỆ DUY NHẤT phải truyền: mặc định replay.py là 1.0, bộ đã chốt là 0.
        "--presence-penalty", "0",
        # KHÔNG truyền: --temperature --top-p --top-k --min-p --seed --max-new-tokens
        # --n-ctx --n-gpu-layers. Mặc định replay.py đã đúng bộ đã chốt.
        # KHÔNG truyền --limit / --ids: hai ô chạy đủ 137 câu.
    ]
    print(f"  $ CUDA_VISIBLE_DEVICES={dev} " + " ".join(cmd) + "\n")
    r = subprocess.run(cmd, cwd=REPO, env=_env_ghim_gpu(dev))
    if r.returncode != 0:
        print(f"\n❌ {cell.nhan} thất bại (rc={r.returncode})", file=sys.stderr)
        return False
    if not cell.out_path.exists():
        print(f"\n❌ không sinh {_rel(cell.out_path)}", file=sys.stderr)
        return False
    print(f"\n✅ {cell.nhan} → {_rel(cell.out_path)}")
    return True


def stage_run(args) -> int:
    _tieu_de("CHẶNG run — hai ô, tuần tự trên một card")
    srcs = _srcs(args)
    for he, rel in srcs.items():
        if not (REPO / rel).exists():
            print(f"❌ thiếu nguồn ngữ cảnh {he}: {rel}", file=sys.stderr)
            return 1
        print(f"  nguồn {he:9} = {rel}")

    try:
        chon = ([CELL_BY_IDX[int(i)] for i in args.cells.split(",") if i.strip()]
                if args.cells else CELLS)
    except (KeyError, ValueError):
        print(f"❌ --cells không hợp lệ: {args.cells!r} (chỉ nhận 1 và/hoặc 2)",
              file=sys.stderr)
        return 2
    print(f"  sẽ chạy ô {[c.idx for c in chon]} · CUDA_VISIBLE_DEVICES={args.gpu}")

    ok = True
    for cell in chon:
        if not _chay_o(cell, srcs, args.gpu):
            ok = False
            if not args.tiep_tuc_khi_loi:
                print("  DỪNG (dùng --tiep-tuc-khi-loi để chạy nốt ô còn lại)",
                      file=sys.stderr)
                break
    print("\n" + ("✅ run xong" if ok else "❌ run có ô thất bại"))
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# table
# ---------------------------------------------------------------------------

def _agg_file(rel: str) -> dict | None:
    """aggregate của src/evaluation/metrics.py trên một file kết quả."""
    from src.evaluation.metrics import aggregate
    p = REPO / rel
    if not p.exists():
        return None
    return aggregate(json.loads(p.read_text(encoding="utf-8"))["results"])


def _doc_o(cell: Cell) -> dict | None:
    """Đọc một ô → aggregate (KHÔNG tự tính lại) + chỉ báo sức khoẻ."""
    if not cell.out_path.exists():
        return None
    d = json.loads(cell.out_path.read_text(encoding="utf-8"))
    rep = d.get("replay", {})
    # elapsed trung bình CHỈ trên câu đi qua mô hình: cột GraphRAG có 10 câu hằng số
    # với elapsed = 0.0 (replay.py:566) → mean bị kéo xuống chỉ vì cột nào có bao
    # nhiêu câu hằng số. So hai cột thì phải so cùng một loại câu.
    qua = [r["elapsed_seconds"] for r in d["results"] if not r.get("frozen_copy")]
    return {
        "agg": _agg_file(_rel(cell.out_path)),
        "elapsed_mean_qua_mo_hinh": (sum(qua) / len(qua)) if qua else None,
        "n_qua": len(qua),
        "format_ok_rate": rep.get("format_ok_rate"),
        "n_hit_token_cap": rep.get("n_hit_token_cap"),
        "ids_hit_token_cap": rep.get("ids_hit_token_cap") or [],
        "backend": rep.get("backend"),
    }


def stage_table(args) -> int:
    _tieu_de("CHẶNG table — gom hai ô → finetune/reports/8b_eval.md")

    o = {c.idx: _doc_o(c) for c in CELLS}
    thieu = [CELL_BY_IDX[i].nhan for i in sorted(o) if o[i] is None]
    srcs = _srcs(args)

    L = [
        "# Qwen3-8B gốc, 2-shot — hai khuôn ngữ cảnh",
        "",
        "Sinh bởi `finetune/kaggle_8b_eval.py --stage table`. Mọi con số do",
        "`src/evaluation/metrics.py::aggregate` tính — script này KHÔNG tự tính lại thang",
        "đo nào và KHÔNG ghim số cứng chép từ báo cáo.",
        "",
        f"- Nguồn ngữ cảnh: `{srcs['graphrag']}` (GraphRAG) và `{srcs['baseline']}`",
        "  (Naive RAG) — đúng hai file của lượt 4B, nên Δ giữa hai lượt chỉ phản ánh mô",
        "  hình sinh, không lẫn khác biệt truy hồi.",
        "- Tham số sinh: bộ đã chốt ở `gate_base_model.md` §3, giống hệt lượt 4B.",
        "- `n_shot = 2` cho cả hai ô. Lượt 4B cho thấy mô hình gốc 0-shot hỏng định dạng",
        "  (`format_ok` 6.6%), nên 0-shot không được chạy lại ở đây.",
        "",
    ]
    if thieu:
        L += [f"> ⚠️ THIẾU {len(thieu)} ô: " + "; ".join(thieu) +
              " → các dòng tương ứng để trống, KHÔNG suy số từ ô còn lại.", ""]

    L += [
        "## 1. Bốn thang đo chính",
        "",
        "| Mô hình sinh | Hệ truy hồi | N | F1 Khoản | F1 Điều | Norm Recall | "
        "Từ chối đúng | format_ok |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for cell in CELLS:
        d = o[cell.idx]
        he = "GraphRAG" if cell.system == "graphrag" else "Naive RAG"
        if d is None or d["agg"] is None:
            L.append(f"| Qwen3-8B gốc 2-shot | {he} | — | — | — | — | — | — |")
            continue
        a = d["agg"]
        L.append(
            f"| Qwen3-8B gốc 2-shot | {he} | {a.get('count')} | "
            f"{_so(a.get('f1_mean'))} | {_so(a.get('f1_dieu_mean'))} | "
            f"{_so(a.get('norm_recall_mean'))} | {_so(a.get('negative_accuracy'))} | "
            f"{_so(d.get('format_ok_rate'))} |")

    L += ["",
          "## 2. Đối chiếu với Qwen3-4B gốc 2-shot",
          "",
          "Cùng ngữ cảnh, cùng tham số sinh, cùng `n_shot` → khác biệt duy nhất là cỡ mô",
          "hình. Số 4B đọc từ `finetune/results/results_{hệ}_" + TAG_4B + ".json`.",
          "",
          "| Hệ truy hồi | 4B F1 Khoản | 8B F1 Khoản | Δ (8B − 4B) | 4B format_ok | 8B format_ok |",
          "|---|---:|---:|---:|---:|---:|"]
    for cell in CELLS:
        he = "GraphRAG" if cell.system == "graphrag" else "Naive RAG"
        rel4 = f"finetune/results/results_{cell.system}_{TAG_4B}.json"
        a4 = _agg_file(rel4)
        p4 = REPO / rel4
        fmt4 = None
        if p4.exists():
            fmt4 = json.loads(p4.read_text(encoding="utf-8")).get(
                "replay", {}).get("format_ok_rate")
        d8 = o[cell.idx]
        f4 = a4.get("f1_mean") if a4 else None
        f8 = d8["agg"].get("f1_mean") if (d8 and d8["agg"]) else None
        delta = f"{f8 - f4:+.3f}" if (f4 is not None and f8 is not None) else "—"
        L.append(f"| {he} | {_so(f4)} | {_so(f8)} | {delta} | {_so(fmt4)} | "
                 f"{_so(d8.get('format_ok_rate')) if d8 else '—'} |")

    L += ["",
          "## 3. Sức khoẻ ô",
          "",
          "| Ô | backend | câu qua mô hình | giây/câu | chạm trần token |",
          "|---|---|---:|---:|---:|"]
    for cell in CELLS:
        d = o[cell.idx]
        if d is None:
            L.append(f"| {cell.nhan} | — | — | — | — |")
            continue
        cap = d.get("n_hit_token_cap")
        L.append(f"| {cell.nhan} | {d.get('backend') or '—'} | {d.get('n_qua')} | "
                 f"{_so(d.get('elapsed_mean_qua_mo_hinh'), 1)} | "
                 f"{cap if cap is not None else '—'} |")
    for cell in CELLS:
        d = o[cell.idx]
        if d and d.get("ids_hit_token_cap"):
            L.append("")
            L.append(f"- {cell.nhan} — id chạm trần: "
                     + ", ".join(f"`{i}`" for i in d["ids_hit_token_cap"]))
    L += ["",
          "> `n_hit_token_cap > 0` nghĩa là có câu bị cắt ở trần 2048 token → mất khối",
          "> trích dẫn cuối câu → F1 = 0 vì lý do KỸ THUẬT, không phải vì mô hình chọn sai",
          "> điều khoản. 8B sinh dài hơn 4B nên phải xem cột này trước khi diễn giải Δ.",
          ""]

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    BANG_MD.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    print(f"\n  đã ghi {_rel(BANG_MD)}")
    return 1 if thieu else 0


# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", required=True, choices=["prep", "run", "table"])
    ap.add_argument("--cells", default="",
                    help="danh sách ô cần chạy, vd '2' (mặc định cả hai)")
    ap.add_argument("--gpu", type=int, default=0,
                    help="card ghim cho subprocess qua CUDA_VISIBLE_DEVICES")
    ap.add_argument("--tiep-tuc-khi-loi", action="store_true",
                    help="ô hỏng thì chạy tiếp ô sau thay vì dừng")
    ap.add_argument("--gguf-repo", default=GGUF_REPO)
    ap.add_argument("--gguf-file", default="", help="ép tên file GGUF trên Hub")
    ap.add_argument("--gguf-revision", default=None, help="ghim revision của repo Hub")
    ap.add_argument("--gguf-sha256", default="",
                    help="bật cổng chặn sha256 cho GGUF (lấy từ 8b_artifacts.json)")
    ap.add_argument("--src-graphrag", default=SRC_GRAPHRAG)
    ap.add_argument("--src-baseline", default=SRC_BASELINE)
    args = ap.parse_args()

    return {"prep": stage_prep, "run": stage_run, "table": stage_table}[args.stage](args)


if __name__ == "__main__":
    sys.exit(main())
