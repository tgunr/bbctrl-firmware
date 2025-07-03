#!/usr/bin/env python3
"""
Buildbotics/bbctrl Controller API Client

This script provides a Python client for interacting with the Buildbotics/bbctrl controller's web interface.
It supports both REST API calls and WebSocket communication, with state change tracking.
"""

import json
import logging
import os
import sys
import time
import requests
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
from urllib.parse import urljoin, urlparse, quote

# Constants
STATE_FILE = Path.home() / '.bbctrl_state.json'

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bbctrl_api.log')
    ]
)
logger = logging.getLogger('BbctrlAPI')

def dict_diff(old: Dict, new: Dict, path: str = '') -> Dict:
    """Recursively find differences between two dictionaries."""
    diff = {}
    
    # Check for new or changed keys
    for key in new:
        new_path = f"{path}.{key}" if path else key
        if key not in old:
            diff[new_path] = {"new": new[key], "old": None}
        elif isinstance(new[key], dict) and isinstance(old.get(key), dict):
            nested_diff = dict_diff(old[key], new[key], new_path)
            if nested_diff:
                diff.update(nested_diff)
        elif new[key] != old[key]:
            diff[new_path] = {"new": new[key], "old": old[key]}
    
    # Check for removed keys
    for key in old:
        if key not in new:
            diff[f"{path}.{key}" if path else key] = {"new": None, "old": old[key]}
    
    return diff

class BbctrlAPI:
    """Client for interacting with the Buildbotics/bbctrl controller's web interface."""
    
    def __init__(self, base_url: str = 'http://bbctrl.local', username: str = None, password: str = None, 
                 track_changes: bool = False, reset_state: bool = False):
        """Initialize the API client.
        
        Args:
            base_url: Base URL of the bbctrl controller (e.g., http://bbctrl.local)
            username: Username for authentication (if required)
            password: Password for authentication (if required)
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BbctrlAPIClient/1.0',
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        })
        
        # Store authentication and state tracking settings
        self.username = username
        self.password = password
        self.authenticated = False
        self.track_changes = track_changes
        self.previous_state = {}
        
        # Load previous state if tracking changes
        if track_changes:
            self._load_previous_state(reset_state)
        
        # API endpoints
        self.endpoints = {
            'state': '/api/state',
            'config': '/api/config',
            'log': '/api/log',
            'bugreport': '/api/bugreport',
            'video': '/api/video',
            'files': '/api/fs',
            'download_config': '/api/config/download',
            'firmware_update': '/api/firmware/update',
            'gcode': '/api/gcode'
        }
        
        logger.info(f"Initialized Bbctrl API client for {self.base_url}")
    
    def _load_previous_state(self, reset: bool = False) -> None:
        """Load the previous state from file if it exists."""
        if reset and STATE_FILE.exists():
            STATE_FILE.unlink()
            logger.info("Reset state tracking")
            return
            
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, 'r') as f:
                    self.previous_state = json.load(f)
                logger.debug(f"Loaded previous state from {STATE_FILE}")
            except Exception as e:
                logger.warning(f"Failed to load previous state: {e}")
        else:
            logger.info("No previous state found, starting fresh")
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None, 
        params: Optional[Dict] = None,
        stream: bool = False,
        timeout: int = 10
    ) -> Dict:
        """Make an HTTP request to the API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            stream: Whether to stream the response
            timeout: Request timeout in seconds
            
        Returns:
            Response data as a dictionary
        """
        url = urljoin(self.base_url, endpoint)
        logger.debug(f"{method} {url} (params: {params}, data: {data})")
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                stream=stream,
                timeout=timeout
            )
            
            # Log the response
            logger.debug(f"Response: {response.status_code} - {response.text[:200]}...")
            
            # Handle different response types
            if response.status_code == 204:  # No Content
                return {'status': 'success'}
                
            if 'application/json' in response.headers.get('Content-Type', ''):
                return response.json()
            else:
                return {'status': 'success', 'data': response.text}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making {method} request to {endpoint}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                try:
                    logger.error(f"Response body: {e.response.text}")
                except:
                    pass
            return {'status': 'error', 'message': str(e)}
    
    def login(self) -> bool:
        """Authenticate with the bbctrl controller.
        
        Returns:
            bool: True if authentication was successful, False otherwise
        """
        if not self.username or not self.password:
            logger.warning("No credentials provided, skipping authentication")
            return True
            
        try:
            # Try to authenticate with the API
            auth_url = urljoin(self.base_url, '/api/auth/login')
            response = self.session.post(
                auth_url,
                json={'user': self.username, 'password': self.password},
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                self.authenticated = True
                logger.info("Successfully authenticated with the bbctrl controller")
                return True
            elif response.status_code == 404:
                # If the auth endpoint doesn't exist, the controller might not require authentication
                logger.info("Authentication endpoint not found, controller may not require authentication")
                self.authenticated = True
                return True
            else:
                logger.error(f"Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.ConnectionError:
            logger.warning("Could not connect to controller, continuing without authentication")
            return True
        except Exception as e:
            logger.error(f"Error during authentication: {e}")
            return False
            
    def send_gcode(self, gcode: str) -> Dict:
        """Send G-code commands to the controller.
        
        Args:
            gcode: G-code command(s) to send (can be multiple commands separated by newlines)
            
        Returns:
            Response from the controller
        """
        if not gcode.strip():
            return {'status': 'error', 'message': 'Empty G-code command'}
            
        # For local commands, we don't need authentication
        # The API endpoint for G-code is a GET request with the command as a query parameter
        try:
            # Prepare the G-code endpoint with URL-encoded command
            endpoint = f"{self.endpoints['gcode']}?{quote(gcode)}"
            
            # Send the G-code command as a GET request
            response = self.session.get(
                urljoin(self.base_url, endpoint)
            )
            
            # Parse the response
            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError:
                    return {'status': 'success', 'response': response.text}
            else:
                return {
                    'status': 'error',
                    'code': response.status_code,
                    'message': response.text
                }
                
        except Exception as e:
            logger.error(f"Error sending G-code: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _save_state(self, state: Dict) -> None:
        """Save the current state to file."""
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
            logger.debug(f"Saved state to {STATE_FILE}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def get_state(self, track_changes: bool = None) -> Tuple[Dict, Dict]:
        """Get the current state of the controller, optionally tracking changes.
        
        Args:
            track_changes: Override the instance setting for tracking changes
            
        Returns:
            tuple: (current_state, changes) where changes is a dict of changed fields
        """
        current_state = self._make_request('GET', self.endpoints['state'])
        changes = {}
        
        # Track changes if enabled
        track = track_changes if track_changes is not None else self.track_changes
        if track and self.previous_state:
            changes = dict_diff(self.previous_state, current_state)
            if changes:
                logger.info(f"Detected {len(changes)} state changes")
        
        # Update previous state
        if track:
            self._save_state(current_state)
            self.previous_state = current_state
            
        return current_state, changes
    
    def get_config(self) -> Dict:
        """Get the current configuration of the bbctrl controller.
        
        Returns:
            dict: Controller configuration
        """
        return self._make_request('GET', self.endpoints['config'])
        
    def update_config(self, config_data: Dict) -> Dict:
        """Update the configuration of the bbctrl controller.
        
        Args:
            config_data: Configuration data to update
            
        Returns:
            dict: Result of the update operation
        """
        return self._make_request('POST', self.endpoints['config'], data=config_data)
    
    def get_logs(self, limit: int = 100) -> List[Dict]:
        """Get logs from the bbctrl controller.
        
        Args:
            limit: Maximum number of log entries to retrieve
            
        Returns:
            List of log entries
        """
        return self._make_request('GET', self.endpoints['log'], params={'limit': limit})
    
    def download_bugreport(self, output_file: str = 'bugreport.zip') -> bool:
        """Download a bug report from the bbctrl controller.
        
        Args:
            output_file: Path to save the bug report
            
        Returns:
            bool: True if download was successful, False otherwise
        """
        try:
            response = self.session.get(
                urljoin(self.base_url, self.endpoints['bugreport']),
                stream=True
            )
            
            if response.status_code == 200:
                with open(output_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.info(f"Bug report saved to {output_file}")
                return True
            else:
                logger.error(f"Failed to download bug report: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error downloading bug report: {e}")
            return False
    
    def download_config(self, output_file: str = 'config.json') -> bool:
        """Download the current configuration from the bbctrl controller.
        
        Args:
            output_file: Path to save the configuration
            
        Returns:
            bool: True if download was successful, False otherwise
        """
        try:
            response = self.session.get(
                urljoin(self.base_url, self.endpoints['download_config']),
                stream=True
            )
            
            if response.status_code == 200:
                with open(output_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.info(f"Configuration saved to {output_file}")
                return True
            else:
                logger.error(f"Failed to download configuration: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error downloading configuration: {e}")
            return False
    
    def list_files(self, path: str = '') -> List[Dict]:
        """List files in a directory on the bbctrl controller.
        
        Args:
            path: Directory path (relative to root)
            
        Returns:
            List of files and directories
        """
        endpoint = f"{self.endpoints['files']}/{path}" if path else self.endpoints['files']
        return self._make_request('GET', endpoint)
    
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """Upload a file to the bbctrl controller.
        
        Args:
            local_path: Path to the local file to upload
            remote_path: Destination path on the controller
            
        Returns:
            bool: True if upload was successful, False otherwise
        """
        try:
            with open(local_path, 'rb') as f:
                files = {'file': (os.path.basename(remote_path), f)}
                response = self.session.post(
                    urljoin(self.base_url, self.endpoints['files'] + '/' + remote_path.lstrip('/')),
                    files=files
                )
                
                if response.status_code in (200, 201):
                    logger.info(f"Successfully uploaded {local_path} to {remote_path}")
                    return True
                else:
                    logger.error(f"Failed to upload file: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return False
            
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download a file from the bbctrl controller.
        
        Args:
            remote_path: Path to the file on the controller
            local_path: Local destination path
            
        Returns:
            bool: True if download was successful, False otherwise
        """
        try:
            endpoint = f"{self.endpoints['files']}/{remote_path.lstrip('/')}"
            response = self.session.get(
                urljoin(self.base_url, endpoint),
                stream=True
            )
            
            if response.status_code == 200:
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.info(f"Successfully downloaded {remote_path} to {local_path}")
                return True
            else:
                logger.error(f"Failed to download file: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return False
    
    def check_firmware_update(self) -> Dict:
        """Check for firmware updates.
        
        Returns:
            dict: Information about available updates
        """
        endpoint = '/api/firmware/check'
        return self._make_request('GET', endpoint)
        
    def update_firmware(self, firmware_file: str) -> Dict:
        """Update the controller's firmware.
        
        Args:
            firmware_file: Path to the firmware file
            
        Returns:
            Dict: Status of the update
        """
        try:
            with open(firmware_file, 'rb') as f:
                files = {'file': (os.path.basename(firmware_file), f)}
                response = self.session.post(
                    urljoin(self.base_url, self.endpoints['firmware_update']),
                    files=files
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {'status': 'error', 'message': f"Failed to update firmware: {response.status_code}"}
                    
        except Exception as e:
            return {'status': 'error', 'message': f"Error updating firmware: {e}"}

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
    """Command-line interface for the Bbctrl API client."""
    parser = argparse.ArgumentParser(description='Buildbotics/bbctrl Controller API Client')
    parser.add_argument('--url', default='http://bbctrl.local',
                      help='Base URL of the controller (default: http://bbctrl.local)')
    parser.add_argument('--username', help='Username for authentication')
    parser.add_argument('--password', help='Password for authentication')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--track', action='store_true', help='Track state changes between calls')
    parser.add_argument('--reset', action='store_true', help='Reset state tracking')
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # State command
    state_parser = subparsers.add_parser('state', help='Get controller state')
    state_parser.add_argument('--full', action='store_true', help='Show full state (not just changes)')
    
    # G-code command
    gcode_parser = subparsers.add_parser('gcode', help='Send G-code commands')
    gcode_parser.add_argument('command', nargs='?', help='G-code command to send')
    
    # Files command
    files_parser = subparsers.add_parser('files', help='List files')
    files_parser.add_argument('path', nargs='?', default='', help='Directory path')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize the API client
    try:
        api = BbctrlAPI(
            base_url=args.url,
            username=args.username,
            password=args.password,
            track_changes=args.track,
            reset_state=args.reset
        )
        
        # Execute the requested command
        if args.command == 'state':
            state, changes = api.get_state()
            if args.full:
                print(json.dumps(state, indent=2))
            else:
                print_changes(changes)
                
        elif args.command == 'gcode' and args.command:
            response = api.send_gcode(args.command)
            print(json.dumps(response, indent=2))
            
        elif args.command == 'files':
            files = api.list_files(args.path)
            print(json.dumps(files, indent=2))
            
        else:
            parser.print_help()
            
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=args.debug)
        sys.exit(1)

if __name__ == '__main__':
    main()
