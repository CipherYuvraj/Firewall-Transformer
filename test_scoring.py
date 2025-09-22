#!/usr/bin/env python3
"""
Test script for the trained model and scoring.
"""

import sys
import os
sys.path.append('scripts')

from transformers import RobertaForMaskedLM, RobertaTokenizer
from scoring import PseudoLogLikelihoodScorer
import json

def test_model():
    print("Loading model and tokenizer...")
    
    # Load model and tokenizer
    try:
        model = RobertaForMaskedLM.from_pretrained("model/")
        tokenizer = RobertaTokenizer.from_pretrained("model/")
        print(f"✓ Model loaded successfully")
        print(f"✓ Tokenizer loaded with vocab size: {tokenizer.vocab_size}")
        
        # Create scorer
        scorer = PseudoLogLikelihoodScorer(model, tokenizer)
        print("✓ Scorer initialized")
        
        # Test with sample canonical logs
        test_samples = [
            "[METHOD] GET [PATH] /api/users [QUERY] limit=10 [HEADERS] user-agent:browser",
            "[METHOD] POST [PATH] /api/login [QUERY] [HEADERS] content-type:application/json",
            "[METHOD] GET [PATH] /admin/config [QUERY] debug=true [HEADERS] authorization:token",
            "[METHOD] DELETE [PATH] /api/users/../../etc/passwd [QUERY] [HEADERS] x-forwarded-for:attacker"
        ]
        
        print("\nTesting scoring on sample logs:")
        results = []
        
        for i, text in enumerate(test_samples, 1):
            print(f"\nSample {i}: {text}")
            inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=256)
            score = scorer.pseudo_loglikelihood(inputs['input_ids'].squeeze())
            print(f"Anomaly Score: {score:.6f}")
            
            results.append({
                "text": text,
                "score": float(score),
                "suspicious": score > -5.0  # Simple threshold for demo
            })
        
        # Save results
        with open("test_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✓ Test completed! Results saved to test_results.json")
        print(f"Model has {model.num_parameters():,} parameters")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_model()