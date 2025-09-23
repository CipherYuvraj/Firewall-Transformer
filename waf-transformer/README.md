{
  "m": "HTTP_METHOD",
  "p": "/normalized/path/:num/:id",
  "q": { "key": "value", "page": ":num" },
  "b" : "<body in case of post requests>"
  "s" : "source hostname orip",
  "h": {
    "ua": "Mozilla/5.0",
    "ct": "application/json",
    "cl": ":num",
    "cookieKeys": ["sid", "ab"]
  }
}


Steps :

1. python3 make_text.py < /mnt/data/ecom_benign.jsonl > ecom.txt
2. python3 train_tokenizer.py
3. python3 train_mlm.py