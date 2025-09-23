# Generate a synthetic benign JSONL dataset for an e-commerce store
# matching the user's schema. Saves to /mnt/data/ecom_benign.jsonl
import json, random, time, pathlib, itertools, string

out_path = pathlib.Path("ecom_benign.jsonl")

UAS = [
    "Mozilla/5.0", "Safari/17.5", "Chrome/128.0", "curl/8.4.0", "Firefox/129.0"
]
CONTENT_TYPES = ["application/json", "application/x-www-form-urlencoded", "text/plain"]
HOSTS = ["shop.example.com", "api.shop.example.com", "10.0.0.5", "10.0.0.10"]
COOKIE_KEYS_POOL = ["sid", "ab", "pref", "cart", "trk"]
SEARCH_TERMS = ["shoe", "shirt", "laptop", "phone", "headphones", "bag", "watch", "book"]
CATEGORIES = ["electronics", "fashion", "home", "beauty", "sports", "toys"]
PAYMENT_METHODS = ["card", "cod", "wallet"]
LANGS = ["en", "en", "en", "en", "en", "en", "hi", "bn", "ta"]

def choose_cookie_keys():
    k = random.sample(COOKIE_KEYS_POOL, k=random.randint(1, min(3, len(COOKIE_KEYS_POOL))))
    return k

def make_get_record():
    route = random.choice([
        ("/", {}),
        ("/home", {}),
        ("/search", {"q": random.choice(SEARCH_TERMS), "page": ":num"}),
        ("/category/:num", {"sort": random.choice(["price","popular","rating"]), "page": ":num"}),
        ("/product/:num", {}),
        ("/cart", {}),
        ("/checkout", {}),
        ("/order/:num", {}),
        ("/api/products", {"category": random.choice(CATEGORIES), "page": ":num"}),
        ("/api/reviews/:num", {"page": ":num"}),
        ("/api/suggest", {"q": random.choice(SEARCH_TERMS[:4])}),
    ])
    path, q = route
    return {
        "m": "GET",
        "p": f"/store{path}",
        "q": {k: str(v) for k, v in q.items()},
        "b": "",
        "s": random.choice(HOSTS),
        "h": {
            "ua": random.choice(UAS),
            "ct": "text/plain",
            "cl": ":num",
            "cookieKeys": choose_cookie_keys()
        }
    }

def make_post_record():
    route = random.choice([
        ("/api/cart/add", {"productId": ":num", "qty": ":num"}),
        ("/api/cart/update", {"productId": ":num", "qty": ":num"}),
        ("/api/checkout/create", {"payment": random.choice(PAYMENT_METHODS), "addrId": ":num"}),
        ("/api/user/login", {"email": "user@example.com", "hasPwd": "true"}),
        ("/api/user/register", {"ref": "ads", "lang": random.choice(LANGS)}),
        ("/api/review/submit", {"productId": ":num", "rating": ":num"}),
        ("/api/wishlist/add", {"productId": ":num"}),
    ])
    path, body = route
    # Encode body as a compact JSON string per the user's "b" requirement
    body_json = json.dumps(body, separators=(",", ":"))
    return {
        "m": "POST",
        "p": f"/store{path}",
        "q": {},  # queries in POST kept empty here
        "b": body_json,
        "s": random.choice(HOSTS),
        "h": {
            "ua": random.choice(UAS),
            "ct": random.choice(CONTENT_TYPES),
            "cl": ":num",
            "cookieKeys": choose_cookie_keys()
        }
    }

random.seed(42)

N = 10000  # number of lines
with out_path.open("w") as f:
    for i in range(N):
        rec = make_get_record() if random.random() < 0.65 else make_post_record()
        f.write(json.dumps(rec, separators=(",", ":")) + "\n")

# show a small preview (first 10 lines)
preview = []
with out_path.open() as f:
    for _ in range(10):
        preview.append(next(f).rstrip())

out_path, "\n".join(preview)
