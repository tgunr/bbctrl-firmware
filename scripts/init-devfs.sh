#!/bin/bash

export LC_ALL=C
export DEBIAN_FRONTEND=noninteractive

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "ERROR: This script must be run as root to install packages."
  echo "Please run with: sudo $0"
  exit 1
fi

# Install packages
apt-get install -yq git build-essential libx11-dev libxft-dev libxtst-dev \
  libxinerama-dev libxcursor-dev libfontconfig-dev libssl-dev libnode-dev scons

# If main installation failed, try installing scons separately
if ! command -v scons >/dev/null 2>&1; then
    echo "Installing scons separately..."
    apt-get install -yq scons
fi

if [ -e /proc/cpuinfo ]; then
  CPUS=$(grep -c ^processor /proc/cpuinfo)
else
  CPUS=24
fi

export CBANG_HOME=$PWD/cbang

PROJECTS="buildbotics/updiprog buildbotics/rpipdi buildbotics/bbkbd "
PROJECTS+="cauldrondevelopmentllc/cbang cauldrondevelopmentllc/camotics"

for PROJECT in $PROJECTS; do
  NAME=$(basename $PROJECT)
  if [ ! -e $NAME ]; then
    git clone https://github.com/$PROJECT
  else
    git -C $NAME fetch
    git -C $NAME reset --hard origin/master
  fi

  if [ $NAME == cbang ]; then
    scons -C cbang -j$CPUS v8_compress_pointers=0

  elif [ $NAME == camotics ]; then
    scons -C camotics -j$CPUS build/camotics.so with_gui=0 wrap_glibc=0 with_tpl=0
  else
    make -C $NAME -j$CPUS
  fi
done
