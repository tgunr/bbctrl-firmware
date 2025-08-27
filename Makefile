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

RSYNC_EXCLUDE := \*.pyc __pycache__ \*.egg-info \\#* \*~ .\\#\*
RSYNC_EXCLUDE := $(patsubst %,--exclude %,$(RSYNC_EXCLUDE))
RSYNC_OPTS    := $(RSYNC_EXCLUDE) -rv --no-g --delete --force

# Simple dev version incrementer
PACKAGE_VERSION := $(shell cat package.json | grep '"version"' | cut -d'"' -f4)
# Extract base version (remove any -dev.X suffix)
BASE_VERSION := $(shell echo $(PACKAGE_VERSION) | cut -d'-' -f1)
DEV_VERSION := $(shell ./scripts/manage-dev-version increment)
VERSION := $(BASE_VERSION).dev$(DEV_VERSION)
$(info Using dev version: $(VERSION))

PKG_NAME := bbctrl-$(VERSION)
PUB_PATH := root@buildbotics.com:/var/www/buildbotics.com/bbctrl-2.0
BETA_VERSION := $(VERSION)-rc$(shell ./scripts/next-rc)
BETA_PKG_NAME := bbctrl-$(BETA_VERSION)
CUR_BETA_VERSION := $(shell cat dist/latest-beta.txt)
CUR_BETA_PKG_NAME := bbctrl-$(CUR_BETA_VERSION)

IMAGE := $(shell date +%Y%m%d)-debian-bookworm-bbctrl.img
IMG_PATH := root@buildbotics.com:/var/www/buildbotics.com/upload

CPUS := $(shell grep -c ^processor /proc/cpuinfo)

SUBPROJECTS := avr pwr
SUBPROJECTS := $(patsubst %,src/%,$(SUBPROJECTS))
$(info SUBPROJECTS="$(SUBPROJECTS)")

WATCH := src/pug src/pug/templates src/stylus src/js src/resources Makefile
WATCH += src/static

ifndef HOST
HOST=bbctrl.local
endif

ifndef PASSWORD
PASSWORD=buildbotics
endif


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

pkg: all $(SUBPROJECTS) arm-bin
	./setup.py sdist

beta-pkg: pkg
	cp dist/$(PKG_NAME).tar.bz2 dist/$(BETA_PKG_NAME).tar.bz2
	echo -n $(BETA_VERSION) > dist/latest-beta.txt

arm-bin: bbkbd updiprog rpipdi camotics

bbkbd:
	@if [ ! -d bbkbd ]; then \
		git clone https://github.com/buildbotics/bbkbd; \
	fi
	-$(MAKE) -C bbkbd && mkdir -p bin && cp bbkbd/bbkbd bin/ || echo "Warning: bbkbd build failed, skipping"

updiprog:
	@if [ ! -d updiprog ]; then \
		git clone https://github.com/buildbotics/updiprog; \
	fi
	-$(MAKE) -C updiprog && mkdir -p bin && cp updiprog/updiprog bin/ || echo "Warning: updiprog build failed, skipping"

rpipdi:
	@if [ ! -d rpipdi ]; then \
		git clone https://github.com/buildbotics/rpipdi; \
	fi
	-$(MAKE) -C rpipdi && mkdir -p bin && cp rpipdi/rpipdi bin/ || echo "Warning: rpipdi build failed, skipping"

bin/camotics.so:
	@echo "Building camotics.so..."
	@if [ ! -d cbang ]; then \
		git clone https://github.com/CauldronDevelopmentLLC/cbang; \
	fi
	@if [ ! -d camotics ]; then \
		git clone https://github.com/CauldronDevelopmentLLC/camotics; \
	fi
	@mkdir -p bin
	@echo "Building cbang dependency..."
	-cd cbang && scons -j$(CPUS) v8_compress_pointers=0 && cd .. && \
	echo "Building camotics.so..." && \
	export CBANG_HOME=$$PWD/cbang && \
	cd camotics && scons -j$(CPUS) build/camotics.so with_gui=0 wrap_glibc=0 with_tpl=0 && cd .. && \
	cp camotics/build/camotics.so bin/ || echo "Warning: camotics build failed, skipping"

camotics: bin/camotics.so

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
	echo -n $(VERSION) > dist/latest.txt
	rsync $(RSYNC_OPTS) dist/$(PKG_NAME).tar.bz2 dist/latest.txt $(PUB_PATH)/

publish-beta: beta-pkg
	$(MAKE) push-beta

push-beta:
	rsync $(RSYNC_OPTS) dist/$(CUR_BETA_PKG_NAME).tar.bz2 dist/latest-beta.txt \
	  $(PUB_PATH)/

update: pkg
	http_proxy= ./scripts/remote-firmware-update $(HOST) "$(PASSWORD)" \
	  dist/$(PKG_NAME).tar.bz2
	@-tput sgr0 && echo # Fix terminal output

ssh-update: pkg
	scp scripts/update-bbctrl dist/$(PKG_NAME).tar.bz2 $(HOST):/tmp/
	ssh -t $(HOST) "sudo /tmp/update-bbctrl /tmp/$(PKG_NAME).tar.bz2"

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
	rm -rf build html dist bin bbkbd updiprog rpipdi cbang camotics
	@for SUB in $(SUBPROJECTS); do \
	  $(MAKE) -C src/$$SUB clean; \
	done

dist-clean: clean
	rm -rf node_modules

.PHONY: all install clean tidy pkg lint pylint jshint
.PHONY: html resources dist-clean
