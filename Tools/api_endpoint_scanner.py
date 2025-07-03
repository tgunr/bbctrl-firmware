#!/usr/bin/env python3
"""
OneFinity API Endpoint Scanner

This script scans for available API endpoints on the OneFinity controller.
"""

import requests
import json
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

class EndpointScanner:
    def __init__(self, base_url='http://bbctrl.local'):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        self.found_endpoints = set()
    
    def check_endpoint(self, endpoint):
        """Check if an endpoint exists and is accessible"""
        url = urljoin(self.base_url, endpoint)
        
        # Try GET first
        try:
            response = self.session.get(url, timeout=5, allow_redirects=False)
            if response.status_code < 400:  # 2xx or 3xx is good
                return (endpoint, 'GET', response.status_code, len(response.content))
            
            # Try POST if GET fails
            response = self.session.post(url, json={}, timeout=5, allow_redirects=False)
            if response.status_code < 400:
                return (endpoint, 'POST', response.status_code, len(response.content))
                
        except requests.RequestException:
            pass
            
        return None
    
    def scan_endpoints(self, endpoints):
        """Scan multiple endpoints in parallel"""
        results = []
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all checks
            future_to_endpoint = {executor.submit(self.check_endpoint, ep): ep for ep in endpoints}
            
            # Process results as they complete
            for future in future_to_endpoint:
                result = future.result()
                if result:
                    results.append(result)
                    endpoint, method, status, size = result
                    print(f"[+] {status} {method} {endpoint} ({size} bytes)")
        
        return results

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Scan OneFinity Controller API Endpoints')
    parser.add_argument('--host', default='bbctrl.local', help='Controller hostname or IP')
    parser.add_argument('--port', type=int, default=80, help='Controller port')
    parser.add_argument('--wordlist', help='Path to wordlist file')
    args = parser.parse_args()
    
    base_url = f"http://{args.host}:{args.port}"
    scanner = EndpointScanner(base_url)
    
    # Common API endpoints to check
    common_endpoints = [
        # Common REST API endpoints
        '/api',
        '/api/status',
        '/api/state',
        '/api/config',
        '/api/gcode',
        '/api/machine',
        '/api/controller',
        '/api/network',
        '/api/files',
        '/api/upload',
        '/api/job',
        '/api/planner',
        '/api/position',
        '/api/settings',
        '/api/sys',
        '/api/tools',
        '/api/units',
        '/api/var',
        '/api/watch',
        '/api/wifi',
        
        # Alternative API endpoints
        '/rest/api',
        '/v1/api',
        '/v1/status',
        '/v1/gcode',
        '/v1/machine',
        
        # WebSocket endpoints
        '/ws',
        '/websocket',
        '/socket.io',
        '/api/ws',
        '/api/websocket',
        
        # Direct G-code endpoints
        '/gcode',
        '/send',
        '/command',
        '/api/command',
        
        # Status endpoints
        '/status',
        '/state',
        '/info',
        
        # File operations
        '/files',
        '/api/files/list',
        '/api/files/upload',
        
        # Authentication
        '/login',
        '/api/login',
        '/auth',
        '/api/auth',
        
        # OneFinity specific
        '/onefinity/api',
        '/onefinity/status',
        '/bbctrl/api',
        '/bbctrl/status',
    ]
    
    # Add wordlist endpoints if provided
    if args.wordlist:
        try:
            with open(args.wordlist, 'r') as f:
                wordlist_endpoints = [line.strip() for line in f if line.strip()]
                common_endpoints.extend(wordlist_endpoints)
        except Exception as e:
            print(f"Error reading wordlist: {e}")
    
    # Remove duplicates
    endpoints_to_scan = list(dict.fromkeys(common_endpoints))
    
    print(f"Scanning {len(endpoints_to_scan)} endpoints on {base_url}")
    print("=" * 60)
    
    results = scanner.scan_endpoints(endpoints_to_scan)
    
    print("\nScan complete. Found", len(results), "accessible endpoints.")
    
    # Save results to a file
    with open('endpoint_scan_results.txt', 'w') as f:
        for endpoint, method, status, size in results:
            f.write(f"{status} {method} {endpoint} ({size} bytes)\n")
    
    print("Results saved to endpoint_scan_results.txt")

if __name__ == "__main__":
    main()
