# Use Debian 11 (Bullseye) as base image with explicit version tag for reproducibility
FROM debian:11.9-slim@sha256:fbaacd55d14bd0ae0c0441c2347217da77ad83c517054623357d1f9d07f79f5e

# Add non-root user
RUN groupadd -r builder && useradd -r -g builder builder

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NODE_ENV=production

# Install basic build requirements with no-recommends to reduce image size
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    wget \
    binfmt-support \
    qemu \
    parted \
    gcc-avr \
    avr-libc \
    avrdude \
    pylint3 \
    python3 \
    python3-tornado \
    curl \
    unzip \
    python3-setuptools \
    gcc-arm-linux-gnueabihf \
    bc \
    scons \
    libssl-dev \
    python3-dev \
    libx11-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/archives/*

# Install Node.js LTS with explicit version
RUN curl -sL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/archives/* \
    && npm install -g npm@latest \
    && npm cache clean --force

# Create build directory and set permissions
WORKDIR /build
RUN chown -R builder:builder /build

# Copy package files first to leverage Docker cache
COPY --chown=builder:builder package.json package-lock.json ./

# Install npm dependencies
RUN npm ci --only=production

# Copy the rest of the source code
COPY --chown=builder:builder . .

# Set proper permissions
RUN chmod -R 755 /build

# Switch to non-root user
USER builder

# Set up QEMU for ARM emulation
RUN update-binfmts --enable qemu-arm

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD pgrep -f "make pkg" || exit 1

# Set labels for better maintainability
LABEL maintainer="Your Name <your.email@example.com>" \
      description="Build environment for Bbctrl controller firmware" \
      version="1.0.0"

# Default command - can be overridden
CMD ["make", "pkg"]

# Set working directory
WORKDIR /build