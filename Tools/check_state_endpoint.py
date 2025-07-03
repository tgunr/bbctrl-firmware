#!/usr/bin/env python3
"""
Check the /api/state endpoint of the OneFinity controller
"""

import requests
import json

def get_state(host='bbctrl.local', port=80):
    """Get the state from the OneFinity controller"""
    url = f"http://{host}:{port}/api/state"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            try:
                return response.json()
            except json.JSONDecodeError:
                return {'raw_response': response.text}
        return {'error': f"HTTP {response.status_code}", 'details': response.text}
    except requests.RequestException as e:
        return {'error': 'connection_failed', 'details': str(e)}

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Check OneFinity Controller State')
    parser.add_argument('--host', default='bbctrl.local', help='Controller hostname or IP')
    parser.add_argument('--port', type=int, default=80, help='Controller port')
    parser.add_argument('--output', help='Output file to save the state')
    
    args = parser.parse_args()
    
    print(f"Fetching state from {args.host}:{args.port}/api/state...")
    state = get_state(args.host, args.port)
    
    if 'error' in state:
        print(f"Error: {state['error']}")
        if 'details' in state:
            print(f"Details: {state['details']}")
    else:
        print("State retrieved successfully!")
        print(json.dumps(state, indent=2))
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(state, f, indent=2)
            print(f"State saved to {args.output}")
