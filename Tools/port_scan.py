#!/usr/bin/env python3
"""
Port Scanner for bbctrl Controller

This script scans for open WebSocket ports on the bbctrl controller
and attempts to identify the correct WebSocket endpoint.
"""
import asyncio
import socket
import ssl
import json
import websockets
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Common WebSocket ports to check
COMMON_PORTS = [
    80,           # Standard HTTP/WebSocket
    443,          # Standard HTTPS/WSS
    8080,         # Common alternative HTTP
    8443,         # Common alternative HTTPS
    8000,         # Common development port
    81,           # Alternative HTTP
    3000,         # Common development port
    5000,         # Common development port
    9000,         # Common development port
    9001,         # Common development port
    7681,         # Some IoT devices use this
    7682,         # Some IoT devices use this
    7683,         # Some IoT devices use this
    7684,         # Some IoT devices use this
    7685,         # Some IoT devices use this
    9002,         # Alternative WebSocket port
    9003,         # Alternative WebSocket port
    9004,         # Alternative WebSocket port
    9005,         # Alternative WebSocket port
]

# Common WebSocket paths to check
WS_PATHS = [
    '/ws',
    '/socket.io',
    '/socket.io/socket.io.js',
    '/api/ws',
    '/websocket',
    '/wss',
    '/wss/ws',
    '/ws/control',
    '/api/websocket',
    '/bbctrl/ws',
    '/bbctrl/ws',
    '/bbctrl/api/ws',
]

async def check_websocket(host, port, path, use_ssl=False, timeout=2):
    """Check if a WebSocket endpoint is available"""
    url = f"{'wss' if use_ssl else 'ws'}://{host}:{port}{path}"
    ssl_context = None
    
    if use_ssl:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
    
    try:
        # Use asyncio.wait_for for Python 3.9 compatibility
        async def connect():
            return await websockets.connect(
                url,
                ssl=ssl_context,
                open_timeout=timeout,
                close_timeout=1
            )
            
        ws = await asyncio.wait_for(connect(), timeout=timeout)
        
        # Try to send a simple ping or handshake
        try:
            await ws.ping()
            await ws.close()
            return True, f"WebSocket available at {url}"
        except:
            try:
                await ws.close()
            except:
                pass
            return True, f"WebSocket connection established but ping failed at {url}"
    except asyncio.TimeoutError:
        return False, f"Timeout connecting to {url}"
    except Exception as e:
        return False, f"Error connecting to {url}: {str(e)}"

def check_tcp_port(host, port, timeout=1):
    """Check if a TCP port is open"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            return result == 0
    except:
        return False

async def scan_ports(host, ports=None, paths=None, use_ssl=False):
    """Scan for open WebSocket ports and paths"""
    if ports is None:
        ports = COMMON_PORTS
    if paths is None:
        paths = WS_PATHS
    
    print(f"Scanning {host} for WebSocket endpoints...\n")
    
    # First, check which ports are open
    print("Checking for open TCP ports...")
    open_ports = []
    
    with ThreadPoolExecutor() as executor:
        loop = asyncio.get_event_loop()
        tasks = []
        
        for port in ports:
            tasks.append(loop.run_in_executor(executor, check_tcp_port, host, port))
        
        results = await asyncio.gather(*tasks)
        
        for port, is_open in zip(ports, results):
            if is_open:
                print(f"  Port {port}: OPEN")
                open_ports.append(port)
            else:
                print(f"  Port {port}: CLOSED")
    
    if not open_ports:
        print("\nNo open ports found. The device may be offline or not accepting connections.")
        return
    
    print("\nChecking WebSocket endpoints on open ports...")
    
    # Check WebSocket endpoints on open ports
    for port in open_ports:
        print(f"\nChecking port {port}...")
        
        for path in paths:
            print(f"  Trying {path}...", end="\r")
            success, message = await check_websocket(host, port, path, use_ssl)
            print(f"  {message}")
            if success:
                print(f"\n✅ Found WebSocket at: {'wss' if use_ssl else 'ws'}://{host}:{port}{path}")
                return
    
    print("\nNo WebSocket endpoints found on open ports.")
    print("You may need to:")
    print("1. Check if the bbctrl controller is powered on and connected to the network")
    print("2. Verify the hostname or IP address")
    print("3. Check if you need to be on the same network as the controller")
    print("4. Try connecting to the web interface in a browser first")

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Scan for bbctrl Controller WebSocket endpoints')
    parser.add_argument('--host', default='bbctrl.local', help='Controller hostname or IP')
    parser.add_argument('--ports', help='Comma-separated list of ports to scan')
    parser.add_argument('--ssl', action='store_true', help='Use secure WebSocket (wss)')
    parser.add_argument('--timeout', type=float, default=2, help='Connection timeout in seconds')
    
    args = parser.parse_args()
    
    ports = COMMON_PORTS
    if args.ports:
        try:
            ports = [int(p.strip()) for p in args.ports.split(',')]
        except ValueError:
            print("Invalid port list. Using default ports.")
    
    print(f"Starting WebSocket scan for {args.host}...\n")
    await scan_ports(args.host, ports, WS_PATHS, args.ssl)

if __name__ == "__main__":
    asyncio.run(main())
