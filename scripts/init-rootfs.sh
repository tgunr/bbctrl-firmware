#!/bin/bash

if [ -e /debootstrap/debootstrap ]; then
  /debootstrap/debootstrap --second-stage
fi

export LC_ALL=C
export DEBIAN_FRONTEND=noninteractive

# Install packages
apt-get install -yq avahi-daemon minicom python3-pip python3-smbus gdisk sudo \
  python3-serial psmisc i2c-tools xorg samba samba-common-bin smbclient \
  cifs-utils fbi libgles2-mesa openssh-server haveged dphys-swapfile vim \
  parted iputils-ping locales bash-completion pciutils wpasupplicant iw \
  wireless-tools mesa-utils firmware-brcm80211 wget curl wireless-regdb file \
  systemd-timesyncd gpiod libnode108 usbutils firmware-realtek \
  firmware-misc-nonfree network-manager libxdamage1 libasound2 libxkbcommon0 \
  libatk-bridge2.0-0 libatk1.0-0 libnss3 libpango-1.0-0 libcairo2 squashfs-tools

# Clean up
apt-get autoremove -y
apt-get autoclean -y
apt-get clean

# Get Chromium
if [ ! -e /opt/chromium-browser ]; then
  SNAP=XKEcBqPM06H1Z7zGOdG5fbICuf8NWK5R_2643.snap
  wget https://api.snapcraft.io/api/v1/snaps/download/$SNAP
  unsquashfs $SNAP
  mv squashfs-root/usr/lib/chromium-browser /opt/
  ln -s /opt/chromium-browser/chrome /usr/bin/chromium
  rm -rf squashfs-root $SNAP
fi

# Generate locales
echo en_US UTF-8 > /etc/locale.gen
locale-gen

# Run dpkg-db-backup
/usr/libexec/dpkg/dpkg-db-backup

# Get wifi firmware
(
  mkdir -p /lib/firmware/brcm
  cd /lib/firmware/brcm
  URL=https://github.com/RPi-Distro/firmware-nonfree/raw/buster/brcm
  for EXT in txt clm_blob bin; do
    FILE=brcmfmac43455-sdio.$EXT
    if [ ! -e $FILE ]; then
      wget $URL/$FILE
    fi
  done
)

# Enable networking but don't wait for it
systemctl enable systemd-networkd
SYSD=/etc/systemd/system
rm -f $SYSD/network-online.target.wants/systemd-networkd-wait-online.service
rm -f $SYSD/network-online.target.wants/NetworkManager-wait-online.service

# Stop splash service
mkdir -p $SYSD/getty.target.wants
ln -s $SYSD/kill-splash.service $SYSD/getty.target.wants/kill-splash.service

# Fix login timeout
sed -i 's/^LOGIN_TIMEOUT.*/LOGIN_TIMEOUT 0/' /etc/login.defs

# Create bbmc user
if ! getent passwd bbmc >/dev/null; then
  useradd -m -p $(openssl passwd -1 buildbotics) -s /bin/bash bbmc
fi
adduser bbmc sudo
adduser bbmc dialout
adduser bbmc video

# Samba
printf "buildbotics\nbuildbotics\n" | smbpasswd -a bbmc
