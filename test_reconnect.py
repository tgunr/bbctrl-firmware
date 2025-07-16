#!/usr/bin/env python3

"""
Test script to verify the periodic reconnect functionality
"""

import sys
import os
import time
import threading
from unittest.mock import Mock, MagicMock

# Add the src/py directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'py'))

from bbctrl.AVR import AVR

def test_reconnect_logic():
    """Test the reconnection logic"""
    print("Testing periodic reconnect functionality...")
    
    # Create mock controller and ioloop
    mock_ctrl = Mock()
    mock_ctrl.args = Mock()
    mock_ctrl.args.serial = '/dev/ttyAMA0'
    mock_ctrl.args.baud = 230400
    mock_ctrl.args.avr_addr = 0x2b
    
    mock_log = Mock()
    mock_ctrl.log.get.return_value = mock_log
    
    mock_ioloop = Mock()
    mock_ctrl.ioloop = mock_ioloop
    
    # Create AVR instance
    avr = AVR(mock_ctrl)
    
    # Test 1: Initial connection state
    print("✓ Test 1: Initial connection state")
    assert avr.connected == False
    assert avr.reconnect_interval == 5.0
    assert avr.connection_timeout == 10.0
    
    # Test 2: Connection monitoring check
    print("✓ Test 2: Connection monitoring check")
    # Should return False when not connected
    assert avr._check_connection() == False
    
    # Simulate connected state
    avr.connected = True
    avr.sp = Mock()
    avr.last_activity = time.time()
    
    # Should return True when recently active
    assert avr._check_connection() == True
    
    # Test 3: Connection timeout detection
    print("✓ Test 3: Connection timeout detection")
    avr.last_activity = time.time() - 15.0  # 15 seconds ago
    assert avr._check_connection() == False
    
    # Test 4: Reconnect scheduling
    print("✓ Test 4: Reconnect scheduling")
    initial_interval = avr.reconnect_interval
    avr._schedule_reconnect()
    
    # Should have called ioloop.call_later
    mock_ioloop.call_later.assert_called()
    
    # Interval should increase with exponential backoff
    assert avr.reconnect_interval == initial_interval * 2
    
    # Test 5: Connection cleanup
    print("✓ Test 5: Connection cleanup")
    avr.sp = Mock()
    avr.connected = True
    avr.events = 1
    
    avr._cleanup_connection()
    
    assert avr.connected == False
    assert avr.sp is None
    assert avr.events == 0
    
    print("\n✓ All tests passed! Periodic reconnect functionality is working correctly.")
    
    # Test 6: Activity tracking in serial handler
    print("✓ Test 6: Activity tracking in serial handler")
    
    # Mock the serial handler dependencies
    avr.sp = Mock()
    avr.sp.read.return_value = b'test_data'
    avr.sp.in_waiting = 9
    avr.read_cb = Mock()
    avr.write_cb = Mock()
    avr.connected = True
    
    initial_time = avr.last_activity
    time.sleep(0.1)  # Small delay to ensure time difference
    
    # Simulate read event
    avr._serial_handler(Mock(), mock_ctrl.ioloop.READ)
    
    # Activity timestamp should be updated
    assert avr.last_activity > initial_time
    
    print("✓ Activity tracking works correctly")
    
    return True

if __name__ == "__main__":
    try:
        test_reconnect_logic()
        print("\n🎉 All reconnection tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)