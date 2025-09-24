# train_mlm.py
from datasets import load_dataset
from transformers import (RobertaConfig, RobertaForMaskedLM,
                          PreTrainedTokenizerFast, DataCollatorForLanguageModeling,
                          Trainer, TrainingArguments)
from sklearn.model_selection import train_test_split
import pandas as pd

# Split
lines = [l.rstrip() for l in open("ecom.txt")]
train_lines, val_lines = train_test_split(lines, test_size=0.1, random_state=42)

open("train.txt","w").write("\n".join(train_lines))
open("val.txt","w").write("\n".join(val_lines))

tok = PreTrainedTokenizerFast(
    tokenizer_file="model/tokenizer/bpe.json",
    bos_token="[CLS]", eos_token="[SEP]",
    unk_token="[UNK]", pad_token="[PAD]", mask_token="[MASK]"
)

def load_text(fp): return load_dataset("text", data_files=fp, split="train")
ds_tr = load_text("train.txt"); ds_va = load_text("val.txt")
def enc(b): return tok(b["text"], truncation=True, max_length=256)
ds_tr = ds_tr.map(enc, batched=True, remove_columns=["text"])
ds_va = ds_va.map(enc, batched=True, remove_columns=["text"])

cfg = RobertaConfig(
  vocab_size=tok.vocab_size, hidden_size=256,
  num_hidden_layers=6, num_attention_heads=8,
  max_position_embeddings=512, layer_norm_eps=1e-5
)
model = RobertaForMaskedLM(cfg)

args = TrainingArguments(
  output_dir="model/checkpoints",
  per_device_train_batch_size=64,
  per_device_eval_batch_size=64,
  num_train_epochs=3,
  learning_rate=5e-4,
  logging_steps=100,
  save_total_limit=2,
)
collator = DataCollatorForLanguageModeling(tok, mlm_probability=0.15)
trainer = Trainer(model=model, args=args, data_collator=collator,
                  train_dataset=ds_tr, eval_dataset=ds_va)
trainer.train()
trainer.save_model("model/checkpoints/latest")
tok.save_pretrained("model/checkpoints/latest")
