# Build and Deploy Summary for Buildbotics Firmware

This document summarizes how to build and deploy the Buildbotics CNC Controller firmware, extracted from the repository.

Key docs checked:
- [`docs/development.md`](docs/development.md:1)
- [`docs/development-docker.md`](docs/development-docker.md:1)
- [`docs/docker-build.md`](docs/docker-build.md:1)
- [`scripts/docker-build`](scripts/docker-build:1)
- [`README.md`](README.md:1)
- [`src/avr/README.md`](src/avr/README.md:1)
- [`src/py/bbctrl/Web.py`](src/py/bbctrl/Web.py:1)
- [`MACOS_BUILD_PLAN.md`](MACOS_BUILD_PLAN.md:1)

High-level components to build:
- AVR firmware: `src/avr/` (main) and `src/pwr/` (power)
- Python backend: `src/py/`
- Web UI: `src/js/`, `src/pug/`, `src/stylus/`
- CAMotics module (C++ Python module, cross-compiled for ARM)
- Packaging: `dist/` (.tar.bz2)

Native Debian prerequisites (summary):
- Install packages as listed in [`README.md`](README.md:1) / [`docs/development.md`](docs/development.md:1):
  build-essential, git, wget, binfmt-support, qemu(-user-static), parted, gcc-avr, avr-libc, avrdude, pylint, python3, python3-tornado, curl, unzip, python3-setuptools, nodejs, cross compilers, debootstrap, etc.
- Node.js / npm for frontend builds.

Native build steps:
1. git clone https://github.com/buildbotics/bbctrl-firmware
2. cd bbctrl-firmware
3. make        # build all components
4. make pkg    # create package (dist/*.tar.bz2)
5. make camotics  # build CAMotics via chroot/qemu (first run slow)

AVR programming:
- Pwr AVR (ATtiny): must be uploaded manually with ISP:
  make -C src/pwr program
- Main AVR initial programming:
  make -C src/avr init    # sets fuses, installs bootloader, programs firmware

Docker-based build (recommended on macOS / non-Debian):
- ./scripts/docker-build   # runs docker-compose run --rm bbctrl-build make pkg
- Or use the dev container workflow:
  ./scripts/dev up
  ./scripts/dev build
- Selective targets via docker-build:
  ./scripts/docker-build make html
  ./scripts/docker-build make camotics
- Outputs are in `dist/`, `build/`, and `node_modules/` persisted via Docker volumes.
- Permission fix if root-owned:
  sudo chown -R $USER:$USER build dist node_modules

Packaging & deployment:
- Package location: `dist/` (.tar.bz2) created by make pkg
- Upload to controller:
  make update HOST=bbctrl.local PASSWORD=<pass>
- Web/API upload (controller side) writes to firmware/update.tar.bz2 and triggers update (see [`src/py/bbctrl/Web.py`](src/py/bbctrl/Web.py:1))

CAMotics / cross-compilation notes:
- CAMotics must be built for ARM using qemu + binfmt + chroot (automated by make camotics).

CI/CD:
- GitHub Actions run tests, lint, build on push/PR; tags create releases and upload packages (see [`docs/development-docker.md`](docs/development-docker.md:1)).

Quick recommended workflows:
- Debian host:
  apt install prerequisites -> git clone -> make pkg -> make -C src/pwr program -> make -C src/avr init -> make update...
- macOS / non-Debian:
  Install Docker -> ./scripts/docker-build (or ./scripts/dev up) -> package in dist/

Caveats & tips:
- CAMotics build is slow first-run.
- AVR initial flashing requires an ISP programmer.
- Use Docker to avoid dependency issues on macOS.
- See [`MACOS_BUILD_PLAN.md`](MACOS_BUILD_PLAN.md:1) for macOS-specific notes.

Last checked files: see "Key docs checked" above.

End of summary.