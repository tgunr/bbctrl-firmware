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

<<<<<<< HEAD
This script helps manage PEP 440 versioning with pre-release support.
=======
This script helps manage semantic versioning with pre-release support.
>>>>>>> c6a0e630340ffc26531cb57095df7ec9284c1903
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
<<<<<<< HEAD
    """Manages PEP 440 version information across project files."""
=======
    """Manages version information across project files."""
>>>>>>> c6a0e630340ffc26531cb57095df7ec9284c1903

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
            version_str = data.get('version', '0.0.0')

        # Strip build metadata for version management purposes
        # This allows us to work with the base version for comparisons
        try:
            version = Version(version_str)
            if version.build:
                # Remove build metadata for version management
                base_version = f"{version.major}.{version.minor}.{version.patch}"
                if version.prerelease:
                    base_version += f"-{version.prerelease}"
                return base_version
            return version_str
        except ValueError:
            # If parsing fails, return as-is
            return version_str

    def get_current_commit(self):
        """Get current git commit hash (short)."""
        try:
            import subprocess
            result = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'],
                                  capture_output=True, text=True, cwd=self.project_root)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def set_version(self, version_string, include_commit=True):
        """Set version in all relevant files."""
        # Create base version first
        base_version = Version(version_string)

        # Add commit hash to build metadata if requested
        if include_commit:
            commit = self.get_current_commit()
            if commit:
                try:
                    version = base_version.with_build(f"build.{commit}")
                except Exception as e:
                    print(f"Warning: Could not add build metadata: {e}")
                    version = base_version
            else:
                version = base_version
        else:
            version = base_version

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

    def bump_version(self, bump_type, include_commit=True):
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

        self.set_version(str(new_version), include_commit)
        print(f"Bumped {bump_type}: {current} → {new_version}")

    def next_stage(self, include_commit=True):
        """Move to next development stage."""
        current = self.get_current_version()
        version = Version(current)
        new_version = version.next_stage()

        self.set_version(str(new_version), include_commit)
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
<<<<<<< HEAD
        description='PEP 440 Version Management Utility for Buildbotics CNC Controller',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
   python version-manager.py current                    # Show current version
   python version-manager.py bump minor                 # Bump minor version
   python version-manager.py next-stage                 # Move to next stage
   python version-manager.py validate "2.2.0.dev1"      # Validate version
   python version-manager.py set "2.2.0a1"              # Set specific version
   python version-manager.py info                       # Show current version info
=======
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
>>>>>>> c6a0e630340ffc26531cb57095df7ec9284c1903
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # bump command
    bump_parser = subparsers.add_parser('bump', help='Bump version')
    bump_parser.add_argument('type', choices=['major', 'minor', 'patch', 'prerelease'],
                           help='Type of version bump')
    bump_parser.add_argument('--no-commit', action='store_true',
                           help='Do not include git commit hash in build metadata')

    # next-stage command
    next_stage_parser = subparsers.add_parser('next-stage', help='Move to next development stage')
    next_stage_parser.add_argument('--no-commit', action='store_true',
                                 help='Do not include git commit hash in build metadata')

    # validate command
    validate_parser = subparsers.add_parser('validate', help='Validate version string')
    validate_parser.add_argument('version', help='Version string to validate')

    # current command
    subparsers.add_parser('current', help='Show current version')

    # set command
    set_parser = subparsers.add_parser('set', help='Set specific version')
    set_parser.add_argument('version', help='Version string to set')
    set_parser.add_argument('--no-commit', action='store_true',
                           help='Do not include git commit hash in build metadata')

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
            include_commit = not getattr(args, 'no_commit', False)
            manager.bump_version(args.type, include_commit)
        elif args.command == 'next-stage':
            include_commit = not getattr(args, 'no_commit', False)
            manager.next_stage(include_commit)
        elif args.command == 'validate':
            success = manager.validate_version(args.version)
            sys.exit(0 if success else 1)
        elif args.command == 'current':
            manager.show_current()
        elif args.command == 'set':
            include_commit = not getattr(args, 'no_commit', False)
            manager.set_version(args.version, include_commit)
            print(f"Set version to: {args.version}")
        elif args.command == 'info':
            manager.show_info(args.version)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()