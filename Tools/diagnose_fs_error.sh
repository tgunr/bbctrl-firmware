#!/bin/bash

echo "=== Buildbotics Controller /api/fs/ Diagnostic Script ==="
echo "Timestamp: $(date)"
echo

echo "1. Checking current bbctrl service status..."
sudo systemctl status bbctrl --no-pager
echo

echo "2. Checking if bbctrl process is running..."
ps aux | grep -v grep | grep bbctrl
echo

echo "3. Checking current log tail (last 20 lines)..."
echo "--- Current bbctrl.log ---"
sudo tail -20 /var/log/bbctrl.log
echo

echo "4. Restarting bbctrl service to apply diagnostic logging..."
sudo systemctl restart bbctrl
echo "Service restart initiated..."
sleep 3

echo "5. Checking service status after restart..."
sudo systemctl status bbctrl --no-pager
echo

echo "6. Waiting 5 seconds for initialization..."
sleep 5

echo "7. Checking new log entries (last 50 lines)..."
echo "--- New bbctrl.log entries ---"
sudo tail -50 /var/log/bbctrl.log
echo

echo "8. Testing /api/fs/ endpoint..."
echo "--- Testing API endpoint ---"
curl -v http://localhost:8080/api/fs/ 2>&1 || echo "API call failed"
echo

echo "9. Final log check (last 30 lines after API test)..."
echo "--- Final bbctrl.log entries ---"
sudo tail -30 /var/log/bbctrl.log
echo

echo "=== Diagnostic complete ==="
echo "Look for 'FileSystem' entries in the logs above to identify the issue."