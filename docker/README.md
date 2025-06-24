# Docker Setup for bbctrl-firmware

This directory contains Docker configuration for building and developing the bbctrl-firmware.

## Prerequisites

- Docker 20.10.0+
- Docker Compose 1.29.0+
- Make (optional, but recommended)

## Available Services

### Production Build

To build the production image:

```bash
docker-compose build bbctrl-build
```

To run a one-time build:

```bash
docker-compose run --rm bbctrl-build
```

### Development Environment

To start the development environment:

```bash
docker-compose up -d bbctrl-dev
```

This will start a container with:
- Source code mounted at `/build`
- Development server running on port 8080
- Python debugger on port 5678
- Node.js debugger on port 9229

### Useful Commands

- Attach to the development container:
  ```bash
  docker-compose exec bbctrl-dev bash
  ```

- View logs:
  ```bash
  docker-compose logs -f bbctrl-dev
  ```

- Run tests:
  ```bash
  docker-compose exec bbctrl-dev make test
  ```

## Volumes

The following named volumes are used:

- `bbctrl-build-cache`: Build cache
- `bbctrl-node-modules`: Node.js dependencies
- `bbctrl-dist-output`: Build output
- `bbctrl-venv`: Python virtual environment

## Environment Variables

Common environment variables can be set in a `.env` file in the project root.

## Troubleshooting

- **Permission issues**: Make sure your user has the correct permissions on the project directory
- **Port conflicts**: Check if ports 8080, 5678, or 9229 are already in use
- **Volume issues**: Run `docker-compose down -v` to reset all volumes (this will delete all data in the volumes)
