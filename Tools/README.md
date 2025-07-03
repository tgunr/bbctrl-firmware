# G-code Sender Tools for bbctrl Controller

This directory contains various tools for communicating with a Buildbotics/bbctrl CNC controller and sending G-code commands. The main focus is on providing a reliable way to read G-code files and submit commands line by line with user permission.

## Main Solution: Hybrid G-code Sender

### `hybrid_gcode_sender.py` - **RECOMMENDED**

This is the new hybrid solution that combines the best aspects of the existing tools. It provides a reliable way to:

- Connect to a bbctrl.local CNC controller
- Read and parse G-code files 
- Submit G-code commands line by line with user confirmation
- Use both API and WebSocket communication methods for maximum reliability

#### Features

1. **Hybrid Communication**
   - Uses the REST API by default for sending G-code commands
   - Falls back to WebSocket if the API fails
   - Uses WebSocket for real-time state monitoring

2. **G-code File Processing**
   - Parses G-code files and removes comments and empty lines
   - Handles both `;` and `()` style comments
   - Preserves original line numbers for reference

3. **User Interaction**
   - Displays each command with line number before sending
   - Waits for user confirmation for each command
   - Options to send, skip, quit, or continue without further prompts
   - Shows controller responses after each command

4. **Real-time Feedback**
   - Displays position, line number, and state updates from the controller
   - Shows errors immediately
   - Background monitoring thread for state updates

5. **Error Handling**
   - Robust error handling with retry options
   - Graceful fallback between communication methods
   - Detailed logging for troubleshooting

#### Usage

```bash
# Basic usage
python hybrid_gcode_sender.py --file path/to/your/gcode_file.gcode

# With custom host
python hybrid_gcode_sender.py --host 192.168.1.100 --file gcode_file.gcode

# API only (no WebSocket)
python hybrid_gcode_sender.py --api-only --file gcode_file.gcode

# WebSocket only (no API)
python hybrid_gcode_sender.py --ws-only --file gcode_file.gcode

# With authentication
python hybrid_gcode_sender.py --username admin --password mypass --file gcode_file.gcode

# Verbose output for debugging
python hybrid_gcode_sender.py --verbose --file gcode_file.gcode
```

#### Command-line Options

- `--host` - Controller hostname or IP (default: bbctrl.local)
- `--port` - Controller port (default: 80)
- `--username` - Username for authentication (if required)
- `--password` - Password for authentication (if required)
- `--file` - G-code file to send (required)
- `--api-only` - Use only API (no WebSocket)
- `--ws-only` - Use only WebSocket (no API)
- `--verbose` - Enable verbose output

#### Interactive Commands

During execution, you have these options for each G-code command:

- Press **Enter** or **'y'** to send the command
- Enter **'s'** to skip the command
- Enter **'q'** to quit
- Enter **'c'** to continue without further prompts (auto-send remaining commands)

If an error occurs, you can:
- **'Y'** to retry sending the command
- **'s'** to skip the command
- **'q'** to quit

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Make the script executable (optional):
```bash
chmod +x hybrid_gcode_sender.py
```

## Legacy Tools

The following tools were part of the original implementation but have various limitations:

### `bbctrl_cli.py`
- Command-line interface for the controller's web API
- Can send G-code commands but doesn't support line-by-line execution with user confirmation
- **Issue**: Missing the key feature of user confirmation per line

### `bbctrl_api_client.py`
- API client library used by bbctrl_cli.py
- Provides methods for sending G-code commands
- **Issue**: No line-by-line execution with user confirmation

### `send_gcode_step.py`
- Attempts to implement line-by-line G-code sending with user confirmation
- Uses Selenium WebDriver with Firefox to interact with the web interface
- **Issues**: 
  - Complex implementation with browser automation
  - Reliability problems with finding web interface elements
  - Requires Firefox and Selenium dependencies
  - Many potential points of failure

### `simple_gcode_sender.py`
- Simple implementation that sends G-code commands directly to the API
- Can read from a file and send commands
- **Issue**: Doesn't wait for user confirmation between commands

### `websocket_gcode_sender.py`
- Uses WebSocket connection to send G-code commands
- Has an interactive mode
- **Issue**: Doesn't specifically support reading from a file with line-by-line confirmation

### `bbctrl_gcode.py`
- Another implementation for sending G-code commands via the web interface
- Can read from a file
- **Issue**: Doesn't wait for user confirmation between commands

### `bbctrl_client.py`
- WebSocket client for connecting to the controller
- **Issue**: Doesn't have specific G-code sending functionality

## Improvements Made

The new `hybrid_gcode_sender.py` addresses all the issues found in the existing code:

1. **Reliability**: Uses direct API calls instead of browser automation
2. **Fallback**: WebSocket fallback if API fails
3. **User Control**: Line-by-line user confirmation as requested
4. **Real-time Feedback**: WebSocket state monitoring
5. **Error Handling**: Comprehensive error handling with retry options
6. **Simplicity**: Clean implementation with minimal dependencies
7. **Flexibility**: Multiple communication modes (API-only, WebSocket-only, or hybrid)

## API Endpoints Used

Based on the existing code analysis, the following API endpoints are used:

- `GET /api/gcode?{command}` - Send G-code commands
- `GET /api/state` - Get controller state
- `POST /api/auth/login` - Authentication (if required)

For WebSocket communication:
- `ws://{host}:{port}/sockjs/{server_id}/{session_id}/websocket` - WebSocket connection using SockJS protocol

## Dependencies

- `requests` - For HTTP API communication
- `websocket-client` - For WebSocket communication
- Standard Python libraries (json, threading, queue, etc.)

Optional dependencies for legacy tools:
- `beautifulsoup4` - For bbctrl_gcode.py
- `selenium` - For send_gcode_step.py
- `webdriver-manager` - For send_gcode_step.py

## Troubleshooting

1. **Connection Issues**
   - Ensure the controller is accessible at the specified host/port
   - Try using `--verbose` for detailed logging
   - Test with `--api-only` or `--ws-only` to isolate communication method issues

2. **Authentication Issues**
   - Provide `--username` and `--password` if the controller requires authentication
   - Check controller settings for authentication requirements

3. **G-code File Issues**
   - Ensure the file exists and is readable
   - Check that the file contains valid G-code commands
   - Use `--verbose` to see which commands are being parsed

4. **WebSocket Issues**
   - Some firewalls may block WebSocket connections
   - Try using `--api-only` if WebSocket connections fail

## Testing

To test the connection without sending a G-code file, you can create a simple test file:

```bash
echo "G28" > test.gcode
python hybrid_gcode_sender.py --file test.gcode
```

This will attempt to send a home command (G28) to test the connection.

## Future Enhancements

Potential improvements for future versions:

1. **Pause/Resume**: Add ability to pause and resume G-code execution
2. **Job Progress**: Display progress bar and estimated time remaining
3. **State Visualization**: Enhanced display of controller state and position
4. **Batch Mode**: Option to send multiple files in sequence
5. **Configuration File**: Support for configuration files to store connection settings
6. **GUI Version**: Graphical user interface for easier operation