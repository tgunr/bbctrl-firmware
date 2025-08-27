#!/usr/bin/env python3

from setuptools import setup
import json
import os

pkg = json.load(open('package.json', 'r'))

# Check for build info and enhance version
version = pkg['version']
if os.path.exists('.build-info.json'):
    try:
        with open('.build-info.json', 'r') as f:
            build_info = json.load(f)
            commit = build_info.get('commit', '')
            build_time = build_info.get('build_time', '')
            if commit and build_time:
                version = f"{version}+build.{commit}.{build_time}"
                print(f"Using build info in version: {version}")
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Warning: Could not read build info: {e}")

setup(
  name = pkg['name'],
  version = version,
  description = 'Buildbotics Machine Controller',
  long_description = open('README.md', 'rt').read(),
  author = 'Joseph Coffland',
  author_email = 'joseph@buildbotics.org',
  platforms = ['any'],
  license = pkg['license'],
  url = pkg['homepage'],
  package_dir = {'': 'src/py'},
  packages = ['bbctrl', 'inevent', 'lcd', 'udevevent'],
  include_package_data = True,
  entry_points = {
    'console_scripts': [
      'bbctrl = bbctrl:run'
    ]
  },
  scripts = [
    'scripts/update-bbctrl',
    'scripts/upgrade-bbctrl',
    'scripts/sethostname',
    'scripts/config-wifi',
    'scripts/run-browser',
    'scripts/mount-usb',
    'scripts/eject-usb',
    'scripts/update-bb-firmware',
  ],
  install_requires = 'tornado sockjs-tornado pyserial pyudev smbus2'.split(),
  zip_safe = False,
)
