#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TASK-FT-06 — chạy SÁU Ô của ma trận mục 4.7. Script này chạy TRÊN KAGGLE T4.

Chia thành `--stage` vì session Kaggle có thể đứt bất cứ lúc nào và `/kaggle/working`
bị xoá theo session: mỗi chặng chạy lại được độc lập, và chặng `run` đẩy kết quả lên
HF ngay sau từng ô thay vì đợi tới cuối.

    prep           tải + đối chiếu sha256 wheel llama-cpp-python và hai file GGUF
    gate-template  CỔNG CHẶN A — chat template nhúng trong hai GGUF phải trùng khít
    gate-prompt    CỔNG CHẶN B — đọc prompt đã render bằng mắt (món nợ của FT-03 §5.2)
    run            sáu ô, mỗi ô một lệnh `finetune.replay`, đẩy HF sau từng ô
    table          gom sáu file kết quả → finetune/reports/ft06_matrix.md

Kaggle cấp **T4 x2** → xem khối chú thích "Ghim GPU" dưới đây: mỗi lời gọi `replay.py`
ghim đúng MỘT card qua `CUDA_VISIBLE_DEVICES` của subprocess. `--parallel` (mặc định
TẮT) chia sáu ô thành hai luồng, mỗi luồng một card, trong luồng thì tuần tự.

Sáu ô (thứ tự đã sắp có chủ ý — ô giá trị nhất trước, để session đứt thì phần quan
trọng đã có trên HF):

    1. FT   n_shot 0  graphrag     4. base n_shot 2  baseline
    2. FT   n_shot 0  baseline     5. base n_shot 0  graphrag
    3. base n_shot 2  graphrag     6. base n_shot 0  baseline

Hàng FT chỉ chạy 0-shot: bộ huấn luyện FT-04 dựng bằng CHÍNH `build_messages`, tức mô
hình đã được dạy đúng khuôn (system, user) → chèn thêm hai cặp minh hoạ định dạng là
tạo lệch train/eval. Hàng gốc chạy CẢ HAI vì với nó few-shot là biến thật:
`format_ok` nhảy 0.083 → 0.833 (gate_base_model.md §1).

────────────────────────────────────────────────────────────────────────────────
THAM SỐ SINH — đọc trước khi sửa bất cứ dòng nào
────────────────────────────────────────────────────────────────────────────────
Bộ đã chốt (gate_base_model.md §3): temperature 0.7 · top_p 0.8 · top_k 20 · min_p 0
· presence_penalty 0 · seed 42 · max_new_tokens 2048 · n_ctx 16384 · n_gpu_layers -1.

Script KHÔNG truyền lại bảy trong tám giá trị đó: chúng đã là mặc định của
`replay.py` (`GenParams` dòng 159-168, `DEFAULT_N_CTX` dòng 86, `--n-gpu-layers`
dòng 648, `--seed` dòng 645). Truyền lại là nhân đôi nguồn chân lý — đổi ở một ô mà
quên ô khác thì cột Δ của mục 4.7 so hai thứ khác nhau mà không có dấu hiệu gì.

**NGOẠI LỆ DUY NHẤT — `--presence-penalty 0` PHẢI truyền tường minh.** Mặc định của
`replay.py` là **1.0** (dòng 166), KHÔNG phải 0. `gate_base_model.md` §3 chốt 0 theo
quy tắc đăng ký trước ("chọn giá trị nhỏ nhất mà `hit_token_cap = 0`"). Không truyền
là chạy sai bộ đã chốt — đúng loại lỗi im lặng mà §3 cảnh báo.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

MODELS_DIR = REPO / "finetune/models"
REPORTS_DIR = REPO / "finetune/reports"
RESULTS_DIR = REPO / "finetune/results"

# Nguồn ngữ cảnh: PHẢI là cặp file của CÙNG một mẻ chạy 20260710-085236 — chính mẻ
# sinh ra 0.578 (GraphRAG) và 0.435 (Naive RAG) ở hàng Gemini. Trộn hai timestamp
# khác nhau là đổi luôn vế trái của cột Δ.
SRC_GRAPHRAG = "data/evaluation/results_graphrag_20260710-085236.json"
SRC_BASELINE = "data/evaluation/results_baseline_20260710-085236.json"
SRC_BY_SYSTEM = {"graphrag": SRC_GRAPHRAG, "baseline": SRC_BASELINE}

# Hàng Gemini — lấy từ báo cáo (kế hoạch §2), KHÔNG tính lại ở đây.
GEMINI_F1_NAIVE = 0.435
GEMINI_F1_GRAPHRAG = 0.578
GEMINI_DELTA = 0.143

HF_REPO_DEFAULT = "dangnguyen254/thesis-graphrag-gguf"
HF_PREFIX_DEFAULT = "session3_ft06"

# Khoá metadata GGUF chứa chat template. KHÔNG đoán: đây đúng là khoá mà
# `replay.py:323` đọc (`meta.get("tokenizer.chat_template")` trên
# `Llama.metadata`) — cùng chuỗi mà llama.cpp thực dùng. Chặng gate-template vẫn
# kiểm lại sự tồn tại của khoá lúc chạy và in mọi khoá gần giống nếu thiếu.
CHAT_TEMPLATE_KEY = "tokenizer.chat_template"

# Thẻ vai của ChatML (Qwen3). Không hardcode mù: chặng gate-prompt kiểm ba chuỗi này
# có thật trong file template mà chặng gate-template đã ghi ra, và cảnh báo nếu không.
SYSTEM_OPEN = "<|im_start|>system"
ASSISTANT_OPEN = "<|im_start|>assistant"
TURN_END = "<|im_end|>"

# `replay.py:759` chèn dòng phân cách 70 ký tự '#' giữa header và prompt.
DUMP_SEPARATOR = "#" * 70

# Ràng buộc phiên bản — cùng bộ đã ghim ở phiên FT-03/FT-05
# (`notebooks/vn-legal-graphrag (5).ipynb` ô 7). Dùng làm `-c` cho MỌI lệnh pip để
# một lần cài phụ thuộc phụ không âm thầm hạ torch về bản CPU-only hoặc đổi
# llama_cpp_python sang bản khác cái wheel đã đối chiếu sha256.
CONSTRAINTS = """\
torch==2.10.0
torchvision==0.25.0
torchaudio==2.10.0
transformers==5.5.0
trl==0.24.0
peft==0.20.0
unsloth==2026.7.5
huggingface_hub==1.25.1
llama_cpp_python==0.3.16
"""


# ---------------------------------------------------------------------------
# Hiện vật đã ghim
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Artifact:
    """Một file phải tải về và đối chiếu sha256 trước khi dùng."""

    ten: str
    repo: str
    file: str
    sha256: str | None
    revision: str | None = None
    local_name: str | None = None   # tên file trong finetune/models/ (None = không symlink)


# Wheel llama-cpp-python: sha256 lấy từ khối "Giá trị đã ghim — tuyên bố tái lập" ở
# đầu `notebooks/kaggle_clean.ipynb` (dòng "wheel sha256"). Bản dựng cp312 + CUDA
# 75;89 — sm75 là T4.
WHEEL = Artifact(
    ten="wheel llama-cpp-python 0.3.16",
    repo=HF_REPO_DEFAULT,
    file="runtime/llama_cpp_python-0.3.16-cp312-cp312-linux_x86_64.whl",
    sha256="a3cb84bddb15c1759a0ece5ec8ef9d10d1419f926c895064d1a91ec517fd0da7",
)

FT_GGUF = Artifact(
    ten="GGUF đã tinh chỉnh (FT-05)",
    repo=HF_REPO_DEFAULT,
    file="gguf/ft04-5k-2ep-20260729-2122-Q4_K_M.gguf",
    sha256="c115e6a79299d1fe0e41eb5f6720955108df1e869676dc96f0b7ba61c37ce5d0",
    local_name="ft04-5k-2ep-20260729-2122-Q4_K_M.gguf",
)

# ⚠️ GGUF GỐC — `sha256` CỐ Ý ĐỂ None, xem `_resolve_base_pin`.
# `gate_base_model.md` và `finetune/README.md` chỉ ghi TÊN model. Phiên FT-03 đọc
# revision + sha256 từ `/kaggle/working/base_manifest.json`
# (`notebooks/vn-legal-graphrag (5).ipynb` ô 15: `old["repo"]`, `old["file"]`,
# `old["revision"]`, `old["sha256"]`) — file đó chưa từng được commit.
#
# `revision` thì KHÔI PHỤC ĐƯỢC, không phải đoán: nó nằm trong **output đã lưu** của
# chính ô 15 notebook đó, hai chỗ độc lập —
#   HEAD .../resolve/ae44f08e1392f39c0e474af10c3ff8355c8b6688/Qwen_…-Q4_K_M.gguf
#   path mới: …/snapshots/ae44f08e1392f39c0e474af10c3ff8355c8b6688/Qwen_…-Q4_K_M.gguf
# và ô đó chạy `assert h == old["sha256"]` rồi in "OK, sha256 khớp bản đã ghi", tức
# đúng revision này đã qua cổng sha256 ở phiên 1.
#
# `sha256` thì KHÔNG khôi phục được: ô 15 in kết luận chứ không in chuỗi hash, và
# không có chuỗi 64 hex nào của file GGUF gốc trong repo. Điền tay là bịa giá trị
# ghim → script đọc lúc chạy và exit 1 nếu không có.
BASE_GGUF_REPO = "bartowski/Qwen_Qwen3-4B-Instruct-2507-GGUF"
BASE_GGUF_FILE = "Qwen_Qwen3-4B-Instruct-2507-Q4_K_M.gguf"
BASE_GGUF_REVISION = "ae44f08e1392f39c0e474af10c3ff8355c8b6688"
# 8 ký tự đầu của sha256 — phần DUY NHẤT được ghi lại (trong đơn việc FT-06). Không
# đủ làm cổng chặn, nhưng đủ để bắt lỗi "cung cấp sai hash của file khác".
BASE_SHA256_PREFIX = "2fde00ce"
# Tên cục bộ giữ ĐÚNG như phiên FT-03 (bartowski có tiền tố `Qwen_`, repo mong đợi
# tên không tiền tố — `kaggle_clean.ipynb` ô 24).
BASE_LOCAL_NAME = "Qwen3-4B-Instruct-2507-Q4_K_M.gguf"


# ---------------------------------------------------------------------------
# Sáu ô
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Cell:
    idx: int
    model_key: str      # "ft" | "base"
    n_shot: int
    system: str         # "graphrag" | "baseline"
    tag: str

    @property
    def out_path(self) -> Path:
        # Đường dẫn TẤT ĐỊNH (không có timestamp). Bắt buộc để `--resume` sống qua
        # session đứt: `replay.py:725` suy file .partial.jsonl từ tên file đầu ra, nên
        # nếu tên đổi mỗi lần chạy thì --resume luôn bắt đầu lại từ 0.
        return RESULTS_DIR / f"results_{self.system}_{self.tag}.json"

    @property
    def partial_path(self) -> Path:
        return self.out_path.with_suffix(".partial.jsonl")

    @property
    def nhan(self) -> str:
        return f"ô {self.idx}: {self.model_key} n_shot={self.n_shot} {self.system}"


CELLS = [
    Cell(1, "ft", 0, "graphrag", "ft06-ft-s0"),
    Cell(2, "ft", 0, "baseline", "ft06-ft-s0"),
    Cell(3, "base", 2, "graphrag", "ft06-base-s2"),
    Cell(4, "base", 2, "baseline", "ft06-base-s2"),
    Cell(5, "base", 0, "graphrag", "ft06-base-s0"),
    Cell(6, "base", 0, "baseline", "ft06-base-s0"),
]
CELL_BY_IDX = {c.idx: c for c in CELLS}

# Cặp ô cùng model + cùng n_shot, khác nguồn ngữ cảnh — dùng ở chặng table để đối
# chiếu elapsed_seconds giữa hai card.
CAP_O = [(1, 2), (3, 4), (5, 6)]

# --- Ghim GPU -------------------------------------------------------------------
# Kaggle cấp T4 **x2**. Với `--n-gpu-layers -1` và hai card nhìn thấy được, llama.cpp
# tự chia layer qua cả hai. Q4_K_M chỉ 2,4 GB nên chia KHÔNG nhanh hơn, mà đổi thứ tự
# rút gọn → có thể lệch số học. Nguy hiểm thật không phải chậm mà là **không nhất
# quán giữa các ô**: khi đó cột Δ đo lẫn cả khác biệt phần cứng.
#
# Nên MỌI lời gọi `replay.py` chạy với `CUDA_VISIBLE_DEVICES` ghim đúng MỘT card,
# truyền qua env của subprocess — KHÔNG đặt biến toàn cục cho cả script (đặt toàn cục
# thì chặng gate-template/table cũng bị ảnh hưởng, và không còn thấy được ô nào ghim
# card nào).
#
# Chia luồng khi --parallel: mỗi luồng một card, trong luồng thì TUẦN TỰ. Không chia
# một ô qua hai card, không chạy hai ô cùng lúc trên cùng một card (tranh VRAM + tranh
# I/O làm `elapsed_seconds` vô nghĩa, mà đó là số liệu đi vào bảng).
LANES: dict[int, list[int]] = {
    0: [1, 3, 2],   # FT s0 graphrag → base s2 graphrag → FT s0 baseline
    1: [5, 4, 6],   # base s0 graphrag → base s2 baseline → base s0 baseline
}
GPU_TUAN_TU = 0     # chế độ tuần tự: mọi ô trên card này

GPU_INFO_PATH = REPORTS_DIR / "ft06_gpu_info.json"
# Log của hai luồng ghi ra file riêng rồi in gộp khi cả hai xong. KHÔNG dùng threading
# để trộn stdout — log lẫn vào nhau là không đọc được.
LOG_DIR = Path("/kaggle/working") if Path("/kaggle/working").is_dir() else RESULTS_DIR


# ---------------------------------------------------------------------------
# Tiện ích
# ---------------------------------------------------------------------------

def _tieu_de(s: str) -> None:
    print("\n" + "=" * 78)
    print(s)
    print("=" * 78)


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _constraints_path() -> Path:
    p = Path("/kaggle/working/ft06_constraints.txt")
    if not p.parent.exists():
        p = REPO / "finetune/results/ft06_constraints.txt"
        p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(CONSTRAINTS, encoding="utf-8")
    return p


def _pip(*args: str) -> int:
    cmd = [sys.executable, "-m", "pip", "install", "-q", *args,
           "-c", str(_constraints_path())]
    print("  $", " ".join(cmd))
    return subprocess.run(cmd).returncode


def _hf_token() -> str | None:
    # Notebook nạp token qua kaggle_secrets rồi đặt vào os.environ. KHÔNG hardcode.
    return os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")


def _tai(art_repo: str, art_file: str, revision: str | None = None) -> Path:
    from huggingface_hub import hf_hub_download

    p = hf_hub_download(repo_id=art_repo, filename=art_file, revision=revision,
                        token=_hf_token())
    return Path(p)


def _symlink(src: Path, dst: Path) -> None:
    """Symlink thay vì copy: GGUF ~2,5 GB, `/kaggle/working` chỉ có 20 GB."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    try:
        os.symlink(src, dst)
    except OSError:
        # Windows không có quyền symlink mặc định → hardlink, cuối cùng mới copy.
        try:
            os.link(src, dst)
        except OSError:
            import shutil
            shutil.copy2(src, dst)


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(REPO)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


# ---------------------------------------------------------------------------
# Ghim GPU
# ---------------------------------------------------------------------------

def _env_ghim_gpu(dev: int) -> dict[str, str]:
    """env cho MỘT subprocess, ghim đúng một card. Không đụng os.environ của script."""
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(dev)
    return env


def _nvidia_smi() -> list[str]:
    """`nvidia-smi --query-gpu=index,name,memory.total --format=csv` → list dòng."""
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,memory.total", "--format=csv"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError) as e:  # noqa: PERF203
        return [f"(không chạy được nvidia-smi: {type(e).__name__})"]
    if r.returncode != 0:
        return [f"(nvidia-smi rc={r.returncode}: {(r.stderr or '').strip()[:200]})"]
    return [l for l in (r.stdout or "").splitlines() if l.strip()]


def _ghim_map(song_song: bool, gpu: int | None) -> dict[int, int]:
    """{số ô: card}. Nguồn duy nhất cho cả lúc chạy và lúc lập bảng."""
    if gpu is not None:
        return {c.idx: gpu for c in CELLS}
    if song_song:
        return {idx: dev for dev, idxs in LANES.items() for idx in idxs}
    return {c.idx: GPU_TUAN_TU for c in CELLS}


def _bao_cao_gpu(song_song: bool, gpu: int | None, nguon: str) -> dict:
    """In + ghi ft06_gpu_info.json. Chặng table đọc lại để đưa vào ft06_matrix.md.

    Đây là **giá trị ghim thứ bảy** của tuyên bố tái lập: mọi ô chạy trên ĐÚNG MỘT T4,
    ghim tường minh. Phải ghi vào khoá luận cùng với sáu giá trị kia.
    """
    smi = _nvidia_smi()
    # Số card NHÌN THẤY ĐƯỢC ở mức script (nvidia-smi bỏ dòng tiêu đề).
    n_thay = max(0, len([l for l in smi if not l.lower().startswith("index")]))
    ghim = _ghim_map(song_song, gpu)
    che_do = ("song song, hai luồng, mỗi luồng một card" if song_song and gpu is None
              else f"tuần tự, mọi ô trên card {ghim[1]}")

    _tieu_de("GHIM PHẦN CỨNG — giá trị ghim thứ bảy của tuyên bố tái lập")
    for l in smi:
        print("  " + l)
    print(f"\n  số card nhìn thấy được : {n_thay}")
    print(f"  chế độ                 : {che_do}   ({nguon})")
    print(f"  CUDA_VISIBLE_DEVICES của từng ô:")
    for c in CELLS:
        print(f"    ô {c.idx}  {c.model_key:<4} n_shot={c.n_shot}  {c.system:<8} "
              f"→ CUDA_VISIBLE_DEVICES={ghim[c.idx]}")
    if n_thay > 1 and not song_song and gpu is None:
        print(f"\n  Ghi chú: thấy {n_thay} card nhưng chạy TUẦN TỰ trên card "
              f"{GPU_TUAN_TU}. Đó là mặc định có chủ ý — mỗi ô vẫn ghim đúng một card, "
              f"nên llama.cpp không chia layer qua hai card. Muốn dùng cả hai: --parallel.")

    d = {
        "nvidia_smi_csv": smi,
        "n_card_nhin_thay": n_thay,
        "che_do": che_do,
        "song_song": bool(song_song and gpu is None),
        "ghim_cuda_visible_devices": {str(k): v for k, v in ghim.items()},
        "nguon": nguon,
    }
    GPU_INFO_PATH.parent.mkdir(parents=True, exist_ok=True)
    GPU_INFO_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  ghi → {_rel(GPU_INFO_PATH)}")
    return d


# ---------------------------------------------------------------------------
# Ghim của model gốc — đọc lúc chạy, KHÔNG điền tay
# ---------------------------------------------------------------------------

def _resolve_base_pin(args) -> tuple[str, str, str, str]:
    """Trả (repo, file, revision, sha256) cho GGUF gốc.

    Thứ tự tìm: cờ CLI → biến môi trường → `base_manifest.json` (chính file mà phiên
    FT-03 dùng). Không có thì exit 1 — thà dừng còn hơn chạy 822 lượt trên một file
    không chứng minh được là đúng file của FT-03.
    """
    repo, file = BASE_GGUF_REPO, BASE_GGUF_FILE
    rev = args.base_revision or os.getenv("FT06_BASE_REVISION")
    sha = args.base_sha256 or os.getenv("FT06_BASE_SHA256")
    nguon_rev = "cờ CLI / biến môi trường" if rev else ""
    nguon_sha = "cờ CLI / biến môi trường" if sha else ""

    if not (rev and sha):
        mf = Path(args.base_manifest)
        if mf.exists():
            m = json.loads(mf.read_text(encoding="utf-8"))
            repo = m.get("repo", repo)
            file = m.get("file", file)
            if not rev and m.get("revision"):
                rev, nguon_rev = m["revision"], str(mf)
            if not sha and m.get("sha256"):
                sha, nguon_sha = m["sha256"], str(mf)

    if not rev:
        rev = BASE_GGUF_REVISION
        nguon_rev = "output đã lưu của notebook FT-03 ô 15 (xem chú thích trong file này)"

    if not sha:
        print(
            "\n❌ DỪNG — không có sha256 đã ghim của GGUF GỐC.\n"
            f"   repo     : {repo}\n"
            f"   file     : {file}\n"
            f"   revision : {rev}  ({nguon_rev})\n"
            "   sha256   : KHÔNG CÓ\n\n"
            "   Giá trị này không nằm trong repo. `gate_base_model.md` và\n"
            "   `finetune/README.md` chỉ ghi tên model; phiên FT-03 đọc nó từ\n"
            "   `/kaggle/working/base_manifest.json` (notebook FT-03 ô 15), mà file đó\n"
            "   chưa từng được commit — và ô đó in kết luận 'sha256 khớp' chứ không in\n"
            "   chuỗi hash, nên output notebook cũng không khôi phục được.\n\n"
            "   Script CỐ Ý không tự điền: ghim bịa thì cổng chặn sha256 thành vô nghĩa.\n"
            "   Ba cách cung cấp:\n"
            f"     1. để `{args.base_manifest}` tồn tại với khoá `sha256`\n"
            "        (đúng khuôn FT-03: repo / file / revision / sha256)\n"
            "     2. --base-sha256 <sha>\n"
            "     3. FT06_BASE_SHA256=<sha>\n\n"
            f"   Ghi chú: revision ĐÃ được ghim ({rev[:12]}…) nên bản tải về vốn đã\n"
            "   khoá theo commit bất biến của Hub; sha256 là ổ khoá thứ hai, độc lập —\n"
            "   nó bắt cả trường hợp file tải về bị hỏng dở giữa đường.\n",
            file=sys.stderr,
        )
        raise SystemExit(1)

    if BASE_SHA256_PREFIX and not sha.startswith(BASE_SHA256_PREFIX):
        print(f"  ⚠️  sha256 cung cấp bắt đầu bằng {sha[:8]!r}, đơn việc FT-06 ghi "
              f"{BASE_SHA256_PREFIX!r} → có thể đang ghim hash của FILE KHÁC. Kiểm lại.")

    print(f"  ghim GGUF gốc — revision: {nguon_rev}")
    print(f"                  sha256  : {nguon_sha}")
    return repo, file, rev, sha


# ---------------------------------------------------------------------------
# CHẶNG prep
# ---------------------------------------------------------------------------

def _bang_sha(rows: list[tuple[str, int, str, str]]) -> bool:
    """In bảng tên/dung lượng/sha tính được/sha ghim/KHỚP-LỆCH. Trả True nếu tất cả khớp."""
    print(f"\n  {'file':<52} {'GB':>6}  {'kết luận':<7}")
    print("  " + "-" * 74)
    ok_all = True
    for ten, size, tinh, ghim in rows:
        ok = tinh == ghim
        ok_all &= ok
        print(f"  {ten[:52]:<52} {size / 1e9:>6.2f}  {'KHỚP' if ok else 'LỆCH':<7}")
        print(f"    tính được: {tinh}")
        print(f"    đã ghim  : {ghim}")
    return ok_all


def stage_prep(args) -> int:
    _tieu_de("CHẶNG prep — cài wheel đã ghim + tải hai GGUF, đối chiếu sha256")

    if not _hf_token():
        print("  ⚠️  không có HF_TOKEN trong môi trường. Repo model là private thì "
              "bước tải sẽ 401. Notebook nạp token qua kaggle_secrets.")

    base_repo, base_file, base_rev, base_sha = _resolve_base_pin(args)

    # --- 1. wheel: đối chiếu sha256 TRƯỚC khi pip install -----------------------
    print(f"\n[1/3] {WHEEL.ten}")
    wheel = _tai(WHEEL.repo, WHEEL.file)
    tinh = sha256_file(wheel)
    if tinh != WHEEL.sha256:
        print(f"\n❌ sha256 wheel LỆCH.\n   tính được {tinh}\n   đã ghim   {WHEEL.sha256}\n"
              "   KHÔNG cài. Bản dựng llama.cpp khác là đổi luôn nền tái lập của mọi "
              "con số ở mục 4.7.", file=sys.stderr)
        return 1
    print(f"  sha256 KHỚP → cài")
    if _pip(str(wheel)) != 0:
        print("❌ pip install wheel thất bại", file=sys.stderr)
        return 1

    # `huggingface_hub` bị ghim ở 1.25.1 (hub v1.x đã gỡ hf_transfer → dùng hf_xet).
    _pip("huggingface_hub==1.25.1", "hf_xet")

    # --- 2. hai file GGUF -------------------------------------------------------
    print(f"\n[2/3] tải hai file GGUF")
    rows: list[tuple[str, int, str, str]] = []

    print(f"  gốc: {base_repo} :: {base_file} @ {base_rev}")
    base_p = _tai(base_repo, base_file, revision=base_rev)
    rows.append((base_file, base_p.stat().st_size, sha256_file(base_p), base_sha))

    print(f"  FT : {FT_GGUF.repo} :: {FT_GGUF.file}")
    ft_p = _tai(FT_GGUF.repo, FT_GGUF.file)
    rows.append((FT_GGUF.file, ft_p.stat().st_size, sha256_file(ft_p), FT_GGUF.sha256))

    print(f"\n[3/3] bảng đối chiếu")
    if not _bang_sha(rows):
        print("\n❌ Có file LỆCH sha256 → DỪNG. File trên Hub đã đổi so với bản đã ghim; "
              "chạy tiếp là ghi vào khoá luận một con số không tái lập được.",
              file=sys.stderr)
        return 1

    _symlink(base_p, MODELS_DIR / BASE_LOCAL_NAME)
    _symlink(ft_p, MODELS_DIR / FT_GGUF.local_name)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n  symlink → {_rel(MODELS_DIR / BASE_LOCAL_NAME)}")
    print(f"  symlink → {_rel(MODELS_DIR / FT_GGUF.local_name)}")

    # Ghi lại ghim đã dùng — để chặng sau không phải giải lại, và để khoá luận có
    # một file duy nhất trả lời "đã chạy trên đúng những file nào".
    (REPORTS_DIR / "ft06_artifacts.json").write_text(json.dumps({
        "wheel": {"repo": WHEEL.repo, "file": WHEEL.file, "sha256": WHEEL.sha256},
        "base": {"repo": base_repo, "file": base_file, "revision": base_rev,
                 "sha256": base_sha, "local": _rel(MODELS_DIR / BASE_LOCAL_NAME)},
        "ft": {"repo": FT_GGUF.repo, "file": FT_GGUF.file, "sha256": FT_GGUF.sha256,
               "local": _rel(MODELS_DIR / FT_GGUF.local_name)},
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # --- kiểm import: khuôn FT-03 (notebook ô 11) -------------------------------
    # `finetune.replay` kéo theo src/retrieval → neo4j, anthropic, qdrant-client,
    # sentence-transformers. Cài đúng cái thiếu, không `pip install -r
    # requirements.txt` (sẽ kéo cả torch/UI và có nguy cơ hạ torch về CPU-only).
    print("\n  kiểm import finetune.replay (cài đúng module thiếu, tối đa 10 vòng)")
    for _ in range(10):
        r = subprocess.run(
            [sys.executable, "-c", "from finetune.replay import build_chat_messages; print('OK')"],
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
        mod = m.group(1).split(".")[0]
        print(f"  thiếu: {mod} → cài")
        _pip(mod)
    else:
        print("  ❌ quá 10 vòng vẫn không import được", file=sys.stderr)
        return 1

    # Chế độ ở đây là DỰ KIẾN (đọc từ cờ --parallel của chính lệnh prep); chặng run
    # ghi lại lần nữa với nguồn "thực tế".
    _bao_cao_gpu(args.parallel, args.gpu, "prep — dự kiến")

    print("\n✅ prep XONG. Chặng kế: --stage gate-template")
    return 0


# ---------------------------------------------------------------------------
# CỔNG CHẶN A — chat template
# ---------------------------------------------------------------------------

def _doc_chat_template(gguf: Path) -> str | None:
    """Đọc chat template nhúng trong GGUF, qua CHÍNH đường mà replay.py dùng.

    Tái dùng `replay.make_backend` (dòng 367) → `LlamaCppBackend._llm.metadata`, đúng
    như `replay.py:322-323`. Không tự mở file GGUF bằng parser riêng: khác đường đọc
    thì cổng chặn này không còn nói gì về prompt mà mẻ chạy thực nhận.

    `n_gpu_layers=0` + `n_ctx=512`: chỉ cần metadata, không sinh gì — không có lý do
    chiếm VRAM của T4 hai lần liên tiếp.
    """
    from finetune.replay import GenParams, make_backend

    backend = make_backend(str(gguf), 512, 0, GenParams())
    meta = backend._llm.metadata or {}
    if CHAT_TEMPLATE_KEY not in meta:
        gan = sorted(k for k in meta if "template" in k.lower() or "chat" in k.lower())
        print(f"  ❌ không có khoá {CHAT_TEMPLATE_KEY!r} trong metadata GGUF.\n"
              f"     khoá gần giống: {gan}\n"
              f"     tổng số khoá: {len(meta)}", file=sys.stderr)
        return None
    return meta[CHAT_TEMPLATE_KEY]


def stage_gate_template(args) -> int:
    _tieu_de("CỔNG CHẶN A — chat template nhúng trong hai GGUF phải trùng khít")
    print("Nếu hai file mang template khác nhau thì hai hàng của ma trận nhận prompt\n"
          "khác nhau, và cột Δ không còn đo mô hình sinh mà đo cả khác biệt prompt.")

    paths = {"base": MODELS_DIR / BASE_LOCAL_NAME, "ft": MODELS_DIR / FT_GGUF.local_name}
    tmpl: dict[str, str] = {}
    for ten, p in paths.items():
        if not p.exists():
            print(f"❌ thiếu {_rel(p)} → chạy `--stage prep` trước", file=sys.stderr)
            return 1
        print(f"\n  đọc template từ {ten}: {_rel(p)}")
        t = _doc_chat_template(p)
        if t is None:
            return 2
        out = REPORTS_DIR / f"ft06_chat_template_{ten}.jinja"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(t, encoding="utf-8")
        tmpl[ten] = t
        print(f"    độ dài {len(t):,} ký tự · sha256 {sha256_text(t)}")
        print(f"    ghi → {_rel(out)}")

    a, b = tmpl["base"], tmpl["ft"]
    print(f"\n  base: {len(a):>7,} ký tự  sha256 {sha256_text(a)}")
    print(f"  ft  : {len(b):>7,} ký tự  sha256 {sha256_text(b)}")

    if sha256_text(a) == sha256_text(b):
        print("\n✅ TRÙNG KHÍT — hai hàng của ma trận nhận cùng một khuôn prompt.")
        print("   Hệ quả dùng được ở cổng chặn B: chỉ cần dump prompt bằng MỘT model.")
        return 0

    diff = list(difflib.unified_diff(a.splitlines(), b.splitlines(),
                                     fromfile="base.jinja", tofile="ft.jinja",
                                     lineterm=""))
    n_khac = sum(1 for l in diff
                 if l[:1] in "+-" and not l.startswith(("+++", "---")))
    print(f"\n  KHÁC — {n_khac} dòng khác nhau. difflib.unified_diff (tối đa 60 dòng):")
    for l in diff[:60]:
        print("   " + l)
    if len(diff) > 60:
        print(f"   … còn {len(diff) - 60} dòng nữa, xem hai file .jinja đã ghi")

    print(f"\n❌ KHÁC ({n_khac} dòng). Dừng. Hai hàng của ma trận sẽ nhận prompt khác "
          "nhau, cột Δ mất ý nghĩa. Báo người phụ trách.", file=sys.stderr)
    return 2


# ---------------------------------------------------------------------------
# CỔNG CHẶN B — prompt đã render
# ---------------------------------------------------------------------------

def _tach_dump(text: str) -> tuple[str, str]:
    """Cắt file --dump-prompt thành (header, body). Phân cách: replay.py:759."""
    if DUMP_SEPARATOR in text:
        h, _, b = text.partition(DUMP_SEPARATOR)
        return h, b.lstrip("\n")
    return "", text


def _kiem_mot_prompt(path: Path, system: str, n_shot: int) -> list[tuple[str, bool, str]]:
    """Năm kiểm tra tự động trên một file prompt đã dump. Trả list (tên, ok, chi tiết)."""
    from finetune.replay import MODE_MAP_PATH, build_chat_messages

    text = path.read_text(encoding="utf-8")
    header, body = _tach_dump(text)
    kq: list[tuple[str, bool, str]] = []

    # (1) render bằng chat template thật, KHÔNG phải nhánh lùi.
    # replay.py:351 trả "render-loi:<Exception>" khi jinja2 nổ → header sẽ mang chuỗi đó.
    ok = "render=gguf-chat-template-jinja2" in header
    kq.append(("render bằng chat template GGUF (không phải render-loi:…)", ok,
               next((l for l in header.splitlines() if "render=" in l), "(không thấy dòng render=)")))

    # (2) system prompt còn nguyên đầu.
    # ⚠️ Bản đặc tả yêu cầu so với `src_data["system"]`, nhưng khoá đó trong results
    # JSON là TÊN HỆ ("graphrag"/"baseline"), không phải system prompt
    # (replay.py:686 dùng nó làm khoá tra mode_map). System prompt thật là phần tử 0
    # của `build_messages` → dựng lại bằng CHÍNH `build_chat_messages` rồi so.
    src = json.loads((REPO / SRC_BY_SYSTEM[system]).read_text(encoding="utf-8"))
    first = next(s for s in src["results"] if s["top_k_count"] > 0)
    mode = json.loads(MODE_MAP_PATH.read_text(encoding="utf-8"))["he_thong"][system]["mode_map"][first["id"]]
    msgs = build_chat_messages(first["question"], first["context"], mode, n_shot)
    dau200 = msgs[0]["content"][:200]

    i = body.find(SYSTEM_OPEN)
    if i < 0:
        kq.append((f"có thẻ mở vai system ({SYSTEM_OPEN})", False, "không tìm thấy"))
    else:
        sau = body[i + len(SYSTEM_OPEN):].lstrip("\n")
        ok = sau.startswith(dau200)
        kq.append(("200 ký tự đầu system prompt khớp build_messages", ok,
                   f"chờ {dau200[:60]!r}… · thấy {sau[:60]!r}…"))

    # (3) số lượt vai
    ky_vong = 2 if n_shot == 0 else 6
    ok = len(msgs) == ky_vong
    kq.append((f"số tin nhắn = {ky_vong}", ok,
               f"thấy {len(msgs)}: {[m['role'] for m in msgs]}"))

    # (4) prompt kết thúc bằng "TRẢ LỜI:" rồi tới thẻ mở vai assistant
    j = body.rfind(ASSISTANT_OPEN)
    if j < 0:
        kq.append(("kết thúc bằng thẻ mở vai assistant", False, "không tìm thấy"))
    else:
        truoc = body[:j].rstrip()
        if truoc.endswith(TURN_END):
            truoc = truoc[: -len(TURN_END)].rstrip()
        ok = truoc.endswith("TRẢ LỜI:")
        kq.append(('nội dung cuối trước thẻ assistant là "TRẢ LỜI:"', ok,
                   f"…{truoc[-40:]!r}"))

    # (5) số lần xuất hiện thẻ mở vai assistant
    ky_vong_as = 1 if n_shot == 0 else 3
    thay = body.count(ASSISTANT_OPEN)
    kq.append((f"số thẻ mở vai assistant = {ky_vong_as}", thay == ky_vong_as,
               f"thấy {thay}"))
    return kq


def stage_gate_prompt(args) -> int:
    _tieu_de("CỔNG CHẶN B — đọc prompt đã render bằng mắt")
    print("Đây là kiểm tra hạ tầng #2 của gate_base_model.md §5 — treo từ phiên 1 của")
    print("FT-03 ('hai file --dump-prompt đã sinh nhưng chưa ai mở ra nhìn bằng mắt').")
    print("Chặng này đóng đúng món nợ đó: sinh lại prompt cho cả BỐN tổ hợp, kiểm tự")
    print("động năm mục, rồi in ra để người đọc nhìn tận mắt.\n")

    # Dùng model FT: cổng chặn A đã chứng minh hai template trùng khít, nên một model
    # là đủ; và FT là hiện vật CHƯA TỪNG được render (base đã dump ở FT-03).
    gguf = MODELS_DIR / FT_GGUF.local_name
    if not gguf.exists():
        print(f"❌ thiếu {_rel(gguf)} → chạy `--stage prep` trước", file=sys.stderr)
        return 1
    print(f"  model dùng để render: {_rel(gguf)} (cổng A đã chứng minh base ≡ ft)")

    # Kiểm ba thẻ vai có thật trong template đã ghi ở cổng A — không hardcode mù.
    tpl = REPORTS_DIR / "ft06_chat_template_ft.jinja"
    if tpl.exists():
        t = tpl.read_text(encoding="utf-8")
        thieu = [s for s in (SYSTEM_OPEN, ASSISTANT_OPEN, TURN_END) if s not in t]
        if thieu:
            print(f"  ⚠️  thẻ vai không thấy trong template: {thieu} → mục (4)(5) có "
                  f"thể FAIL vì sai giả định ChatML, không vì prompt sai")
    else:
        print("  ⚠️  chưa có ft06_chat_template_ft.jinja (chạy gate-template trước) → "
              "không kiểm chéo được giả định ChatML")

    to_hop = [("graphrag", 0), ("graphrag", 2), ("baseline", 0), ("baseline", 2)]
    tat_ca_ok = True
    for system, n_shot in to_hop:
        dump = REPORTS_DIR / f"ft06_prompt_{system}_s{n_shot}.txt"
        _tieu_de(f"{system} · n_shot={n_shot}")
        cmd = [
            sys.executable, "-m", "finetune.replay",
            "--input", SRC_BY_SYSTEM[system],
            "--model", _rel(gguf),
            "--limit", "1",
            "--n-shot", str(n_shot),
            "--dump-prompt", _rel(dump),
            "--out", _rel(RESULTS_DIR / f"results_{system}_ft06-gate-prompt-s{n_shot}.json"),
            # Bộ đã chốt ở gate_base_model.md §3. CHỈ presence_penalty phải truyền
            # tường minh (mặc định replay.py là 1.0) — xem docstring đầu file.
            "--presence-penalty", "0",
        ]
        print("  $ " + " ".join(cmd))
        r = subprocess.run(cmd, cwd=REPO)
        if r.returncode != 0 or not dump.exists():
            print(f"  ❌ replay thất bại (rc={r.returncode}) hoặc không sinh {_rel(dump)}",
                  file=sys.stderr)
            tat_ca_ok = False
            continue

        print(f"\n  --- KẾT QUẢ KIỂM TỰ ĐỘNG: {_rel(dump)} ---")
        for ten, ok, chi_tiet in _kiem_mot_prompt(dump, system, n_shot):
            print(f"   [{'PASS' if ok else 'FAIL'}] {ten}")
            print(f"          {chi_tiet}")
            tat_ca_ok &= ok

        dong = dump.read_text(encoding="utf-8").splitlines()
        print(f"\n  --- 40 DÒNG ĐẦU ({_rel(dump)}, tổng {len(dong)} dòng) ---")
        for l in dong[:40]:
            print("   " + l[:300])
        print(f"  --- 20 DÒNG CUỐI ---")
        for l in dong[-20:]:
            print("   " + l[:300])

    if not tat_ca_ok:
        print("\n❌ Cổng chặn B KHÔNG QUA. Dừng — chạy 822 lượt trên một prompt khác "
              "cái ta tưởng là mất trắng cả mẻ. Đọc mục FAIL ở trên.", file=sys.stderr)
        return 2
    print("\n✅ Cổng chặn B QUA cả bốn tổ hợp. Món nợ kiểm tra hạ tầng #2 của "
          "gate_base_model.md §5 đã đóng.")
    return 0


# ---------------------------------------------------------------------------
# CHẶNG run
# ---------------------------------------------------------------------------

def _status_path(gpu: int | None) -> Path:
    """File trạng thái. Hai luồng song song phải ghi hai file khác nhau — chung một
    file là hai tiến trình ghi đè lẫn nhau và mất một nửa báo cáo."""
    hau_to = f"_gpu{gpu}" if gpu is not None else ""
    return REPORTS_DIR / f"ft06_run_status{hau_to}.json"


def _doc_status(p: Path) -> dict:
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def _ghi_status(p: Path, d: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def _hf_keo_partial(cell: Cell, repo: str, prefix: str) -> None:
    """Session Kaggle chết → `/kaggle/working` bị xoá → file .partial.jsonl mất.

    Kéo lại từ HF để `--resume` thực sự tiếp tục thay vì bắt đầu lại từ câu 1.
    Best-effort: không có thì thôi.
    """
    if cell.partial_path.exists():
        return
    try:
        p = _tai(repo, f"{prefix}/{cell.partial_path.name}")
        cell.partial_path.parent.mkdir(parents=True, exist_ok=True)
        cell.partial_path.write_bytes(Path(p).read_bytes())
        n = sum(1 for l in cell.partial_path.read_text(encoding="utf-8").splitlines() if l.strip())
        print(f"  kéo lại {cell.partial_path.name} từ HF ({n} item) → --resume tiếp được")
    except Exception as e:  # noqa: BLE001
        print(f"  (không kéo được partial từ HF: {type(e).__name__} — coi như chạy mới)")


def _hf_day(paths: list[Path], repo: str, prefix: str) -> None:
    from huggingface_hub import upload_file

    for p in paths:
        if not p.exists():
            continue
        try:
            upload_file(path_or_fileobj=str(p), path_in_repo=f"{prefix}/{p.name}",
                        repo_id=repo, token=_hf_token())
            print(f"  ĐÃ ĐẨY → {repo}/{prefix}/{p.name}")
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠️  đẩy {p.name} THẤT BẠI: {type(e).__name__}: {e}\n"
                  f"      Kết quả vẫn còn ở {_rel(p)} — session chết là mất.")


def _run_song_song(args) -> int:
    """Hai luồng bằng subprocess, mỗi luồng ghim MỘT card, mỗi luồng một file log.

    Không dùng threading: hai mẻ sinh mỗi mẻ 400+ dòng tiến độ, trộn vào một stdout là
    không đọc được. Log riêng → in gộp khi cả hai xong.
    """
    g = _bao_cao_gpu(True, None, "run — thực tế")
    n_thay = g.get("n_card_nhin_thay") or 0
    if n_thay < len(LANES):
        print(f"\n❌ --parallel cần {len(LANES)} card, chỉ thấy {n_thay}.\n"
              f"   Ghim vào một card không tồn tại thì llama.cpp không thấy GPU nào và\n"
              f"   ÂM THẦM lùi về CPU — ô đó chạy hàng giờ rồi cho ra số không so được\n"
              f"   với ô chạy trên GPU. Bỏ --parallel để chạy tuần tự trên card "
              f"{GPU_TUAN_TU}.", file=sys.stderr)
        return 1
    chon = set(args.cells) if args.cells else None

    luong: list[dict] = []
    for dev, idxs in LANES.items():
        lane = [i for i in idxs if chon is None or i in chon]
        if not lane:
            print(f"  luồng card {dev}: không có ô nào được chọn → bỏ qua")
            continue
        log = LOG_DIR / f"ft06_gpu{dev}.log"
        cmd = [sys.executable, str(Path(__file__).resolve()), "--stage", "run",
               "--gpu", str(dev), "--cells", ",".join(str(i) for i in lane),
               "--hf-repo", args.hf_repo, "--hf-prefix", args.hf_prefix]
        if args.no_push:
            cmd.append("--no-push")
        print(f"\n  luồng card {dev}: ô {lane} → log {log}")
        print("  $ " + " ".join(cmd))
        fh = log.open("w", encoding="utf-8")
        # env ghim card cho CẢ luồng con: mọi lời gọi replay.py bên trong nó kế thừa,
        # và luồng con còn ghim lại lần nữa ở từng lời gọi (đai + dây lưng).
        p = subprocess.Popen(cmd, cwd=REPO, stdout=fh, stderr=subprocess.STDOUT,
                             env=_env_ghim_gpu(dev))
        luong.append({"dev": dev, "o": lane, "log": log, "proc": p, "fh": fh})

    print("\n  cả hai luồng đang chạy. Chờ… (mỗi luồng ~3 ô × 137 câu, tuần tự trong luồng)")
    for L in luong:
        # Chỉ CHỜ, không kill: một luồng hỏng thì luồng kia vẫn chạy tiếp.
        L["rc"] = L["proc"].wait()
        L["fh"].close()
        print(f"  luồng card {L['dev']} kết thúc rc={L['rc']}")

    for L in luong:
        _tieu_de(f"LOG LUỒNG CARD {L['dev']} — ô {L['o']}  ({L['log']})")
        print(L["log"].read_text(encoding="utf-8", errors="replace")
              if L["log"].exists() else "(không có log)")

    # Gộp hai file trạng thái để chặng table và người đọc thấy toàn cảnh.
    gop: dict = {}
    for L in luong:
        gop.update(_doc_status(_status_path(L["dev"])))
    _ghi_status(_status_path(None), gop)

    _tieu_de("TỔNG KẾT SÁU Ô")
    for c in CELLS:
        v = gop.get(c.tag + "|" + c.system)
        if v is None:
            print(f"  {c.nhan:<34} KHÔNG CHẠY")
        elif v["returncode"] == 0:
            print(f"  {c.nhan:<34} OK   card {v.get('gpu')}  {v.get('aggregate') or ''}")
        else:
            print(f"  {c.nhan:<34} HỎNG rc={v['returncode']} card {v.get('gpu')}")
    hong_luong = [L["dev"] for L in luong if L["rc"] != 0]
    if hong_luong:
        print(f"\n  ⚠️  luồng hỏng: card {hong_luong} — xem log tương ứng ở trên")
    if not args.no_push:
        _hf_day([_status_path(None), GPU_INFO_PATH], args.hf_repo, args.hf_prefix)
    print("\n  Chặng kế: --stage table")
    return 0


def stage_run(args) -> int:
    if args.parallel and args.gpu is None:
        return _run_song_song(args)

    dev = args.gpu if args.gpu is not None else GPU_TUAN_TU
    _tieu_de(f"CHẶNG run — SÁU Ô, tuần tự, CUDA_VISIBLE_DEVICES={dev}")
    if args.gpu is None:
        _bao_cao_gpu(False, None, "run — thực tế")

    gguf = {"base": MODELS_DIR / BASE_LOCAL_NAME, "ft": MODELS_DIR / FT_GGUF.local_name}
    for k, p in gguf.items():
        if not p.exists():
            print(f"❌ thiếu GGUF {k}: {_rel(p)} → chạy `--stage prep` trước", file=sys.stderr)
            return 1

    # Giữ ĐÚNG thứ tự người gõ ở --cells: luồng song song truyền thứ tự của luồng
    # (vd 1,3,2) và thứ tự đó có chủ ý.
    thu_tu = [CELL_BY_IDX[i] for i in args.cells] if args.cells else list(CELLS)
    sp = _status_path(args.gpu)
    status = _doc_status(sp)

    for cell in thu_tu:
        _tieu_de(f"{cell.nhan}  card {dev}  → {_rel(cell.out_path)}")
        if not args.no_push:
            _hf_keo_partial(cell, args.hf_repo, args.hf_prefix)

        cmd = [
            sys.executable, "-m", "finetune.replay",
            "--input", SRC_BY_SYSTEM[cell.system],
            "--model", _rel(gguf[cell.model_key]),
            "--n-shot", str(cell.n_shot),
            "--resume",
            "--tag", cell.tag,
            # --out TẤT ĐỊNH: replay.py:725 suy .partial.jsonl từ tên file đầu ra, nên
            # tên có timestamp làm --resume vô dụng ngay lần đứt đầu tiên.
            "--out", _rel(cell.out_path),
            # NGOẠI LỆ DUY NHẤT phải truyền: mặc định replay.py là 1.0, bộ đã chốt là 0
            # (gate_base_model.md §3). Sáu ô dùng GIỐNG HỆT một bộ tham số sinh.
            "--presence-penalty", "0",
            # KHÔNG truyền: --temperature --top-p --top-k --min-p --seed
            # --max-new-tokens --n-ctx --n-gpu-layers. Mặc định replay.py đã đúng bộ
            # đã chốt; truyền lại là nhân đôi nguồn chân lý.
            # KHÔNG truyền --limit / --ids: sáu ô chạy đủ 137 câu.
        ]
        print(f"  $ CUDA_VISIBLE_DEVICES={dev} " + " ".join(cmd) + "\n")

        agg_line, dong_cuoi = "", []
        # Ghim card qua env của SUBPROCESS. Không đặt os.environ toàn cục: một ô chia
        # layer qua hai card trong khi ô khác không là confound phần cứng ngay trong
        # cùng cột Δ, và đặt toàn cục thì không còn thấy được ô nào ghim card nào.
        proc = subprocess.Popen(cmd, cwd=REPO, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True,
                                encoding="utf-8", errors="replace", bufsize=1,
                                env=_env_ghim_gpu(dev))
        for line in proc.stdout:            # stream ra notebook, đừng nuốt
            sys.stdout.write(line)
            sys.stdout.flush()
            dong_cuoi.append(line.rstrip("\n"))
            if "aggregate:" in line:
                agg_line = line.strip()
        rc = proc.wait()

        status[cell.tag + "|" + cell.system] = {
            "o": cell.idx, "model": cell.model_key, "n_shot": cell.n_shot,
            "system": cell.system, "returncode": rc, "gpu": dev,
            "out": _rel(cell.out_path), "aggregate": agg_line or None,
        }
        _ghi_status(sp, status)

        if rc != 0:
            print(f"\n  ⚠️  CẢNH BÁO — {cell.nhan} HỎNG (rc={rc}). VẪN CHẠY TIẾP các ô "
                  f"sau; ô này sẽ hiện là thiếu trong bảng cuối.")
            print("      " + " | ".join(dong_cuoi[-3:]))
        else:
            print(f"\n  {agg_line or '(không thấy dòng aggregate trong stdout)'}")

        # Đẩy NGAY, kể cả khi rc != 0 — partial dở vẫn cứu được nửa mẻ.
        if not args.no_push:
            _hf_day([cell.out_path, cell.partial_path, sp],
                    args.hf_repo, args.hf_prefix)

    xong = [k for k, v in status.items() if v["returncode"] == 0]
    print(f"\n  {len(xong)}/{len(thu_tu)} ô của lượt này xong"
          + ("" if args.gpu is None else f" (luồng card {dev})")
          + (". Chặng kế: --stage table" if args.gpu is None else "."))
    return 0


# ---------------------------------------------------------------------------
# CHẶNG table
# ---------------------------------------------------------------------------

def _doc_o(cell: Cell) -> dict | None:
    """Đọc một file kết quả → aggregate (KHÔNG tự tính lại) + chỉ báo sức khoẻ ô."""
    from src.evaluation.metrics import aggregate

    if not cell.out_path.exists():
        return None
    d = json.loads(cell.out_path.read_text(encoding="utf-8"))
    rep = d.get("replay", {})
    # elapsed trung bình mỗi câu, CHỈ trên câu đi qua mô hình. `aggregate` tính
    # latency_mean_s trên cả 137 item, mà 10 câu hằng số của cột GraphRAG có
    # elapsed = 0.0 (replay.py:566) → mean bị kéo xuống ~7% chỉ vì cột nào có bao
    # nhiêu câu hằng số. So hai card thì phải so cùng một loại câu.
    qua = [r["elapsed_seconds"] for r in d["results"] if not r.get("frozen_copy")]
    return {
        "agg": aggregate(d["results"]),
        "elapsed_mean_qua_mo_hinh": (sum(qua) / len(qua)) if qua else None,
        "n_qua": len(qua),
        "format_ok_rate": rep.get("format_ok_rate"),
        "format_ok_mau_so": rep.get("format_ok_mau_so"),
        "n_hit_token_cap": rep.get("n_hit_token_cap"),
        "ids_hit_token_cap": rep.get("ids_hit_token_cap") or [],
        "soft_article_hit_mean": rep.get("soft_article_hit_mean"),
        "n_qua_mo_hinh": rep.get("n_qua_mo_hinh"),
        "n_cau": len(d["results"]),
        "file": _rel(cell.out_path),
    }


def _f(v, fmt=".3f") -> str:
    return f"{v:{fmt}}" if isinstance(v, (int, float)) else "—"


def _tu_choi(agg: dict) -> str:
    if "negative_correct_rate" not in agg:
        return "—"
    n = agg.get("negative_count", 0)
    r = agg["negative_correct_rate"]
    return f"{r:.3f} ({round(r * n)}/{n})"


LECH_LATENCY_NGUONG = 0.25   # 25% — ngưỡng cảnh báo throttle giữa hai card


def _muc_ghim_gpu() -> list[str]:
    """Mục 3 của báo cáo: ghim phần cứng — giá trị ghim thứ bảy."""
    L = ["", "## 3. Ghim phần cứng — giá trị ghim thứ bảy", ""]
    if not GPU_INFO_PATH.exists():
        return L + [f"`{_rel(GPU_INFO_PATH)}` chưa có (chạy `--stage prep` hoặc "
                    "`--stage run`). **Không có mục này thì tuyên bố tái lập còn thiếu "
                    "một giá trị ghim.**"]
    g = json.loads(GPU_INFO_PATH.read_text(encoding="utf-8"))
    L += [
        "Kaggle cấp **T4 x2**. Với `--n-gpu-layers -1` và hai card nhìn thấy được,",
        "llama.cpp tự chia layer qua cả hai. Q4_K_M chỉ 2,4 GB nên chia **không nhanh",
        "hơn**, mà đổi thứ tự rút gọn → có thể lệch số học; và cái nguy hiểm thật là",
        "**không nhất quán giữa các ô**, khi đó cột Δ đo lẫn cả khác biệt phần cứng.",
        "Nên mọi lời gọi `replay.py` ghim đúng **một** card qua `CUDA_VISIBLE_DEVICES`",
        "của subprocess.",
        "",
        "```",
        *[f"{l}" for l in g.get("nvidia_smi_csv", [])],
        "```",
        "",
        f"- số card nhìn thấy được: **{g.get('n_card_nhin_thay')}**",
        f"- chế độ đã dùng: **{g.get('che_do')}** (ghi nhận lúc: {g.get('nguon')})",
        "",
        "| Ô | Mô hình | n_shot | Hệ | `CUDA_VISIBLE_DEVICES` |",
        "|---:|---|---:|---|---:|",
    ]
    ghim = g.get("ghim_cuda_visible_devices", {})
    for c in CELLS:
        L.append(f"| {c.idx} | {c.model_key} | {c.n_shot} | {c.system} | "
                 f"{ghim.get(str(c.idx), '—')} |")
    L += ["", "**Ghi vào khoá luận cùng với sáu giá trị ghim kia.** Không ô nào chia "
          "layer qua hai card; không hai ô nào chạy cùng lúc trên cùng một card."]
    return L


def _muc_doi_chieu_latency(o: dict) -> list[str]:
    """Mục 4: cặp ô cùng model + cùng n_shot, khác nguồn → so elapsed trung bình.

    Lệch lớn giữa hai ô chạy trên HAI CARD KHÁC NHAU là dấu hiệu một card bị throttle,
    và khi đó `latency_mean_s` của Bảng 4.13 không so được giữa các hàng.
    """
    ghim = {}
    if GPU_INFO_PATH.exists():
        ghim = json.loads(GPU_INFO_PATH.read_text(encoding="utf-8")) \
            .get("ghim_cuda_visible_devices", {})

    L = ["", "## 4. Đối chiếu `elapsed_seconds` giữa hai card", "",
         "Trung bình **mỗi câu đi qua mô hình** (loại 10 câu hằng số của cột GraphRAG —",
         "chúng có `elapsed = 0.0` nên nếu tính vào thì hai cột lệch nhau chỉ vì số câu",
         "hằng số khác nhau, không vì phần cứng).", "",
         "| Cặp ô (cùng model + cùng n_shot) | GraphRAG s/câu | Naive s/câu | Lệch | Card | Kết luận |",
         "|---|---:|---:|---:|---|---|"]
    canh_bao: list[str] = []
    for i_g, i_n in CAP_O:
        cg, cn = CELL_BY_IDX[i_g], CELL_BY_IDX[i_n]
        dg, dn = o.get(i_g), o.get(i_n)
        ten = f"ô {i_g}+{i_n} · {cg.model_key} n_shot={cg.n_shot}"
        card = f"{ghim.get(str(i_g), '?')} vs {ghim.get(str(i_n), '?')}"
        if not (dg and dn) or None in (dg["elapsed_mean_qua_mo_hinh"],
                                       dn["elapsed_mean_qua_mo_hinh"]):
            L.append(f"| {ten} | — | — | — | {card} | thiếu ô |")
            continue
        a, b = dg["elapsed_mean_qua_mo_hinh"], dn["elapsed_mean_qua_mo_hinh"]
        lech = abs(a - b) / min(a, b) if min(a, b) > 0 else 0.0
        khac_card = ghim.get(str(i_g)) != ghim.get(str(i_n))
        if khac_card and lech > LECH_LATENCY_NGUONG:
            kl = f"⚠️ **LỆCH {lech:.0%} > 25% TRÊN HAI CARD KHÁC NHAU**"
            canh_bao.append(f"- **{ten}**: {a:.2f} s/câu (card {ghim.get(str(i_g))}) vs "
                            f"{b:.2f} s/câu (card {ghim.get(str(i_n))}) — lệch {lech:.0%}")
        elif khac_card:
            kl = "hai card, lệch trong ngưỡng"
        else:
            kl = "cùng card — lệch không quy về throttle"
        L.append(f"| {ten} | {a:.2f} | {b:.2f} | {lech:.0%} | {card} | {kl} |")

    if canh_bao:
        L += ["", "### ⚠️ CẢNH BÁO — nghi một card bị throttle", ""] + canh_bao + [
            "",
            "Hai ô cùng model + cùng `n_shot` chỉ khác nguồn ngữ cảnh thì khối lượng tính",
            "toán mỗi câu KHÔNG chênh tới mức này (prompt GraphRAG dài hơn Naive nên chênh",
            "vài phần trăm là bình thường; hai chục phần trăm thì không). Trên hai card",
            "khác nhau, cách giải thích đơn giản nhất là **một card bị throttle** — hệ quả:",
            "`latency_mean_s` của Bảng 4.13 **không so được** giữa các hàng, phải ghi chú",
            "hoặc chạy lại cả hai ô của cặp trên cùng một card (`--cells` + bỏ `--parallel`).",
        ]
    else:
        L += ["", "Không cặp nào lệch quá 25% trên hai card khác nhau."]
    return L


def stage_table(args) -> int:
    _tieu_de("CHẶNG table — gom sáu ô vào finetune/reports/ft06_matrix.md")

    o = {c.idx: _doc_o(c) for c in CELLS}
    thieu = [CELLS[i - 1].nhan for i in sorted(o) if o[i] is None]

    # (mô hình sinh, ô naive, ô graphrag)
    hang = [
        ("Cục bộ gốc, 0-shot", 6, 5),
        ("Cục bộ gốc, 2-shot", 4, 3),
        ("Cục bộ đã tinh chỉnh, 0-shot", 2, 1),
    ]

    L: list[str] = [
        "# TASK-FT-06 — Ma trận mục 4.7: ba mô hình sinh × hai khuôn ngữ cảnh",
        "",
        "Sinh bởi `finetune/kaggle_ft06.py --stage table`. Mọi con số ở bảng 1 do",
        "`src/evaluation/metrics.py::aggregate` tính (dòng 195-260) — script này KHÔNG",
        "tự tính lại thang đo nào.",
        "",
        f"- Nguồn ngữ cảnh: `{SRC_GRAPHRAG}` và `{SRC_BASELINE}` — **cùng một mẻ chạy**,",
        "  chính mẻ sinh ra 0.578 / 0.435 ở hàng Gemini. Truy hồi đóng băng ở cả sáu ô.",
        "- Tham số sinh: bộ đã chốt ở `gate_base_model.md` §3 (temperature 0.7 · top_p 0.8",
        "  · top_k 20 · min_p 0 · **presence_penalty 0** · seed 42 · max_new_tokens 2048",
        "  · n_ctx 16384 · n_gpu_layers −1), giống hệt nhau ở cả sáu ô.",
        "- N=1 cho mọi ô cục bộ — chốt ở kế hoạch §TASK-FT-06 (tính tất định đã đo).",
        "",
        "## 1. Bốn thang đo của Bảng 4.5",
        "",
        "| Mô hình sinh | Hệ truy hồi | F1 cấp Khoản | F1 cấp Điều | Norm Recall | Từ chối đúng (x/14) | Δ (F1 Khoản) |",
        "|---|---|---:|---:|---:|---:|---:|",
        f"| Gemini 2.5 Pro | Naive RAG | {GEMINI_F1_NAIVE:.3f} | — | — | — | |",
        f"| Gemini 2.5 Pro | GraphRAG | {GEMINI_F1_GRAPHRAG:.3f} | — | — | — | **+{GEMINI_DELTA:.3f}** |",
    ]
    for ten, i_naive, i_graph in hang:
        n_, g_ = o[i_naive], o[i_graph]
        for nhan, cell_data in (("Naive RAG", n_), ("GraphRAG", g_)):
            if cell_data is None:
                L.append(f"| {ten} | {nhan} | — | — | — | — | |")
                continue
            a = cell_data["agg"]
            delta = ""
            if nhan == "GraphRAG" and n_ is not None:
                d = a["f1_mean"] - n_["agg"]["f1_mean"]
                delta = f"**{d:+.3f}**"
            L.append(f"| {ten} | {nhan} | {_f(a['f1_mean'])} | {_f(a['f1_dieu_mean'])} "
                     f"| {_f(a['norm_recall_mean'])} | {_tu_choi(a)} | {delta} |")

    L += [
        "",
        "Hàng Gemini lấy từ báo cáo (kế hoạch §2). Ba cột còn lại của hàng đó để `—` có",
        "chủ ý: chúng không nằm trong ba con số mà kế hoạch ghim, và điền bằng số lấy từ",
        "chỗ khác (khác N, khác cách gộp) là trộn hai đại lượng. Lấy ở `docs/V2_RESULTS.md`",
        "khi cần, và ghi rõ nguồn.",
        "",
        "## 2. Sức khoẻ từng ô — đọc TRƯỚC khi tin bảng 1",
        "",
        "| Ô | Mô hình | n_shot | Hệ | `format_ok_rate` | `n_hit_token_cap` | `soft_article_hit` | qua mô hình | file |",
        "|---:|---|---:|---|---:|---:|---:|---:|---|",
    ]
    for c in CELLS:
        d = o[c.idx]
        if d is None:
            L.append(f"| {c.idx} | {c.model_key} | {c.n_shot} | {c.system} | "
                     f"— | — | — | — | **THIẾU** |")
            continue
        fmt = (f"{d['format_ok_rate']:.3f} (mẫu số {d['format_ok_mau_so']})"
               if isinstance(d["format_ok_rate"], float) else "—")
        L.append(f"| {c.idx} | {c.model_key} | {c.n_shot} | {c.system} | {fmt} | "
                 f"{d['n_hit_token_cap']} | {_f(d['soft_article_hit_mean'])} | "
                 f"{d['n_qua_mo_hinh']}/{d['n_cau']} | `{d['file']}` |")

    canh_bao = [(c, o[c.idx]) for c in CELLS
                if o[c.idx] and (o[c.idx]["n_hit_token_cap"] or 0) > 0]
    if canh_bao:
        L += ["", "### ⚠️ CẢNH BÁO — có ô chạm trần token", ""]
        for c, d in canh_bao:
            L.append(f"- **{c.nhan}**: {d['n_hit_token_cap']} câu chạm trần "
                     f"(`{', '.join(d['ids_hit_token_cap'][:15])}`)")
        L += [
            "",
            "Khối trích dẫn nằm **CUỐI** câu trả lời, nên chạm trần `max_new_tokens` là",
            "mất citation vì lý do **thuần kỹ thuật** — không phải vì mô hình không biết",
            "luật. **Mọi con số của những ô này ở bảng 1 phải đọc lại** trước khi đưa vào",
            "khoá luận (`gate_base_model.md` §4.2).",
        ]
    elif len(thieu) < len(CELLS):
        L += ["", "`n_hit_token_cap` = 0 ở mọi ô đã chạy. Đọc là *không thấy bằng chứng "
              "lặp*, KHÔNG phải *đã loại trừ lặp* (`gate_base_model.md` §4.2).", ""]

    L += _muc_ghim_gpu()
    L += _muc_doi_chieu_latency(o)

    if thieu:
        L += ["", "### Ô còn thiếu", ""] + [f"- {t}" for t in thieu] + [
            "", "Bảng chưa đầy đủ. Chạy lại `--stage run --cells <số ô>`.",
        ]

    out = REPORTS_DIR / "ft06_matrix.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    print(f"\n  ghi → {_rel(out)}")
    if not args.no_push:
        _hf_day([out], args.hf_repo, args.hf_prefix)
    return 0


# ---------------------------------------------------------------------------

STAGES = {
    "prep": stage_prep,
    "gate-template": stage_gate_template,
    "gate-prompt": stage_gate_prompt,
    "run": stage_run,
    "table": stage_table,
}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="TASK-FT-06 — sáu ô của ma trận mục 4.7, chạy trên Kaggle T4",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Tham số sinh: bộ đã chốt ở gate_base_model.md §3. Script chỉ truyền tường "
               "minh --presence-penalty 0 (mặc định replay.py là 1.0); bảy giá trị còn lại "
               "để mặc định replay.py lo, tránh nhân đôi nguồn chân lý.",
    )
    ap.add_argument("--stage", required=True, choices=list(STAGES))
    ap.add_argument("--cells", default="",
                    help="chặng run: chỉ chạy các ô này, vd '3,4' (mặc định: cả sáu). "
                         "Thứ tự gõ được giữ nguyên.")
    ap.add_argument("--parallel", action="store_true",
                    help="chặng run: hai luồng, mỗi luồng ghim MỘT card "
                         f"(card 0: ô {LANES[0]}, card 1: ô {LANES[1]}); trong luồng thì "
                         "tuần tự. Mặc định TẮT = sáu ô tuần tự trên card "
                         f"{GPU_TUAN_TU}. Không bao giờ chia một ô qua hai card.")
    ap.add_argument("--gpu", type=int, default=None,
                    help="ghim mọi ô của lượt này vào card N. Chặng run dùng cờ này khi "
                         "tự gọi lại chính nó cho từng luồng của --parallel.")
    ap.add_argument("--hf-repo", default=HF_REPO_DEFAULT,
                    help=f"repo HF để đẩy kết quả (mặc định {HF_REPO_DEFAULT})")
    ap.add_argument("--hf-prefix", default=HF_PREFIX_DEFAULT,
                    help=f"đường dẫn trong repo HF (mặc định {HF_PREFIX_DEFAULT})")
    ap.add_argument("--no-push", action="store_true",
                    help="không đẩy HF (chạy thử cục bộ)")
    ap.add_argument("--base-manifest", default="/kaggle/working/base_manifest.json",
                    help="file JSON chứa ghim GGUF gốc (khuôn FT-03: repo/file/revision/sha256)")
    ap.add_argument("--base-revision", default=None, help="ghi đè revision GGUF gốc")
    ap.add_argument("--base-sha256", default=None, help="ghi đè sha256 GGUF gốc")
    args = ap.parse_args()

    args.cells = [int(s) for s in args.cells.split(",") if s.strip()] if args.cells else []
    xau = [n for n in args.cells if n not in {c.idx for c in CELLS}]
    if xau:
        print(f"❌ --cells có số không phải ô: {xau} (hợp lệ 1..{len(CELLS)})", file=sys.stderr)
        return 2

    return STAGES[args.stage](args)


if __name__ == "__main__":
    raise SystemExit(main())
