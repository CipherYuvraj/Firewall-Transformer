from ml_scorer.score_requests import score

req = {
        "m": "POST",
        "p": "/store/api/wishlist/add",
        "q": {},
        "b": "{\"productId\":\":num\"}",
        "s": "10.0.0.10",
        "h": {
            "ua": "curl/8.4.0",
            "ct": "application/json",
            "cl": ":num",
            "cookieKeys": ["cart", "ab", "trk"]
        }
    }

score = score(req)
print(f"Score: {score}")
