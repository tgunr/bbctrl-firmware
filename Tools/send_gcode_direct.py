#!/usr/bin/env python3

import requests
import json
import time
import sys
import websocket
import threading

class BuildboticsController:
    def __init__(self, host='bbctrl.local', port=80):
        self.host = host
        self.port = port
        self.base_url = f'http://{host}' if port == 80 else f'http://{host}:{port}'
        self.ws_url = f'ws://{host}/websocket' if port == 80 else f'ws://{host}:{port}/websocket'
        self.ws = None
        self.connected = False
        
    def connect_websocket(self):
        """Connect to the WebSocket for sending G-code commands"""
        try:
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )
            
            # Start WebSocket in a separate thread
            self.ws_thread = threading.Thread(target=self.ws.run_forever)
            self.ws_thread.daemon = True
            self.ws_thread.start()
            
            # Wait for connection
            timeout = 10
            while not self.connected and timeout > 0:
                time.sleep(0.1)
                timeout -= 0.1
                
            return self.connected
            
        except Exception as e:
            print(f"WebSocket connection error: {e}")
            return False
    
    def on_open(self, ws):
        print("WebSocket connected")
        self.connected = True
    
    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            if 'state' in data:
                print(f"State update: {data.get('xx', 'unknown')}")
        except:
            pass
    
    def on_error(self, ws, error):
        print(f"WebSocket error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        print("WebSocket closed")
        self.connected = False
    
    def get_state(self):
        """Get current machine state via REST API"""
        try:
            response = requests.get(f'{self.base_url}/api/state', timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error getting state: {e}")
        return None
    
    def send_gcode(self, command):
        """Send G-code command via WebSocket"""
        if not self.connected:
            print("Not connected to WebSocket")
            return False
            
        try:
            self.ws.send(command)
            print(f"Sent: {command}")
            return True
        except Exception as e:
            print(f"Error sending command: {e}")
            return False
    
    def send_gcode_sequence(self, commands, delay=1.0):
        """Send a sequence of G-code commands"""
        print("=== Buildbotics Direct G-code Sender ===")
        
        # Check initial state
        state = self.get_state()
        if state:
            print(f"Machine state: {state.get('xx', 'unknown')}")
            print(f"Cycle: {state.get('cycle', 'unknown')}")
        else:
            print("Could not get machine state")
            
        # Connect WebSocket
        if not self.connect_websocket():
            print("Failed to connect WebSocket")
            return False
            
        print(f"\nSending {len(commands)} G-code commands...")
        
        for i, cmd in enumerate(commands, 1):
            print(f"\n--- Command {i}/{len(commands)}: {cmd} ---")
            
            if self.send_gcode(cmd):
                print("Command sent successfully")
            else:
                print("Failed to send command")
                
            # Wait between commands
            if i < len(commands):
                print(f"Waiting {delay} seconds...")
                time.sleep(delay)
        
        print("\n=== G-code sequence complete ===")
        return True
    
    def close(self):
        """Close WebSocket connection"""
        if self.ws:
            self.ws.close()

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 send_gcode_direct.py 'G90'")
        print("  python3 send_gcode_direct.py 'G90' 'G0 X10 Y10' 'M3 S1000'")
        print("  python3 send_gcode_direct.py --file gcode_file.nc")
        return
    
    controller = BuildboticsController()
    
    try:
        if sys.argv[1] == '--file':
            if len(sys.argv) < 3:
                print("ERROR: Please specify a G-code file")
                return
            
            try:
                with open(sys.argv[2], 'r') as f:
                    commands = [line.strip() for line in f if line.strip() and not line.startswith(';')]
            except FileNotFoundError:
                print(f"ERROR: File {sys.argv[2]} not found")
                return
        else:
            commands = sys.argv[1:]
        
        controller.send_gcode_sequence(commands)
        
    finally:
        controller.close()

if __name__ == "__main__":
    main()