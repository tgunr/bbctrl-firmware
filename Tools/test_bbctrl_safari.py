#!/usr/bin/env python3

import subprocess
import json
import time

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

def execute_javascript_in_safari(js_code):
    """Execute JavaScript in the frontmost Safari tab"""
    # Escape quotes in JavaScript code
    escaped_js = js_code.replace('"', '\\"').replace('\n', '\\n')
    
    script = f'''
    tell application "Safari"
        if (count of windows) > 0 then
            return do JavaScript "{escaped_js}" in current tab of front window
        else
            return "No Safari windows open"
        end if
    end tell
    '''
    return run_applescript(script)

def test_api_endpoint():
    """Test the /api/fs/ endpoint via Safari's JavaScript console"""
    js_code = '''
    fetch('/api/fs/')
      .then(response => response.json())
      .then(data => {
        console.log('API Response:', data);
        return JSON.stringify(data, null, 2);
      })
      .catch(error => {
        console.error('API Error:', error);
        return 'Error: ' + error.message;
      });
    '''
    
    print("Testing /api/fs/ endpoint via Safari...")
    result = execute_javascript_in_safari(js_code)
    print("Result:", result)
    return result

def send_gcode_command(gcode):
    """Send a G-code command via the web interface"""
    js_code = f'''
    // Send G-code command via the web interface
    if (typeof app !== 'undefined' && app.$api) {{
        app.$api.post('', '{gcode}')
          .then(response => {{
            console.log('G-code sent:', '{gcode}');
            return 'G-code sent successfully: {gcode}';
          }})
          .catch(error => {{
            console.error('G-code error:', error);
            return 'Error sending G-code: ' + error.message;
          }});
    }} else {{
        return 'Web app not available';
    }}
    '''
    
    print(f"Sending G-code: {gcode}")
    result = execute_javascript_in_safari(js_code)
    print("Result:", result)
    return result

def main():
    print("=== Buildbotics Controller Safari Interface Test ===")
    
    # Check if Safari is open to bbctrl.local
    url = get_safari_url()
    print(f"Current Safari URL: {url}")
    
    if not url or 'bbctrl' not in url.lower():
        print("ERROR: Safari is not open to bbctrl.local")
        print("Please open Safari and navigate to your Buildbotics controller")
        return
    
    print("\n1. Testing API filesystem endpoint...")
    test_api_endpoint()
    
    print("\n2. Testing G-code commands...")
    # Send some basic G-code commands
    commands = [
        "G90",  # Absolute positioning
        "M3 S1000",  # Start spindle at 1000 RPM
        "G0 X10 Y10",  # Rapid move
        "M5",  # Stop spindle
    ]
    
    for cmd in commands:
        send_gcode_command(cmd)
        time.sleep(1)  # Wait between commands
    
    print("\n=== Test complete ===")

if __name__ == "__main__":
    main()