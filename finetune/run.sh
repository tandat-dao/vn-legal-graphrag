#!/usr/bin/env bash
# =============================================================================
# run.sh - PHIEN 2: QLoRA (5k x 2 epoch) -> merge -> GGUF Q4_K_M
#
# Chay tren RunPod RTX 4090 (Community Cloud).
# Tu huy pod o MOI duong thoat, ke ca khi loi hoac bi Ctrl-C.
#
# CACH CHAY (RunPod):
#   export HF_TOKEN=hf_xxxxx
#   export SELFDESTRUCT=1
#   bash run.sh
#
# DRY-RUN TREN KAGGLE (mien phi) - PHAI BO CHANG PREFLIGHT:
#   export SELFDESTRUCT=0 SMOKE=1
#   STAGES=install,train bash run.sh      # 50 mau, max_seq_length=2048
#
#   Vi sao bo preflight: preflight exit 1 khi sm<80, ma Kaggle chi co T4 =
#   sm75. Chay ca preflight tren Kaggle la chac chan that bai o giay thu 30.
#
#   ⚠ Dry-run tren Kaggle KHONG kiem duoc duong bf16/FlashAttention-2:
#   sm75 khong co bf16 goc nen train_qlora.py tu chuyen sang fp16 va Unsloth
#   khong dung FA2. No chi chung minh "duong code chay het", KHONG chung minh
#   duong so hoc that cua RTX 4090 (sm89). Loi rieng cua nhanh bf16/FA2 chi
#   lo ra o lan chay that.
#
# CHAY LAI TUNG CHANG sau khi loi (vd pod chet o buoc gguf):
#   RUN_NAME=$(cat /workspace/run_name.txt) STAGES=gguf,publish bash run.sh
#   (khong dat RUN_NAME thi script tu doc lai /workspace/run_name.txt)
# =============================================================================
set -Eeuo pipefail

# ------------------------------- CAU HINH ------------------------------------
HF_REPO_MODEL="${HF_REPO_MODEL:-dangnguyen254/thesis-graphrag-gguf}"
HF_REPO_DATA="${HF_REPO_DATA:-dangnguyen254/thesis-graphrag-data}"
BASE_MODEL="${BASE_MODEL:-unsloth/Qwen3-4B-Instruct-2507}"

# GHIM PHIEN BAN - phai giong het o phien 1 va phien 3
LLAMA_TAG="${LLAMA_TAG:-b10165}"
LCP_VERSION="${LCP_VERSION:-0.3.16}"

# Tarball binary llama.cpp: ban CPU-only static, lay tu HF repo model (khong
# lay tu GitHub Releases - ten file o do doi giua cac tag). Ghim bang sha256.
LLAMA_TARBALL="${LLAMA_TARBALL:-llamacpp-${LLAMA_TAG}-cpu-static-x64.tar.gz}"
LLAMA_TARBALL_SHA256="9f8e92b8a69b3c8399e6f42324430f8a0faaf1bba707deeee7c8cb96bbd9c6d5"

MAX_SEQ_LEN=16384                       # GIU 16k - khong ha
EPOCHS=2
SMOKE="${SMOKE:-0}"
if [ "$SMOKE" = "1" ]; then MAX_SEQ_LEN=2048; EPOCHS=1; fi

WORK=/workspace
mkdir -p "$WORK"

# RUN_NAME: dat duoc bang bien moi truong; neu khong thi doc lai lan chay dau.
# Truoc day RUN_NAME luon chua $(date) nen chay lai STAGES=gguf,publish sinh
# ten KHAC -> $Q4 tro vao file khong ton tai, dung quy trinh phuc hoi ma chinh
# file nay khuyen nghi.
RUN_NAME_FILE="$WORK/run_name.txt"
if [ -n "${RUN_NAME:-}" ]; then
  :
elif [ -f "$RUN_NAME_FILE" ]; then
  RUN_NAME="$(cat "$RUN_NAME_FILE")"
  echo ">>> Dung lai RUN_NAME tu $RUN_NAME_FILE: $RUN_NAME"
else
  RUN_NAME="ft04-5k-${EPOCHS}ep-$(date +%Y%m%d-%H%M)"
fi
printf '%s\n' "$RUN_NAME" > "$RUN_NAME_FILE"

ADAPTER_DIR="$WORK/adapter"
MERGED_DIR="$WORK/merged"
GGUF_DIR="$WORK/gguf"
DATA_DIR="$WORK/data"
CONSTRAINTS="$WORK/constraints.txt"
LOG="$WORK/${RUN_NAME}.log"

# Cho phep chay lai tung chang sau khi loi:
#   STAGES=merge,gguf,publish bash run.sh
STAGES="${STAGES:-preflight,install,data,train,merge,gguf,publish}"
has_stage() { [[ ",$STAGES," == *",$1,"* ]]; }

mkdir -p "$GGUF_DIR" "$DATA_DIR"
exec > >(tee -a "$LOG") 2>&1

# --------------------------- TU HUY + DON DEP --------------------------------
cleanup() {
  local code=$?
  echo ""
  echo "===================== KET THUC (exit=$code) ====================="
  date -u +"%Y-%m-%dT%H:%M:%SZ"

  # Day log len HF du thanh cong hay that bai - de con doc duoc sau khi pod chet
  if [ -n "${HF_TOKEN:-}" ]; then
    hf upload "$HF_REPO_MODEL" "$LOG" "logs/${RUN_NAME}.log" \
      --repo-type model --commit-message "log $RUN_NAME (exit=$code)" || true
  fi

  if [ "${SELFDESTRUCT:-0}" = "1" ] && [ -n "${RUNPOD_POD_ID:-}" ]; then
    echo ">>> Tu huy pod $RUNPOD_POD_ID trong 60s. Ctrl-C de huy bo."
    sleep 60                                  # cua so thoat neu ban dang ngoi xem
    runpodctl remove pod "$RUNPOD_POD_ID" || true
  else
    echo ">>> SELFDESTRUCT tat. NHO TU TAT POD."
  fi
}
trap cleanup EXIT

# ============================= 0. PREFLIGHT ==================================
# Muc dich: that bai trong 30 giay dau thay vi sau 6 gio. Moi loi o day
# deu kich hoat trap -> pod tu tat -> ban tra khoang $0.003.
if has_stage preflight; then
  echo "===== [0/7] PREFLIGHT ====="
  nvidia-smi --query-gpu=name,compute_cap,memory.total --format=csv

  CC=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader | head -1 | tr -d '.')
  if [ "$CC" -lt 80 ]; then
    echo "LOI: GPU sm${CC} < sm80. Khong co bf16/FlashAttention-2. Dung lai."
    echo "     (Tren Kaggle T4 = sm75: chay STAGES=install,train de bo chang nay.)"
    exit 1
  fi
  echo "OK: sm${CC} >= sm80"

  VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
  [ "$VRAM" -ge 22000 ] || { echo "LOI: VRAM ${VRAM}MB < 22GB"; exit 1; }

  FREE_GB=$(df -BG --output=avail "$WORK" | tail -1 | tr -dc '0-9')
  [ "$FREE_GB" -ge 50 ] || { echo "LOI: dia trong ${FREE_GB}GB < 50GB"; exit 1; }

  # Wheel llama-cpp-python ghim o day la cp312. Python khac 3.12 thi pip se
  # quay ra BUILD TU NGUON (hoac bao khong tim thay wheel) - phat hien som.
  PYV=$(python -c 'import sys; print("%d.%d" % sys.version_info[:2])')
  [ "$PYV" = "3.12" ] || { echo "LOI: Python $PYV, can 3.12 (wheel llama-cpp-python la cp312)"; exit 1; }
  echo "OK: Python $PYV"

  [ -n "${HF_TOKEN:-}" ] || { echo "LOI: chua dat HF_TOKEN"; exit 1; }
  echo "OK: preflight qua het."
fi

# ============================== 1. CAI DAT ===================================
if has_stage install; then
  echo "===== [1/7] CAI DAT ====="

  # huggingface_hub 1.x: da GO extra [cli] va GO HAN hf_transfer.
  # HF_HUB_ENABLE_HF_TRANSFER bi BO QUA AM THAM (khong bao loi) -> phai dung
  # HF_XET_HIGH_PERFORMANCE voi backend hf_xet.
  pip install -q "huggingface_hub==1.25.1" hf_xet
  export HF_XET_HIGH_PERFORMANCE=1
  hf auth login --token "$HF_TOKEN"        # --add-to-git-credential da bi go (lop Repository)

  # BO GHIM - phai giong het bo dung o Kaggle (notebooks/kaggle_clean.ipynb A3).
  # KHONG "pip install -U": -U keo ban moi nhat va pha bo ghim.
  # KHONG "pip install -r requirements.txt" tren pod: file do la cua he
  # GraphRAG (neo4j/qdrant/sentence-transformers), khong lien quan huan luyen,
  # va cac rang buoc cua no keo nguoc torch.
  cat > "$CONSTRAINTS" <<'CONSTRAINTS_EOF'
torch==2.10.0
transformers==5.5.0
trl==0.24.0
peft==0.20.0
unsloth==2026.7.5
huggingface_hub==1.25.1
CONSTRAINTS_EOF
  echo "--- constraints.txt ---"; cat "$CONSTRAINTS"

  pip install -q -c "$CONSTRAINTS" \
    unsloth unsloth_zoo trl peft transformers accelerate bitsandbytes datasets

  # llama-cpp-python: dung cho smoke test o chang gguf (CUNG thu vien sinh ra
  # so lieu phien 1 va se dung o phien 3).
  pip install -q "llama-cpp-python==$LCP_VERSION" || \
    echo "CANH BAO: khong cai duoc llama-cpp-python==$LCP_VERSION -> smoke test se bi bo qua."

  # llama.cpp: chi lay script convert (python). KHONG cai
  # requirements-convert_hf_to_gguf.txt - file do co --extra-index-url .../whl/cpu
  # va se GO torch CUDA thay bang torch CPU-only, hong am tham den tan luc train.
  if [ ! -d "$WORK/llama.cpp" ]; then
    git clone --depth 1 --branch "$LLAMA_TAG" \
      https://github.com/ggml-org/llama.cpp "$WORK/llama.cpp"
  fi
  pip install -q -c "$CONSTRAINTS" numpy sentencepiece protobuf safetensors
  pip install -q "$WORK/llama.cpp/gguf-py"

  # Binary llama-quantize: tarball CPU-only static tren HF repo model, ghim sha256.
  if [ ! -x "$WORK/llama-bin/llama-quantize" ]; then
    mkdir -p "$WORK/llama-bin"
    hf download "$HF_REPO_MODEL" "$LLAMA_TARBALL" --repo-type model \
      --local-dir "$WORK/llama-bin"
    cd "$WORK/llama-bin"
    echo "${LLAMA_TARBALL_SHA256}  ${LLAMA_TARBALL}" > "${LLAMA_TARBALL}.sha256"
    sha256sum -c "${LLAMA_TARBALL}.sha256" || {
      echo "LOI: sha256 cua $LLAMA_TARBALL KHONG khop ban ghim. Dung lai."
      exit 1
    }
    tar -xzf "$LLAMA_TARBALL"
    find . -name 'llama-*' -type f -exec mv -f {} . \; 2>/dev/null || true
    chmod +x llama-* 2>/dev/null || true
    cd "$WORK"
  fi
  echo "OK: llama.cpp ghim tai tag $LLAMA_TAG (sha256 $LLAMA_TARBALL_SHA256)"

  # Cong chan cuoi chang: torch phai la ban CUDA. Neu mot goi nao o tren keo
  # nham torch CPU-only ve thi phat hien NGAY, khong phai sau 6 gio.
  python -c "import torch,sys; assert torch.cuda.is_available(), 'torch khong thay CUDA'; \
assert not torch.__version__.endswith('+cpu'), 'torch la ban CPU-only: '+torch.__version__; \
print('OK torch', torch.__version__)"
fi

# =============================== 2. DU LIEU ==================================
# FT-04 sinh train.jsonl + val.jsonl CUC BO va .gitignore chan *.jsonl -> pod
# khong the lay tu git. Tai tu HF dataset repo, doi chieu sha256 truoc khi dung.
# Sinh/day len bang finetune/upload_dataset.sh (chay tren may nguoi dung).
if has_stage data; then
  echo "===== [2/7] TAI DU LIEU HUAN LUYEN ====="
  hf download "$HF_REPO_DATA" train.jsonl val.jsonl \
    train.jsonl.sha256 val.jsonl.sha256 \
    --repo-type dataset --local-dir "$DATA_DIR"
  cd "$DATA_DIR"
  sha256sum -c train.jsonl.sha256 val.jsonl.sha256 || {
    echo "LOI: sha256 du lieu KHONG khop. File hong hoac da bi thay. Dung lai."
    exit 1
  }
  wc -l train.jsonl val.jsonl
  cd "$WORK"
  echo "OK: du lieu da tai va doi chieu sha256."
fi

# =============================== 3. TRAIN ====================================
# Cac tham so quan trong nam trong train_qlora.py (build_sft_kwargs):
#   per_device_train_batch_size=1 (KHONG padding -> khong phat n^2)
#   gradient_accumulation_steps=16, packing=False,
#   gradient_checkpointing="unsloth", bf16 tu do theo compute capability,
#   save_steps=50, save_total_limit=2, hub_strategy="checkpoint".
# hub_strategy="checkpoint" day checkpoint gan nhat len HF sau moi lan save,
# nen pod chet thi resume duoc tu HF chu khong mat gi.
if has_stage train; then
  echo "===== [3/7] TRAIN ====="
  RESUME_ARG=""
  if hf download "$HF_REPO_MODEL" --include "last-checkpoint/*" \
       --local-dir "$WORK/resume" 2>/dev/null; then
    RESUME_ARG="--resume-from-checkpoint $WORK/resume/last-checkpoint"
    echo ">>> Tim thay checkpoint tren HF, se train tiep."
  fi

  # SMOKE la "0" hoac "1" -> ${SMOKE:+...} bung ra o CA HAI truong hop vi "0"
  # van la da dat va khac rong. Phai kiem tuong minh.
  LIMIT_ARG=""
  if [ "$SMOKE" = "1" ]; then LIMIT_ARG="--limit-samples 50"; fi

  # Cac co dung GACH NOI - parse_args() cua train_qlora.py (dong 39-65) dinh
  # nghia bang gach noi; dung gach duoi thi argparse bao "unrecognized arguments".
  #
  # --lora-r 16 --lora-alpha 32 truyen TUONG MINH (mac dinh cua script la
  # 32/64): khop kE hoach §TASK-FT-05, va de gia tri hien ngay trong lenh chu
  # khong nap trong mac dinh. Ly do chon 16/32: tac vu chu yeu la hoc DINH DANG
  # dau ra - phien 1 FT-03 cho thay mo hinh DA dinh vi dung dieu luat
  # (soft_article_hit = 1.000) va chi sai cu phap trich dan - nen r=16 du va re hon.
  python train_qlora.py \
    --base-model      "$BASE_MODEL" \
    --dataset         "$DATA_DIR/train.jsonl" \
    --max-seq-length  "$MAX_SEQ_LEN" \
    --epochs          "$EPOCHS" \
    --lora-r          16 \
    --lora-alpha      32 \
    --output-dir      "$ADAPTER_DIR" \
    --hub-model-id    "$HF_REPO_MODEL" \
    --run-name        "$RUN_NAME" \
    $LIMIT_ARG \
    $RESUME_ARG

  hf upload "$HF_REPO_MODEL" "$ADAPTER_DIR" "adapter/${RUN_NAME}" --repo-type model
  echo "OK: adapter da luu tren HF."
fi

# =============================== 4. MERGE ====================================
if has_stage merge; then
  echo "===== [4/7] MERGE LoRA -> bf16 ====="
  python - <<PY
from unsloth import FastLanguageModel
model, tok = FastLanguageModel.from_pretrained(
    model_name    = "$ADAPTER_DIR",
    max_seq_length= $MAX_SEQ_LEN,
    load_in_4bit  = False,     # merge o do chinh xac day du
    dtype         = None,
)
model.save_pretrained_merged("$MERGED_DIR", tok, save_method="merged_16bit")
print("merged ->", "$MERGED_DIR")
PY
  du -sh "$MERGED_DIR"
fi

# ================================ 5. GGUF ====================================
if has_stage gguf; then
  echo "===== [5/7] CONVERT -> GGUF Q4_K_M ====="
  F16="$GGUF_DIR/${RUN_NAME}-f16.gguf"
  Q4="$GGUF_DIR/${RUN_NAME}-Q4_K_M.gguf"

  python "$WORK/llama.cpp/convert_hf_to_gguf.py" "$MERGED_DIR" \
    --outfile "$F16" --outtype f16

  "$WORK/llama-bin/llama-quantize" "$F16" "$Q4" Q4_K_M
  rm -f "$F16"                                  # ~8GB, khong can giu

  echo ""
  echo "############################################################"
  echo "# DANH TINH ARTIFACT - CHEP VAO KHOA LUAN                  #"
  sha256sum "$Q4"
  ls -la "$Q4"
  echo "# llama.cpp tag: $LLAMA_TAG                                #"
  echo "############################################################"

  # ------------------------------ SMOKE TEST -------------------------------
  # Nap that + sinh that de biet file GGUF co dung duoc khong, TRUOC khi tat pod.
  #
  # Dung llama-cpp-python (dung thu vien sinh ra so lieu phien 1 va se dung o
  # phien 3), KHONG dung llama-server: tarball da ghim la ban CPU-only static
  # va KHONG chua llama-server. Ban cu goi llama-server roi
  # `grep ... && grep ...`; duoi `set -Eeuo pipefail` mot danh sach A && B ma A
  # hong se lam SCRIPT THOAT -> trap -> pod tu huy SAU KHI da train xong va
  # CHUA kip publish -> mat file GGUF vua ton 8 tieng tao ra.
  #
  # Vi vay: moi lenh kiem o day deu duoc boc de KHONG bao gio lam thoat script.
  # Hong thi in canh bao va van di tiep sang publish.
  #
  # Luu y pham vi: build CPU nen day KHONG kiem duoc offload GPU. No tra loi
  # dung mot cau hoi - "file GGUF nap duoc va sinh ra chu khong?".
  echo ">>> Smoke test (llama-cpp-python, CPU)..."
  SMOKE_RC=0
  python - <<PY || SMOKE_RC=$?
import json, sys
try:
    from llama_cpp import Llama
except Exception as e:
    print("CANH BAO: khong import duoc llama_cpp ->", e)
    sys.exit(2)

llm = Llama(model_path="$Q4", n_ctx=2048, n_gpu_layers=0, seed=42, verbose=False)
out = llm.create_chat_completion(
    messages=[{"role": "user",
               "content": "Neu ngan gon quy dinh ve dieu kien chuyen muc dich su dung dat."}],
    # DUNG bo tham so sinh da ghim (phien 1 + phien 3). presence_penalty = 0 da
    # duoc chot o FT-03 theo quy tac dang ky truoc; ban cu ghi 1.0 la sai.
    temperature=0.7, top_p=0.8, top_k=20, min_p=0.0,
    presence_penalty=0.0, seed=42, max_tokens=128,
)
txt = (out["choices"][0]["message"].get("content") or "").strip()
json.dump(out, open("$WORK/smoke_out.json", "w", encoding="utf-8"), ensure_ascii=False)
print("--- dau ra (200 ky tu dau) ---")
print(txt[:200])
usage = out.get("usage") or {}
print("prompt_tokens =", usage.get("prompt_tokens"),
      "| completion_tokens =", usage.get("completion_tokens"))
assert len(txt) > 50, f"dau ra qua ngan ({len(txt)} ky tu) - GGUF co the hong"
print("OK smoke test.")
PY
  if [ "$SMOKE_RC" -ne 0 ]; then
    echo "############################################################"
    echo "# CANH BAO: SMOKE TEST HONG (rc=$SMOKE_RC).                #"
    echo "# VAN DI TIEP sang publish de KHONG mat file GGUF.         #"
    echo "# Kiem tra lai file truoc khi dung cho phien 3.            #"
    echo "############################################################"
  fi
fi

# ============================== 6. PUBLISH ===================================
if has_stage publish; then
  echo "===== [6/7] DAY GGUF LEN HF ====="
  export HF_XET_HIGH_PERFORMANCE=1
  Q4="$GGUF_DIR/${RUN_NAME}-Q4_K_M.gguf"
  cd "$GGUF_DIR" && sha256sum "$(basename "$Q4")" > "$Q4.sha256" && cd "$WORK"

  hf upload "$HF_REPO_MODEL" "$Q4"        "gguf/$(basename "$Q4")"        --repo-type model
  hf upload "$HF_REPO_MODEL" "$Q4.sha256" "gguf/$(basename "$Q4").sha256" --repo-type model

  echo ""
  echo "HOAN TAT. File dung cho CA phien 1 va phien 3:"
  echo "  hf download $HF_REPO_MODEL gguf/$(basename "$Q4") --local-dir ."
fi

echo "===== TAT CA CHANG DA XONG ====="
