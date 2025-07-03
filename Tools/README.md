# Buildbotics CNC Controller Tools

This directory contains diagnostic and control tools for the Buildbotics CNC Controller.

## Setup

1. Create a virtual environment:
```bash
cd Tools
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## G-code Command Tools

### send_gcode_direct.py ✅ WORKING
**Direct WebSocket G-code sender - RECOMMENDED**

Send G-code commands directly via WebSocket connection:

```bash
# Single command
python3 send_gcode_direct.py 'G90'

# Multiple commands in sequence
python3 send_gcode_direct.py 'G90' 'G21' 'G0 X10 Y10' 'G1 X20 Y20 F100'

# From a file
python3 send_gcode_direct.py --file my_program.nc
```

**Features:**
- ✅ Direct WebSocket connection to controller
- ✅ Checks machine state before sending
- ✅ Sends commands with configurable delays
- ✅ Real-time feedback and status updates
- ✅ Handles command sequences reliably

### send_gcode_mdi.py ⚠️ EXPERIMENTAL
**Safari-based MDI interface automation**

Attempts to automate the web interface MDI tab via AppleScript:

```bash
python3 send_gcode_mdi.py 'G90'
```

**Note:** This tool has AppleScript compatibility issues and is not recommended for production use.

## Diagnostic Tools

### diagnose_fs_error.sh
**Comprehensive filesystem API diagnostics**

```bash
chmod +x diagnose_fs_error.sh
./diagnose_fs_error.sh
```

### check_filesystem_state.sh
**Filesystem state verification**

```bash
chmod +x check_filesystem_state.sh
./check_filesystem_state.sh
```

### ssh_commands.txt
**Manual SSH diagnostic commands**

Copy and paste commands from this file into your SSH session for manual diagnostics.

### test_bbctrl_safari.py
**Safari web interface automation**

```bash
python3 test_bbctrl_safari.py
```

## Usage Examples

### Basic G-code Sequence
```bash
python3 send_gcode_direct.py 'G90' 'G21' 'G28' 'G0 X0 Y0 Z5'
```

### Spindle Control
```bash
python3 send_gcode_direct.py 'M3 S1000' 'G4 P2' 'M5'
```

### Coordinate System Setup
```bash
python3 send_gcode_direct.py 'G90' 'G21' 'G54' 'G0 X0 Y0'
```

## Troubleshooting

### Connection Issues
1. Ensure controller is accessible at `bbctrl.local`
2. Check that the web interface loads in Safari
3. Verify machine is in READY state

### WebSocket Errors
- The controller uses port 80 (not 8080)
- WebSocket endpoint is `/websocket`
- Connection requires the machine to be idle

### Command Failures
- Check machine state with diagnostic tools
- Ensure proper G-code syntax
- Verify axes are homed if required

## Controller Status

The tools automatically check:
- Machine state (READY, RUNNING, HOLDING, etc.)
- Current cycle (idle, mdi, etc.)
- Connection status
- API endpoint availability

## Development Notes

- The `/api/fs/` filesystem endpoint is working correctly
- WebSocket connection uses the same protocol as the web interface
- Commands are sent exactly as they would be through the MDI interface
- All tools respect the controller's safety interlocks