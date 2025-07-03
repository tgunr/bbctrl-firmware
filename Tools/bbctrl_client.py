import json
import websocket
import threading
import time
import uuid
import random
import logging
import argparse
import sys

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('websocket')
logger.setLevel(logging.DEBUG)

def print_websocket_trace(*args):
    print("\n--- WebSocket Trace ---")
    for arg in args:
        print(arg)
    print("----------------------\n")

class BbctrlClient:
    def __init__(self, host="bbctrl.local", verbose=False, max_reconnect_attempts=3, reconnect_delay=2):
        self.host = host
        self.ws = None
        self.connected = False
        self.session_id = None
        self.stop_event = threading.Event()
        self.ping_interval = 25  # seconds
        self.ping_thread = None
        self.ws_thread = None
        self.message_counter = 0
        self.verbose = verbose
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay

    def log(self, message, level="info"):
        """Log a message with timestamp and optional level"""
        if level == "debug" and not self.verbose:
            return
        print(f"[{time.strftime('%H:%M:%S')}] {message}")

    def on_message(self, ws, message):
        self.log(f"Received: {message}")
        try:
            if message == 'o':
                self.connected = True
                self.log("SockJS connection established")
                # Add a small delay before sending handshake
                time.sleep(0.5)
                self.send_handshake()
            elif message.startswith('a'):
                try:
                    # SockJS message format: a[{...}]
                    messages = json.loads(message[1:])
                    if not isinstance(messages, list):
                        messages = [messages]
                    
                    # Process each message in the array
                    for msg in messages:
                        if isinstance(msg, dict):
                            # Handle session ID updates first
                            if 'sid' in msg:
                                self.session_id = msg.get('sid', '')
                                self.log(f"Session ID received: '{self.session_id}'")
                                
                                # Even with empty session ID, we can proceed
                                # Some implementations of SockJS don't require a session ID
                                self.connected = True
                                
                                # Add a small delay after receiving session ID
                                time.sleep(0.5)
                                
                                # Send connect message after receiving session ID
                                self.send_connect()
                                
                                # If this is the only field in the message, we're done processing it
                                if len(msg) == 1:
                                    continue
                            
                            # Process other message types
                            if 'channel' in msg:
                                self.handle_channel_message(msg)
                            elif 'line' in msg:
                                self.log(f"State update - Line: {msg.get('line')}")
                            elif 'log' in msg:
                                self.log(f"Log: {msg['log']}")
                            elif 'error' in msg:
                                self.log(f"Error: {msg['error']}")
                            else:
                                # Only log as unhandled if it's not just a sid message
                                if not (len(msg) == 1 and 'sid' in msg):
                                    self.log(f"Unhandled message format: {msg}")
                        else:
                            self.log(f"Unexpected message format (not a dict): {msg}")
                except json.JSONDecodeError as e:
                    self.log(f"Failed to parse message: {e}")
            elif message.startswith('h'):
                self.log("Heartbeat received")
                if self.ws:
                    self.ws.send('h')
            else:
                self.log(f"Unhandled message: {message}")
        except Exception as e:
            self.log(f"Error in on_message: {e}")

    def handle_messages(self, messages):
        for msg in messages:
            if not isinstance(msg, dict):
                if isinstance(msg, str):
                    try:
                        msg = json.loads(msg)
                        if not isinstance(msg, dict):
                            self.log(f"Unexpected message format (not a dict): {msg}")
                            continue
                    except json.JSONDecodeError:
                        self.log(f"Failed to parse message: {msg}")
                        continue
            else:
                self.log(f"Unexpected message type: {type(msg)}")
                continue

            self.log(f"Processing message: {msg}")

            if 'channel' in msg:

                if msg['channel'] == '/meta/handshake':
                    if msg.get('successful'):
                        self.session_id = msg.get('clientId', '')
                    if not self.session_id:
                        self.log("Error: Server returned empty client ID in handshake response")
                        self.log(f"Full handshake response: {msg}")
                        # Try to continue anyway, some servers might work without clientId
                    else:
                        self.log(f"Handshake successful, client ID: {self.session_id}")
                    self.send_connect()
                else:
                    error_msg = msg.get('error', 'Unknown error')
                    self.log(f"Handshake failed: {error_msg}")
                    # Add more specific error handling if needed
                    if error_msg == '403::Handshake denied':
                        self.log("Authentication required - check your credentials")
            elif msg['channel'] == '/meta/connect':
                if msg.get('successful'):
                    self.log("Connected to WebSocket")
                    self.subscribe_to_state()
                else:
                    self.log(f"Connection failed: {msg.get('error', 'Unknown error')}")
            
            elif msg['channel'] == '/meta/subscribe':
                if msg.get('successful'):
                    self.log(f"Subscribed to {msg.get('subscription')}")
                else:
                    self.log(f"Subscription failed: {msg.get('error', 'Unknown error')}")
            
            elif msg['channel'] == '/meta/unsubscribe':
                if msg.get('successful'):
                    self.log(f"Unsubscribed from {msg.get('subscription')}")
                else:
                    self.log(f"Unsubscription failed: {msg.get('error', 'Unknown error')}")
        
            # Handle state updates
            elif 'line' in msg:     
                self.log(f"State update - Line: {msg.get('line')}")
        
            # Handle log messages
            elif 'log' in msg:
                self.log(f"Log: {msg['log']}")
        
            # Handle session ID updates
            elif 'sid' in msg:
                self.session_id = msg['sid']
                self.log(f"Session ID: {self.session_id}")
        
            # Handle error messages
            elif 'error' in msg:
                self.log(f"Error: {msg['error']}")
        
            # Handle unknown message format
            else:
                    self.log(f"Unhandled message format: {msg}")
        
    def on_error(self, ws, error):
        self.log(f"WebSocket Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        self.log(f"### WebSocket closed ### Status code: {close_status_code}, Message: {close_msg}")
        self.connected = False
        
        # Don't attempt to reconnect if we're intentionally stopping
        if self.stop_event.is_set() or isinstance(close_msg, KeyboardInterrupt):
            self.log("Not reconnecting due to intentional shutdown")
            return
            
        # Implement exponential backoff for reconnection attempts
        reconnect_delay = self.reconnect_delay
        attempt = 0
        
        while attempt < self.max_reconnect_attempts and not self.stop_event.is_set():
            attempt += 1
            self.log(f"Reconnection attempt {attempt}/{self.max_reconnect_attempts} in {reconnect_delay} seconds...")
            time.sleep(reconnect_delay)
            
            if self.connect():
                self.log("Reconnection successful")
                return
                
            # Increase delay for next attempt (exponential backoff)
            reconnect_delay = min(reconnect_delay * 2, 30)  # Cap at 30 seconds
        
        if attempt >= self.max_reconnect_attempts:
            self.log("Max reconnection attempts reached. Giving up.")

    def on_open(self, ws):
        self.log("### WebSocket connected ###")
        self.connected = True
        self.send_handshake()
    
    def start_ping(self):
        while not self.stop_event.is_set() and self.connected:
            try:
                if self.ws and self.connected:
                    self.ws.send('h')
                    time.sleep(self.ping_interval)
            except Exception as e:
                self.log(f"Error in ping: {e}")
                self.connected = False
                break

    def send_handshake(self):
        handshake = {
            "channel": "/meta/handshake",
            "version": "1.0",
            "supportedConnectionTypes": ["websocket"],
            "id": str(self.message_counter),
            "minimumVersion": "1.0",
            "ext": {
                "ack": True,
                "token": None  # Add this line if token-based auth is needed
            }
        }
        self.message_counter += 1
        self.log(f"Sending handshake: {handshake}")
        
        # Add a small delay before sending to ensure the connection is ready
        time.sleep(0.2)
        return self.send_raw(json.dumps([handshake]))
    
    def subscribe_to_state(self):
        subscribe_msg = {
            "channel": "/meta/subscribe",
            "clientId": self.session_id,
            "subscription": "/state",
            "id": str(self.message_counter)
        }
        self.message_counter += 1
        self.send_raw(json.dumps([subscribe_msg]))
    
    def send_raw(self, message):
        if not self.ws:
            self.log("WebSocket not initialized, cannot send message")
            return False
            
        try:
            self.ws.send(message)
            self.log(f"Sent: {message}")
            return True
        except Exception as e:
            self.log(f"Error sending message: {e}")
            self.connected = False
            return False
            
    def close(self):
        self.stop_event.set()
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
        if hasattr(self, 'ws_thread') and self.ws_thread:
            self.ws_thread.join(timeout=1.0)
        if hasattr(self, 'ping_thread') and self.ping_thread:
            self.ping_thread.join(timeout=1.0)
        self.log("Client closed")

    def connect(self):
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
            self.ws = None

        server_id = random.randint(0, 999)
        session_id = str(uuid.uuid4())
        ws_url = f"ws://{self.host}/sockjs/{server_id}/{session_id}/websocket"
    
        self.log(f"Connecting to {ws_url}...")
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open,
            on_ping=lambda ws, msg: print_websocket_trace("Ping:", msg),
            on_pong=lambda ws, msg: print_websocket_trace("Pong:", msg),
            on_cont_message=lambda ws, msg, msg_type, fin: print_websocket_trace("Continuation Message:", msg, msg_type, fin)
        )

        self.ws_thread = threading.Thread(target=self.ws.run_forever, kwargs={'ping_interval': 25, 'ping_timeout': 10})
        self.ws_thread.daemon = True
        self.ws_thread.start()

        self.ping_thread = threading.Thread(target=self.start_ping)
        self.ping_thread.daemon = True
        self.ping_thread.start()

        start_time = time.time()
        while not self.connected and (time.time() - start_time) < 10:
            time.sleep(0.1)

        return self.connected

    def send_connect(self):
        connect_msg = {
            "channel": "/meta/connect",
            "connectionType": "websocket",
            "clientId": self.session_id,
            "id": str(self.message_counter)
            }
        self.message_counter += 1
        self.log(f"Sending connect message with clientId: '{self.session_id}'")
        
        # Add a small delay before sending to ensure the connection is ready
        time.sleep(0.2)
        return self.send_raw(json.dumps([connect_msg]))
        
def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Buildbotics Controller WebSocket Client")
    parser.add_argument("--host", default="bbctrl.local", help="Hostname or IP address of the controller (default: bbctrl.local)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--max-reconnect", type=int, default=3, help="Maximum number of reconnection attempts (default: 3)")
    parser.add_argument("--reconnect-delay", type=int, default=2, help="Initial delay between reconnection attempts in seconds (default: 2)")
    parser.add_argument("--no-connect", action="store_true", help="Don't connect to the controller, just parse arguments and exit")
    return parser.parse_args()

if __name__ == "__main__":
    # Check if --help is in the arguments, and if so, just let argparse handle it
    if "--help" in sys.argv or "-h" in sys.argv:
        parser = argparse.ArgumentParser(description="Buildbotics Controller WebSocket Client")
        parser.add_argument("--host", default="bbctrl.local", help="Hostname or IP address of the controller (default: bbctrl.local)")
        parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
        parser.add_argument("--max-reconnect", type=int, default=3, help="Maximum number of reconnection attempts (default: 3)")
        parser.add_argument("--reconnect-delay", type=int, default=2, help="Initial delay between reconnection attempts in seconds (default: 2)")
        parser.add_argument("--no-connect", action="store_true", help="Don't connect to the controller, just parse arguments and exit")
        parser.print_help()
        sys.exit(0)
    
    # Parse arguments
    args = parse_arguments()
    
    # Configure logging based on verbosity
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level)
    logger = logging.getLogger('websocket')
    logger.setLevel(log_level)
    
    # Exit early if --no-connect is specified
    if args.no_connect:
        print("Arguments parsed successfully. Not connecting due to --no-connect flag.")
        sys.exit(0)
    
    # Create and connect client
    client = BbctrlClient(
        host=args.host,
        verbose=args.verbose,
        max_reconnect_attempts=args.max_reconnect,
        reconnect_delay=args.reconnect_delay
    )
    
    try:
        if client.connect():
            print("Connected! Press Ctrl+C to exit.")
            while not client.stop_event.is_set():
                time.sleep(1)
    except KeyboardInterrupt:
        print("\nDisconnecting...")
    finally:
        client.close()