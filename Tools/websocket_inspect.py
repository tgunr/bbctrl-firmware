#!/usr/bin/env python3
"""
WebSocket Inspector for OneFinity Controller

This script connects to the OneFinity controller's WebSocket interface
and logs all incoming messages. It can also be used to send commands
to the controller for testing purposes.
"""
import asyncio
import json
import websockets
import ssl
import argparse
from datetime import datetime

class OneFinityWebSocket:
    def __init__(self, host='bbctrl.local', port=80, ssl_port=443, use_ssl=False):
        self.host = host
        self.port = ssl_port if use_ssl else port
        self.uri = f"{'wss' if use_ssl else 'ws'}://{self.host}:{self.port}/ws"
        self.ssl_context = ssl.create_default_context() if use_ssl else None
        if use_ssl:
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
        
        self.websocket = None
        self.running = False
        self.message_count = 0
    
    async def connect(self):
        """Establish WebSocket connection to the controller"""
        print(f"Connecting to {self.uri}...")
        self.websocket = await websockets.connect(
            self.uri,
            ssl=self.ssl_context,
            ping_interval=30,
            ping_timeout=10,
            close_timeout=1
        )
        print(f"Connected to {self.uri}")
        self.running = True
    
    async def send_command(self, command, data=None):
        """Send a command to the controller"""
        if not self.websocket:
            print("Not connected to WebSocket server")
            return
        
        message = {'command': command}
        if data is not None:
            message.update(data)
        
        message_str = json.dumps(message)
        print(f"Sending: {message_str}")
        await self.websocket.send(message_str)
    
    async def receive_messages(self):
        """Receive and log messages from the controller"""
        if not self.websocket:
            print("Not connected to WebSocket server")
            return
        
        print("Listening for messages... (Press Ctrl+C to stop)")
        try:
            async for message in self.websocket:
                self.message_count += 1
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                try:
                    # Try to parse as JSON
                    data = json.loads(message)
                    print(f"\n[{timestamp}] Message #{self.message_count} (JSON):")
                    print(json.dumps(data, indent=2))
                    
                    # Save to file for later analysis
                    with open("websocket_messages.log", "a", encoding="utf-8") as f:
                        f.write(f"[{timestamp}] {message}\n")
                        
                except json.JSONDecodeError:
                    # Not JSON, log as raw message
                    print(f"\n[{timestamp}] Message #{self.message_count} (raw):")
                    print(message[:500] + ("..." if len(message) > 500 else ""))
                    
        except websockets.exceptions.ConnectionClosed:
            print("\nConnection closed by server")
            self.running = False
        except Exception as e:
            print(f"\nError receiving message: {e}")
            self.running = False
    
    async def run_interactive(self):
        """Run an interactive session to send commands"""
        await self.connect()
        
        # Start receiving messages in the background
        receive_task = asyncio.create_task(self.receive_messages())
        
        try:
            # Interactive command loop
            while self.running:
                try:
                    print("\nAvailable commands:")
                    print("  status - Get controller status")
                    print("  gcode <command> - Send G-code command")
                    print("  home - Home all axes")
                    print("  unlock - Unlock the controller")
                    print("  exit - Close the connection")
                    
                    user_input = input("\nEnter command: ").strip().lower()
                    
                    if user_input == 'exit':
                        break
                    elif user_input == 'status':
                        await self.send_command('status')
                    elif user_input.startswith('gcode '):
                        gcode = user_input[6:].strip()
                        await self.send_command('gcode', {'gcode': gcode})
                    elif user_input == 'home':
                        await self.send_command('gcode', {'gcode': '$H'})
                    elif user_input == 'unlock':
                        await self.send_command('gcode', {'gcode': '$X'})
                    else:
                        print("Unknown command. Type 'exit' to quit.")
                    
                    # Small delay to prevent busy waiting
                    await asyncio.sleep(0.1)
                    
                except (KeyboardInterrupt, EOFError):
                    print("\nExiting...")
                    break
                except Exception as e:
                    print(f"Error: {e}")
        
        finally:
            # Cleanup
            self.running = False
            if not receive_task.done():
                receive_task.cancel()
            if self.websocket:
                await self.websocket.close()
            print("Disconnected")

async def main():
    parser = argparse.ArgumentParser(description='OneFinity Controller WebSocket Inspector')
    parser.add_argument('--host', default='bbctrl.local', help='Controller hostname or IP')
    parser.add_argument('--port', type=int, default=80, help='WebSocket port (default: 80)')
    parser.add_argument('--ssl', action='store_true', help='Use secure WebSocket (wss)')
    parser.add_argument('--ssl-port', type=int, default=443, help='Secure WebSocket port (default: 443)')
    
    args = parser.parse_args()
    
    inspector = OneFinityWebSocket(
        host=args.host,
        port=args.port,
        ssl_port=args.ssl_port,
        use_ssl=args.ssl
    )
    
    try:
        await inspector.run_interactive()
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if inspector.websocket:
            await inspector.websocket.close()

if __name__ == "__main__":
    asyncio.run(main())
