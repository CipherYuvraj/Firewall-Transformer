# make_text.py
import json, sys
def as_text(r):
    q = "&".join(f"{k}={v}" for k,v in sorted(r.get("q",{}).items()))
    h = r.get("h",{})
    ua, ct, cl = h.get("ua",""), h.get("ct",""), h.get("cl","")
    ck = ",".join(h.get("cookieKeys",[]))
    # ONE flat string, stable fields first
    return f'{r["m"]} {r["p"]} ? {q} UA={ua} CT={ct} CL={cl} CK={ck} B={r.get("b","")[:80]} S={r.get("s","")}'
for line in sys.stdin:
    r=json.loads(line); print(as_text(r))
