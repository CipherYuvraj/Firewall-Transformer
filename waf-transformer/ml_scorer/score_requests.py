from typing import Dict
import torch
from transformers import RobertaForMaskedLM, PreTrainedTokenizerFast

def as_text(r: Dict) -> str:
    q = "&".join(f"{k}={v}" for k,v in sorted(r.get("q",{}).items()))
    h = r.get("h",{})
    ua, ct, cl = h.get("ua",""), h.get("ct",""), h.get("cl","")
    ck = ",".join(h.get("cookieKeys",[]))
    # ONE flat string, stable fields first
    return f'{r["m"]} {r["p"]} ? {q} UA={ua} CT={ct} CL={cl} CK={ck} B={r.get("b","")[:120]} S={r.get("s","")}'

def load_model(model_dir: str):
    tok = PreTrainedTokenizerFast.from_pretrained(model_dir)
    mdl = RobertaForMaskedLM.from_pretrained(model_dir)
    mdl.eval().to("cpu")
    return tok, mdl

@torch.no_grad()
def score_request(tok, mdl, r: Dict) -> float:
    text = as_text(r)
    ids = tok(text, return_tensors="pt")
    out = mdl(**ids, labels=ids["input_ids"])
    return float(out.loss)


def score(req):
    tok, mdl = load_model("model/checkpoints/latest")
    s = score_request(tok, mdl, req)
    print(s)