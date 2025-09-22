#!/usr/bin/env python3
"""
Real-time HTTP request interceptor and anomaly scorer for live server monitoring.
Captures requests to https://1x31xtw5-80.inc1.devtunnels.ms/data and scores them in real-time.
"""
import asyncio
import aiohttp
import json
import time
import torch
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from transformers import RobertaForMaskedLM, RobertaTokenizer
import logging

# Local imports
from scripts.scoring import PseudoLogLikelihoodScorer
from scripts.canonicalize import canonicalize_request

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('live_monitoring.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class RequestCapture:
    """Data structure for captured HTTP requests"""
    timestamp: str
    method: str
    path: str
    query_params: Dict
    headers: Dict
    body: str
    source_ip: str
    user_agent: str
    content_type: str
    content_length: str
    canonical_form: str
    anomaly_score: float
    risk_level: str
    processing_time_ms: float

class LiveAnomalyDetector:
    """Real-time anomaly detection system for live web traffic"""
    
    def __init__(self, model_path: str = "model_json", server_url: str = "https://1x31xtw5-80.inc1.devtunnels.ms"):
        """
        Initialize the live anomaly detector
        
        Args:
            model_path: Path to trained model directory
            server_url: Target server URL to monitor
        """
        self.model_path = model_path
        self.server_url = server_url
        self.data_endpoint = f"{server_url}/data"
        
        # Load model and tokenizer
        logger.info(f"Loading model from {model_path}...")
        self.model = RobertaForMaskedLM.from_pretrained(model_path)
        self.tokenizer = RobertaTokenizer.from_pretrained(model_path)
        self.scorer = PseudoLogLikelihoodScorer(self.model, self.tokenizer)
        logger.info(f"✅ Model loaded successfully (vocab: {self.tokenizer.vocab_size})")
        
        # Request storage
        self.captured_requests: List[RequestCapture] = []
        self.alerts: List[RequestCapture] = []
        
        # Thresholds (based on your test results)
        self.normal_threshold = 450  # Above this is suspicious
        self.attack_threshold = 600  # Above this is likely attack
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'normal_requests': 0,
            'suspicious_requests': 0,
            'attack_requests': 0,
            'start_time': datetime.now()
        }
    
    def convert_to_internal_format(self, method: str, path: str, query_params: Dict, 
                                 headers: Dict, body: str, source_ip: str) -> Dict:
        """
        Convert captured request to your model's expected format
        
        Args:
            method: HTTP method
            path: Request path
            query_params: Query parameters dict
            headers: Headers dict
            body: Request body
            source_ip: Client IP address
            
        Returns:
            Dict in your model's format (m, p, q, b, s, h)
        """
        # Extract common headers
        user_agent = headers.get('user-agent', headers.get('User-Agent', 'unknown'))
        content_type = headers.get('content-type', headers.get('Content-Type', 'text/plain'))
        content_length = headers.get('content-length', headers.get('Content-Length', '0'))
        
        # Extract cookie information
        cookie_header = headers.get('cookie', headers.get('Cookie', ''))
        cookie_keys = []
        if cookie_header:
            # Parse cookie names
            for cookie in cookie_header.split(';'):
                if '=' in cookie:
                    key = cookie.split('=')[0].strip()
                    cookie_keys.append(key)
        
        # Convert to your format
        internal_format = {
            'm': method.upper(),
            'p': path,
            'q': query_params if query_params else {},
            'b': body if body else "",
            's': source_ip,
            'h': {
                'ua': user_agent,
                'ct': content_type,
                'cl': content_length,
                'cookieKeys': cookie_keys
            }
        }
        
        return internal_format
    
    def score_request(self, request_data: Dict) -> tuple[float, float]:
        """
        Score a request for anomaly detection
        
        Args:
            request_data: Request in internal format
            
        Returns:
            Tuple of (anomaly_score, processing_time_ms)
        """
        start_time = time.time()
        
        try:
            # Canonicalize the request
            canonical = canonicalize_request(request_data)
            
            # Tokenize
            inputs = self.tokenizer(canonical, return_tensors="pt", truncation=True, max_length=256)
            
            # Score with model
            with torch.no_grad():
                score = self.scorer.pseudo_loglikelihood(inputs['input_ids'].squeeze())
            
            processing_time = (time.time() - start_time) * 1000  # Convert to ms
            return float(score), processing_time
            
        except Exception as e:
            logger.error(f"Error scoring request: {e}")
            return 999.0, (time.time() - start_time) * 1000  # High score for errors
    
    def classify_risk(self, score: float) -> str:
        """Classify risk level based on anomaly score"""
        if score < self.normal_threshold:
            return "NORMAL"
        elif score < self.attack_threshold:
            return "SUSPICIOUS"
        else:
            return "ATTACK"
    
    async def intercept_request(self, session: aiohttp.ClientSession, method: str, 
                              path: str = "/data", query_params: Dict = None, 
                              headers: Dict = None, body: str = None) -> RequestCapture:
        """
        Simulate intercepting a request by making it and analyzing the pattern
        
        Args:
            session: HTTP session
            method: HTTP method
            path: Request path
            query_params: Query parameters
            headers: Request headers
            body: Request body
            
        Returns:
            RequestCapture object with analysis results
        """
        timestamp = datetime.now().isoformat()
        
        # Default values
        query_params = query_params or {}
        headers = headers or {}
        body = body or ""
        source_ip = "127.0.0.1"  # Simulated for testing
        
        # Convert to internal format
        request_data = self.convert_to_internal_format(
            method, path, query_params, headers, body, source_ip
        )
        
        # Canonicalize
        canonical = canonicalize_request(request_data)
        
        # Score the request
        score, processing_time = self.score_request(request_data)
        risk_level = self.classify_risk(score)
        
        # Create capture object
        capture = RequestCapture(
            timestamp=timestamp,
            method=method.upper(),
            path=path,
            query_params=query_params,
            headers=headers,
            body=body,
            source_ip=source_ip,
            user_agent=headers.get('user-agent', 'unknown'),
            content_type=headers.get('content-type', 'text/plain'),
            content_length=str(headers.get('content-length', '0')),
            canonical_form=canonical,
            anomaly_score=score,
            risk_level=risk_level,
            processing_time_ms=processing_time
        )
        
        # Store the capture
        self.captured_requests.append(capture)
        
        # Update statistics
        self.stats['total_requests'] += 1
        if risk_level == "NORMAL":
            self.stats['normal_requests'] += 1
        elif risk_level == "SUSPICIOUS":
            self.stats['suspicious_requests'] += 1
        else:  # ATTACK
            self.stats['attack_requests'] += 1
            self.alerts.append(capture)
        
        # Log based on risk level
        if risk_level == "ATTACK":
            logger.warning(f"🚨 ATTACK DETECTED: {method} {path} → Score: {score:.2f}")
        elif risk_level == "SUSPICIOUS":
            logger.info(f"⚠️  SUSPICIOUS: {method} {path} → Score: {score:.2f}")
        else:
            logger.info(f"✅ NORMAL: {method} {path} → Score: {score:.2f}")
        
        return capture
    
    def print_statistics(self):
        """Print current monitoring statistics"""
        uptime = datetime.now() - self.stats['start_time']
        
        print("\n" + "="*60)
        print("🔍 LIVE ANOMALY DETECTION STATISTICS")
        print("="*60)
        print(f"⏱️  Uptime: {uptime}")
        print(f"📊 Total Requests: {self.stats['total_requests']}")
        print(f"✅ Normal: {self.stats['normal_requests']} ({self.stats['normal_requests']/max(1,self.stats['total_requests'])*100:.1f}%)")
        print(f"⚠️  Suspicious: {self.stats['suspicious_requests']} ({self.stats['suspicious_requests']/max(1,self.stats['total_requests'])*100:.1f}%)")
        print(f"🚨 Attacks: {self.stats['attack_requests']} ({self.stats['attack_requests']/max(1,self.stats['total_requests'])*100:.1f}%)")
        print("="*60)
        
        # Show recent alerts
        if self.alerts:
            print("\n🚨 RECENT ALERTS:")
            for alert in self.alerts[-5:]:  # Last 5 alerts
                print(f"   {alert.timestamp} - {alert.method} {alert.path} (Score: {alert.anomaly_score:.2f})")
    
    def save_results(self, filename: str = None):
        """Save monitoring results to JSON file"""
        if filename is None:
            filename = f"monitoring_results_{int(time.time())}.json"
        
        results = {
            'statistics': self.stats,
            'captured_requests': [asdict(req) for req in self.captured_requests],
            'alerts': [asdict(alert) for alert in self.alerts]
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Results saved to {filename}")

async def main():
    """Main function to run live monitoring"""
    print("🚀 Starting Live Anomaly Detection System")
    print("="*60)
    
    # Initialize detector
    detector = LiveAnomalyDetector()
    
    # Create HTTP session
    async with aiohttp.ClientSession() as session:
        print(f"🎯 Monitoring endpoint: {detector.data_endpoint}")
        print("📝 Simulating various request patterns...")
        print("\nPress Ctrl+C to stop monitoring\n")
        
        try:
            # Simulate normal e-commerce requests
            normal_requests = [
                ("GET", "/data", {"category": "electronics", "page": "1"}, {"user-agent": "Mozilla/5.0"}),
                ("POST", "/data", {}, {"content-type": "application/json"}, '{"productId": "123"}'),
                ("GET", "/data", {"search": "laptop"}, {"user-agent": "Chrome/120.0"}),
                ("GET", "/data", {"sort": "price", "filter": "available"}, {"user-agent": "Firefox/119.0"}),
            ]
            
            # Simulate suspicious/attack requests
            attack_requests = [
                ("GET", "/data", {"id": "../../../etc/passwd"}, {"user-agent": "curl/7.68.0"}),
                ("POST", "/data", {}, {"content-type": "text/html"}, "<script>alert('XSS')</script>"),
                ("GET", "/data", {"search": "'; DROP TABLE users; --"}, {"user-agent": "sqlmap/1.0"}),
                ("GET", "/data", {"cmd": "whoami && ls -la"}, {"user-agent": "exploit-kit"}),
            ]
            
            # Run simulation
            all_requests = normal_requests + attack_requests
            
            for i, (method, path, params, headers, *body) in enumerate(all_requests):
                request_body = body[0] if body else ""
                
                # Process the request
                await detector.intercept_request(
                    session, method, path, params, headers, request_body
                )
                
                # Print progress
                if (i + 1) % 2 == 0:
                    detector.print_statistics()
                
                # Small delay between requests
                await asyncio.sleep(1)
            
            # Final statistics
            print("\n🏁 SIMULATION COMPLETED")
            detector.print_statistics()
            
            # Save results
            detector.save_results()
            
        except KeyboardInterrupt:
            print("\n⏹️  Monitoring stopped by user")
            detector.print_statistics()
            detector.save_results()

if __name__ == "__main__":
    asyncio.run(main())