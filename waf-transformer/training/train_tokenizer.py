# train_tokenizer.py
from tokenizers import Tokenizer, models, trainers, pre_tokenizers
from pathlib import Path
tok = Tokenizer(models.BPE(unk_token="[UNK]"))
tok.pre_tokenizer = pre_tokenizers.ByteLevel()
trainer = trainers.BpeTrainer(
  vocab_size=20000,
  min_frequency=2,
  special_tokens=["[PAD]","[CLS]","[SEP]","[MASK]","[UNK]"]
)
with open("ecom.txt") as f: tok.train_from_iterator((l.strip() for l in f), trainer)
Path("model/tokenizer").mkdir(parents=True, exist_ok=True)
tok.save("model/tokenizer/bpe.json")
