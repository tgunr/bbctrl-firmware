#!/usr/bin/env python3
"""
Simple G-code Sender for OneFinity Controller

This script sends G-code commands directly to the OneFinity controller
using the most common API endpoint.
"""

import requests
import json
import time
import sys

def send_gcode(host='bbctrl.local', port=80, gcode=None, username=None, password=None):
    """Send a G-code command to the OneFinity controller"""
    url = f"http://{host}:{port}/api/gcode"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/plain, */*'
    }
    
    # Prepare the request data
    data = {'gcode': gcode}
    
    try:
        # First try without authentication
        response = requests.post(url, json=data, headers=headers, timeout=10)
        
        # If unauthorized (401), try with basic auth if credentials are provided
        if response.status_code == 401 and username and password:
            auth = (username, password)
            response = requests.post(url, json=data, headers=headers, auth=auth, timeout=10)
        
        # Process the response
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"Success: {json.dumps(result, indent=2)}")
                return True
            except json.JSONDecodeError:
                print(f"Success: {response.text}")
                return True
        else:
            print(f"Error {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {str(e)}")
        return False

def get_status(host='bbctrl.local', port=80, username=None, password=None):
    """Get the current status of the controller"""
    url = f"http://{host}:{port}/api/status"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*'
    }
    
    try:
        # First try without authentication
        response = requests.get(url, headers=headers, timeout=5)
        
        # If unauthorized (401), try with basic auth if credentials are provided
        if response.status_code == 401 and username and password:
            auth = (username, password)
            response = requests.get(url, headers=headers, auth=auth, timeout=5)
        
        if response.status_code == 200:
            try:
                return response.json()
            except json.JSONDecodeError:
                return {'status': 'online', 'raw_response': response.text}
        else:
            return {'error': f"HTTP {response.status_code}", 'details': response.text}
            
    except requests.exceptions.RequestException as e:
        return {'error': 'connection_failed', 'details': str(e)}

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Send G-code to OneFinity Controller')
    parser.add_argument('--host', default='bbctrl.local', help='Controller hostname or IP')
    parser.add_argument('--port', type=int, default=80, help='Controller port')
    parser.add_argument('--username', help='Login username')
    parser.add_argument('--password', help='Login password')
    parser.add_argument('--gcode', help='G-code command to send')
    parser.add_argument('--file', help='File containing G-code commands to send')
    parser.add_argument('--status', action='store_true', help='Get controller status')
    
    args = parser.parse_args()
    
    if args.status:
        status = get_status(args.host, args.port, args.username, args.password)
        print("Controller status:")
        print(json.dumps(status, indent=2))
        return
    
    if args.gcode:
        send_gcode(args.host, args.port, args.gcode, args.username, args.password)
    elif args.file:
        try:
            with open(args.file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith(';'):  # Skip empty lines and comments
                        print(f"Sending: {line}")
                        if not send_gcode(args.host, args.port, line, args.username, args.password):
                            print("Failed to send command, stopping")
                            break
                        time.sleep(0.5)  # Small delay between commands
        except Exception as e:
            print(f"Error reading file: {str(e)}")
    else:
        print("No command specified. Use --gcode or --file option.")
        print("Example:")
        print("  python simple_gcode_sender.py --gcode 'G28'")
        print("  python simple_gcode_sender.py --file commands.gcode")
        print("  python simple_gcode_sender.py --status")

if __name__ == "__main__":
    main()
