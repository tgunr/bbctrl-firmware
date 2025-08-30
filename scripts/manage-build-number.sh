#!/bin/bash

# Build number management script
# Usage: ./manage-build-number.sh <current_version> <build_info_file>

CURRENT_VERSION="$1"
BUILD_INFO_FILE="$2"

# Default build info file if not specified
if [ -z "$BUILD_INFO_FILE" ]; then
    BUILD_INFO_FILE=".build-info"
fi

# Create build info file if it doesn't exist
if [ ! -f "$BUILD_INFO_FILE" ]; then
    echo "VERSION=$CURRENT_VERSION" > "$BUILD_INFO_FILE"
    echo "BUILD=1" >> "$BUILD_INFO_FILE"
    echo "1"
    exit 0
fi

# Read current build info
source "$BUILD_INFO_FILE"

# Check if version has changed
if [ "$VERSION" != "$CURRENT_VERSION" ]; then
    # Version changed, reset build number
    NEW_BUILD=1
    echo "VERSION=$CURRENT_VERSION" > "$BUILD_INFO_FILE"
    echo "BUILD=$NEW_BUILD" >> "$BUILD_INFO_FILE"
    echo "$NEW_BUILD"
else
    # Same version, increment build number
    NEW_BUILD=$((BUILD + 1))
    echo "VERSION=$CURRENT_VERSION" > "$BUILD_INFO_FILE"
    echo "BUILD=$NEW_BUILD" >> "$BUILD_INFO_FILE"
    echo "$NEW_BUILD"
fi