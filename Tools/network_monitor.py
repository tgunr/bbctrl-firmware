#!/usr/bin/env python3
"""
Network Monitor for bbctrl Controller

This script helps monitor and analyze network traffic between the browser and the
bbctrl controller by acting as a proxy. It can be used to understand the API
calls made by the web interface.
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import urllib.parse
import json
import socket
import threading
import time
from datetime import datetime
import os
import ssl

# Disable SSL verification for self-signed certificates
ssl._create_default_https_context = ssl._create_unverified_context

class RequestHandler(BaseHTTPRequestHandler):    
    def do_GET(self):
        """Handle GET requests"""
        self.log_request()
        
        # Forward the request to the target
        target_url = f"http://bbctrl.local{self.path}"
        
        try:
            # Set up headers for the forwarded request
            headers = {}
            for header, value in self.headers.items():
                if header.lower() not in ['host', 'connection', 'accept-encoding']:
                    headers[header] = value
            
            # Make the request to the target
            req = urllib.request.Request(target_url, headers=headers, method='GET')
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read()
                
                # Log the request and response
                self.log_response(target_url, 'GET', headers, None, 
                               response.status, response.getheaders(), content)
                
                # Send the response back to the client
                self.send_response(response.status)
                for header, value in response.getheaders():
                    self.send_header(header, value)
                self.end_headers()
                self.wfile.write(content)
                
        except Exception as e:
            self.send_error(500, str(e))
            self.log_error(f"Error forwarding GET request: {str(e)}")
    
    def do_POST(self):
        """Handle POST requests"""
        self.log_request()
        
        # Read the request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b''
        
        # Parse the request body if it's JSON
        try:
            body_json = json.loads(body.decode('utf-8')) if body else None
        except:
            body_json = None
        
        # Forward the request to the target
        target_url = f"http://bbctrl.local{self.path}"
        
        try:
            # Set up headers for the forwarded request
            headers = {}
            for header, value in self.headers.items():
                if header.lower() not in ['host', 'content-length', 'connection', 'accept-encoding']:
                    headers[header] = value
            
            # Make the request to the target
            req = urllib.request.Request(target_url, data=body, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read()
                
                # Log the request and response
                self.log_response(target_url, 'POST', headers, body_json, 
                               response.status, response.getheaders(), content)
                
                # Send the response back to the client
                self.send_response(response.status)
                for header, value in response.getheaders():
                    self.send_header(header, value)
                self.end_headers()
                self.wfile.write(content)
                
        except Exception as e:
            self.send_error(500, str(e))
            self.log_error(f"Error forwarding POST request: {str(e)}")
    
    def log_request(self, code='-', size='-'):
        """Log the request to the console"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {self.command} {self.path}")
    
    def log_response(self, url, method, request_headers, request_body, status_code, response_headers, response_body):
        """Log the full request and response to a file"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_dir = "network_logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # Create a log entry
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'method': method,
            'url': url,
            'request_headers': dict(request_headers),
            'request_body': request_body,
            'status_code': status_code,
            'response_headers': dict(response_headers),
            'response_body': response_body.decode('utf-8', errors='replace') if response_body else None
        }
        
        # Save the log entry to a file
        log_file = os.path.join(log_dir, f"request_{timestamp}.json")
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_entry, f, indent=2, ensure_ascii=False)
        
        print(f"  -> {status_code} (logged to {log_file})")
    
    def log_error(self, message):
        """Log an error message"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] ERROR: {message}")

def start_proxy(port=8080):
    """Start the proxy server"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, RequestHandler)
    
    print(f"Starting proxy server on port {port}...")
    print("Configure your browser to use this proxy (e.g., localhost:8080)")
    print("Press Ctrl+C to stop the server\n")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down the proxy server...")
    finally:
        httpd.server_close()
        print("Proxy server stopped")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Network Monitor for bbctrl Controller')
    parser.add_argument('--port', type=int, default=8080, help='Port to run the proxy server on')
    args = parser.parse_args()
    
    start_proxy(args.port)
