#!/usr/bin/env python3
"""
bbctrl G-code Sender

This script sends G-code commands to the bbctrl controller by directly
interacting with its web interface.
"""

import requests
import json
import time
from bs4 import BeautifulSoup

class BbctrlController:
    def __init__(self, host='bbctrl.local', port=80, username=None, password=None):
        self.base_url = f"http://{host}:{port}"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json'
        })
        self.username = username
        self.password = password
        self.logged_in = False
        self.csrf_token = None

    def login(self):
        """Log in to the bbctrl controller"""
        try:
            # First, get the login page to extract CSRF token
            login_url = f"{self.base_url}/login"
            response = self.session.get(login_url)
            
            # Try to find CSRF token in the page
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_input = soup.find('input', {'name': '_csrf'})
            
            if csrf_input:
                self.csrf_token = csrf_input.get('value')
                print(f"Found CSRF token: {self.csrf_token}")
            else:
                print("No CSRF token found, trying without it")
            
            # Prepare login data
            login_data = {
                'username': self.username or 'admin',  # Default username
                'password': self.password or 'bbctrl'  # Default password
            }
            
            if self.csrf_token:
                login_data['_csrf'] = self.csrf_token
            
            # Send login request
            response = self.session.post(
                f"{self.base_url}/api/login",
                json=login_data,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get('success'):
                        self.logged_in = True
                        print("Successfully logged in")
                        return True
                except:
                    pass
            
            print(f"Login failed: {response.status_code} - {response.text}")
            return False
            
        except Exception as e:
            print(f"Error during login: {str(e)}")
            return False
    
    def send_gcode(self, gcode_command):
        """Send a G-code command to the controller"""
        if not self.logged_in and not self.login():
            print("Not logged in and login failed")
            return False
        
        try:
            # Try the most common API endpoint for G-code
            response = self.session.post(
                f"{self.base_url}/api/gcode",
                json={'gcode': gcode_command},
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"Successfully sent G-code: {gcode_command}")
                return True
            
            print(f"Failed to send G-code: {response.status_code} - {response.text}")
            return False
            
        except Exception as e:
            print(f"Error sending G-code: {str(e)}")
            return False
    
    def get_status(self):
        """Get the current status of the controller"""
        try:
            response = self.session.get(f"{self.base_url}/api/status", timeout=5)
            if response.status_code == 200:
                return response.json()
            return None
        except:
            return None

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Send G-code to bbctrl Controller')
    parser.add_argument('--host', default='bbctrl.local', help='Controller hostname or IP')
    parser.add_argument('--port', type=int, default=80, help='Controller port')
    parser.add_argument('--username', help='Login username')
    parser.add_argument('--password', help='Login password')
    parser.add_argument('--gcode', help='G-code command to send')
    parser.add_argument('--file', help='File containing G-code commands to send')
    parser.add_argument('--status', action='store_true', help='Get controller status')
    
    args = parser.parse_args()
    
    print("bbctrl G-code Sender")
    print("------------------")
    print(f"Connecting to {args.host}:{args.port}")
    
    controller = BbctrlController(
        host=args.host,
        port=args.port,
        username=args.username,
        password=args.password
    )
    
    if args.status:
        status = controller.get_status()
        print("Controller status:")
        print(json.dumps(status, indent=2))
        return
    
    if args.gcode:
        controller.send_gcode(args.gcode)
    elif args.file:
        try:
            with open(args.file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith(';'):  # Skip empty lines and comments
                        print(f"Sending: {line}")
                        if not controller.send_gcode(line):
                            print("Failed to send command, stopping")
                            break
                        time.sleep(0.5)  # Small delay between commands
        except Exception as e:
            print(f"Error reading file: {str(e)}")
    else:
        print("No command specified. Use --gcode or --file option.")
        print("Example:")
        print("  python bbctrl_gcode.py --gcode 'G28'")
        print("  python bbctrl_gcode.py --file commands.gcode")

if __name__ == "__main__":
    main()
