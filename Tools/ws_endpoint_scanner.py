#!/usr/bin/env python3
"""
WebSocket Endpoint Scanner for bbctrl Controller

This script scans for WebSocket endpoints on the bbctrl controller.
"""

import asyncio
import websockets
import json
import sys
from urllib.parse import urljoin

# Common WebSocket endpoints to try
COMMON_WS_ENDPOINTS = [
    '/ws',
    '/websocket',
    '/ws/',
    '/websocket/',
    '/api/ws',
    '/api/websocket',
    '/socket.io',
    '/socket.io/',
    '/ws/events',
    '/ws/events/',
    '/api/ws/events',
    '/api/ws/events/',
    '/ws/control',
    '/ws/control/',
    '/api/ws/control',
    '/api/ws/control/',
    '/ws/gcode',
    '/ws/gcode/',
    '/api/ws/gcode',
    '/api/ws/gcode/',
    '/ws/status',
    '/ws/status/',
    '/api/ws/status',
    '/api/ws/status/',
]

async def test_ws_endpoint(host, port, path, ssl=False, timeout=5):
    """Test if a WebSocket endpoint is available"""
    scheme = 'wss' if ssl else 'ws'
    url = f"{scheme}://{host}:{port}{path}"
    
    try:
        # Try to connect with a timeout
        async with asyncio.timeout(timeout):
            async with websockets.connect(url, ping_interval=None) as ws:
                # If we get here, the connection was successful
                print(f"✅ Found WebSocket endpoint: {url}")
                
                # Try to send a simple message to see if it responds
                try:
                    await ws.send(json.dumps({"jsonrpc": "2.0", "method": "status"}))
                    response = await asyncio.wait_for(ws.recv(), timeout=2)
                    print(f"  Response: {response[:200]}..." if len(response) > 200 else f"  Response: {response}")
                except Exception as e:
                    print(f"  Could not get response: {e}")
                
                return True
    except asyncio.TimeoutError:
        print(f"⌛ Timeout connecting to {url}")
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ WebSocket error on {url}: {e.status_code} {e.response.reason}")
    except Exception as e:
        print(f"❌ Error connecting to {url}: {e}")
    
    return False

async def scan_ws_endpoints(host, port=80, ssl=False, timeout=5):
    """Scan for WebSocket endpoints"""
    print(f"Scanning WebSocket endpoints on {host}:{port}...\n")
    
    tasks = []
    for endpoint in COMMON_WS_ENDPOINTS:
        tasks.append(test_ws_endpoint(host, port, endpoint, ssl, timeout))
    
    # Run all tests concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Print summary
    found = sum(1 for r in results if r is True)
    print(f"\nScan complete. Found {found} WebSocket endpoints.")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='WebSocket Endpoint Scanner for bbctrl Controller')
    parser.add_argument('--host', default='bbctrl.local', help='Controller hostname or IP')
    parser.add_argument('--port', type=int, default=80, help='Controller port')
    parser.add_argument('--ssl', action='store_true', help='Use HTTPS/WSS')
    parser.add_argument('--timeout', type=int, default=5, help='Connection timeout in seconds')
    
    args = parser.parse_args()
    
    # Run the scanner
    asyncio.run(scan_ws_endpoints(args.host, args.port, args.ssl, args.timeout))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nScan interrupted by user")
        sys.exit(0)
