"""Chạy Qwen3-30B-A3B-Instruct-2507 gốc, 2-shot, trên HAI khuôn ngữ cảnh.

    prep   wheel llama-cpp-python đã ghim + GGUF 18.6 GB + CỔNG CHẶN VRAM hai card
    run    hai ô tuần tự, có mốc thời gian/ETA từng câu và chốt dừng theo giờ
    table  gom kết quả (kể cả DANG DỞ) → finetune/reports/30b_eval.md

Dẫn xuất từ `kaggle_8b_eval.py`. Ba khác biệt bản chất, đều do cỡ model:

1. KHÔNG ghim `CUDA_VISIBLE_DEVICES`. 18.6 GB trọng số + KV cache của n_ctx 16384
   vượt 16 GB của một T4 → phải để llama.cpp thấy CẢ HAI card và tự chia layer
   (`LLAMA_SPLIT_MODE_LAYER` là mặc định của llama.cpp).

2. CỔNG CHẶN VRAM ở `prep`. `replay.py:272-279` khởi tạo `Llama(...)` KHÔNG truyền
   `split_mode` / `tensor_split` / `main_gpu`, nên ta không ép được tỉ lệ chia mà
   không sửa file đó. Nếu wheel đã ghim build một-GPU, model sẽ tràn xuống RAM CPU:
   vẫn CHẠY nhưng chậm hàng chục lần — đúng loại hỏng mà chốt giờ không cứu được vì
   lúc phát hiện thì đã muộn. Nên `prep` nạp thử model với n_ctx nhỏ rồi đọc
   `nvidia-smi`: không thấy VRAM trên CẢ HAI card thì TRẢ MÃ LỖI và dừng.

3. Chốt dừng theo giờ + mốc tiến độ. `replay.py:797` có in `[i/n]` nhưng KHÔNG có
   timestamp/elapsed/ETA. Script đọc stdout của subprocess theo dòng, bồi thêm ba
   thứ đó, và khi chạm hạn giờ thì dừng tử tế để `table` còn chạy được trên phần
   đã có.

────────────────────────────────────────────────────────────────────────────────
VÌ SAO DỪNG SỚM KHÔNG MẤT DỮ LIỆU
────────────────────────────────────────────────────────────────────────────────
`replay.py:782-793` ghi từng câu vào `.partial.jsonl` rồi `flush()` NGAY, không đợi
buffer. Nên giết tiến trình giữa chừng chỉ mất đúng câu đang sinh dở.

Hệ quả phải nhớ: file JSON đầu ra CHỈ được viết khi replay chạy hết. Đứt giữa chừng
thì chỉ còn `.partial.jsonl` → chặng `table` của script này đọc được CẢ HAI dạng.

`--resume` là BẮT BUỘC ở mọi lời gọi: `replay.py:734-735` cho thấy chạy KHÔNG kèm
`--resume` sẽ `unlink()` file partial — tức xoá sạch tiến độ cũ.

────────────────────────────────────────────────────────────────────────────────
THAM SỐ SINH — giống hệt lượt 4B và 8B, KHÔNG được đổi
────────────────────────────────────────────────────────────────────────────────
temperature 0.7 · top_p 0.8 · top_k 20 · min_p 0 · presence_penalty 0 · seed 42 ·
max_new_tokens 2048 · n_ctx 16384 · n_gpu_layers −1 (`gate_base_model.md` §3).

Bảy trong tám giá trị đã là mặc định của `replay.py` → không truyền lại.
**NGOẠI LỆ DUY NHẤT: `--presence-penalty 0`** — mặc định của `replay.py` là 1.0.

Đổi bất kỳ giá trị nào ở đây làm cột Δ so với hàng 4B/8B mất nghĩa.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

MODELS_DIR = REPO / "finetune/models"
REPORTS_DIR = REPO / "finetune/reports"
RESULTS_DIR = REPO / "finetune/results"

# --- nguồn ngữ cảnh: ĐÚNG hai file của lượt 4B/8B --------------------------------
SRC_GRAPHRAG = "data/evaluation/results_graphrag_final1_20260729-022916.json"
SRC_BASELINE = "data/evaluation/results_baseline_20260710-085236.json"

# --- wheel llama-cpp-python: ghim y hệt lượt 4B/8B -------------------------------
WHEEL_REPO = "dangnguyen254/thesis-graphrag-gguf"
WHEEL_FILE = "runtime/llama_cpp_python-0.3.16-cp312-cp312-linux_x86_64.whl"
WHEEL_SHA256 = "a3cb84bddb15c1759a0ece5ec8ef9d10d1419f926c895064d1a91ec517fd0da7"

# --- GGUF 30B-A3B ---------------------------------------------------------------
GGUF_REPO = "unsloth/Qwen3-30B-A3B-Instruct-2507-GGUF"
GGUF_LOCAL_NAME = "Qwen3-30B-A3B-Instruct-2507-Q4_K_M.gguf"
GGUF_FILE_ALT = [
    "Qwen3-30B-A3B-Instruct-2507-Q4_K_M.gguf",
    "Q4_K_M/Qwen3-30B-A3B-Instruct-2507-Q4_K_M.gguf",
    "qwen3-30b-a3b-instruct-2507-q4_k_m.gguf",
]

ARTIFACTS_JSON = REPORTS_DIR / "30b_artifacts.json"
BANG_MD = REPORTS_DIR / "30b_eval.md"

TAG = "30b-base-s2"
N_SHOT = 2

# Hai hàng đối chiếu — CHỈ ĐỌC, không chạy lại.
TAG_4B = "ft06b-base-s2"
TAG_8B = "8b-base-s2"

# Kaggle cắt session ở 12 giờ. Chừa 2 giờ để `table` chạy và để tải kết quả về.
GIO_TOI_DA_MAC_DINH = 10.0
# Ngưỡng coi là "card có tham gia": dưới mức này nghĩa là card gần như rỗng.
VRAM_TOI_THIEU_MIB = 2000

_RE_TIEN_DO = re.compile(r"^\s*\[(\d+)/(\d+)\]\s")


@dataclass(frozen=True)
class Cell:
    idx: int
    system: str          # "graphrag" | "baseline"

    @property
    def nhan(self) -> str:
        return f"ô {self.idx} · {self.system} · 30B-A3B gốc {N_SHOT}-shot"

    @property
    def out_path(self) -> Path:
        # Tên TẤT ĐỊNH (không timestamp): replay.py suy .partial.jsonl từ tên này,
        # nên tên có timestamp làm --resume vô dụng ngay lần đứt đầu tiên.
        return RESULTS_DIR / f"results_{self.system}_{TAG}.json"

    @property
    def partial_path(self) -> Path:
        return self.out_path.with_suffix(".partial.jsonl")


# GraphRAG trước: đó là ô có giá trị khoa học cao hơn, session đứt thì phần quan
# trọng đã xong.
CELLS = [Cell(1, "graphrag"), Cell(2, "baseline")]
CELL_BY_IDX = {c.idx: c for c in CELLS}


# ---------------------------------------------------------------------------
# Tiện ích
# ---------------------------------------------------------------------------

def _tieu_de(s: str) -> None:
    print(f"\n{'=' * 78}\n{s}\n{'=' * 78}", flush=True)


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
    return os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")


def _pip(*args: str) -> int:
    cmd = [sys.executable, "-m", "pip", "install", "-q", *args]
    print("  $", " ".join(cmd), flush=True)
    return subprocess.run(cmd).returncode


def _tai(repo: str, file: str, revision: str | None = None) -> Path:
    from huggingface_hub import hf_hub_download
    return Path(hf_hub_download(repo_id=repo, filename=file, revision=revision,
                                token=_hf_token()))


def _symlink(src: Path, dst: Path) -> None:
    """Symlink thay vì copy: GGUF 18.6 GB, /kaggle/working chỉ có ~20 GB."""
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


def _so(x, n: int = 3) -> str:
    return "—" if x is None else f"{x:.{n}f}"


def _dhms(giay: float) -> str:
    return str(timedelta(seconds=int(giay)))


def _srcs(args) -> dict[str, str]:
    return {"graphrag": args.src_graphrag, "baseline": args.src_baseline}


def _nvidia_smi() -> list[tuple[int, int, int]]:
    """→ [(index, memory_used_MiB, memory_total_MiB)]. Rỗng nếu không gọi được."""
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return []
    out = []
    for dong in (r.stdout or "").strip().splitlines():
        phan = [p.strip() for p in dong.split(",")]
        if len(phan) >= 3 and phan[0].isdigit():
            out.append((int(phan[0]), int(phan[1]), int(phan[2])))
    return out


# ---------------------------------------------------------------------------
# prep
# ---------------------------------------------------------------------------

# Chạy trong TIẾN TRÌNH CON: nạp model rồi tự đọc nvidia-smi khi trọng số còn nằm
# trên GPU. Đo từ tiến trình cha sau khi con thoát thì VRAM đã được giải phóng.
_KICH_BAN_KIEM_VRAM = r"""
import json, subprocess, sys
from llama_cpp import Llama
duong_dan, n_ctx = sys.argv[1], int(sys.argv[2])
llm = Llama(model_path=duong_dan, n_ctx=n_ctx, n_gpu_layers=-1, verbose=False)
r = subprocess.run(["nvidia-smi", "--query-gpu=index,memory.used,memory.total",
                    "--format=csv,noheader,nounits"], capture_output=True, text=True)
print("VRAM_JSON:" + json.dumps(r.stdout))
del llm
"""


def _kiem_vram(gguf: Path, n_ctx_thu: int) -> tuple[bool, list[tuple[int, int, int]]]:
    print(f"  nạp thử model với n_ctx={n_ctx_thu} (mất vài phút, 18.6 GB)…", flush=True)
    r = subprocess.run([sys.executable, "-c", _KICH_BAN_KIEM_VRAM,
                        str(gguf), str(n_ctx_thu)],
                       cwd=REPO, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print("  ❌ không nạp được model:", file=sys.stderr)
        print((r.stderr or "")[-2000:], file=sys.stderr)
        return False, []

    m = re.search(r"VRAM_JSON:(.*)", r.stdout or "")
    if not m:
        print("  ❌ không đọc được nvidia-smi từ tiến trình con", file=sys.stderr)
        return False, []
    cards: list[tuple[int, int, int]] = []
    for dong in json.loads(m.group(1)).strip().splitlines():
        phan = [p.strip() for p in dong.split(",")]
        if len(phan) >= 3 and phan[0].isdigit():
            cards.append((int(phan[0]), int(phan[1]), int(phan[2])))

    print("\n  VRAM khi model đã nạp:")
    for idx, used, total in cards:
        print(f"    GPU {idx}: {used:>6} / {total} MiB")

    dung = [c for c in cards if c[1] >= VRAM_TOI_THIEU_MIB]
    return len(dung) >= 2, cards


def stage_prep(args) -> int:
    _tieu_de("CHẶNG prep — wheel + GGUF 30B-A3B + cổng chặn VRAM hai card")

    print("\n[1/5] wheel llama-cpp-python — đối chiếu sha256 TRƯỚC khi cài")
    _pip("huggingface_hub==1.25.1", "hf_xet")
    wheel = _tai(WHEEL_REPO, WHEEL_FILE)
    tinh = sha256_file(wheel)
    if tinh != WHEEL_SHA256:
        print(f"\n❌ sha256 wheel LỆCH.\n   tính được {tinh}\n   đã ghim   {WHEEL_SHA256}",
              file=sys.stderr)
        return 1
    print(f"  sha256 KHỚP ({tinh[:12]}…) → cài")
    if _pip(str(wheel)) != 0:
        print("❌ pip install wheel thất bại", file=sys.stderr)
        return 1

    print("\n[2/5] card đang có")
    cards0 = _nvidia_smi()
    if not cards0:
        print("  ❌ không gọi được nvidia-smi — session này không có GPU?", file=sys.stderr)
        return 1
    for idx, used, total in cards0:
        print(f"    GPU {idx}: {used} / {total} MiB đang dùng")
    if len(cards0) < 2:
        print(f"\n❌ Chỉ thấy {len(cards0)} card. Model 18.6 GB + KV cache KHÔNG vừa một\n"
              "   T4 16 GB → phần thừa rơi xuống RAM CPU và chậm hàng chục lần.\n"
              "   Đặt Accelerator = GPU T4 x2 ở panel phải rồi chạy lại.", file=sys.stderr)
        return 1

    print(f"\n[3/5] GGUF từ {args.gguf_repo} (~18.6 GB, tải lâu)")
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
              "   Mở trang repo xem tên thật rồi truyền --gguf-file.", file=sys.stderr)
        return 1

    sha = sha256_file(gguf)
    print(f"  kích thước {gguf.stat().st_size / 1e9:.2f} GB")
    print(f"  sha256     {sha}")
    if args.gguf_sha256:
        if sha != args.gguf_sha256:
            print(f"\n❌ sha256 GGUF LỆCH so với giá trị đã ghim ({args.gguf_sha256}) → DỪNG.",
                  file=sys.stderr)
            return 1
        print("  sha256 KHỚP giá trị đã ghim")
    else:
        print("  ⚠️  CHƯA ghim sha256 (lần chạy đầu) — ghi vào 30b_artifacts.json;\n"
              "      lần sau truyền --gguf-sha256 để biến thành cổng chặn thật.")

    _symlink(gguf, MODELS_DIR / GGUF_LOCAL_NAME)
    print(f"  symlink {_rel(MODELS_DIR / GGUF_LOCAL_NAME)}")

    print("\n[4/5] kiểm import finetune.replay")
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
            print("  ❌ lỗi import KHÔNG phải thiếu module", file=sys.stderr)
            return 1
        thieu = m.group(1).split(".")[0]
        print(f"  thiếu module {thieu} → cài")
        _pip(thieu)
    else:
        print("  ❌ vẫn thiếu module sau 10 vòng", file=sys.stderr)
        return 1

    print("\n[5/5] CỔNG CHẶN VRAM — model phải nằm trên CẢ HAI card")
    ok, cards = _kiem_vram(MODELS_DIR / GGUF_LOCAL_NAME, args.n_ctx_kiem)
    if not ok:
        dung = [c for c in cards if c[1] >= VRAM_TOI_THIEU_MIB]
        print(f"\n❌ CỔNG CHẶN VRAM KHÔNG QUA — chỉ {len(dung)}/{len(cards)} card có "
              f"≥ {VRAM_TOI_THIEU_MIB} MiB.\n"
              "   Model KHÔNG được chia qua hai card. Nguyên nhân thường gặp:\n"
              "   • wheel llama-cpp-python đã ghim build một-GPU → phần thừa rơi xuống\n"
              "     RAM CPU, vẫn chạy nhưng chậm hàng chục lần (137 câu sẽ không kịp\n"
              "     trong 12 giờ của Kaggle);\n"
              "   • hoặc CUDA_VISIBLE_DEVICES đang bị ghim ở đâu đó — chặng run của\n"
              "     script này CỐ Ý không ghim, kiểm tra biến môi trường của session.\n"
              "   DỪNG ở đây thay vì đốt vài giờ GPU rồi mới biết.", file=sys.stderr)
        return 1
    print("  ✅ cả hai card đều giữ trọng số → llama.cpp đã chia layer")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_JSON.write_text(json.dumps({
        "wheel": {"repo": WHEEL_REPO, "file": WHEEL_FILE, "sha256": WHEEL_SHA256},
        "gguf": {"repo": args.gguf_repo, "file": gguf.name,
                 "revision": args.gguf_revision, "sha256": sha,
                 "size_bytes": gguf.stat().st_size,
                 "local": _rel(MODELS_DIR / GGUF_LOCAL_NAME)},
        "vram_sau_khi_nap": [{"gpu": i, "used_mib": u, "total_mib": t}
                             for i, u, t in cards],
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

def _chay_o(cell: Cell, srcs: dict[str, str], han_chot: float) -> tuple[bool, bool]:
    """→ (thành công, hết giờ). Bồi timestamp/elapsed/ETA vào dòng [i/n] của replay."""
    _tieu_de(cell.nhan)
    gguf = MODELS_DIR / GGUF_LOCAL_NAME
    if not gguf.exists():
        print(f"❌ chưa có {_rel(gguf)} — chạy --stage prep trước", file=sys.stderr)
        return False, False

    cmd = [
        sys.executable, "-u", "-m", "finetune.replay",
        # replay.py tự đọc finetune/data/mode_map.json — KHÔNG truyền, KHÔNG suy lại.
        "--input", srcs[cell.system],
        "--model", _rel(gguf),
        "--n-shot", str(N_SHOT),
        # BẮT BUỘC: thiếu cờ này thì replay.py:734-735 XOÁ .partial.jsonl cũ.
        "--resume",
        "--tag", TAG,
        "--out", _rel(cell.out_path),
        # NGOẠI LỆ DUY NHẤT phải truyền: mặc định replay.py là 1.0, bộ đã chốt là 0.
        "--presence-penalty", "0",
        # KHÔNG truyền tham số sinh còn lại — mặc định replay.py đã đúng bộ đã chốt.
        # KHÔNG ghim CUDA_VISIBLE_DEVICES: 18.6 GB cần cả hai T4, để llama.cpp
        # nhìn thấy cả hai card và tự chia layer.
    ]
    print("  $ " + " ".join(cmd))
    print(f"  hạn chót: {datetime.fromtimestamp(han_chot):%H:%M:%S}\n", flush=True)

    t0 = time.monotonic()
    het_gio = False
    n_xong = 0
    proc = subprocess.Popen(cmd, cwd=REPO, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace", bufsize=1)
    try:
        for dong in proc.stdout:                     # type: ignore[union-attr]
            dong = dong.rstrip("\n")
            m = _RE_TIEN_DO.match(dong)
            if m:
                i, n = int(m.group(1)), int(m.group(2))
                n_xong = i
                troi = time.monotonic() - t0
                # ETA suy từ tốc độ TRUNG BÌNH của phiên này. Câu đã có sẵn trong
                # .partial.jsonl chạy tức thì nên ETA ban đầu lạc quan quá — nó sẽ
                # tự chỉnh sau vài câu thật.
                moi_cau = troi / max(i, 1)
                eta = moi_cau * (n - i)
                print(f"{datetime.now():%H:%M:%S} {dong}  "
                      f"[trôi {_dhms(troi)} · ~{moi_cau:.0f}s/câu · ETA {_dhms(eta)}]",
                      flush=True)
            else:
                print(dong, flush=True)

            if time.monotonic() > han_chot:
                het_gio = True
                print(f"\n⏰ CHẠM HẠN GIỜ sau {n_xong} câu — dừng tử tế.\n"
                      "   .partial.jsonl đã flush từng câu nên chỉ mất câu đang sinh dở.\n"
                      "   Chạy lại chặng run (có --resume) để tiếp đúng chỗ.", flush=True)
                proc.terminate()
                try:
                    proc.wait(timeout=120)
                except subprocess.TimeoutExpired:
                    proc.kill()
                break
    finally:
        if proc.stdout:
            proc.stdout.close()
        rc = proc.wait()

    if het_gio:
        return False, True
    if rc != 0:
        print(f"\n❌ {cell.nhan} thất bại (rc={rc})", file=sys.stderr)
        return False, False
    print(f"\n✅ {cell.nhan} → {_rel(cell.out_path)} "
          f"({_dhms(time.monotonic() - t0)})")
    return True, False


def stage_run(args) -> int:
    _tieu_de("CHẶNG run — hai ô tuần tự, KHÔNG ghim card (cần cả 32 GB VRAM)")
    srcs = _srcs(args)
    for he, rel in srcs.items():
        if not (REPO / rel).exists():
            print(f"❌ thiếu nguồn ngữ cảnh {he}: {rel}", file=sys.stderr)
            return 1
        print(f"  nguồn {he:9} = {rel}")

    if os.getenv("CUDA_VISIBLE_DEVICES"):
        print(f"\n⚠️  CUDA_VISIBLE_DEVICES={os.environ['CUDA_VISIBLE_DEVICES']} đang được\n"
              "    đặt trong môi trường. Chặng này CỐ Ý không ghim card — nếu biến này\n"
              "    che mất một T4 thì model sẽ tràn xuống RAM CPU và chậm hàng chục lần.")

    try:
        chon = ([CELL_BY_IDX[int(i)] for i in args.cells.split(",") if i.strip()]
                if args.cells else CELLS)
    except (KeyError, ValueError):
        print(f"❌ --cells không hợp lệ: {args.cells!r} (chỉ nhận 1 và/hoặc 2)",
              file=sys.stderr)
        return 2

    han_chot = time.monotonic() + args.gio_toi_da * 3600
    print(f"  sẽ chạy ô {[c.idx for c in chon]} · ngân sách {args.gio_toi_da:g} giờ")
    for cell in chon:
        for p in (cell.partial_path, cell.out_path):
            if p.exists():
                n = (len([l for l in p.read_text(encoding='utf-8').splitlines() if l.strip()])
                     if p.suffix == ".jsonl" else None)
                print(f"    có sẵn {_rel(p)}" + (f" ({n} câu)" if n is not None else ""))

    ok_tat_ca, het_gio = True, False
    for cell in chon:
        if time.monotonic() > han_chot:
            print(f"\n⏰ hết ngân sách giờ trước khi vào {cell.nhan} — bỏ qua")
            het_gio = True
            break
        ok, hg = _chay_o(cell, srcs, han_chot)
        if hg:
            het_gio = True
            break
        if not ok:
            ok_tat_ca = False
            if not args.tiep_tuc_khi_loi:
                print("  DỪNG (dùng --tiep-tuc-khi-loi để chạy nốt ô còn lại)",
                      file=sys.stderr)
                break

    if het_gio:
        print("\n⏰ run DỪNG SỚM vì hạn giờ. Chạy `--stage table` để xem phần đã có,\n"
              "   rồi chạy lại `--stage run` trong session mới để tiếp.")
        return 2
    print("\n" + ("✅ run xong" if ok_tat_ca else "❌ run có ô thất bại"))
    return 0 if ok_tat_ca else 1


# ---------------------------------------------------------------------------
# table
# ---------------------------------------------------------------------------

def _doc_ket_qua(cell: Cell) -> tuple[list[dict], bool] | None:
    """→ (danh sách item, có_phải_dang_dở). None nếu chưa có gì.

    Ưu tiên file JSON đầy đủ; không có thì dựng từ `.partial.jsonl` — replay.py chỉ
    viết JSON khi chạy HẾT, nên đứt giữa chừng thì partial là thứ duy nhất còn lại.
    """
    if cell.out_path.exists():
        d = json.loads(cell.out_path.read_text(encoding="utf-8"))
        return d["results"], False
    if cell.partial_path.exists():
        items = [json.loads(l) for l in
                 cell.partial_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        return (items, True) if items else None
    return None


def _agg(items: list[dict]) -> dict | None:
    from src.evaluation.metrics import aggregate
    return aggregate(items) if items else None


def _agg_file(rel: str) -> dict | None:
    p = REPO / rel
    if not p.exists():
        return None
    return _agg(json.loads(p.read_text(encoding="utf-8"))["results"])


def _hang_doi_chieu(system: str, tag: str) -> tuple[dict | None, int]:
    """→ (aggregate, số câu). Đọc JSON đầy đủ, KHÔNG có thì lùi về .partial.jsonl.

    Cần cả hai đường vì file JSON của lượt 4B không nằm trên mọi nhánh: trên
    `dev/fine-tune` (nhánh mà notebook clone) tag `ft06b-*` chỉ còn `.partial.jsonl`.
    Chỉ đọc JSON là cột đối chiếu rỗng đúng lúc cần nhất, mà rỗng ở đây trông y hệt
    "chưa chạy" — sai lệch im lặng.
    """
    p = REPO / f"finetune/results/results_{system}_{tag}.json"
    if p.exists():
        items = json.loads(p.read_text(encoding="utf-8"))["results"]
        return _agg(items), len(items)
    pp = p.with_suffix(".partial.jsonl")
    if pp.exists():
        items = [json.loads(l) for l in
                 pp.read_text(encoding="utf-8").splitlines() if l.strip()]
        return (_agg(items), len(items)) if items else (None, 0)
    return None, 0


def stage_table(args) -> int:
    _tieu_de("CHẶNG table — gom kết quả (kể cả dang dở) → 30b_eval.md")
    srcs = _srcs(args)

    doc = {c.idx: _doc_ket_qua(c) for c in CELLS}
    L = [
        "# Qwen3-30B-A3B-Instruct-2507 gốc, 2-shot — hai khuôn ngữ cảnh",
        "",
        "Sinh bởi `finetune/kaggle_30b_eval.py --stage table`. Mọi con số do",
        "`src/evaluation/metrics.py::aggregate` tính — script KHÔNG tự tính lại thang đo.",
        "",
        f"- Nguồn ngữ cảnh: `{srcs['graphrag']}` (GraphRAG) và `{srcs['baseline']}`",
        "  (Naive RAG) — đúng hai file của lượt 4B và 8B, nên Δ giữa ba lượt chỉ phản",
        "  ánh mô hình sinh.",
        "- Tham số sinh: bộ đã chốt ở `gate_base_model.md` §3, giống hệt hai lượt trước.",
        "- Model chia layer qua **hai T4**; chặng `prep` có cổng chặn VRAM bắt buộc qua",
        "  trước khi được chạy.",
        "",
    ]

    dang_do = [CELL_BY_IDX[i].nhan for i, v in doc.items() if v and v[1]]
    thieu = [CELL_BY_IDX[i].nhan for i, v in doc.items() if v is None]
    if dang_do:
        L += ["> ⚠️ **KẾT QUẢ DANG DỞ** ở: " + "; ".join(dang_do) + ".",
              "> Số dựng từ `.partial.jsonl`, N < 137 → **KHÔNG so trực tiếp** với hàng",
              "> 4B/8B (đủ 137 câu) và không đưa vào báo cáo như số chốt.", ""]
    if thieu:
        L += ["> ⚠️ CHƯA CÓ kết quả: " + "; ".join(thieu) + ".", ""]

    L += ["## 1. Bốn thang đo chính", "",
          "| Mô hình sinh | Hệ truy hồi | N | Đủ 137? | F1 Khoản | F1 Điều | Norm Recall | Từ chối đúng |",
          "|---|---|---:|---|---:|---:|---:|---:|"]
    for cell in CELLS:
        he = "GraphRAG" if cell.system == "graphrag" else "Naive RAG"
        v = doc[cell.idx]
        if v is None:
            L.append(f"| 30B-A3B gốc 2-shot | {he} | — | — | — | — | — | — |")
            continue
        items, la_partial = v
        a = _agg(items) or {}
        du = "✅" if (len(items) == 137 and not la_partial) else f"❌ dang dở"
        L.append(f"| 30B-A3B gốc 2-shot | {he} | {len(items)} | {du} | "
                 f"{_so(a.get('f1_mean'))} | {_so(a.get('f1_dieu_mean'))} | "
                 f"{_so(a.get('norm_recall_mean'))} | {_so(a.get('negative_accuracy'))} |")

    L += ["", "## 2. Đối chiếu ba cỡ mô hình (cùng ngữ cảnh, cùng tham số sinh)", "",
          "Cột N đi kèm từng hàng: Δ chỉ có nghĩa khi hai vế cùng mẫu số 137.",
          "",
          "| Hệ truy hồi | 4B (N) | 8B (N) | 30B-A3B (N) | Δ (30B − 8B) | Δ (30B − 4B) |",
          "|---|---:|---:|---:|---:|---:|"]
    for cell in CELLS:
        he = "GraphRAG" if cell.system == "graphrag" else "Naive RAG"
        a4, n4 = _hang_doi_chieu(cell.system, TAG_4B)
        a8, n8 = _hang_doi_chieu(cell.system, TAG_8B)
        v = doc[cell.idx]
        a30 = _agg(v[0]) if v else None
        n30 = len(v[0]) if v else 0
        f4 = a4.get("f1_mean") if a4 else None
        f8 = a8.get("f1_mean") if a8 else None
        f30 = a30.get("f1_mean") if a30 else None
        # Δ chỉ in khi CÙNG mẫu số — khác N thì hiệu số không so được, và in ra
        # trông y hệt một con số hợp lệ.
        d8 = (f"{f30 - f8:+.3f}" if (f30 is not None and f8 is not None and n30 == n8)
              else ("≠N" if (f30 is not None and f8 is not None) else "—"))
        d4 = (f"{f30 - f4:+.3f}" if (f30 is not None and f4 is not None and n30 == n4)
              else ("≠N" if (f30 is not None and f4 is not None) else "—"))
        sao = " *" if (v and v[1]) else ""
        L.append(f"| {he} | {_so(f4)} ({n4 or '—'}) | {_so(f8)} ({n8 or '—'}) | "
                 f"{_so(f30)}{sao} ({n30 or '—'}) | {d8} | {d4} |")
    L += ["",
          "`≠N` = hai vế khác mẫu số nên KHÔNG trừ được; `*` = dựng từ kết quả dang dở."]

    L += ["", "## 3. Sức khoẻ ô", "",
          "| Ô | N | chạm trần token | ghi chú |", "|---|---:|---:|---|"]
    for cell in CELLS:
        v = doc[cell.idx]
        if v is None:
            L.append(f"| {cell.nhan} | — | — | chưa chạy |")
            continue
        items, la_partial = v
        cap = sum(1 for it in items if it.get("hit_token_cap"))
        L.append(f"| {cell.nhan} | {len(items)} | {cap} | "
                 f"{'dựng từ .partial.jsonl' if la_partial else 'file JSON đầy đủ'} |")
    L += ["",
          "> Chạm trần token nghĩa là câu bị cắt ở 2048 token → mất khối trích dẫn cuối",
          "> câu → F1 = 0 vì lý do KỸ THUẬT, không phải vì mô hình chọn sai điều khoản.",
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
    ap.add_argument("--cells", default="", help="danh sách ô, vd '2' (mặc định cả hai)")
    ap.add_argument("--gio-toi-da", type=float, default=GIO_TOI_DA_MAC_DINH,
                    help="ngân sách giờ cho chặng run (Kaggle cắt ở 12h)")
    ap.add_argument("--tiep-tuc-khi-loi", action="store_true")
    ap.add_argument("--gguf-repo", default=GGUF_REPO)
    ap.add_argument("--gguf-file", default="", help="ép tên file GGUF trên Hub")
    ap.add_argument("--gguf-revision", default=None)
    ap.add_argument("--gguf-sha256", default="",
                    help="bật cổng chặn sha256 (lấy từ 30b_artifacts.json)")
    ap.add_argument("--n-ctx-kiem", type=int, default=512,
                    help="n_ctx dùng cho cổng chặn VRAM ở prep")
    ap.add_argument("--src-graphrag", default=SRC_GRAPHRAG)
    ap.add_argument("--src-baseline", default=SRC_BASELINE)
    args = ap.parse_args()

    return {"prep": stage_prep, "run": stage_run, "table": stage_table}[args.stage](args)


if __name__ == "__main__":
    sys.exit(main())
