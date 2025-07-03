#!/usr/bin/env python3

import subprocess
import time
import sys

def run_applescript(script):
    """Run AppleScript and return the result"""
    try:
        result = subprocess.run(['osascript', '-e', script], 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"AppleScript error: {e}")
        return None

def get_safari_url():
    """Get the URL of the frontmost Safari tab"""
    script = '''
    tell application "Safari"
        if (count of windows) > 0 then
            return URL of current tab of front window
        else
            return "No Safari windows open"
        end if
    end tell
    '''
    return run_applescript(script)

def click_mdi_tab():
    """Click the MDI tab in the Buildbotics interface"""
    script = '''
    tell application "Safari"
        if (count of windows) > 0 then
            do JavaScript "
                // Find and click the MDI tab
                let mdiTab = document.querySelector('input[type=\"radio\"][name=\"tabs\"]#tab2');
                if (mdiTab) {
                    mdiTab.click();
                    console.log('MDI tab clicked');
                    return 'MDI tab activated';
                } else {
                    return 'MDI tab not found';
                }
            " in current tab of front window
        else
            return "No Safari windows open"
        end if
    end tell
    '''
    return run_applescript(script)

def send_gcode_command(gcode):
    """Send a G-code command via the MDI interface"""
    # Escape quotes and special characters for AppleScript
    escaped_gcode = gcode.replace('"', '\\"').replace("'", "\\'")
    
    script = f'''
    tell application "Safari"
        if (count of windows) > 0 then
            do JavaScript "
                // Find the Vue app instance
                let controlElement = document.querySelector('#control');
                if (controlElement && controlElement.__vue__) {{
                    let vue = controlElement.__vue__;
                    
                    // Set the MDI input value
                    vue.mdi = '{escaped_gcode}';
                    
                    // Submit the command
                    vue.submit_mdi();
                    
                    console.log('G-code sent:', '{escaped_gcode}');
                    return 'G-code sent: {escaped_gcode}';
                }} else {{
                    return 'Vue app not found';
                }}
            " in current tab of front window
        else
            return "No Safari windows open"
        end if
    end tell
    '''
    return run_applescript(script)

def check_machine_state():
    """Check the current machine state"""
    script = '''
    tell application "Safari"
        if (count of windows) > 0 then
            do JavaScript "
                let controlElement = document.querySelector('#control');
                if (controlElement && controlElement.__vue__) {
                    let vue = controlElement.__vue__;
                    return JSON.stringify({
                        state: vue.mach_state,
                        can_mdi: vue.can_mdi,
                        cycle: vue.state.cycle,
                        xx: vue.state.xx
                    });
                } else {
                    return 'Vue app not found';
                }
            " in current tab of front window
        else
            return "No Safari windows open"
        end if
    end tell
    '''
    return run_applescript(script)

def wait_for_ready(timeout=10):
    """Wait for machine to be ready for next command"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        state = check_machine_state()
        if state and 'can_mdi' in state and '"can_mdi":true' in state:
            return True
        time.sleep(0.5)
    return False

def send_gcode_sequence(commands, delay=1.0):
    """Send a sequence of G-code commands with delays"""
    print("=== Buildbotics G-code MDI Sender ===")
    
    # Check if Safari is open to bbctrl
    url = get_safari_url()
    print(f"Current Safari URL: {url}")
    
    if not url or 'bbctrl' not in url.lower():
        print("ERROR: Safari is not open to bbctrl.local")
        print("Please open Safari and navigate to your Buildbotics controller")
        return False
    
    # Switch to MDI tab
    print("\n1. Switching to MDI tab...")
    result = click_mdi_tab()
    print(f"Result: {result}")
    time.sleep(1)
    
    # Check initial state
    print("\n2. Checking machine state...")
    state = check_machine_state()
    print(f"State: {state}")
    
    # Send commands
    print(f"\n3. Sending {len(commands)} G-code commands...")
    for i, cmd in enumerate(commands, 1):
        print(f"\n--- Command {i}/{len(commands)}: {cmd} ---")
        
        # Wait for machine to be ready
        if not wait_for_ready():
            print("WARNING: Machine not ready, sending anyway...")
        
        # Send command
        result = send_gcode_command(cmd)
        print(f"Result: {result}")
        
        # Wait between commands
        if i < len(commands):
            print(f"Waiting {delay} seconds...")
            time.sleep(delay)
    
    print("\n=== G-code sequence complete ===")
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 send_gcode_mdi.py 'G90'")
        print("  python3 send_gcode_mdi.py 'G90' 'G0 X10 Y10' 'M3 S1000'")
        print("  python3 send_gcode_mdi.py --file gcode_file.nc")
        return
    
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
    
    send_gcode_sequence(commands)

if __name__ == "__main__":
    main()