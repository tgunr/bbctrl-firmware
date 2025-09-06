# Building with Docker

This guide explains how to build the Buildbotics CNC Controller firmware using Docker, which allows building on non-Debian systems including macOS.

## Prerequisites

- Docker
- Docker Compose
- Git

## Building

1. Clone the repository:
```bash
git clone https://github.com/buildbotics/bbctrl-firmware
cd bbctrl-firmware
```

2. Build using Docker:
```bash
./scripts/docker-build
```

This will:
- Create a Docker container with all required build dependencies
- Build all components including the AVR firmware, web interface, and CAMotics module
- Create a package in the `dist` directory

## Alternative Build Commands

- Build specific targets:
```bash
./scripts/docker-build make html     # Build only the web interface
./scripts/docker-build make camotics # Build only the CAMotics module
```

- Run tests:
```bash
./scripts/docker-build make lint     # Run linting
```

## Build Outputs

The build creates several output directories that are preserved between builds using Docker volumes:
- `build/`: Build artifacts
- `dist/`: Final packages
- `node_modules/`: NPM dependencies

These are stored in Docker volumes to improve build performance and prevent permission issues.

## Development Workflow

For development, you can mount your working directory into the container and use file watchers:
```bash
./scripts/docker-build make watch
```

This will watch for file changes and rebuild automatically.

## Troubleshooting

1. If you get permission errors, the files created inside the container might be owned by root. Fix this by running:
```bash
sudo chown -R $USER:$USER build dist node_modules
```

2. To clean all build artifacts and start fresh:
```bash
docker-compose down -v  # Remove all volumes
./scripts/docker-build make dist-clean
```