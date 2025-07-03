#!/usr/bin/env python3
"""
OneFinity Controller REST API Explorer

This script helps explore the available REST API endpoints on the OneFinity controller.
"""
import requests
import json
from urllib.parse import urljoin
from datetime import datetime
import os
import sys

class OneFinityAPI:
    def __init__(self, base_url='http://bbctrl.local'):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        self.log_file = "api_explorer.log"
        
    def log(self, message):
        """Log messages to console and file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_message + '\n')
    
    def make_request(self, method, endpoint, data=None, params=None):
        """Make an HTTP request to the API"""
        url = urljoin(f"{self.base_url}/", endpoint.lstrip('/'))
        self.log(f"{method.upper()} {url}")
        
        try:
            if method.lower() == 'get':
                response = self.session.get(url, params=params, timeout=10)
            elif method.lower() == 'post':
                response = self.session.post(url, json=data, params=params, timeout=10)
            elif method.lower() == 'put':
                response = self.session.put(url, json=data, params=params, timeout=10)
            elif method.lower() == 'delete':
                response = self.session.delete(url, params=params, timeout=10)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            self.log(f"Status: {response.status_code}")
            
            # Try to parse JSON response
            try:
                response_data = response.json()
                self.log("Response JSON:")
                self.log(json.dumps(response_data, indent=2))
                return response_data
            except ValueError:
                self.log(f"Response (not JSON): {response.text[:500]}")
                return response.text
                
        except requests.exceptions.RequestException as e:
            self.log(f"Request failed: {str(e)}")
            return None
    
    def explore_endpoints(self):
        """Explore common REST API endpoints"""
        endpoints = [
            ('GET', 'api/version'),
            ('GET', 'api/status'),
            ('GET', 'api/config'),
            ('GET', 'api/state'),
            ('GET', 'api/gcode'),
            ('GET', 'api/machine'),
            ('GET', 'api/controller'),
            ('GET', 'api/network'),
            ('GET', 'api/files'),
            ('GET', 'api/upload'),
            ('GET', 'api/job'),
            ('GET', 'api/planner'),
            ('GET', 'api/position'),
            ('GET', 'api/settings'),
            ('GET', 'api/sys'),
            ('GET', 'api/tools'),
            ('GET', 'api/units'),
            ('GET', 'api/var'),
            ('GET', 'api/watch'),
            ('GET', 'api/wifi'),
        ]
        
        self.log("Starting API exploration...")
        results = {}
        
        for method, endpoint in endpoints:
            self.log(f"\n{'='*80}")
            self.log(f"Testing {method} {endpoint}")
            result = self.make_request(method, endpoint)
            results[endpoint] = result
            
        self.log("\nAPI exploration complete.")
        return results
    
    def send_gcode(self, gcode):
        """Send G-code command to the controller"""
        self.log(f"Sending G-code: {gcode}")
        return self.make_request('POST', 'api/gcode', data={'gcode': gcode})
    
    def get_status(self):
        """Get controller status"""
        return self.make_request('GET', 'api/status')
    
    def get_files(self, path=''):
        """List files in a directory"""
        return self.make_request('GET', 'api/files', params={'path': path})
    
    def upload_file(self, file_path, target_path=''):
        """Upload a file to the controller"""
        if not os.path.isfile(file_path):
            self.log(f"Error: File not found: {file_path}")
            return None
            
        url = urljoin(f"{self.base_url}/", 'api/upload')
        if target_path:
            url = f"{url}?path={target_path}"
            
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f)}
                response = self.session.post(url, files=files, timeout=30)
                
                self.log(f"Status: {response.status_code}")
                try:
                    return response.json()
                except ValueError:
                    return response.text
                    
        except Exception as e:
            self.log(f"Upload failed: {str(e)}")
            return None

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='OneFinity Controller REST API Explorer')
    parser.add_argument('--host', default='http://bbctrl.local', help='Controller base URL')
    parser.add_argument('--explore', action='store_true', help='Explore all API endpoints')
    parser.add_argument('--gcode', help='Send a G-code command')
    parser.add_argument('--status', action='store_true', help='Get controller status')
    parser.add_argument('--files', nargs='?', const='', help='List files (optional: path)')
    parser.add_argument('--upload', help='Upload a file (requires --target-path)')
    parser.add_argument('--target-path', default='', help='Target path for file uploads')
    
    args = parser.parse_args()
    
    api = OneFinityAPI(args.host)
    
    if args.explore:
        api.explore_endpoints()
    elif args.gcode:
        api.send_gcode(args.gcode)
    elif args.status:
        result = api.get_status()
        print(json.dumps(result, indent=2))
    elif args.files is not None:  # Handle empty string case
        result = api.get_files(args.files)
        print(json.dumps(result, indent=2))
    elif args.upload:
        result = api.upload_file(args.upload, args.target_path)
        print(json.dumps(result, indent=2) if isinstance(result, (dict, list)) else result)
    else:
        print("No action specified. Use --help for usage information.")
        print("\nExample usage:")
        print("  python rest_api_explorer.py --status")
        print("  python rest_api_explorer.py --gcode 'G28'")
        print("  python rest_api_explorer.py --files")
        print("  python rest_api_explorer.py --upload file.gcode --target-path /gcodes")

if __name__ == "__main__":
    main()
