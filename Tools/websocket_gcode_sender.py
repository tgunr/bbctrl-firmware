#!/usr/bin/env python3
"""
WebSocket G-code Sender for OneFinity Controller

This script establishes a WebSocket connection to the OneFinity controller
and sends G-code commands through it.
"""

import asyncio
import websockets
import json
import argparse
import time
from urllib.parse import urlparse, urlunparse

class OneFinityWebSocket:
    def __init__(self, host='bbctrl.local', port=80, ssl=False):
        self.host = host
        self.port = port
        self.ssl = ssl
        self.websocket = None
        self.connected = False
        self.message_id = 1
        
        # Determine WebSocket URL
        scheme = 'wss' if ssl else 'ws'
        self.ws_url = f"{scheme}://{host}:{port}/ws"
    
    async def connect(self):
        """Establish WebSocket connection"""
        print(f"Connecting to {self.ws_url}...")
        try:
            self.websocket = await websockets.connect(
                self.ws_url,
                ping_interval=None,
                ping_timeout=10,
                close_timeout=5,
                max_size=10 * 1024 * 1024  # 10MB max message size
            )
            self.connected = True
            print("Connected to WebSocket server")
            
            # Start listening for messages in the background
            asyncio.create_task(self.listen())
            
            return True
            
        except Exception as e:
            print(f"Failed to connect to WebSocket: {e}")
            self.connected = False
            return False
    
    async def listen(self):
        """Listen for incoming WebSocket messages"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    print(f"\nReceived message: {json.dumps(data, indent=2)}")
                except json.JSONDecodeError:
                    print(f"\nReceived non-JSON message: {message}")
        except websockets.exceptions.ConnectionClosed as e:
            print(f"\nWebSocket connection closed: {e}")
            self.connected = False
        except Exception as e:
            print(f"\nError in WebSocket listener: {e}")
            self.connected = False
    
    async def send_command(self, command, params=None):
        """Send a command to the WebSocket server"""
        if not self.connected:
            print("Not connected to WebSocket server")
            return False
        
        try:
            message_id = self.message_id
            self.message_id += 1
            
            message = {
                'id': message_id,
                'jsonrpc': '2.0',
                'method': command
            }
            
            if params is not None:
                message['params'] = params
            
            print(f"Sending: {json.dumps(message, indent=2)}")
            await self.websocket.send(json.dumps(message))
            return True
            
        except Exception as e:
            print(f"Error sending command: {e}")
            self.connected = False
            return False
    
    async def send_gcode(self, gcode):
        """Send a G-code command"""
        return await self.send_command('gcode', {'gcode': gcode})
    
    async def get_status(self):
        """Get controller status"""
        return await self.send_command('status')
    
    async def close(self):
        """Close the WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False

async def interactive_shell(controller):
    """Interactive shell for sending commands"""
    print("\nInteractive G-code shell")
    print("Type 'exit' or 'quit' to exit")
    print("Type 'status' to get controller status")
    
    while True:
        try:
            # Get user input
            try:
                command = input("\nG-code> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting...")
                break
            
            if not command:
                continue
                
            if command.lower() in ('exit', 'quit'):
                print("Exiting...")
                break
                
            if command.lower() == 'status':
                await controller.get_status()
                continue
            
            # Send the G-code command
            await controller.send_gcode(command)
            
        except Exception as e:
            print(f"Error: {e}")

async def main():
    parser = argparse.ArgumentParser(description='WebSocket G-code Sender for OneFinity Controller')
    parser.add_argument('--host', default='bbctrl.local', help='Controller hostname or IP')
    parser.add_argument('--port', type=int, default=80, help='Controller port')
    parser.add_argument('--ssl', action='store_true', help='Use secure WebSocket (WSS)')
    parser.add_argument('--gcode', help='G-code command to send (optional)')
    parser.add_argument('--file', help='File containing G-code commands to send (one per line)')
    parser.add_argument('--interactive', '-i', action='store_true', help='Start interactive shell')
    
    args = parser.parse_args()
    
    # Create controller instance
    controller = OneFinityWebSocket(
        host=args.host,
        port=args.port,
        ssl=args.ssl
    )
    
    # Connect to WebSocket
    if not await controller.connect():
        print("Failed to connect to WebSocket server")
        return
    
    try:
        # Send single G-code command if specified
        if args.gcode:
            print(f"Sending G-code: {args.gcode}")
            await controller.send_gcode(args.gcode)
        
        # Send G-code from file if specified
        elif args.file:
            try:
                with open(args.file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith(';'):  # Skip empty lines and comments
                            print(f"Sending: {line}")
                            await controller.send_gcode(line)
                            await asyncio.sleep(0.5)  # Small delay between commands
            except Exception as e:
                print(f"Error reading file: {e}")
        
        # Start interactive shell if no commands specified or if explicitly requested
        if args.interactive or (not args.gcode and not args.file):
            await interactive_shell(controller)
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        # Close the connection
        await controller.close()
        print("Disconnected from WebSocket server")

if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        print("\nExiting...")
