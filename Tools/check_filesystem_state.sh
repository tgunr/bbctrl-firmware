#!/bin/bash

echo "=== Buildbotics Controller Filesystem State Check ==="
echo "Timestamp: $(date)"
echo

echo "1. Checking bbctrl working directory and upload folder..."
echo "Working directory: /var/lib/bbctrl"
ls -la /var/lib/bbctrl/ 2>/dev/null || echo "ERROR: /var/lib/bbctrl does not exist"
echo

echo "Upload directory: /var/lib/bbctrl/upload"
ls -la /var/lib/bbctrl/upload/ 2>/dev/null || echo "ERROR: /var/lib/bbctrl/upload does not exist"
echo

echo "2. Checking if buildbotics.nc exists..."
if [ -f "/var/lib/bbctrl/upload/buildbotics.nc" ]; then
    echo "✓ buildbotics.nc exists"
    ls -la /var/lib/bbctrl/upload/buildbotics.nc
else
    echo "✗ buildbotics.nc is missing"
fi
echo

echo "3. Checking directory permissions..."
echo "bbctrl directory permissions:"
ls -ld /var/lib/bbctrl/ 2>/dev/null || echo "Directory does not exist"
echo "upload directory permissions:"
ls -ld /var/lib/bbctrl/upload/ 2>/dev/null || echo "Directory does not exist"
echo

echo "4. Checking disk space..."
df -h /var/lib/bbctrl/ 2>/dev/null || echo "Cannot check disk space"
echo

echo "5. Testing API endpoint directly..."
echo "--- Testing /api/fs/ ---"
curl -s http://localhost:8080/api/fs/ | python3 -m json.tool 2>/dev/null || echo "API call failed or returned non-JSON"
echo

echo "6. Testing specific file that's failing..."
echo "--- Testing /api/fs/Home/buildbotics.nc ---"
curl -v http://localhost:8080/api/fs/Home/buildbotics.nc 2>&1
echo

echo "=== Filesystem state check complete ==="