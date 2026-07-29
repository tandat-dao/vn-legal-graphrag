#!/usr/bin/env bash
# =============================================================================
# run.sh - PHIEN 2: QLoRA (5k x 2 epoch) -> merge -> GGUF Q4_K_M
#
# Chay tren RunPod RTX 4090 (Community Cloud).
# Tu huy pod o MOI duong thoat, ke ca khi loi hoac bi Ctrl-C.
#
# CACH CHAY:
#   export HF_TOKEN=hf_xxxxx
#   export SELFDESTRUCT=1          # dat =0 khi dry-run tren Kaggle
#   bash run.sh
#
# DRY-RUN TRUOC (bat buoc, tren Kaggle, mien phi):
#   export SELFDESTRUCT=0 SMOKE=1
#   bash run.sh                    # 50 mau, max_seq_length=2048
# =============================================================================
set -Eeuo pipefail

# ------------------------------- CAU HINH ------------------------------------
HF_REPO_MODEL="${HF_REPO_MODEL:-<user>/thesis-graphrag-gguf}"
HF_REPO_DATA="${HF_REPO_DATA:-<user>/thesis-graphrag-data}"
BASE_MODEL="${BASE_MODEL:-unsloth/Qwen3-4B-Instruct-2507}"

# GHIM PHIEN BAN - phai giong het o phien 1 va phien 3
LLAMA_TAG="${LLAMA_TAG:-b7891}"        # doi thanh tag ban thuc su dung
LCP_VERSION="${LCP_VERSION:-0.3.16}"

MAX_SEQ_LEN=16384                       # GIU 16k - khong ha
EPOCHS=2
SMOKE="${SMOKE:-0}"
if [ "$SMOKE" = "1" ]; then MAX_SEQ_LEN=2048; EPOCHS=1; fi

WORK=/workspace
RUN_NAME="ft04-5k-${EPOCHS}ep-$(date +%Y%m%d-%H%M)"
ADAPTER_DIR="$WORK/adapter"
MERGED_DIR="$WORK/merged"
GGUF_DIR="$WORK/gguf"
LOG="$WORK/${RUN_NAME}.log"

# Cho phep chay lai tung chang sau khi loi:
#   STAGES=merge,gguf,publish bash run.sh
STAGES="${STAGES:-preflight,install,train,merge,gguf,publish}"
has_stage() { [[ ",$STAGES," == *",$1,"* ]]; }

mkdir -p "$WORK" "$GGUF_DIR"
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
  echo "===== [0/5] PREFLIGHT ====="
  nvidia-smi --query-gpu=name,compute_cap,memory.total --format=csv

  CC=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader | head -1 | tr -d '.')
  if [ "$CC" -lt 80 ]; then
    echo "LOI: GPU sm${CC} < sm80. Khong co bf16/FlashAttention-2. Dung lai."
    exit 1
  fi
  echo "OK: sm${CC} >= sm80"

  VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
  [ "$VRAM" -ge 22000 ] || { echo "LOI: VRAM ${VRAM}MB < 22GB"; exit 1; }

  FREE_GB=$(df -BG --output=avail "$WORK" | tail -1 | tr -dc '0-9')
  [ "$FREE_GB" -ge 50 ] || { echo "LOI: dia trong ${FREE_GB}GB < 50GB"; exit 1; }

  [ -n "${HF_TOKEN:-}" ] || { echo "LOI: chua dat HF_TOKEN"; exit 1; }
  echo "OK: preflight qua het."
fi

# ============================== 1. CAI DAT ===================================
if has_stage install; then
  echo "===== [1/5] CAI DAT ====="
  pip install -q -U "huggingface_hub[cli]" hf_transfer
  export HF_HUB_ENABLE_HF_TRANSFER=1        # tang toc tai/day file lon
  hf auth login --token "$HF_TOKEN" --add-to-git-credential

  pip install -q -U unsloth unsloth_zoo trl peft transformers accelerate bitsandbytes datasets

  # llama.cpp: chi lay script convert (python) + binary dung san (khong build)
  if [ ! -d "$WORK/llama.cpp" ]; then
    git clone --depth 1 --branch "$LLAMA_TAG" \
      https://github.com/ggml-org/llama.cpp "$WORK/llama.cpp"
    pip install -q -r "$WORK/llama.cpp/requirements/requirements-convert_hf_to_gguf.txt"
  fi
  if [ ! -x "$WORK/llama-bin/llama-quantize" ]; then
    mkdir -p "$WORK/llama-bin" && cd "$WORK/llama-bin"
    curl -sL -o bin.zip \
      "https://github.com/ggml-org/llama.cpp/releases/download/${LLAMA_TAG}/llama-${LLAMA_TAG}-bin-ubuntu-x64.zip"
    echo "sha256 cua binary llama.cpp (GHI VAO KHOA LUAN):"
    sha256sum bin.zip
    unzip -oq bin.zip && find . -name 'llama-*' -type f -exec mv {} . \; 2>/dev/null || true
    chmod +x llama-* 2>/dev/null || true
    cd "$WORK"
  fi
  echo "OK: llama.cpp ghim tai tag $LLAMA_TAG"
fi

# =============================== 2. TRAIN ====================================
# Goi script train cua ban. Trong SFTConfig/TrainingArguments can co:
#
#   per_device_train_batch_size = 1          # KHONG padding -> khong phat n^2
#   gradient_accumulation_steps = 16
#   max_seq_length              = 16384
#   packing                     = False      # tu tat: 1 mau = 1 chuoi
#   gradient_checkpointing      = "unsloth"
#   bf16                        = True
#   save_steps                  = 50         # ~30 phut/checkpoint
#   save_total_limit            = 2
#   push_to_hub                 = True
#   hub_model_id                = HF_REPO_MODEL
#   hub_strategy                = "checkpoint"   # day thu muc last-checkpoint
#   hub_private_repo            = True
#
# hub_strategy="checkpoint" la thu quan trong: no day checkpoint gan nhat len HF
# sau moi lan save, nen neu pod chet ban resume duoc tu HF chu khong mat gi.
if has_stage train; then
  echo "===== [2/5] TRAIN ====="
  RESUME_ARG=""
  if hf download "$HF_REPO_MODEL" --include "last-checkpoint/*" \
       --local-dir "$WORK/resume" 2>/dev/null; then
    RESUME_ARG="--resume_from_checkpoint $WORK/resume/last-checkpoint"
    echo ">>> Tim thay checkpoint tren HF, se train tiep."
  fi

  python train_qlora.py \
    --base_model      "$BASE_MODEL" \
    --dataset         "$HF_REPO_DATA" \
    --max_seq_length  "$MAX_SEQ_LEN" \
    --epochs          "$EPOCHS" \
    --output_dir      "$ADAPTER_DIR" \
    --hub_model_id    "$HF_REPO_MODEL" \
    --run_name        "$RUN_NAME" \
    ${SMOKE:+--limit_samples 50} \
    $RESUME_ARG

  hf upload "$HF_REPO_MODEL" "$ADAPTER_DIR" "adapter/${RUN_NAME}" --repo-type model
  echo "OK: adapter da luu tren HF."
fi

# =============================== 3. MERGE ====================================
if has_stage merge; then
  echo "===== [3/5] MERGE LoRA -> bf16 ====="
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

# ================================ 4. GGUF ====================================
if has_stage gguf; then
  echo "===== [4/5] CONVERT -> GGUF Q4_K_M ====="
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

  # SMOKE TEST: nap that + sinh that truoc khi tat pod.
  # Neu file GGUF hong ma pod da chet thi ban phai bat lai pod de lam lai.
  echo ">>> Smoke test..."
  "$WORK/llama-bin/llama-server" -m "$Q4" -c "$MAX_SEQ_LEN" -ngl 99 -np 1 \
    --host 127.0.0.1 --port 8080 > "$WORK/smoke.log" 2>&1 &
  SRV=$!
  for i in $(seq 1 60); do
    curl -sf http://127.0.0.1:8080/health >/dev/null && break || sleep 5
  done
  # xac nhan toan bo layer nam tren GPU
  grep -qi "offloaded .*/.* layers to GPU" "$WORK/smoke.log" && \
    grep -i "offloaded" "$WORK/smoke.log" | tail -2

  curl -s http://127.0.0.1:8080/v1/chat/completions -H 'Content-Type: application/json' \
    -d '{"messages":[{"role":"user","content":"Trich dan can cu phap ly cho quy dinh ve toc do toi da trong khu dan cu."}],
         "temperature":0.7,"top_p":0.8,"top_k":20,"presence_penalty":1.0,
         "seed":42,"max_tokens":256}' | tee "$WORK/smoke_out.json" | head -c 2000
  kill $SRV 2>/dev/null || true

  python -c "
import json,sys
d=json.load(open('$WORK/smoke_out.json'))
t=d['choices'][0]['message']['content']
assert len(t.strip())>50, 'output rong / qua ngan'
print('\nOK smoke test. prompt_tokens=', d['usage']['prompt_tokens'])
"
fi

# ============================== 5. PUBLISH ===================================
if has_stage publish; then
  echo "===== [5/5] DAY GGUF LEN HF ====="
  export HF_HUB_ENABLE_HF_TRANSFER=1
  Q4="$GGUF_DIR/${RUN_NAME}-Q4_K_M.gguf"
  sha256sum "$Q4" > "$Q4.sha256"

  hf upload "$HF_REPO_MODEL" "$Q4"        "gguf/$(basename $Q4)"        --repo-type model
  hf upload "$HF_REPO_MODEL" "$Q4.sha256" "gguf/$(basename $Q4).sha256" --repo-type model

  echo ""
  echo "HOAN TAT. File dung cho CA phien 1 va phien 3:"
  echo "  hf download $HF_REPO_MODEL gguf/$(basename $Q4) --local-dir ."
fi

echo "===== TAT CA CHANG DA XONG ====="
