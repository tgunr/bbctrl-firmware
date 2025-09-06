#!/usr/bin/env python3
"""
Analyze the bbctrl Controller Web Interface
"""

import requests
from bs4 import BeautifulSoup
import re
import json
from urllib.parse import urljoin, urlparse

class WebInterfaceAnalyzer:
    def __init__(self, base_url='http://bbctrl.local'):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        })
    
    def fetch_page(self, path='/'):
        """Fetch a page from the web interface"""
        url = urljoin(self.base_url, path)
        print(f"Fetching {url}...")
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def analyze_main_page(self, html_content):
        """Analyze the main page for API endpoints and WebSocket connections"""
        print("\nAnalyzing main page...")
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all script tags
        scripts = soup.find_all('script', src=True)
        print(f"Found {len(scripts)} script tags")
        
        # Look for inline scripts with API/WebSocket code
        inline_scripts = soup.find_all('script')
        print(f"Found {len(inline_scripts) - len(scripts)} inline scripts")
        
        # Look for API endpoints in script tags
        api_patterns = [
            r'["\'](/api/[^\s"\']+)["\']',
            r'fetch\s*\(\s*["\']([^\s"\']+/api/[^\s"\']+)["\']',
            r'["\'](https?://[^\s"\']+/api/[^\s"\']+)["\']',
            r'"apiEndpoint"\s*:\s*"([^"]+)"',
            r'"wsEndpoint"\s*:\s*"([^"]+)"',
            r'websocket:\s*["\']([^\s"\']+)["\']',
            r'socket:\s*["\']([^\s"\']+)["\']',
            r'ws://[^\s"\']+',
            r'wss://[^\s"\']+',
        ]
        
        print("\nPossible API/WebSocket endpoints found:")
        for script in inline_scripts:
            if script.string:
                for pattern in api_patterns:
                    matches = re.findall(pattern, script.string, re.IGNORECASE)
                    for match in matches:
                        if isinstance(match, tuple):
                            match = match[0]  # Get the first group if there are groups
                        print(f"  - {match}")
        
        # Look for form actions
        print("\nForm actions:")
        for form in soup.find_all('form', action=True):
            print(f"  - {form['action']}")
        
        # Look for iframes
        print("\nIframe sources:")
        for iframe in soup.find_all('iframe', src=True):
            print(f"  - {iframe['src']}")
        
        # Look for links to other pages
        print("\nLinks to other pages:")
        for link in soup.find_all('a', href=True):
            href = link['href']
            if not href.startswith(('http://', 'https://', '//')):
                href = urljoin(self.base_url, href)
            print(f"  - {href}")
    
    def run(self):
        """Run the analysis"""
        # Fetch the main page
        main_page = self.fetch_page()
        if not main_page:
            print("Failed to fetch main page")
            return
        
        # Save the main page for inspection
        with open('main_page.html', 'w', encoding='utf-8') as f:
            f.write(main_page)
        print("Saved main page to main_page.html")
        
        # Analyze the main page
        self.analyze_main_page(main_page)
        
        # Try to find the WebSocket URL
        print("\nAttempting to find WebSocket URL...")
        ws_url = self.find_websocket_url(main_page)
        if ws_url:
            print(f"Found WebSocket URL: {ws_url}")
        else:
            print("Could not determine WebSocket URL")
    
    def find_websocket_url(self, html_content):
        """Try to find WebSocket URL in HTML content"""
        # Common WebSocket URL patterns
        patterns = [
            r'new\s+WebSocket\s*\(\s*["\'](ws[s]?://[^\s"\']+)["\']',
            r'new\s+WebSocket\s*\(\s*[`](ws[s]?://[^\s`]+)[`]',
            r'"wsEndpoint"\s*:\s*"(ws[s]?://[^\s"\']+)"',
            r'"websocket"\s*:\s*"(ws[s]?://[^\s"\']+)"',
            r'socket\s*=\s*io\(\)\.connect\(\s*["\']([^\s"\']+)["\']',
            r'socket\s*=\s*io\(\)\.connect\(\s*[`]([^`]+)[`]',
            r'io\.connect\(\s*["\']([^\s"\']+)["\']',
            r'io\.connect\(\s*[`]([^`]+)[`]',
            r'socket\s*=\s*new\s+WebSocket\(\s*["\'](ws[s]?://[^\s"\']+)["\']',
            r'socket\s*=\s*new\s+WebSocket\(\s*[`](ws[s]?://[^`]+)[`]',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]  # Get the first group if there are groups
                if match.startswith(('ws://', 'wss://')):
                    return match
        
        return None

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze bbctrl Controller Web Interface')
    parser.add_argument('--host', default='bbctrl.local', help='Controller hostname or IP')
    parser.add_argument('--port', type=int, default=80, help='Controller port')
    
    args = parser.parse_args()
    
    base_url = f"http://{args.host}:{args.port}"
    print(f"Analyzing web interface at {base_url}")
    
    analyzer = WebInterfaceAnalyzer(base_url)
    analyzer.run()

if __name__ == "__main__":
    main()
