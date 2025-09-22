DIR := $(shell dirname $(lastword $(MAKEFILE_LIST)))

NODE_MODS  := $(DIR)/node_modules
PUG        := $(NODE_MODS)/.bin/pug
STYLUS     := $(NODE_MODS)/.bin/stylus

TARGET_DIR := build/http
HTML       := index
HTML       := $(patsubst %,$(TARGET_DIR)/%.html,$(HTML))
RESOURCES  := $(shell find src/resources -type f)
RESOURCES  := $(patsubst src/resources/%,$(TARGET_DIR)/%,$(RESOURCES))
TEMPLS     := $(wildcard src/pug/templates/*.pug)

SHARE           := share
CAMOTICS_MOD    := $(SHARE)/camotics/build/camotics.so
CAMOTICS_TARGET := src/py/bbctrl/camotics.so

# CAMotics build configuration
BUILD_SCRIPT     := scripts/build-camotics-arm
CAMOTICS_BUILD_DIR := camotics/build
CAMOTICS_OUTPUT  := $(CAMOTICS_BUILD_DIR)/camotics.so

# ARM chroot configuration
CHROOT_DIR := /opt/arm-chroot
BBKBD_OUTPUT := bbkbd/bbkbd

RSYNC_EXCLUDE := \*.pyc __pycache__ \*.egg-info \\\#* \*~ .\\\#\*
RSYNC_EXCLUDE := $(patsubst %,--exclude %,$(RSYNC_EXCLUDE))
RSYNC_OPTS    := $(RSYNC_EXCLUDE) -rv --no-g --delete --force

VERSION  := $(shell python3 -c "import json; print(json.load(open('package.json'))['version'])")

# Build number tracking
BUILD_INFO_FILE := .build-info
CURRENT_BUILD := $(shell ./scripts/manage-build-number.sh $(VERSION) $(BUILD_INFO_FILE))
VERSION_WITH_BUILD := $(VERSION)+build.$(CURRENT_BUILD)

# Version is already in PEP 440 format
NORMALIZED_VERSION := $(VERSION_WITH_BUILD)
PKG_NAME := bbctrl-$(NORMALIZED_VERSION)
# Use version with build number for tarball naming
TARBALL_VERSION := $(VERSION_WITH_BUILD)
TARBALL_NAME := bbctrl-$(TARBALL_VERSION)
PUB_PATH := root@buildbotics.com:/var/www/buildbotics.com/bbctrl-2.0
BETA_VERSION := $(VERSION)rc$(shell ./scripts/next-rc)
# Beta version is already in PEP 440 format
NORMALIZED_BETA_VERSION := $(BETA_VERSION)
BETA_PKG_NAME := bbctrl-$(NORMALIZED_BETA_VERSION)
CUR_BETA_VERSION := $(shell cat dist/latest-beta.txt 2>/dev/null || echo "none")
CUR_BETA_PKG_NAME := bbctrl-$(CUR_BETA_VERSION)

IMAGE := $(shell date +%Y%m%d)-debian-bookworm-bbctrl.img
IMG_PATH := root@buildbotics.com:/var/www/buildbotics.com/upload

CPUS := $(shell grep -c ^processor /proc/cpuinfo)

SUBPROJECTS := avr pwr
SUBPROJECTS := $(patsubst %,src/%,$(SUBPROJECTS))
$(info SUBPROJECTS="$(SUBPROJECTS)")

# Upload files - only check subfolders and specific files (globals, log)
UPLOAD_FILES := $(shell find bbctrl/upload -type d -mindepth 1 2>/dev/null) \
               $(shell test -f bbctrl/upload/globals && echo bbctrl/upload/globals) \
               $(shell test -f bbctrl/upload/log && echo bbctrl/upload/log) \
               $(shell find bbctrl/upload/*/  -type f 2>/dev/null | sed 's/ /\\ /g')

WATCH := src/pug src/pug/templates src/stylus src/js src/resources Makefile
WATCH += src/static

USER=bbmc
HOST=bbctrl.local
PASSWORD=buildbotics
SSHID=$(HOME)/.ssh/id_rsa

all: html $(SUBPROJECTS)

.PHONY: $(SUBPROJECTS)
$(SUBPROJECTS):
	$(MAKE) -C $@

html: resources $(HTML)
resources: $(RESOURCES)

demo: html resources bbemu
	ln -sf ../../../$(TARGET_DIR) src/py/bbctrl/http
	./setup.py install
	cp src/avr/emu/bbemu /usr/local/bin

bbemu:
	$(MAKE) -C src/avr/emu

# Build CAMotics for ARM architecture
# This target builds CAMotics using a chroot environment for cross-compilation
camotics: $(BUILD_SCRIPT) | $(CAMOTICS_BUILD_DIR)
	@echo "=== Starting CAMotics ARM build ==="
	@echo "Build script: $(BUILD_SCRIPT)"
	@echo "Output directory: $(CAMOTICS_BUILD_DIR)"
	@echo "Target file: $(CAMOTICS_OUTPUT)"
	@echo "Checking if build script is executable..."
	@if [ ! -x $(BUILD_SCRIPT) ]; then \
		echo "ERROR: Build script $(BUILD_SCRIPT) is not executable!"; \
		echo "Run: chmod +x $(BUILD_SCRIPT)"; \
		exit 1; \
	fi
	@echo "Build script checks passed. Starting build..."
	@echo "Building CAMotics for ARM architecture..."
	@if /bin/bash $(BUILD_SCRIPT); then \
		echo "=== CAMotics ARM build completed successfully ==="; \
		echo "Verifying output file..."; \
		if [ -f $(CAMOTICS_OUTPUT) ]; then \
			echo "Output file created: $(CAMOTICS_OUTPUT)"; \
			file $(CAMOTICS_OUTPUT); \
		else \
			echo "WARNING: Expected output file $(CAMOTICS_OUTPUT) not found!"; \
		fi \
	else \
		echo "=== CAMotics ARM build failed! ==="; \
		exit 1; \
	fi

# Create build directory if it doesn't exist
$(CAMOTICS_BUILD_DIR):
	@echo "Creating CAMotics build directory: $@"
	@mkdir -p $@

pkg: all $(SUBPROJECTS) arm-bin
	# Create dist directory if it doesn't exist
	@mkdir -p dist
	# Update package.json with build number for correct tarball naming
	@cp package.json package.json.backup
	@sed -i 's/"version": "[^"]*"/"version": "$(VERSION_WITH_BUILD)"/' package.json
	#cp -a $(SHARE)/camotics/tpl_lib src/py/bbctrl/
	/usr/bin/python3 setup.py sdist
	# Restore original package.json
	@mv package.json.backup package.json
	# Rename the tarball to use the correct PEP 440 format
	@mv dist/$(PKG_NAME).tar.bz2 dist/$(TARBALL_NAME).tar.bz2 2>/dev/null || echo "Tarball already has correct name"

beta-pkg: pkg
	cp dist/$(TARBALL_NAME).tar.bz2 dist/$(BETA_PKG_NAME).tar.bz2
	echo -n $(VERSION_WITH_BUILD) > dist/latest-beta.txt

arm-bin: $(CAMOTICS_OUTPUT)
	mkdir -p bin
	cp $(CAMOTICS_OUTPUT) bin/
	@echo "Checking for bbkbd..."
	@if [ ! -d bbkbd ]; then \
		echo "Cloning bbkbd..."; \
		git clone --depth=1 https://github.com/buildbotics/bbkbd.git; \
	fi
	@if [ ! -f $(BBKBD_OUTPUT) ]; then \
		echo "Building bbkbd for ARM..."; \
		sudo cp -r bbkbd $(CHROOT_DIR)/opt/ && \
		sudo chroot $(CHROOT_DIR) /bin/bash -c "cd /opt/bbkbd && make clean && make" && \
		sudo cp $(CHROOT_DIR)/opt/bbkbd/bbkbd bbkbd/; \
	fi
	@cp $(BBKBD_OUTPUT) bin/
	@echo "Checking for updiprog..."
	@if [ ! -d updiprog ]; then \
		echo "Cloning updiprog..."; \
		git clone --depth=1 https://github.com/buildbotics/updiprog.git; \
	fi
	@if [ ! -f updiprog/updiprog ]; then \
		echo "Building updiprog..."; \
		$(MAKE) -C updiprog; \
	fi
	@cp updiprog/updiprog bin/
	@echo "Checking for rpipdi..."
	@if [ ! -d rpipdi ]; then \
		echo "Cloning rpipdi..."; \
		git clone --depth=1 https://github.com/buildbotics/rpipdi.git; \
	fi
	@if [ ! -f rpipdi/rpipdi ]; then \
		echo "Building rpipdi..."; \
		$(MAKE) -C rpipdi; \
	fi
	@cp rpipdi/rpipdi bin/

%.img.xz: %.img
	xz -T $(CPUS) $<

$(IMAGE):
	sudo ./scripts/make-image.sh
	mv build/system.img $(IMAGE)

image: $(IMAGE)
image-xz: $(IMAGE).xz

publish-image: $(IMAGE).xz
	rsync --progress $< $(IMG_PATH)/

publish: pkg
	echo -n $(VERSION_WITH_BUILD) > dist/latest.txt
	rsync $(RSYNC_OPTS) dist/$(TARBALL_NAME).tar.bz2 dist/latest.txt $(PUB_PATH)/

publish-beta: beta-pkg
	$(MAKE) push-beta

push-beta:
	rsync $(RSYNC_OPTS) dist/$(CUR_BETA_PKG_NAME).tar.bz2 dist/latest-beta.txt \
	  $(PUB_PATH)/

update: pkg
	http_proxy= ./scripts/remote-firmware-update $(USER)@$(HOST) "$(PASSWORD)" \
	dist/$(PKG_NAME).tar.bz2
	@-tput sgr0 && echo # Fix terminal output

ssh-update: pkg
	scp -i $(SSHID) scripts/update-bbctrl dist/$(TARBALL_NAME).tar.bz2 $(USER)@$(HOST):~/
	ssh -i $(SSHID) -t $(USER)@$(HOST) "sudo ./update-bbctrl ./$(TARBALL_NAME).tar.bz2"

ssh-204: 
	scp -i $(SSHID) scripts/update-bbctrl $(DIR)/bbctrl-2.0.4.tar.bz2 $(USER)@$(HOST):~/
	ssh -i $(SSHID) -t $(USER)@$(HOST) "sudo ./update-bbctrl ./bbctrl-2.0.4.tar.bz2"

ssh-macros: $(UPLOAD_FILES)
	ssh -i $(SSHID) -t $(USER)@$(HOST) "mkdir -p Downloads/upload"
	rsync -auvL bbctrl/upload/ $(USER)@$(HOST):Downloads/upload/
	ssh -i $(SSHID) -t $(USER)@$(HOST) "sudo rsync -au Downloads/upload/ upload/"

ssh-sync:
	rsync -auvL $(USER)@$(HOST):upload/ bbctrl/upload/

build/templates.pug: $(TEMPLS)
	mkdir -p build
	cat $(TEMPLS) >$@

node_modules: package.json
	npm install && touch node_modules

$(TARGET_DIR)/%: src/resources/%
	install -D $< $@

$(TARGET_DIR)/index.html: build/templates.pug
$(TARGET_DIR)/index.html: $(wildcard src/static/js/*)
$(TARGET_DIR)/index.html: $(wildcard src/static/css/*)
$(TARGET_DIR)/index.html: $(wildcard src/js/*)
$(TARGET_DIR)/index.html: $(wildcard src/stylus/*)
$(TARGET_DIR)/index.html: src/resources/config-template.json

$(TARGET_DIR)/%.html: src/pug/%.pug node_modules
	@mkdir -p $(shell dirname $@)
	$(PUG) -O pug-opts.js -P $< -o $(TARGET_DIR) || (rm -f $@; exit 1)

pylint:
	pylint -E $(shell find src/py -name \*.py | grep -v flycheck_)

jshint:
	./node_modules/jshint/bin/jshint --config jshint.json src/js/*.js

lint: pylint jshint

watch:
	@clear
	$(MAKE)
	@while sleep 1; do \
	  inotifywait -qr -e modify -e create -e delete \
		--exclude .*~ --exclude \#.* $(WATCH); \
	  clear; \
	  $(MAKE); \
	done

tidy:
	rm -f $(shell find "$(DIR)" -name \*~)

clean: tidy
	rm -rf build html dist bbkbd
	@for SUB in $(SUBPROJECTS); do \
	  $(MAKE) -C $$SUB clean; \
	done

dist-clean: clean
	rm -rf node_modules
	@if [ -d bbkbd ]; then $(MAKE) -C bbkbd clean; fi
	@if [ -d updiprog ]; then $(MAKE) -C updiprog clean; fi
	@if [ -d rpipdi ]; then $(MAKE) -C rpipdi clean; fi

.PHONY: all install clean tidy pkg arm-bin camotics lint pylint jshint
.PHONY: html resources dist-clean ssh-macros
