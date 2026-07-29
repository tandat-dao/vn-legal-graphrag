#!/usr/bin/env bash
# =============================================================================
# upload_dataset.sh - day du lieu huan luyen FT-04 len HF dataset repo.
#
# CHAY TREN MAY NGUOI DUNG, KHONG chay tren pod.
#
# Ly do ton tai: finetune/build_dataset.py sinh train.jsonl + val.jsonl CUC BO
# va .gitignore chan finetune/data/*.jsonl (nang, tai tao duoc) -> pod khong
# lay duoc qua git. run.sh chang `data` tai chung tu HF_REPO_DATA va doi chieu
# sha256, nen file .sha256 phai duoc sinh O DAY, TRUOC khi upload.
#
# CACH CHAY:
#   export HF_TOKEN=hf_xxxxx
#   bash finetune/upload_dataset.sh
#
#   # doi repo dich:
#   HF_REPO_DATA=<user>/<repo> bash finetune/upload_dataset.sh
# =============================================================================
set -Eeuo pipefail

HF_REPO_DATA="${HF_REPO_DATA:-dangnguyen254/thesis-graphrag-data}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="$REPO_ROOT/finetune/data"

[ -n "${HF_TOKEN:-}" ] || { echo "LOI: chua dat HF_TOKEN"; exit 1; }
for f in train.jsonl val.jsonl; do
  [ -f "$DATA_DIR/$f" ] || {
    echo "LOI: thieu $DATA_DIR/$f - chay 'python -m finetune.build_dataset' truoc."
    exit 1
  }
done

cd "$DATA_DIR"

# sha256 in RA TRUOC khi upload: day la gia tri de doi chieu voi cai pod tu
# tinh sau khi tai. Chep vao so tay/khoa luan neu can truy vet artifact.
echo "===================== SHA256 TRUOC KHI UPLOAD ====================="
for f in train.jsonl val.jsonl; do
  sha256sum "$f" | tee "$f.sha256"
  echo "  $(wc -l < "$f") dong, $(du -h "$f" | cut -f1)"
done
echo "=================================================================="

hf auth login --token "$HF_TOKEN"

# Repo PRIVATE: bo nguon thangvip/vietnamese-legal-qa co giay phep rieng, va
# day la du lieu trung gian cua khoa luan - khong phat hanh cong khai.
hf repo create "$HF_REPO_DATA" --repo-type dataset --private --exist-ok

for f in train.jsonl val.jsonl train.jsonl.sha256 val.jsonl.sha256; do
  hf upload "$HF_REPO_DATA" "$f" "$f" --repo-type dataset \
    --commit-message "FT-04 dataset: $f"
done

echo ""
echo "XONG. Kiem tra tren pod bang:"
echo "  STAGES=data bash finetune/run.sh"
