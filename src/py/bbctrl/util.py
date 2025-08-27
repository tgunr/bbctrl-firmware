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
        # Fall back to legacy tuple parsing
        return tuple([int(x) for x in s.split('.')])

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
