#!/usr/bin/env python3
"""
Buildbotics/bbctrl Controller CLI

A command-line interface for interacting with the Buildbotics/bbctrl controller's web API.
"""

import argparse
import json
import os
import sys
from typing import Dict, List, Optional, Any

from bbctrl_api_client import BbctrlAPI

def print_json(data: Any, pretty: bool = True) -> None:
    """Print data as formatted JSON."""
    if pretty:
        print(json.dumps(data, indent=2, default=str))
    else:
        print(json.dumps(data, default=str))

def print_changes(changes: Dict, prefix: str = '') -> None:
    """Print state changes in a readable format."""
    if not changes:
        print("No changes detected")
        return
        
    for key, value in changes.items():
        if isinstance(value, dict) and 'new' in value and 'old' in value:
            print(f"{prefix}{key}: {value['old']} -> {value['new']}")
        else:
            print(f"{prefix}{key}: {value}")

def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description='bbctrl Controller CLI')
    parser.add_argument('--url', default='http://bbctrl.local',
                       help='Base URL of the bbctrl controller')
    parser.add_argument('--username', help='Username for authentication')
    parser.add_argument('--password', help='Password for authentication')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--output', choices=['json', 'pretty'], default='pretty',
                       help='Output format')
    parser.add_argument('--track', action='store_true', help='Track state changes between calls')
    parser.add_argument('--reset', action='store_true', help='Reset state tracking')
    parser.add_argument('--full', action='store_true', help='Show full state (not just changes)')
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # State command
    state_parser = subparsers.add_parser('state', help='Get controller state')
    state_parser.add_argument('--full', action='store_true', help='Show full state (not just changes)')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Get or update controller config')
    config_parser.add_argument('--get', action='store_true', help='Get current config')
    config_parser.add_argument('--download', metavar='FILE', help='Download config to file')
    
    # Logs command
    logs_parser = subparsers.add_parser('logs', help='Get controller logs')
    logs_parser.add_argument('--limit', type=int, default=100, help='Maximum number of log entries to retrieve')
    
    # Files command
    files_parser = subparsers.add_parser('files', help='Manage files on the controller')
    files_subparsers = files_parser.add_subparsers(dest='files_command', help='Files subcommand')
    
    # List files
    list_parser = files_subparsers.add_parser('list', help='List files')
    list_parser.add_argument('path', nargs='?', default='', help='Directory path')
    
    # Upload file
    upload_parser = files_subparsers.add_parser('upload', help='Upload a file')
    upload_parser.add_argument('local_path', help='Local file path')
    upload_parser.add_argument('remote_path', help='Destination path on the controller')
    
    # Download file
    download_parser = files_subparsers.add_parser('download', help='Download a file')
    download_parser.add_argument('remote_path', help='File path on the controller')
    download_parser.add_argument('local_path', help='Local destination path')
    
    # G-code command
    gcode_parser = subparsers.add_parser('gcode', help='Send G-code commands')
    gcode_parser.add_argument('command', nargs='?', help='G-code command to send')
    gcode_parser.add_argument('--file', help='File containing G-code commands')
    
    # Bug report command
    bugreport_parser = subparsers.add_parser('bugreport', help='Download bug report')
    bugreport_parser.add_argument('--output', default='bugreport.zip', help='Output file path')
    
    # Firmware command
    firmware_parser = subparsers.add_parser('firmware', help='Firmware operations')
    firmware_subparsers = firmware_parser.add_subparsers(dest='firmware_command', help='Firmware subcommand')
    
    # Check for updates
    firmware_check_parser = firmware_subparsers.add_parser('check', help='Check for firmware updates')
    
    # Update firmware
    firmware_update_parser = firmware_subparsers.add_parser('update', help='Update firmware')
    firmware_update_parser.add_argument('firmware_file', help='Path to firmware file')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Set up logging
    import logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Initialize the API client
        api = BbctrlAPI(
            base_url=args.url,
            username=args.username,
            password=args.password,
            track_changes=args.track,
            reset_state=args.reset
        )
        
        # Authenticate if credentials are provided
        if args.username and args.password:
            if not api.login():
                print("Authentication failed", file=sys.stderr)
                sys.exit(1)
        
        # Execute the requested command
        if args.command == 'state':
            state, changes = api.get_state()
            # Show full state if --full is specified or if --reset was used
            if args.full or args.reset:
                print_json(state, args.output == 'pretty')
            else:
                print_changes(changes)
            
        elif args.command == 'config':
            if args.download:
                if api.download_config(args.download):
                    print(f"Configuration saved to {args.download}")
                else:
                    print("Failed to download configuration", file=sys.stderr)
                    sys.exit(1)
            else:
                config = api.get_config()
                print_json(config, args.output == 'pretty')
                
        elif args.command == 'logs':
            logs = api.get_logs(limit=args.limit)
            print_json(logs, args.output == 'pretty')
            
        elif args.command == 'files':
            if args.files_command == 'list':
                files = api.list_files(args.path)
                print_json(files, args.output == 'pretty')
                
            elif args.files_command == 'upload':
                if api.upload_file(args.local_path, args.remote_path):
                    print(f"Successfully uploaded {args.local_path} to {args.remote_path}")
                else:
                    print(f"Failed to upload {args.local_path}", file=sys.stderr)
                    sys.exit(1)
                    
            elif args.files_command == 'download':
                # This would require implementing download_file in the API client
                print("Download not yet implemented", file=sys.stderr)
                sys.exit(1)
                
        elif args.command == 'gcode':
            if args.file:
                with open(args.file, 'r') as f:
                    gcode = f.read().strip()
            elif args.gcode:
                gcode = args.gcode
            else:
                print("No G-code command or file provided", file=sys.stderr)
                sys.exit(1)
                
            # Split multiple G-code commands by semicolon and send each one
            for cmd in gcode.split(';'):
                cmd = cmd.strip()
                if cmd:  # Skip empty commands
                    print(f"Sending: {cmd}")
                    response = api.send_gcode(cmd)
                    if args.output == 'pretty':
                        print(f"Response for '{cmd}': {response}")
                    else:
                        print_json(response, False)
            
        elif args.command == 'bugreport':
            if api.download_bugreport(args.output):
                print(f"Bug report saved to {args.output}")
            else:
                print("Failed to download bug report", file=sys.stderr)
                sys.exit(1)
                
        elif args.command == 'firmware':
            if args.firmware_command == 'check':
                update_info = api.check_firmware_update()
                print_json(update_info, args.output == 'pretty')
                
            elif args.firmware_command == 'update':
                if not os.path.isfile(args.firmware_file):
                    print(f"Firmware file not found: {args.firmware_file}", file=sys.stderr)
                    sys.exit(1)
                    
                result = api.update_firmware(args.firmware_file)
                print_json(result, args.output == 'pretty')
                
        else:
            parser.print_help()
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

# ... [rest of the class definition] ...

# This should be at module level, not indented
if __name__ == "__main__":
    main()
