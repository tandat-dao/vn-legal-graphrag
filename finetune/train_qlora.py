#!/usr/bin/env python3
# =============================================================================
# train_qlora.py  -  PHIEN 2: QLoRA tren Qwen3-4B-Instruct-2507
#
# Duoc goi boi run.sh. Cung chay truc tiep tren Kaggle de dry-run:
#
#   python train_qlora.py --dataset data.jsonl --limit-samples 50 \
#          --max-seq-length 2048 --epochs 1 --output-dir /tmp/dry/adapter_real \
#          --no-push
#
# THIET KE:
#   * TU RENDER chat template thanh cot "text" truoc khi vao trainer.
#     TRL >= 0.24 khong con tu nhan dien dataset dang "messages".
#     Tu render cung cho phep AUDIT do dai tren DUNG chuoi duoc huan luyen.
#   * TRAIN ON RESPONSES ONLY (mac dinh bat).
#     Mau ~7500 token nhung dap an chi ~400. Neu tinh loss tren toan chuoi,
#     ~94% gradient dung de tai tao lai ngu canh da co san o dau vao.
#   * batch_size=1 -> KHONG padding -> khong co phat n^2 do dem len 16k.
#   * API-agnostic: tu do ten tham so (max_length vs max_seq_length,
#     processing_class vs tokenizer) de chay duoc voi nhieu doi TRL.
# =============================================================================

import argparse, dataclasses, inspect, json, os, pathlib, sys

import unsloth   # PHAI import truoc trl/transformers/peft, neu khong mat toi uu
from unsloth import FastLanguageModel
from unsloth.chat_templates import train_on_responses_only
from trl import SFTTrainer, SFTConfig
from datasets import Dataset, load_dataset
import numpy as np


# Moc cat cho ChatML (Qwen3 dung dinh dang nay).
# train_on_responses_only che moi thu tu INSTR den RESP khoi ham mat mat.
INSTR_PART = "<|im_start|>user\n"
RESP_PART  = "<|im_start|>assistant\n"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--base-model",  default="unsloth/Qwen3-4B-Instruct-2507")
    p.add_argument("--dataset",     required=True,
                   help="file .jsonl cuc bo, hoac repo dataset tren HF")
    p.add_argument("--dataset-split", default="train")
    p.add_argument("--output-dir",  default="/workspace/adapter")
    p.add_argument("--max-seq-length", type=int, default=16384)
    p.add_argument("--epochs",      type=float, default=2)
    p.add_argument("--limit-samples", type=int, default=0, help="0 = dung het")
    p.add_argument("--lr",          type=float, default=2e-4)
    p.add_argument("--lora-r",      type=int, default=32)
    p.add_argument("--lora-alpha",  type=int, default=64)
    p.add_argument("--grad-accum",  type=int, default=16)
    p.add_argument("--save-steps",  type=int, default=50)
    p.add_argument("--seed",        type=int, default=42)
    p.add_argument("--run-name",    default="ft04")
    p.add_argument("--hub-model-id", default=None)
    p.add_argument("--no-push",     action="store_true")
    p.add_argument("--no-response-only", action="store_true",
                   help="tinh loss tren toan chuoi thay vi chi phan dap an")
    p.add_argument("--allow-truncation", action="store_true",
                   help="BO QUA assert do dai. Chi dung khi biet minh dang lam gi.")
    p.add_argument("--resume-from-checkpoint", default=None)
    p.add_argument("--dump-prompts", type=int, default=3,
                   help="ghi N chuoi da render ra file de kiem bang mat")
    return p.parse_args()


# --------------------------------------------------------------------------
def load_rows(path_or_repo, split):
    """Chap nhan .jsonl cuc bo hoac repo HF. Moi ban ghi phai co:
         {"messages": [{"role": "...", "content": "..."}, ...]}
       hoac ba truong roi: system / user / assistant."""
    if os.path.exists(path_or_repo):
        rows = [json.loads(l) for l in open(path_or_repo, encoding="utf-8") if l.strip()]
    else:
        rows = list(load_dataset(path_or_repo, split=split))

    out = []
    for r in rows:
        if "messages" in r:
            out.append(r["messages"])
        elif {"user", "assistant"} <= set(r):
            m = []
            if r.get("system"):
                m.append({"role": "system", "content": r["system"]})
            m.append({"role": "user",      "content": r["user"]})
            m.append({"role": "assistant", "content": r["assistant"]})
            out.append(m)
        else:
            raise ValueError(f"Ban ghi khong nhan dang duoc, cac khoa: {list(r)}")
    return out


def audit_lengths(texts, tok, limit, allow_trunc, outdir):
    """Phep assert o diem 3: KHONG mau nao duoc cham tran.
    Neu vuot, thu vien cat phan DUOI -> cat dung dap an va khoi trich dan
    -> day mo hinh sinh cau tra loi cut khong trich dan. Hong AM THAM."""
    n = np.array([len(tok(t, add_special_tokens=False)["input_ids"]) for t in texts])
    stats = dict(n_samples=int(n.size), p50=int(np.percentile(n, 50)),
                 p95=int(np.percentile(n, 95)), max=int(n.max()),
                 mean=int(n.mean()), total_tokens=int(n.sum()),
                 over_limit=int((n > limit).sum()), limit=limit)

    print("\n--- PHAN BO DO DAI MAU (tokenizer that, chuoi that) ---")
    for k in ("n_samples", "p50", "mean", "p95", "max", "limit", "over_limit"):
        print(f"  {k:14s} {stats[k]:>10,}")
    print(f"  {'total_tokens':14s} {stats['total_tokens']:>10,}"
          f"   <- nhan voi so epoch = khoi luong cong viec that")
    pathlib.Path(outdir, "length_stats.json").write_text(json.dumps(stats, indent=2))

    if stats["over_limit"]:
        idx = np.where(n > limit)[0][:10]
        msg = (f"\n{stats['over_limit']} mau vuot tran {limit} "
               f"(dai nhat {stats['max']}). Chi so: {idx.tolist()}\n"
               f"Chung se bi CAT DUOI -> mat dap an va khoi trich dan.\n"
               f"Sua du lieu, hoac nang --max-seq-length, hoac --allow-truncation.")
        if not allow_trunc:
            raise SystemExit("DUNG LAI." + msg)
        print("CANH BAO (da bo qua theo yeu cau):" + msg)
    else:
        print(f"  OK: 0/{stats['n_samples']} mau vuot tran.\n")
    return stats


def build_sft_kwargs(a, bf16, cf_fields):
    """Ten tham so doi giua cac doi TRL. Do thay vi hardcode."""
    kw = dict(
        per_device_train_batch_size = 1,          # 1 mau = 1 chuoi, KHONG padding
        gradient_accumulation_steps = a.grad_accum,
        num_train_epochs            = a.epochs,
        learning_rate               = a.lr,
        warmup_ratio                = 0.03,
        lr_scheduler_type           = "cosine",
        optim                       = "adamw_8bit",
        weight_decay                = 0.01,
        logging_steps               = 5,
        save_steps                  = a.save_steps,
        save_total_limit            = 2,
        bf16 = bf16, fp16 = not bf16,
        packing                     = False,      # khong gop mau
        output_dir                  = a.output_dir,
        run_name                    = a.run_name,
        report_to                   = "none",
        seed                        = a.seed,
    )
    kw["max_length" if "max_length" in cf_fields else "max_seq_length"] = a.max_seq_length
    if "dataset_text_field" in cf_fields:
        kw["dataset_text_field"] = "text"
    if not a.no_push and a.hub_model_id:
        kw.update(push_to_hub=True, hub_model_id=a.hub_model_id,
                  hub_strategy="checkpoint",     # day last-checkpoint sau moi lan save
                  hub_private_repo=True)
    return {k: v for k, v in kw.items() if k in cf_fields or k == "output_dir"}


# ================================== MAIN =====================================
def main():
    a = parse_args()
    pathlib.Path(a.output_dir).mkdir(parents=True, exist_ok=True)

    import torch
    bf16 = torch.cuda.get_device_capability(0)[0] >= 8   # compute cap, KHONG
    #   dung torch.cuda.is_bf16_supported(): tren T4 (sm75) no tra ve True vi
    #   tinh ca bf16 MO PHONG bang phan mem.
    print(f"GPU {torch.cuda.get_device_name(0)} | "
          f"sm{''.join(map(str, torch.cuda.get_device_capability(0)))} | "
          f"bf16 goc = {bf16}")

    # ---------------- 1. model ----------------
    model, tok = FastLanguageModel.from_pretrained(
        model_name     = a.base_model,
        max_seq_length = a.max_seq_length,
        load_in_4bit   = True,
        dtype          = None,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r              = a.lora_r,
        lora_alpha     = a.lora_alpha,
        lora_dropout   = 0.0,
        bias           = "none",
        target_modules = ["q_proj","k_proj","v_proj","o_proj",
                          "gate_proj","up_proj","down_proj"],
        use_gradient_checkpointing = "unsloth",
        use_rslora     = False,
        random_state   = a.seed,
    )

    # ---------------- 2. du lieu ----------------
    convs = load_rows(a.dataset, a.dataset_split)
    if a.limit_samples:
        convs = convs[:a.limit_samples]
    print(f"Nap {len(convs)} hoi thoai tu {a.dataset}")

    # TU render. add_generation_prompt=False vi luot assistant DA nam trong
    # hoi thoai — day la du lieu huan luyen, khong phai prompt suy luan.
    texts = [tok.apply_chat_template(c, tokenize=False, add_generation_prompt=False)
             for c in convs]

    if a.dump_prompts:
        d = pathlib.Path(a.output_dir, "rendered_samples.txt")
        d.write_text("\n\n" + ("=" * 78 + "\n").join(texts[:a.dump_prompts]))
        print(f"Da ghi {a.dump_prompts} chuoi da render -> {d}")

    audit_lengths(texts, tok, a.max_seq_length, a.allow_truncation, a.output_dir)
    ds = Dataset.from_dict({"text": texts}).shuffle(seed=a.seed)

    # ---------------- 3. trainer ----------------
    cf = {f.name for f in dataclasses.fields(SFTConfig)}
    tr = set(inspect.signature(SFTTrainer.__init__).parameters)
    tok_arg = "processing_class" if "processing_class" in tr else "tokenizer"
    print(f"API TRL: tok_arg={tok_arg} | "
          f"seq_arg={'max_length' if 'max_length' in cf else 'max_seq_length'}")

    trainer = SFTTrainer(
        model         = model,
        train_dataset = ds,
        args          = SFTConfig(**build_sft_kwargs(a, bf16, cf)),
        **{tok_arg: tok},
    )

    if not a.no_response_only:
        trainer = train_on_responses_only(
            trainer, instruction_part=INSTR_PART, response_part=RESP_PART)
        print("Loss chi tinh tren phan DAP AN (prompt bi che).")
        # Kiem bang mat: phan bi che phai hien -100
        ex = trainer.train_dataset[0]
        if "labels" in ex:
            lab = np.array(ex["labels"])
            print(f"  che {(lab == -100).sum()}/{lab.size} token "
                  f"({(lab == -100).mean()*100:.1f}%) — con lai la dap an")
    else:
        print("Loss tinh tren TOAN CHUOI (--no-response-only).")

    # ---------------- 4. train ----------------
    st = trainer.train(resume_from_checkpoint=a.resume_from_checkpoint)
    print(f"\nXONG: loss={st.training_loss:.4f}  runtime={st.metrics['train_runtime']:.0f}s")
    print(f"  thong luong ~ {st.metrics.get('train_tokens_per_second', float('nan')):.0f} tok/s")

    model.save_pretrained(a.output_dir)
    tok.save_pretrained(a.output_dir)
    pathlib.Path(a.output_dir, "train_result.json").write_text(
        json.dumps({"loss": st.training_loss, **st.metrics}, indent=2))
    print("adapter ->", a.output_dir)


if __name__ == "__main__":
    main()
