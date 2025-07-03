#!/usr/bin/env python3
"""
Diagnostic script to identify bbctrl connection issues
"""

import socket
import requests
import subprocess
import sys
import time
from urllib.parse import urlparse

def check_dns_resolution(hostname):
    """Check if hostname resolves to an IP address."""
    print(f"🔍 Checking DNS resolution for {hostname}...")
    try:
        ip = socket.gethostbyname(hostname)
        print(f"✅ {hostname} resolves to {ip}")
        return ip
    except socket.gaierror as e:
        print(f"❌ DNS resolution failed: {e}")
        return None

def check_port_connectivity(host, port):
    """Check if a specific port is open on the host."""
    print(f"🔍 Checking port {port} connectivity to {host}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✅ Port {port} is open on {host}")
            return True
        else:
            print(f"❌ Port {port} is closed or filtered on {host}")
            return False
    except Exception as e:
        print(f"❌ Port check failed: {e}")
        return False

def check_http_response(url):
    """Check if HTTP service responds."""
    print(f"🔍 Checking HTTP response from {url}...")
    try:
        response = requests.get(url, timeout=10)
        print(f"✅ HTTP {response.status_code}: {response.reason}")
        print(f"   Content-Type: {response.headers.get('content-type', 'Unknown')}")
        print(f"   Content-Length: {len(response.content)} bytes")
        
        # Check if it's an error page
        if "error" in response.text.lower() or "not found" in response.text.lower():
            print(f"⚠️  Response contains error content")
            print(f"   First 200 chars: {response.text[:200]}...")
            
        return response
    except requests.exceptions.ConnectTimeout:
        print(f"❌ Connection timeout - service may be down")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {e}")
        return None
    except Exception as e:
        print(f"❌ HTTP request failed: {e}")
        return None

def ping_host(hostname):
    """Ping the host to check basic connectivity."""
    print(f"🔍 Pinging {hostname}...")
    try:
        # Use ping command (works on macOS/Linux)
        result = subprocess.run(['ping', '-c', '3', hostname], 
                              capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            print(f"✅ Ping successful")
            # Extract average time from ping output
            lines = result.stdout.split('\n')
            for line in lines:
                if 'avg' in line or 'average' in line:
                    print(f"   {line.strip()}")
            return True
        else:
            print(f"❌ Ping failed")
            print(f"   Error: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print(f"❌ Ping timeout")
        return False
    except Exception as e:
        print(f"❌ Ping error: {e}")
        return False

def scan_common_ports(host):
    """Scan common ports that bbctrl might use."""
    print(f"🔍 Scanning common ports on {host}...")
    common_ports = [80, 443, 8080, 8443, 3000, 5000, 8000]
    open_ports = []
    
    for port in common_ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                print(f"✅ Port {port} is open")
                open_ports.append(port)
            else:
                print(f"❌ Port {port} is closed")
        except Exception as e:
            print(f"❌ Port {port} check failed: {e}")
    
    return open_ports

def check_local_network():
    """Check local network configuration."""
    print(f"🔍 Checking local network configuration...")
    try:
        # Get default gateway
        result = subprocess.run(['route', 'get', 'default'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'gateway:' in line:
                    gateway = line.split(':')[1].strip()
                    print(f"   Default gateway: {gateway}")
        
        # Check if we're on the same network as typical bbctrl devices
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"   Local hostname: {hostname}")
        print(f"   Local IP: {local_ip}")
        
    except Exception as e:
        print(f"❌ Network check failed: {e}")

def main():
    print("🔧 Buildbotics Controller Connection Diagnostics")
    print("=" * 50)
    
    hostname = "bbctrl.local"
    url = f"http://{hostname}"
    
    # Step 1: Check local network
    check_local_network()
    print()
    
    # Step 2: Check DNS resolution
    ip = check_dns_resolution(hostname)
    print()
    
    # Step 3: Ping test
    ping_success = ping_host(hostname)
    print()
    
    # Step 4: Port scanning
    if ip:
        open_ports = scan_common_ports(ip)
        print()
        
        # Step 5: HTTP connectivity test
        if 80 in open_ports:
            response = check_http_response(url)
            print()
            
            if response:
                # Save response for analysis
                with open('bbctrl_response.html', 'w') as f:
                    f.write(response.text)
                print(f"📄 Response saved to bbctrl_response.html for analysis")
        else:
            print("❌ Port 80 not open - HTTP service may not be running")
    
    print("\n🔧 Diagnosis Summary:")
    print("=" * 30)
    
    if not ip:
        print("❌ ISSUE: DNS resolution failed")
        print("   - Check if bbctrl.local is the correct hostname")
        print("   - Verify the controller is on the same network")
        print("   - Try using the IP address directly")
    elif not ping_success:
        print("❌ ISSUE: Network connectivity failed")
        print("   - Controller may be offline")
        print("   - Check network cables/WiFi connection")
        print("   - Verify firewall settings")
    elif not open_ports:
        print("❌ ISSUE: No services responding")
        print("   - Controller web service may be down")
        print("   - Try restarting the controller")
    else:
        print("✅ Basic connectivity looks good")
        print("   - The issue may be browser-specific or authentication-related")

if __name__ == "__main__":
    main()