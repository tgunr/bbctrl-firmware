#!/usr/bin/env python3
"""
Extract WebSocket and API endpoints from bbctrl controller's main page.
"""

import re
import json
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs

def extract_js_endpoints(html_content, base_url='http://bbctrl.local'):
    """Extract WebSocket and API endpoints from JavaScript code."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find all script tags
    scripts = soup.find_all('script')
    
    # Common WebSocket and API patterns to look for
    patterns = [
        # WebSocket patterns
        (r'new\s+WebSocket\(([^)]+)\)', 'websocket'),
        (r'ws[s]?://[^\s"\'()]+', 'websocket_url'),
        (r'socket\.on\(([^)]+)\)', 'socket_event'),
        (r'socket\.emit\(([^)]+)\)', 'socket_emit'),
        
        # API endpoint patterns
        (r'fetch\(([^)]+)\)', 'fetch'),
        (r'axios\.(get|post|put|delete)\(([^)]+)\)', 'axios'),
        (r'\$\.(get|post|ajax)\(([^)]+)\)', 'jquery_ajax'),
        (r'url:\s*(["\'])(.*?)\1', 'url_param'),
        (r'["\']/api/[^\s"\']+["\']', 'api_endpoint'),
        (r'["\']/ws[^\s"\']*["\']', 'websocket_endpoint'),
    ]
    
    endpoints = {
        'websocket': set(),
        'api': set(),
        'events': set(),
        'other': set()
    }
    
    for script in scripts:
        if not script.string:
            continue
            
        js_code = script.string
        
        # Look for WebSocket and API endpoints
        for pattern, pattern_type in patterns:
            matches = re.finditer(pattern, js_code, re.DOTALL)
            
            for match in matches:
                value = match.group(0)
                
                # Clean up the matched value
                value = value.strip('"\'')
                
                # Categorize the endpoint
                if pattern_type == 'websocket' or pattern_type == 'websocket_url' or pattern_type == 'websocket_endpoint':
                    endpoints['websocket'].add(value)
                elif pattern_type == 'api_endpoint' or 'api/' in value.lower():
                    # Make relative URLs absolute
                    if value.startswith('/'):
                        value = urljoin(base_url, value)
                    endpoints['api'].add(value)
                elif pattern_type == 'socket_event' or pattern_type == 'socket_emit':
                    endpoints['events'].add(value)
                else:
                    endpoints['other'].add(value)
    
    # Clean up the results
    for key in endpoints:
        endpoints[key] = sorted(list(endpoints[key]))
    
    return endpoints

def extract_links(html_content, base_url='http://bbctrl.local'):
    """Extract all links from the HTML."""
    soup = BeautifulSoup(html_content, 'html.parser')
    links = set()
    
    # Find all a, link, script, img, iframe, form tags
    for tag in soup.find_all(['a', 'link', 'script', 'img', 'iframe', 'form']):
        url = None
        
        if tag.name == 'a' and tag.get('href'):
            url = tag['href']
        elif tag.name == 'link' and tag.get('href'):
            url = tag['href']
        elif tag.name == 'script' and tag.get('src'):
            url = tag['src']
        elif tag.name == 'img' and tag.get('src'):
            url = tag['src']
        elif tag.name == 'iframe' and tag.get('src'):
            url = tag['src']
        elif tag.name == 'form' and tag.get('action'):
            url = tag['action']
        
        if url and not url.startswith(('javascript:', 'mailto:', 'tel:', '#')):
            # Make relative URLs absolute
            if url.startswith('/'):
                url = urljoin(base_url, url)
            links.add(url)
    
    return sorted(list(links))

def main():
    # Read the saved main page
    main_page_path = 'main_page.html'
    if not Path(main_page_path).exists():
        print(f"Error: {main_page_path} not found. Please run analyze_web_interface.py first.")
        return
    
    with open(main_page_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Extract endpoints and links
    print("Extracting endpoints from JavaScript...")
    endpoints = extract_js_endpoints(html_content)
    
    print("\nExtracting links from HTML...")
    links = extract_links(html_content)
    
    # Print results
    print("\n=== WebSocket Endpoints ===")
    for endpoint in endpoints['websocket']:
        print(f"- {endpoint}")
    
    print("\n=== API Endpoints ===")
    for endpoint in endpoints['api']:
        print(f"- {endpoint}")
    
    print("\n=== Socket Events ===")
    for event in endpoints['events']:
        print(f"- {event}")
    
    print("\n=== Other Endpoints ===")
    for endpoint in endpoints['other']:
        print(f"- {endpoint}")
    
    print("\n=== Links ===")
    for link in links:
        print(f"- {link}")
    
    # Save results to a file
    results = {
        'websocket_endpoints': endpoints['websocket'],
        'api_endpoints': endpoints['api'],
        'socket_events': endpoints['events'],
        'other_endpoints': endpoints['other'],
        'links': links
    }
    
    with open('endpoints.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print("\nResults saved to endpoints.json")

if __name__ == '__main__':
    main()
