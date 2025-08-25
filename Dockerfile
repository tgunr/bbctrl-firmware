# Use Debian 11 (Bullseye) as base image with explicit version tag for reproducibility
FROM debian:11.9-slim@sha256:fbaacd55d14bd0ae0c0441c2347217da77ad83c517054623357d1f9d07f79f5e

# Set build arguments for user ID and group ID
ARG USER_ID=1000
ARG GROUP_ID=1000

# Add non-root user with host UID/GID, handling existing groups
RUN if ! getent group ${GROUP_ID} >/dev/null; then \
        groupadd -g ${GROUP_ID} builder; \
    else \
        GROUP_NAME=$(getent group ${GROUP_ID} | cut -d: -f1); \
        echo "Using existing group: $GROUP_NAME (${GROUP_ID})"; \
    fi && \
    useradd -r -u ${USER_ID} -g ${GROUP_ID} -m -d /home/builder builder

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NODE_ENV=production \
    NPM_CONFIG_CACHE=/home/builder/.npm \
    APT_OPTS="-o Acquire::Retries=3 -o Acquire::https::Timeout=30"

# Install basic build requirements with retry and timeout
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        git \
        wget \
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

# Create build directories and set permissions
RUN mkdir -p /build /home/builder/.npm \
    && chown -R builder:${GROUP_ID} /build /home/builder/.npm

# Set working directory
WORKDIR /build

# Copy package files first to leverage Docker cache
COPY --chown=builder:${GROUP_ID} package.json package-lock.json ./

# Install npm dependencies with explicit cache directory
RUN npm config set cache /home/builder/.npm \
    && npm ci --only=production

# Copy the rest of the source code
COPY --chown=builder:${GROUP_ID} . .

# Set proper permissions
RUN chmod -R 755 /build /home/builder/.npm

# Switch to non-root user
USER builder

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD pgrep -f "make pkg" || exit 1

# Set labels for better maintainability
LABEL maintainer="Your Name <your.email@example.com>" \
      description="Build environment for Bbctrl controller firmware" \
      version="1.0.0"

# Default command - can be overridden
CMD ["make", "pkg"]