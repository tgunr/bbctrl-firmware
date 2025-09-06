# Buildbotics Development with Docker

This guide explains how to develop the Buildbotics CNC Controller firmware using Docker, which provides a consistent development environment across different platforms including macOS.

## Prerequisites

- Docker
- Docker Compose
- Git
- VS Code (recommended) with the following extensions:
  - Python
  - Remote Containers
  - Debugger for Chrome

## Development Environment Setup

1. Clone the repository:
```bash
git clone https://github.com/buildbotics/bbctrl-firmware
cd bbctrl-firmware
```

2. Start the development environment:
```bash
./scripts/dev up
```

## Development Commands

The `scripts/dev` script provides various development commands:

### Basic Commands
- `./scripts/dev up` - Start development environment
- `./scripts/dev down` - Stop development environment
- `./scripts/dev shell` - Open shell in development container
- `./scripts/dev logs` - Show development container logs
- `./scripts/dev clean` - Clean build artifacts

### Building
- `./scripts/dev build` - Build the project
- `./scripts/dev build html` - Build only the web interface
- `./scripts/dev build camotics` - Build only the CAMotics module

### Testing and Linting
- `./scripts/dev test` - Run tests
- `./scripts/dev lint` - Run linting (Python and JavaScript)

### Debugging
- `./scripts/dev debug-py` - Start Python debugger
- `./scripts/dev debug-js` - Start Node.js debugger

## Development Workflow

1. Start the development environment:
```bash
./scripts/dev up
```

2. Make changes to the code. The development environment watches for changes and rebuilds automatically.

3. Run tests and linting:
```bash
./scripts/dev test
./scripts/dev lint
```

4. Debug your code:
- For Python: Use VS Code's debugger with port 5678
- For JavaScript: Use Chrome DevTools with port 9229

## Directory Structure

- `src/py/` - Python code (BBCtrl)
- `src/js/` - JavaScript code (Web UI)
- `src/avr/` - AVR firmware
- `src/pwr/` - Power management firmware

## Debugging

### Python Debugging
1. Add this code where you want to break:
```python
import debugpy; debugpy.breakpoint()
```

2. Start the debugger:
```bash
./scripts/dev debug-py your_script.py
```

3. Attach VS Code debugger to port 5678

### JavaScript Debugging
1. Start the Node.js debugger:
```bash
./scripts/dev debug-js your_script.js
```

2. Open Chrome DevTools and connect to port 9229

## CI/CD Pipeline

The project uses GitHub Actions for CI/CD:

1. On every push and pull request:
   - Runs tests
   - Runs linting
   - Builds the firmware package

2. On tag creation (v*):
   - Creates a GitHub release
   - Uploads the firmware package as a release asset

## Common Issues

1. Permission errors:
```bash
sudo chown -R $USER:$USER build dist node_modules
```

2. Port conflicts:
```bash
./scripts/dev down
sudo lsof -i :8080  # Check what's using port 8080
```

3. Clean start:
```bash
./scripts/dev clean
./scripts/dev up
```