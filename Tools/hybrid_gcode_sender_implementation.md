# Hybrid G-code Sender Implementation Plan

This document outlines the implementation details for a hybrid G-code sender that combines API and WebSocket approaches to communicate with a bbctrl.local CNC controller. The solution allows for reading a G-code file and submitting commands line by line with user permission.

## File Structure

Create a new file called `hybrid_gcode_sender.py` with the following structure:

```python
#!/usr/bin/env python3
"""
Hybrid G-code Sender for bbctrl Controller

This script reads a G-code file and sends commands one at a time to the bbctrl controller
via its API or WebSocket interface, waiting for user confirmation before sending each command.
It uses the API by default but falls back to WebSocket if the API fails.
"""

import argparse
import json
import os
import queue
import requests
import sys
import threading
import time
import uuid
import websocket

# Set up logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('HybridGCodeSender')

class APIClient:
    """Client for interacting with the bbctrl controller's REST API."""
    
    def __init__(self, host="bbctrl.local", port=80, username=None, password=None):
        """Initialize the API client.
        
        Args:
            host: Hostname or IP address of the controller
            port: Port number
            username: Username for authentication (if required)
            password: Password for authentication (if required)
        """
        self.base_url = f"http://{host}:{port}"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'HybridGCodeSender/1.0',
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json'
        })
        self.username = username
        self.password = password
        self.authenticated = False
        
    def connect(self):
        """Test connection to the controller and authenticate if needed.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Try to get controller state
            response = self.session.get(f"{self.base_url}/api/state", timeout=5)
            
            # If authentication is required
            if response.status_code == 401 and self.username and self.password:
                return self.login()
                
            return response.status_code == 200
        except Exception as e:
            logger.error(f"API connection error: {e}")
            return False
            
    def login(self):
        """Authenticate with the controller.
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            auth_url = f"{self.base_url}/api/auth/login"
            response = self.session.post(
                auth_url,
                json={'user': self.username, 'password': self.password},
                timeout=5
            )
            
            if response.status_code == 200:
                self.authenticated = True
                logger.info("Successfully authenticated with the controller")
                return True
            else:
                logger.error(f"Authentication failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
            
    def send_gcode(self, command):
        """Send a G-code command to the controller.
        
        Args:
            command: G-code command to send
            
        Returns:
            dict or str: Response from the controller
            
        Raises:
            RuntimeError: If the API request fails
        """
        try:
            # The API endpoint for G-code is a GET request with the command as a query parameter
            from urllib.parse import quote
            endpoint = f"/api/gcode?{quote(command)}"
            
            response = self.session.get(
                f"{self.base_url}{endpoint}",
                timeout=10
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"API error: {response.status_code} - {response.text}")
                
            # Parse the response
            if 'application/json' in response.headers.get('Content-Type', ''):
                return response.json()
            else:
                return response.text
                
        except Exception as e:
            logger.error(f"Error sending G-code via API: {e}")
            raise RuntimeError(f"Failed to send G-code via API: {e}")
            
    def get_state(self):
        """Get the current state of the controller.
        
        Returns:
            dict: Controller state
            
        Raises:
            RuntimeError: If the API request fails
        """
        try:
            response = self.session.get(f"{self.base_url}/api/state", timeout=5)
            
            if response.status_code != 200:
                raise RuntimeError(f"API error: {response.status_code} - {response.text}")
                
            if 'application/json' in response.headers.get('Content-Type', ''):
                return response.json()
            else:
                return {'raw': response.text}
                
        except Exception as e:
            logger.error(f"Error getting state via API: {e}")
            raise RuntimeError(f"Failed to get state via API: {e}")


class WebSocketClient:
    """Client for interacting with the bbctrl controller via WebSocket."""
    
    def __init__(self, host="bbctrl.local", port=80):
        """Initialize the WebSocket client.
        
        Args:
            host: Hostname or IP address of the controller
            port: Port number
        """
        self.host = host
        self.port = port
        self.ws = None
        self.connected = False
        self.message_queue = queue.Queue()
        self.state_queue = queue.Queue()
        self.ws_thread = None
        self.message_counter = 1
        self.session_id = None
        
    def connect(self):
        """Connect to the controller via WebSocket.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Generate random server and session IDs for SockJS
            import random
            server_id = random.randint(0, 999)
            session_id = str(uuid.uuid4())
            self.ws_url = f"ws://{self.host}:{self.port}/sockjs/{server_id}/{session_id}/websocket"
            
            logger.info(f"Connecting to WebSocket at {self.ws_url}")
            
            # Create WebSocket connection
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )
            
            # Start WebSocket thread
            self.ws_thread = threading.Thread(target=self.ws.run_forever)
            self.ws_thread.daemon = True
            self.ws_thread.start()
            
            # Wait for connection to establish
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < 10:
                time.sleep(0.1)
                
            return self.connected
            
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            return False
            
    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages.
        
        Args:
            ws: WebSocket instance
            message: Received message
        """
        logger.debug(f"WebSocket received: {message}")
        
        try:
            # Handle SockJS protocol messages
            if message == 'o':
                # SockJS open frame
                self.connected = True
                logger.info("SockJS connection established")
                return
                
            if message.startswith('a'):
                # SockJS message frame (a["message1","message2",...])
                try:
                    # Parse the message array
                    messages = json.loads(message[1:])
                    for msg in messages:
                        try:
                            data = json.loads(msg)
                            
                            # Handle different message types
                            if isinstance(data, dict):
                                # Session ID message
                                if 'sid' in data:
                                    self.session_id = data['sid']
                                    logger.info(f"Received session ID: {self.session_id}")
                                
                                # State update message
                                if 'state' in data or 'line' in data or 'position' in data:
                                    self.state_queue.put(data)
                                    
                                # Response to a command
                                if 'id' in data:
                                    self.message_queue.put(data)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON in WebSocket message: {msg}")
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in WebSocket message array: {message[1:]}")
                    
            elif message.startswith('h'):
                # SockJS heartbeat frame
                logger.debug("Received heartbeat")
                # Send heartbeat back
                if self.ws and self.connected:
                    self.ws.send('h')
                    
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
            
    def _on_error(self, ws, error):
        """Handle WebSocket errors.
        
        Args:
            ws: WebSocket instance
            error: Error message
        """
        logger.error(f"WebSocket error: {error}")
        
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close.
        
        Args:
            ws: WebSocket instance
            close_status_code: Status code
            close_msg: Close message
        """
        logger.info(f"WebSocket closed: {close_status_code} - {close_msg}")
        self.connected = False
        
    def _on_open(self, ws):
        """Handle WebSocket connection open.
        
        Args:
            ws: WebSocket instance
        """
        logger.info("WebSocket connection opened")
        self.connected = True
        
    def send_gcode(self, command):
        """Send a G-code command via WebSocket.
        
        Args:
            command: G-code command to send
            
        Returns:
            dict: Response from the controller
            
        Raises:
            RuntimeError: If the WebSocket request fails
        """
        if not self.connected:
            raise RuntimeError("WebSocket not connected")
            
        try:
            # Create a unique message ID
            message_id = self.message_counter
            self.message_counter += 1
            
            # Create the message
            message = {
                "id": message_id,
                "jsonrpc": "2.0",
                "method": "gcode",
                "params": {"gcode": command}
            }
            
            # Send the message
            self.ws.send(json.dumps(message))
            logger.debug(f"Sent G-code via WebSocket: {command}")
            
            # Wait for response with timeout
            start_time = time.time()
            while (time.time() - start_time) < 10:
                try:
                    response = self.message_queue.get(timeout=0.5)
                    if response.get('id') == message_id:
                        return response
                except queue.Empty:
                    pass
                    
            raise TimeoutError("Timeout waiting for WebSocket response")
            
        except Exception as e:
            logger.error(f"Error sending G-code via WebSocket: {e}")
            raise RuntimeError(f"Failed to send G-code via WebSocket: {e}")
            
    def get_state_update(self, timeout=0.1):
        """Get the next state update from the queue.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            dict or None: State update or None if no update available
        """
        try:
            return self.state_queue.get(timeout=timeout)
        except queue.Empty:
            return None
            
    def close(self):
        """Close the WebSocket connection."""
        if self.ws:
            self.ws.close()
            self.connected = False


class HybridGCodeSender:
    """Hybrid G-code sender that can use both API and WebSocket."""
    
    def __init__(self, host="bbctrl.local", port=80, username=None, password=None, 
                 use_api=True, use_websocket=True, verbose=False):
        """Initialize the hybrid G-code sender.
        
        Args:
            host: Hostname or IP address of the controller
            port: Port number
            username: Username for authentication (if required)
            password: Password for authentication (if required)
            use_api: Whether to use the API
            use_websocket: Whether to use WebSocket
            verbose: Whether to enable verbose logging
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_api = use_api
        self.use_websocket = use_websocket
        self.verbose = verbose
        
        # Set up logging
        if verbose:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)
            
        # Initialize clients
        self.api_client = None
        self.ws_client = None
        
        if use_api:
            self.api_client = APIClient(host, port, username, password)
            
        if use_websocket:
            self.ws_client = WebSocketClient(host, port)
            
        # State monitoring
        self.state_monitor_thread = None
        self.stop_event = threading.Event()
        
    def connect(self):
        """Connect to the controller.
        
        Returns:
            bool: True if at least one connection method succeeded
            
        Raises:
            ConnectionError: If all connection methods fail
        """
        api_connected = False
        ws_connected = False
        
        # Try API connection
        if self.use_api and self.api_client:
            logger.info("Connecting via API...")
            api_connected = self.api_client.connect()
            if api_connected:
                logger.info("API connection successful")
            else:
                logger.warning("API connection failed")
                
        # Try WebSocket connection
        if self.use_websocket and self.ws_client:
            logger.info("Connecting via WebSocket...")
            ws_connected = self.ws_client.connect()
            if ws_connected:
                logger.info("WebSocket connection successful")
                # Start state monitor
                self.start_state_monitor()
            else:
                logger.warning("WebSocket connection failed")
                
        # Check if at least one connection method succeeded
        if not (api_connected or ws_connected):
            raise ConnectionError("Failed to connect to controller using any method")
            
        return True
        
    def start_state_monitor(self):
        """Start the state monitor thread."""
        if not self.ws_client or not self.ws_client.connected:
            logger.warning("Cannot start state monitor: WebSocket not connected")
            return
            
        self.stop_event.clear()
        self.state_monitor_thread = threading.Thread(target=self.monitor_state)
        self.state_monitor_thread.daemon = True
        self.state_monitor_thread.start()
        logger.info("State monitor started")
        
    def monitor_state(self):
        """Monitor controller state updates."""
        while not self.stop_event.is_set() and self.ws_client and self.ws_client.connected:
            try:
                state = self.ws_client.get_state_update(timeout=0.5)
                if state:
                    self.display_state_update(state)
            except Exception as e:
                logger.error(f"Error in state monitor: {e}")
                time.sleep(1)
                
    def display_state_update(self, state):
        """Display a state update.
        
        Args:
            state: State update data
        """
        # Extract key information
        if 'line' in state:
            print(f"\r[Line: {state['line']}]", end="")
            
        if 'position' in state:
            pos = state['position']
            pos_str = " ".join([f"{axis}:{pos[axis]:.3f}" for axis in pos if axis in "xyzabc"])
            print(f"\r[Position: {pos_str}]", end="")
            
        if 'state' in state:
            print(f"\r[State: {state['state']}]", end="")
            
        # Only print a newline for verbose mode or errors
        if self.verbose or 'error' in state:
            print()
            if 'error' in state:
                print(f"ERROR: {state['error']}")
                
    def send_gcode(self, command):
        """Send a G-code command using available methods.
        
        Args:
            command: G-code command to send
            
        Returns:
            tuple: (response, method) where method is 'api' or 'websocket'
            
        Raises:
            RuntimeError: If all methods fail
        """
        # Try API first if enabled
        if self.use_api and self.api_client:
            try:
                response = self.api_client.send_gcode(command)
                return response, "api"
            except Exception as e:
                logger.warning(f"API method failed: {e}")
                # If WebSocket is not enabled, re-raise the exception
                if not (self.use_websocket and self.ws_client):
                    raise
                    
        # Try WebSocket if enabled
        if self.use_websocket and self.ws_client:
            try:
                response = self.ws_client.send_gcode(command)
                return response, "websocket"
            except Exception as e:
                logger.error(f"WebSocket method failed: {e}")
                raise RuntimeError(f"All methods failed to send G-code: {e}")
                
        # If we get here, no methods are enabled
        raise RuntimeError("No methods available to send G-code")
        
    def parse_gcode_file(self, filename):
        """Parse a G-code file, removing comments and empty lines.
        
        Args:
            filename: Path to G-code file
            
        Returns:
            list: List of G-code commands
            
        Raises:
            FileNotFoundError: If the file does not exist
            IOError: If there is an error reading the file
        """
        if not os.path.exists(filename):
            raise FileNotFoundError(f"G-code file not found: {filename}")
            
        commands = []
        
        try:
            with open(filename, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    # Remove whitespace
                    line = line.strip()
                    
                    # Skip empty lines
                    if not line:
                        continue
                        
                    # Remove comments (both ; and () style)
                    if ';' in line:
                        line = line.split(';', 1)[0].strip()
                        
                    # Skip lines that are just comments
                    if not line or line.startswith('('):
                        continue
                        
                    # Remove parenthetical comments
                    in_comment = False
                    clean_line = ""
                    for char in line:
                        if char == '(':
                            in_comment = True
                        elif char == ')':
                            in_comment = False
                        elif not in_comment:
                            clean_line += char
                            
                    clean_line = clean_line.strip()
                    if clean_line:
                        commands.append((line_num, clean_line))
                        
            logger.info(f"Parsed {len(commands)} G-code commands from {filename}")
            return commands
            
        except Exception as e:
            logger.error(f"Error parsing G-code file: {e}")
            raise IOError(f"Error reading G-code file: {e}")
            
    def run_file(self, filename):
        """Run a G-code file with user confirmation for each command.
        
        Args:
            filename: Path to G-code file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Parse the G-code file
            commands = self.parse_gcode_file(filename)
            
            if not commands:
                logger.warning("No valid G-code commands found in file")
                return False
                
            print(f"\nFound {len(commands)} G-code commands in {filename}")
            print("\n--- G-code Stepper ---")
            print("For each command, you can:")
            print("  Press Enter or 'y' to send the command")
            print("  Enter 's' to skip the command")
            print("  Enter 'q' to quit")
            print("  Enter 'c' to continue without further prompts")
            
            auto_continue = False
            
            for i, (line_num, cmd) in enumerate(commands):
                # Display the command
                print(f"\n[{i+1}/{len(commands)}] Line {line_num}: {cmd}")
                
                # Get user confirmation unless auto-continue is enabled
                if not auto_continue:
                    while True:
                        choice = input("Send this command? [Y/s/q/c]: ").lower()
                        
                        if choice in ('', 'y', 'yes'):
                            break  # Continue with sending
                        elif choice in ('s', 'skip'):
                            print(f"Skipping command: {cmd}")
                            break  # Skip to next command
                        elif choice in ('q', 'quit'):
                            print("Quitting")
                            return True
                        elif choice in ('c', 'continue'):
                            print("Continuing without further prompts")
                            auto_continue = True
                            break
                        else:
                            print("Invalid choice. Please enter Y, s, q, or c")
                            
                    # Skip this command if requested
                    if choice in ('s', 'skip'):
                        continue
                        
                # Send the command
                try:
                    response, method = self.send_gcode(cmd)
                    print(f"Sent via {method}. Response: {response}")
                except Exception as e:
                    print(f"Error sending command: {e}")
                    
                    # Ask whether to retry, skip, or quit
                    while True:
                        retry = input("Retry? [Y/s/q]: ").lower()
                        
                        if retry in ('', 'y', 'yes'):
                            try:
                                response, method = self.send_gcode(cmd)
                                print(f"Sent via {method}. Response: {response}")
                                break
                            except Exception as e:
                                print(f"Error sending command: {e}")
                                continue
                        elif retry in ('s', 'skip'):
                            print(f"Skipping command: {cmd}")
                            break
                        elif retry in ('q', 'quit'):
                            print("Quitting")
                            return True
                        else:
                            print("Invalid choice. Please enter Y, s, or q")
                            
            print("\nFinished processing G-code file")
            return True
            
        except Exception as e:
            logger.error(f"Error running G-code file: {e}")
            return False
            
    def close(self):
        """Close all connections."""
        self.stop_event.set()
        
        if self.state_monitor_thread:
            self.state_monitor_thread.join(timeout=1.0)
            
        if self.ws_client:
            self.ws_client.close()
            
        logger.info("Connections closed")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Hybrid G-code Sender for bbctrl Controller')
    parser.add_argument('--host', default='bbctrl.local', help='Controller hostname or IP')
    parser.add_argument('--port', type=int, default=80, help='Controller port')
    parser.add_argument('--username', help='Username for authentication (if required)')
    parser.add_argument('--password', help='Password for authentication (if required)')
    parser.add_argument('--file', required=True, help='G-code file to send')
    parser.add_argument('--api-only', action='store_true', help='Use only API (no WebSocket)')
    parser.add_argument('--ws-only', action='store_true', help='Use only WebSocket (no API)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Determine which methods to use
    use_api = not args.ws_only
    use_websocket = not args.api_only
    
    if not (use_api or use_websocket):
        print("Error: Cannot disable both API and WebSocket")
        return 1
        
    # Create sender
    sender = HybridGCodeSender(
        host=args.host,
        port=args.port,
        username=args.username,
        password=args.password,
        use_api=use_api,
        use_websocket=use_websocket,
        verbose=args.verbose
    )
    
    try:
        # Connect to controller
        print(f"Connecting to {args.host}:{args.port}...")
        sender.connect()
        print("Connected to controller")
        
        # Run the G-code file
        print(f"Processing file: {args.file}")
        sender.run_file(args.file)
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 130
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    finally:
        # Clean up
        sender.close()
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## Dependencies

The script requires the following Python packages:
- `requests` - For API communication
- `websocket-client` - For WebSocket communication

You can install them with:
```
pip install requests websocket-client
```

## Usage

```
python hybrid_gcode_sender.py --file path/to/gcode_file.gcode
```

### Command-line Options

- `--host` - Controller hostname or IP (default: bbctrl.local)
- `--port` - Controller port (default: 80)
- `--username` - Username for authentication (if required)
- `--password` - Password for authentication (if required)
- `--file` - G-code file to send (required)
- `--api-only` - Use only API (no WebSocket)
- `--ws-only` - Use only WebSocket (no API)
- `--verbose` - Enable verbose output

## Features

1. **Hybrid Communication**
   - Uses the API by default for sending G-code commands
   - Falls back to WebSocket if the API fails
   - Uses WebSocket for real-time state updates

2. **G-code File Parsing**
   - Removes comments and empty lines
   - Handles both `;` and `()` style comments
   - Preserves line numbers for reference

3. **User Interaction**
   - Displays each command and waits for user confirmation
   - Options to send, skip, quit, or continue without prompts
   - Shows responses from the controller

4. **Real-time Feedback**
   - Displays position, line number, and state updates
   - Shows errors immediately

5. **Error Handling**
   - Robust error handling with retry options
   - Graceful fallback between communication methods
   - Detailed logging for troubleshooting

## Implementation Notes

1. The API client uses the `/api/gcode` endpoint to send G-code commands.
2. The WebSocket client uses the SockJS protocol to communicate with the controller.
3. The state monitor runs in a separate thread to avoid blocking the main thread.
4. The script handles authentication if required by the controller.
5. The script can be configured to use only API, only WebSocket, or both.