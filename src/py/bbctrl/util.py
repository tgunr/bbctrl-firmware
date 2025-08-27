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

from datetime import datetime
import pkg_resources
from pkg_resources import Requirement, resource_filename
import socket
from .version import Version, parse_version as semver_parse, compare_versions


_version = pkg_resources.require('bbctrl')[0].version

try:
    with open('/sys/firmware/devicetree/base/model', 'r') as f:
        _model = f.read().strip('\0')
except: _model = 'unknown'


# 16-bit less with wrap around
def id16_less(a, b): return (1 << 15) < (a - b) & ((1 << 16) - 1)


def get_resource(path):
    return resource_filename(Requirement.parse('bbctrl'), 'bbctrl/' + path)


def get_version(): return _version
def get_model(): return _model

# Legacy version parsing for backward compatibility
def parse_version(s):
    """
    Parse version string. Supports both legacy tuple format and new SemVer format.

    For backward compatibility, returns tuple for simple versions,
    but uses Version object for SemVer format.
    """
    try:
        # Try to parse as SemVer first
        return semver_parse(s)
    except ValueError:
        try:
            # Handle PEP 440 format that might have been converted from SemVer
            # e.g., "2.1.0.dev2" -> convert to "2.1.0-dev.2" for SemVer parsing
            if '.dev' in s or '.alpha' in s or '.beta' in s or '.rc' in s:
                # Convert PEP 440 prerelease format to SemVer format
                parts = s.split('.')
                if len(parts) >= 4:
                    # Find the prerelease part
                    for i, part in enumerate(parts):
                        if part in ['dev', 'alpha', 'beta', 'rc']:
                            if i + 1 < len(parts):
                                # Convert "2.1.0.dev2" to "2.1.0-dev.2"
                                prerelease_type = parts[i]  # 'dev', 'alpha', 'beta', 'rc'
                                prerelease_num = parts[i + 1]  # '2'
                                # Build SemVer string: "2.1.0-dev.2"
                                semver_str = '.'.join(parts[:3]) + '-' + prerelease_type + '.' + prerelease_num
                                try:
                                    return semver_parse(semver_str)
                                except ValueError:
                                    pass
                            break

            # Fall back to legacy tuple parsing - only for clean numeric versions
            # Filter out any non-numeric parts to avoid ValueError
            numeric_parts = []
            for part in s.split('.'):
                try:
                    numeric_parts.append(int(part))
                except ValueError:
                    # Stop at first non-numeric part (like 'dev2')
                    break
            if numeric_parts:
                # Try to create a Version object from the numeric parts
                try:
                    version_str = '.'.join(map(str, numeric_parts))
                    return semver_parse(version_str)
                except ValueError:
                    # If Version object creation fails, return tuple as last resort
                    return tuple(numeric_parts)
            else:
                raise ValueError(f"Unable to parse version: {s}")
        except (ValueError, IndexError):
            # If all parsing fails, try one more time with numeric-only parts
            numeric_parts = []
            for part in s.split('.'):
                try:
                    numeric_parts.append(int(part))
                except ValueError:
                    break
            if numeric_parts:
                # Try to create a Version object from the numeric parts
                try:
                    version_str = '.'.join(map(str, numeric_parts))
                    return semver_parse(version_str)
                except ValueError:
                    # If Version object creation fails, return tuple as last resort
                    return tuple(numeric_parts)
            else:
                raise ValueError(f"Unable to parse version: {s}")

def version_less(a, b):
    """
    Compare two version strings.

    Supports both legacy tuple comparison and new SemVer comparison.
    """
    try:
        # Try SemVer comparison first
        return compare_versions(a, b) < 0
    except ValueError:
        # Fall back to legacy comparison
        return parse_version(a) < parse_version(b)
def timestamp(): return datetime.now().strftime('%Y%m%d-%H%M%S')


def get_config_filename():
  return socket.gethostname() + datetime.now().strftime('-%Y%m%d-%H%M%S.json')


def timestamp_to_iso8601(ts):
  return datetime.fromtimestamp(ts).replace(microsecond = 0).isoformat() + 'Z'
