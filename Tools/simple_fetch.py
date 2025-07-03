#!/usr/bin/env python3
"""
Simple script to fetch and analyze the OneFinity controller web interface
"""
import http.client
import urllib.parse
import re
from bs4 import BeautifulSoup

def fetch_url(url):
    """Fetch the content of a URL using http.client"""
    parsed = urllib.parse.urlparse(url)
    conn = http.client.HTTPConnection(parsed.netloc, timeout=10)
    path = parsed.path if parsed.path else '/'
    if parsed.query:
        path += '?' + parsed.query
    
    print(f"Fetching {url}...")
    conn.request("GET", path, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
    })
    
    response = conn.getresponse()
    if response.status != 200:
        print(f"Error: Received status code {response.status}")
        return None
    
    content = response.read().decode('utf-8')
    return content

def analyze_content(content):
    """Analyze the page content and extract useful information"""
    if not content:
        return
    
    # Save the raw content
    with open("onefinity_page.html", "w", encoding="utf-8") as f:
        f.write(content)
    print("Saved page content to onefinity_page.html")
    
    # Try to parse with BeautifulSoup
    try:
        soup = BeautifulSoup(content, 'html.parser')
        
        # Print basic info
        print("\n=== Page Info ===")
        print(f"Title: {soup.title.string if soup.title else 'No title'}")
        
        # Find all links
        print("\n=== Links (first 10) ===")
        links = soup.find_all('a', href=True)[:10]
        for i, link in enumerate(links, 1):
            print(f"{i}. {link.get_text(strip=True)[:50]} -> {link['href']}")
        
        # Find all forms
        print("\n=== Forms ===")
        forms = soup.find_all('form')
        for i, form in enumerate(forms, 1):
            print(f"\nForm {i}:")
            print(f"  Action: {form.get('action', 'N/A')}")
            print(f"  Method: {form.get('method', 'get').upper()}")
            
            # Find all input fields in the form
            inputs = form.find_all('input')
            for inp in inputs:
                print(f"  Input: name='{inp.get('name', '')}' type='{inp.get('type', 'text')}'")
        
        # Look for common UI elements
        print("\n=== Common UI Elements ===")
        for tag in ['button', 'nav', 'menu', 'header', 'footer', 'main', 'section']:
            elements = soup.find_all(tag)
            if elements:
                print(f"\nFound {len(elements)} <{tag}> elements:")
                for i, el in enumerate(elements[:3], 1):  # Show first 3 of each
                    print(f"  {i}. Class: {el.get('class', [''])[0]}, ID: {el.get('id', '')}")
        
        # Look for JavaScript files
        print("\n=== JavaScript Files ===")
        scripts = soup.find_all('script', src=True)
        for script in scripts[:5]:  # Show first 5 scripts
            print(f"- {script['src']}")
        
        # Look for common framework indicators
        print("\n=== Framework Detection ===")
        frameworks = {
            'React': 'react',
            'Vue': 'vue',
            'Angular': 'angular',
            'jQuery': 'jquery',
            'Backbone': 'backbone',
            'Ember': 'ember',
            'Meteor': 'meteor',
            'Mithril': 'mithril',
            'Node': 'node',
            'Polymer': 'polymer',
            'Aurelia': 'aurelia',
            'Knockout': 'knockout'
        }
        
        content_lower = content.lower()
        detected = []
        for name, keyword in frameworks.items():
            if keyword in content_lower:
                detected.append(name)
        
        if detected:
            print("Detected frameworks/libraries:", ", ".join(detected))
        else:
            print("No major frameworks detected in the page source.")
        
    except Exception as e:
        print(f"Error analyzing content: {str(e)}")

def main():
    url = "http://bbctrl.local"
    print(f"OneFinity Controller Web Interface Inspector\n{'='*50}\n")
    
    content = fetch_url(url)
    if content:
        analyze_content(content)
    
    print("\nInspection complete. Check onefinity_page.html for the full page source.")

if __name__ == "__main__":
    main()
