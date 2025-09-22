#!/usr/bin/env python3
"""
Test script to evaluate the trained model on e-commerce data
"""
import json
import torch
from transformers import RobertaForMaskedLM, RobertaTokenizer
from scripts.scoring import PseudoLogLikelihoodScorer
from scripts.canonicalize import canonicalize_request

def test_model_on_ecom_data():
    print("=== Testing Trained Model on E-commerce Data ===")
    
    # Load trained model and tokenizer
    print("Loading model and tokenizer...")
    try:
        model = RobertaForMaskedLM.from_pretrained("model_json")
        tokenizer = RobertaTokenizer.from_pretrained("model_json")
        print(f"✅ Model loaded successfully")
        print(f"   Vocab size: {tokenizer.vocab_size}")
        print(f"   Model parameters: {sum(p.numel() for p in model.parameters()):,}")
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return
    
    # Create scorer
    scorer = PseudoLogLikelihoodScorer(model, tokenizer)
    
    # Test on sample data
    print("\n=== Testing on Sample E-commerce Requests ===")
    
    # Load some real data samples
    with open('data/ecom_benign.jsonl', 'r') as f:
        samples = []
        for i, line in enumerate(f):
            if i >= 10:  # Test first 10 samples
                break
            samples.append(json.loads(line.strip()))
    
    scores = []
    for i, sample in enumerate(samples):
        # Canonicalize
        canonical = canonicalize_request(sample)
        
        # Tokenize
        inputs = tokenizer(canonical, return_tensors="pt", truncation=True, max_length=256)
        
        # Score
        with torch.no_grad():
            score = scorer.pseudo_loglikelihood(inputs['input_ids'].squeeze())
        
        scores.append(score)
        
        print(f"Sample {i+1}:")
        print(f"  Method: {sample.get('m', 'N/A')}")
        print(f"  Path: {sample.get('p', 'N/A')}")
        print(f"  Score: {score:.2f}")
        print()
    
    # Statistics
    print("=== Score Statistics ===")
    print(f"Mean score: {torch.mean(torch.tensor(scores)):.2f}")
    print(f"Std score: {torch.std(torch.tensor(scores)):.2f}")
    print(f"Min score: {torch.min(torch.tensor(scores)):.2f}")
    print(f"Max score: {torch.max(torch.tensor(scores)):.2f}")
    
    # Test with some potential attack patterns
    print("\n=== Testing Attack Patterns ===")
    attack_samples = [
        {"m": "GET", "p": "/store/../../../etc/passwd", "q": {}, "b": "", "s": "attacker.com", "h": {"ua": "curl", "ct": "text/plain", "cl": "0", "cookieKeys": []}},
        {"m": "POST", "p": "/store/api/admin", "q": {}, "b": "<script>alert('xss')</script>", "s": "evil.com", "h": {"ua": "curl", "ct": "text/html", "cl": "30", "cookieKeys": []}},
        {"m": "GET", "p": "/store/search", "q": {"q": "'; DROP TABLE products; --"}, "b": "", "s": "10.0.0.1", "h": {"ua": "sqlmap", "ct": "text/plain", "cl": "0", "cookieKeys": []}}
    ]
    
    for i, attack in enumerate(attack_samples):
        canonical = canonicalize_request(attack)
        inputs = tokenizer(canonical, return_tensors="pt", truncation=True, max_length=256)
        
        with torch.no_grad():
            score = scorer.pseudo_loglikelihood(inputs['input_ids'].squeeze())
        
        print(f"Attack {i+1}: {attack['p']} → Score: {score:.2f}")
    
    print("\n✅ Model testing completed!")

if __name__ == "__main__":
    test_model_on_ecom_data()