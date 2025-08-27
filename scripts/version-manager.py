#!/usr/bin/env python3
################################################################################
#                                                                              #
#                 This file is part of the Buildbotics firmware.               #
#                                                                              #
#        Copyright (c) 2015 - 2023, Buildbotics LLC, All rights reserved.      #
#                                                                              #
#         This Source describes Open Hardware and is licensed under the        #
#                                 CERN-OHL-S v2.                               #
#                                                                              #
#         You may redistribute and modify this Source and make products        #
#    using it under the terms of the CERN-OHL-S v2 (https:/cern.ch/cern-ohl).  #
#           This Source is distributed WITHOUT ANY EXPRESS OR IMPLIED          #
#    WARRANTY, INCLUDING OF MERCHANTABILITY, SATISFACTORY QUALITY AND FITNESS  #
#     FOR A PARTICULAR PURPOSE. Please see the CERN-OHL-S v2 for applicable    #
#                                  conditions.                                 #
#                                                                              #
#                Source location: https://github.com/buildbotics               #
#                                                                              #
#      As per CERN-OHL-S v2 section 4, should You produce hardware based on    #
#    these sources, You must maintain the Source Location clearly visible on   #
#    the external case of the CNC Controller or other product you make using   #
#                                  this Source.                                #
#                                                                              #
#                For more information, email info@buildbotics.com              #
#                                                                              #
################################################################################

"""
Version Management Utility for Buildbotics CNC Controller

This script helps manage semantic versioning with pre-release support.
It provides commands to bump versions, validate version strings, and
manage the development workflow.

Usage:
    python version-manager.py <command> [options]

Commands:
    bump <type>         Bump version (major, minor, patch, prerelease)
    next-stage          Move to next development stage
    validate <version>  Validate version string
    current             Show current version
    set <version>       Set specific version
    info <version>      Show version information
"""

import sys
import os
import json
import re
import argparse
from pathlib import Path


# Add src/py to path to import version module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'py'))

try:
    from bbctrl.version import Version, parse_version
except ImportError:
    print("Error: Cannot import version module. Make sure you're running from the project root.")
    sys.exit(1)


class VersionManager:
    """Manages version information across project files."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.package_json = self.project_root / 'package.json'
        self.pkg_info = self.project_root / 'src' / 'py' / 'bbctrl.egg-info' / 'PKG-INFO'

    def get_current_version(self):
        """Get current version from package.json."""
        if not self.package_json.exists():
            raise FileNotFoundError("package.json not found")

        with open(self.package_json, 'r') as f:
            data = json.load(f)
            return data.get('version', '0.0.0')

    def set_version(self, version_string):
        """Set version in all relevant files."""
        version = Version(version_string)

        # Update package.json
        if self.package_json.exists():
            with open(self.package_json, 'r') as f:
                data = json.load(f)

            data['version'] = str(version)

            with open(self.package_json, 'w') as f:
                json.dump(data, f, indent=2)

            print(f"Updated {self.package_json} to {version}")

        # Update PKG-INFO
        if self.pkg_info.exists():
            with open(self.pkg_info, 'r') as f:
                content = f.read()

            # Replace version line
            pattern = r'^Version: .*$'
            new_content = re.sub(pattern, f'Version: {version}', content, flags=re.MULTILINE)

            with open(self.pkg_info, 'w') as f:
                f.write(new_content)

            print(f"Updated {self.pkg_info} to {version}")

    def bump_version(self, bump_type):
        """Bump version according to type."""
        current = self.get_current_version()
        version = Version(current)

        if bump_type == 'major':
            new_version = version.bump_major()
        elif bump_type == 'minor':
            new_version = version.bump_minor()
        elif bump_type == 'patch':
            new_version = version.bump_patch()
        elif bump_type == 'prerelease':
            new_version = version.bump_prerelease()
        else:
            raise ValueError(f"Unknown bump type: {bump_type}")

        self.set_version(str(new_version))
        print(f"Bumped {bump_type}: {current} → {new_version}")

    def next_stage(self):
        """Move to next development stage."""
        current = self.get_current_version()
        version = Version(current)
        new_version = version.next_stage()

        self.set_version(str(new_version))
        print(f"Advanced to next stage: {current} → {new_version}")
        print(f"New stage: {new_version.get_stage()}")

    def validate_version(self, version_string):
        """Validate version string."""
        try:
            version = Version(version_string)
            print(f"✓ Valid version: {version}")
            print(f"  Stage: {version.get_stage()}")
            print(f"  Is prerelease: {version.is_prerelease()}")
            if version.build:
                print(f"  Build metadata: {version.build}")
            return True
        except ValueError as e:
            print(f"✗ Invalid version: {e}")
            return False

    def show_info(self, version_string=None):
        """Show version information."""
        if version_string:
            version = Version(version_string)
        else:
            version = Version(self.get_current_version())

        print(f"Version: {version}")
        print(f"Stage: {version.get_stage()}")
        print(f"Is prerelease: {version.is_prerelease()}")
        print(f"Major: {version.major}")
        print(f"Minor: {version.minor}")
        print(f"Patch: {version.patch}")

        if version.prerelease:
            print(f"Prerelease: {version.prerelease}")
        if version.build:
            print(f"Build: {version.build}")

    def show_current(self):
        """Show current version."""
        try:
            version = self.get_current_version()
            print(f"Current version: {version}")
        except Exception as e:
            print(f"Error getting current version: {e}")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Version Management Utility for Buildbotics CNC Controller',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python version-manager.py current                    # Show current version
  python version-manager.py bump minor                 # Bump minor version
  python version-manager.py next-stage                 # Move to next stage
  python version-manager.py validate "2.2.0-dev.1"     # Validate version
  python version-manager.py set "2.2.0-alpha.1"        # Set specific version
  python version-manager.py info                       # Show current version info
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # bump command
    bump_parser = subparsers.add_parser('bump', help='Bump version')
    bump_parser.add_argument('type', choices=['major', 'minor', 'patch', 'prerelease'],
                           help='Type of version bump')

    # next-stage command
    subparsers.add_parser('next-stage', help='Move to next development stage')

    # validate command
    validate_parser = subparsers.add_parser('validate', help='Validate version string')
    validate_parser.add_argument('version', help='Version string to validate')

    # current command
    subparsers.add_parser('current', help='Show current version')

    # set command
    set_parser = subparsers.add_parser('set', help='Set specific version')
    set_parser.add_argument('version', help='Version string to set')

    # info command
    info_parser = subparsers.add_parser('info', help='Show version information')
    info_parser.add_argument('version', nargs='?', help='Version string (default: current)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        manager = VersionManager()

        if args.command == 'bump':
            manager.bump_version(args.type)
        elif args.command == 'next-stage':
            manager.next_stage()
        elif args.command == 'validate':
            success = manager.validate_version(args.version)
            sys.exit(0 if success else 1)
        elif args.command == 'current':
            manager.show_current()
        elif args.command == 'set':
            manager.set_version(args.version)
            print(f"Set version to: {args.version}")
        elif args.command == 'info':
            manager.show_info(args.version)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()