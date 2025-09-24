from ml_scorer.score_requests import score

req = [
  {
    "m": "GET",
    "p": "/store/api/products",
    "q": {},
    "b": "",
    "s": "127.0.0.1",
    "h": {
      "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
      "ct": "text/plain",
      "cl": "0",
      "cookieKeys": ["session"]
    }
  },
  {
    "m": "OPTIONS",
    "p": "/store/api/cart/add",
    "q": {},
    "b": "",
    "s": "127.0.0.1",
    "h": {
      "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
      "ct": "text/plain",
      "cl": "0",
      "cookieKeys": []
    }
  },
  {
    "m": "POST",
    "p": "/store/api/cart/add",
    "q": {},
    "b": "{\"productId\": 1, \"qty\": 1}",
    "s": "127.0.0.1",
    "h": {
      "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
      "ct": "application/json",
      "cl": "23",
      "cookieKeys": ["session"]
    }
  },
  {
    "m": "GET",
    "p": "/store/home",
    "q": {},
    "b": "",
    "s": "127.0.0.1",
    "h": {
      "ua": "python-requests/2.31.0",
      "ct": "text/plain",
      "cl": "0",
      "cookieKeys": []
    }
  },
  {
    "m": "GET",
    "p": "/store/product/:id",
    "q": {},
    "b": "",
    "s": "127.0.0.1",
    "h": {
      "ua": "python-requests/2.31.0",
      "ct": "text/plain",
      "cl": "0",
      "cookieKeys": []
    }
  },
  {
    "m": "GET",
    "p": "/store/search",
    "q": { "q": "laptop" },
    "b": "",
    "s": "127.0.0.1",
    "h": {
      "ua": "python-requests/2.31.0",
      "ct": "text/plain",
      "cl": "0",
      "cookieKeys": []
    }
  },
  {
    "m": "GET",
    "p": "/store/category/:num",
    "q": { "page": ":num" },
    "b": "",
    "s": "127.0.0.1",
    "h": {
      "ua": "python-requests/2.31.0",
      "ct": "text/plain",
      "cl": "0",
      "cookieKeys": []
    }
  },
  {
    "m": "GET",
    "p": "/store/api/products",
    "q": { "category": "electronics" },
    "b": "",
    "s": "127.0.0.1",
    "h": {
      "ua": "python-requests/2.31.0",
      "ct": "text/plain",
      "cl": "0",
      "cookieKeys": []
    }
  },
  {
    "m": "GET",
    "p": "/store/cart",
    "q": {},
    "b": "",
    "s": "127.0.0.1",
    "h": {
      "ua": "python-requests/2.31.0",
      "ct": "text/plain",
      "cl": "0",
      "cookieKeys": []
    }
  },
  {
    "m": "GET",
    "p": "/store/api/suggest",
    "q": { "q": "phone" },
    "b": "",
    "s": "127.0.0.1",
    "h": {
      "ua": "python-requests/2.31.0",
      "ct": "text/plain",
      "cl": "0",
      "cookieKeys": []
    }
  },
  {
    "m": "GET",
    "p": "/store/product/:id",
    "q": {},
    "b": "",
    "s": "127.0.0.1",
    "h": {
      "ua": "python-requests/2.31.0",
      "ct": "text/plain",
      "cl": "0",
      "cookieKeys": []
    }
  },
  {
    "m": "GET",
    "p": "/store/search",
    "q": { "q": ":string" },
    "b": "",
    "s": "127.0.0.1",
    "h": {
      "ua": "python-requests/2.31.0",
      "ct": "text/plain",
      "cl": "0",
      "cookieKeys": []
    }
  },
  {
    "m": "GET",
    "p": "/store/category/:num",
    "q": {},
    "b": "",
    "s": "127.0.0.1",
    "h": {
      "ua": "python-requests/2.31.0",
      "ct": "text/plain",
      "cl": "0",
      "cookieKeys": []
    }
  },
  {
    "m": "GET",
    "p": "/admin",
    "q": {},
    "b": "",
    "s": "127.0.0.1",
    "h": {
      "ua": "python-requests/2.31.0",
      "ct": "text/plain",
      "cl": "0",
      "cookieKeys": []
    }
  },
  {
    "m": "GET",
    "p": "/store/api/products",
    "q": { "category": "<script>alert(1)</script>" },
    "b": "",
    "s": "127.0.0.1",
    "h": {
      "ua": "python-requests/2.31.0",
      "ct": "text/plain",
      "cl": "0",
      "cookieKeys": []
    }
  }
]

score = score(req)
print(f"Score: {score}")
