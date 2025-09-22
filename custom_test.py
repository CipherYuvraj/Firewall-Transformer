#!/usr/bin/env python3
"""
Interactive anomaly scoring test tool.
Test your own web requests to see their anomaly scores.
"""

import sys
import os
sys.path.append('scripts')

from transformers import RobertaForMaskedLM, RobertaTokenizer
from scoring import PseudoLogLikelihoodScorer
from canonicalize import canonicalize_request
import json

def load_model():
    """Load the trained model and tokenizer."""
    print("Loading model and tokenizer...")
    model = RobertaForMaskedLM.from_pretrained("model/")
    tokenizer = RobertaTokenizer.from_pretrained("model/")
    scorer = PseudoLogLikelihoodScorer(model, tokenizer)
    print(f"✓ Model loaded ({model.num_parameters():,} parameters)")
    return scorer, tokenizer

def score_request(scorer, tokenizer, method, path, query="", headers=""):
    """Score a single web request."""
    # Parse query and headers
    query_params = {}
    if query:
        for param in query.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                query_params[key] = value
    
    headers_dict = {}
    if headers:
        for header in headers.split(';'):
            if ':' in header:
                key, value = header.split(':', 1)
                headers_dict[key.strip().lower()] = value.strip()
    
    # Create log entry in the format expected by canonicalize_request
    log_entry = {
        'method': method,
        'path': path,
        'query_params': query_params,
        'headers': headers_dict
    }
    
    # Canonicalize
    canonical_text = canonicalize_request(log_entry)
    
    # Score
    inputs = tokenizer(canonical_text, return_tensors="pt", truncation=True, max_length=256)
    score = float(scorer.pseudo_loglikelihood(inputs['input_ids'].squeeze()))
    
    return canonical_text, score

def interpret_score(score):
    """Interpret the anomaly score."""
    if score < 150:
        return "LOW (Normal)", "🟢"
    elif score < 250:
        return "MEDIUM (Suspicious)", "🟡"  
    elif score < 350:
        return "HIGH (Anomalous)", "🟠"
    else:
        return "CRITICAL (Attack)", "🔴"

def interactive_test():
    """Interactive testing mode."""
    scorer, tokenizer = load_model()
    
    print("\n" + "="*60)
    print("🔍 INTERACTIVE ANOMALY SCORE TESTER")
    print("="*60)
    print("Test your web requests to see their anomaly scores!")
    print("Higher scores = more anomalous/suspicious")
    print("\nExamples:")
    print("  Method: GET")
    print("  Path: /api/users")  
    print("  Query: limit=10&offset=0 (optional)")
    print("  Headers: user-agent:browser;content-type:json (optional)")
    print("\nType 'quit' to exit\n")
    
    while True:
        try:
            print("-" * 40)
            method = input("Method (GET/POST/etc): ").strip().upper()
            if method.lower() == 'quit':
                break
                
            path = input("Path: ").strip()
            if not path.startswith('/'):
                path = '/' + path
                
            query = input("Query (optional): ").strip()
            headers = input("Headers (optional): ").strip()
            
            # Score the request
            canonical_text, score = score_request(scorer, tokenizer, method, path, query, headers)
            risk_level, emoji = interpret_score(score)
            
            print(f"\n📊 RESULTS:")
            print(f"Canonical: {canonical_text}")
            print(f"Score: {score:.2f}")
            print(f"Risk Level: {emoji} {risk_level}")
            
            if score > 300:
                print("⚠️  HIGH ANOMALY SCORE - Potential attack detected!")
            elif score > 250:
                print("⚠️  Elevated score - Review recommended")
            else:
                print("✓ Normal traffic pattern")
            print()
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
    
    print("Thanks for testing! 👋")

def batch_test_from_file(filename):
    """Test requests from a file."""
    scorer, tokenizer = load_model()
    
    print(f"\n📁 Testing requests from: {filename}")
    print("-" * 50)
    
    results = []
    
    try:
        with open(filename, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                try:
                    # Parse line: METHOD|PATH|QUERY|HEADERS
                    parts = line.split('|')
                    method = parts[0] if len(parts) > 0 else "GET"
                    path = parts[1] if len(parts) > 1 else "/"
                    query = parts[2] if len(parts) > 2 else ""
                    headers = parts[3] if len(parts) > 3 else ""
                    
                    canonical_text, score = score_request(scorer, tokenizer, method, path, query, headers)
                    risk_level, emoji = interpret_score(score)
                    
                    result = {
                        "line": line_num,
                        "method": method,
                        "path": path,
                        "score": score,
                        "risk_level": risk_level,
                        "canonical": canonical_text
                    }
                    results.append(result)
                    
                    print(f"{line_num:3d}. {emoji} {score:7.2f} - {method} {path}")
                    
                except Exception as e:
                    print(f"{line_num:3d}. ❌ Error parsing line: {e}")
    
    except FileNotFoundError:
        print(f"File not found: {filename}")
        return
    
    # Save results
    output_file = f"batch_test_results_{filename.replace('.txt', '')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📊 Summary:")
    print(f"Total requests tested: {len(results)}")
    high_risk = sum(1 for r in results if r['score'] > 300)
    medium_risk = sum(1 for r in results if 250 <= r['score'] <= 300)
    print(f"High risk (>300): {high_risk}")
    print(f"Medium risk (250-300): {medium_risk}")
    print(f"Results saved to: {output_file}")

def predefined_tests():
    """Run predefined test cases."""
    scorer, tokenizer = load_model()
    
    test_cases = [
        # Normal requests
        ("GET", "/", "", ""),
        ("GET", "/api/users", "limit=10", "user-agent:browser"),
        ("POST", "/api/login", "", "content-type:application/json"),
        ("GET", "/static/css/style.css", "", "user-agent:browser"),
        
        # Suspicious requests  
        ("GET", "/admin", "", ""),
        ("POST", "/admin/users", "", "user-agent:scanner"),
        ("GET", "/api/internal/config", "", ""),
        
        # Attack patterns
        ("GET", "/etc/passwd", "", ""),
        ("GET", "/admin/../../../etc/passwd", "", ""),
        ("POST", "/api/users", "id=1' OR '1'='1", ""),
        ("GET", "/search", "q=<script>alert(1)</script>", ""),
        ("DELETE", "/api/users/../../etc/shadow", "", "x-forwarded-for:attacker"),
        ("GET", "/app", "", "user-agent:' UNION SELECT * FROM users--"),
    ]
    
    print("\n🧪 PREDEFINED TEST CASES")
    print("=" * 60)
    
    results = []
    for i, (method, path, query, headers) in enumerate(test_cases, 1):
        canonical_text, score = score_request(scorer, tokenizer, method, path, query, headers)
        risk_level, emoji = interpret_score(score)
        
        results.append({
            "test_case": i,
            "method": method,
            "path": path,
            "query": query,
            "headers": headers,
            "score": score,
            "risk_level": risk_level,
            "canonical": canonical_text
        })
        
        print(f"{i:2d}. {emoji} {score:7.2f} - {method} {path}")
        if query:
            print(f"    Query: {query}")
        if headers:
            print(f"    Headers: {headers}")
        print(f"    Risk: {risk_level}")
        print()
    
    # Save results
    with open("predefined_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("Results saved to: predefined_test_results.json")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "interactive":
            interactive_test()
        elif sys.argv[1] == "predefined":
            predefined_tests()
        elif sys.argv[1] == "file" and len(sys.argv) > 2:
            batch_test_from_file(sys.argv[2])
        else:
            print("Usage:")
            print("  python custom_test.py interactive     # Interactive testing")
            print("  python custom_test.py predefined      # Run predefined tests")
            print("  python custom_test.py file <filename> # Test from file")
    else:
        # Default: show all options
        print("🔍 Anomaly Score Testing Options:")
        print("1. python custom_test.py interactive     # Test your own requests")
        print("2. python custom_test.py predefined      # Run attack/normal examples")
        print("3. python custom_test.py file test.txt   # Batch test from file")
        print("\nFor quick demo, try: python custom_test.py predefined")