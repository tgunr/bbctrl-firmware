CROSS:=arm-linux-gnueabihf-
DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
obj-m:=bbserial.o
ccflags-y:=-std=gnu99 -Wno-declaration-after-statement

KVER=1.20171029-1
KPKG=raspberrypi-kernel_$(KVER)

# Set KDIR to the local repo path
KDIR := ~/linux
KURL=https://github.com/raspberrypi/linux/archive/refs/tags/raspberrypi-kernel_$(KVER).tar.gz
KOPTS=ARCH=arm CROSS_COMPILE=$(CROSS) -C $(KDIR) KCFLAGS="-march=armv7-a -marm"

export KERNEL=kernel7

all: modules

modules: $(KDIR)
	$(MAKE) $(KOPTS) M=$(DIR) modules

$(KDIR):
	# Check if the directory exists and is not empty
	$(if $(wildcard $(KDIR)/*),,echo "Kernel directory is empty or does not exist")

	cd $(KDIR) && patch -p1 < $(DIR)/yylloc.patch
	cd $(KDIR) && $(MAKE) $(KOPTS) bcm2709_defconfig
	cd $(KDIR) && $(MAKE) $(KOPTS) modules_prepare

# Remove or comment out the $(KPKG) target as it's no longer needed
# $(KPKG):
#	if [ ! -f $(KPKG) ]; then \
#		wget $(KURL); \
#		tar xf $(KPKG); \
#	fi

KBUILD_CFLAGS += 

clean:
	$(MAKE) $(KOPTS) M=$(DIR) clean
	rm -rf $(KDIR) $(KPKG)KURL=https://github.com/raspberrypi/linux/archive/refs/tags/raspberrypi-kernel_$(KVER).tar.gz


