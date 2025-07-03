#!/bin/bash
# Buildbotics Subroutine Linking Script

UPLOAD_DIR="/var/lib/bbctrl/upload"
SUBROUTINE_DIR="$UPLOAD_DIR/Subroutines"

echo "========================================="
echo "Buildbotics Subroutine Linking Script"
echo "========================================="

# Check if Subroutines directory exists
if [ ! -d "$SUBROUTINE_DIR" ]; then
    echo "Creating Subroutines directory..."
    mkdir -p "$SUBROUTINE_DIR"
fi

echo "Upload Directory: $UPLOAD_DIR"
echo "Subroutine Directory: $SUBROUTINE_DIR"
echo ""

# Remove existing subroutine symlinks in root
echo "Removing old subroutine symlinks..."
find "$UPLOAD_DIR" -maxdepth 1 -type l -name "*.nc" -delete 2>/dev/null
echo ""

# Create symlinks for all .nc files in Subroutines directory
echo "Creating symbolic links for subroutines..."
link_count=0

if [ -d "$SUBROUTINE_DIR" ]; then
    for file in "$SUBROUTINE_DIR"/*.nc; do
        if [ -f "$file" ]; then
            basename=$(basename "$file")
            target="Subroutines/$basename"
            link="$UPLOAD_DIR/$basename"
            
            echo "  Linking $basename -> $target"
            ln -sf "$target" "$link"
            link_count=$((link_count + 1))
        fi
    done
    
    echo ""
    if [ $link_count -eq 0 ]; then
        echo "No .nc files found in Subroutines directory."
    else
        echo "Done! Created $link_count subroutine links."
    fi
else
    echo "Error: Subroutines directory not found: $SUBROUTINE_DIR"
    exit 1
fi

echo ""
echo "Current subroutine links in upload directory:"
ls -la "$UPLOAD_DIR" | grep "^l.*\.nc" || echo "  (no links found)"

echo ""
echo "Files in Subroutines directory:"
ls -la "$SUBROUTINE_DIR"

echo ""
echo "========================================="
echo "Usage in G-code: o<subroutine_name> call"
echo "Example: o<probe_z> call"
echo "========================================="
