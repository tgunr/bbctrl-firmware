#!/usr/bin/env python3

from setuptools import setup
import json
import os

pkg = json.load(open('package.json', 'r'))

# Check for environment variable first (set by Makefile)
version = os.environ.get('BBCTRL_VERSION')
if version:
    print(f"Using Makefile version: {version}")
else:
    # Fall back to package.json version
    version = pkg['version']
    print(f"Using package.json version: {version}")

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
  data_files = [
    ('', ['.dev-version']),
  ],
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
