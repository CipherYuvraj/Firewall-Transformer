#!/usr/bin/env python3
"""
Test script for the new e-commerce data format
"""
import json
from scripts.canonicalize import canonicalize_request

# Test with your new data format
sample_get = {
    'm': 'GET',
    'p': '/store/category/:num',
    'q': {'sort': 'rating', 'page': ':num'},
    'b': '',
    's': 'api.shop.example.com',
    'h': {'ua': 'Mozilla/5.0', 'ct': 'text/plain', 'cl': ':num', 'cookieKeys': ['trk', 'sid', 'pref']}
}

sample_post = {
    'm': 'POST',
    'p': '/store/api/cart/add',
    'q': {},
    'b': '{"productId":"123","qty":"2"}',
    's': '10.0.0.10',
    'h': {'ua': 'Mozilla/5.0', 'ct': 'application/x-www-form-urlencoded', 'cl': '50', 'cookieKeys': ['trk', 'pref']}
}

print("=== Testing New E-commerce Data Format ===")
print()
print("GET Request:")
print("Input:", json.dumps(sample_get, indent=2))
print("Canonicalized:", canonicalize_request(sample_get))
print()
print("POST Request:")
print("Input:", json.dumps(sample_post, indent=2))
print("Canonicalized:", canonicalize_request(sample_post))

# Test with real data from file
print()
print("=== Testing with Real Data ===")
with open('data/ecom_benign.jsonl', 'r') as f:
    for i, line in enumerate(f):
        if i >= 3:  # Just test first 3 lines
            break
        data = json.loads(line.strip())
        canonical = canonicalize_request(data)
        print(f"Line {i+1}: {canonical}")