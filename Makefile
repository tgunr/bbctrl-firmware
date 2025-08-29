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

RSYNC_EXCLUDE := \*.pyc __pycache__ \*.egg-info \\\#* \*~ .\\\#\*
RSYNC_EXCLUDE := $(patsubst %,--exclude %,$(RSYNC_EXCLUDE))
RSYNC_OPTS    := $(RSYNC_EXCLUDE) -rv --no-g --delete --force

VERSION  := $(shell sed -n 's/^.*"version": "\([^"]*\)",.*$$/\1/p' package.json)
# Normalize version to PEP 440 format for Python packaging
NORMALIZED_VERSION := $(shell python3 -c "import re; v='$(VERSION)'; print(re.sub(r'-([a-zA-Z]+)\.(\d+)', r'.\1\2', v))")
PKG_NAME := bbctrl-$(NORMALIZED_VERSION)
PUB_PATH := root@buildbotics.com:/var/www/buildbotics.com/bbctrl-2.0
BETA_VERSION := $(VERSION)-rc$(shell ./scripts/next-rc)
# Normalize beta version to PEP 440 format
NORMALIZED_BETA_VERSION := $(shell python3 -c "import re; v='$(BETA_VERSION)'; print(re.sub(r'-([a-zA-Z]+)\.(\d+)', r'.\1\2', v))")
BETA_PKG_NAME := bbctrl-$(NORMALIZED_BETA_VERSION)
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

pkg: all $(SUBPROJECTS) arm-bin
	#cp -a $(SHARE)/camotics/tpl_lib src/py/bbctrl/
	./setup.py sdist

beta-pkg: pkg
	cp dist/$(PKG_NAME).tar.bz2 dist/$(BETA_PKG_NAME).tar.bz2
	echo -n $(BETA_VERSION) > dist/latest-beta.txt

arm-bin:
	mkdir -p bin
	cp camotics/build/camotics.so bin/
	cp bbkbd/bbkbd bin/
	cp updiprog/updiprog bin/
	cp rpipdi/rpipdi bin/

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
	http_proxy= ./scripts/remote-firmware-update $(USER)@$(HOST) "$(PASSWORD)" \
	  dist/$(PKG_NAME).tar.bz2
	@-tput sgr0 && echo # Fix terminal output

ssh-update: pkg
	scp -i $(SSHID) scripts/update-bbctrl dist/$(PKG_NAME).tar.bz2 $(USER)@$(HOST):~/
	ssh -i $(SSHID) -t $(USER)@$(HOST) "sudo mv ~/update-bbctrl ~/$(PKG_NAME).tar.bz2 /tmp/ && sudo /tmp/update-bbctrl /tmp/$(PKG_NAME).tar.bz2"

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
	rm -rf build html dist
	@for SUB in $(SUBPROJECTS); do \
	  $(MAKE) -C src/$$SUB clean; \
	done

dist-clean: clean
	rm -rf node_modules

.PHONY: all install clean tidy pkg arm-bin lint pylint jshint
.PHONY: html resources dist-clean
