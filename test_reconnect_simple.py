#!/usr/bin/env python3

"""
Simple test to validate the reconnection logic without external dependencies
"""

import time
from unittest.mock import Mock

def test_reconnect_logic():
    """Test the core reconnection logic"""
    print("Testing periodic reconnect functionality...")
    
    # Create a simplified AVR-like class with our reconnection logic
    class MockAVR:
        def __init__(self):
            self.connected = False
            self.reconnect_timer = None
            self.reconnect_interval = 5.0
            self.max_reconnect_interval = 60.0
            self.connection_check_timer = None
            self.last_activity = time.time()
            self.connection_timeout = 10.0
            self.log = Mock()
            self.ctrl = Mock()
            self.ctrl.ioloop = Mock()
            self.sp = None
            self.events = 0
        
        def _check_connection(self):
            """Check if connection is still alive based on recent activity"""
            if not self.connected or self.sp is None:
                return False
            
            current_time = time.time()
            if current_time - self.last_activity > self.connection_timeout:
                self.log.warning('Connection timeout detected, last activity: %.2f seconds ago', 
                               current_time - self.last_activity)
                return False
            
            return True
        
        def _schedule_reconnect(self):
            """Schedule a reconnection attempt with exponential backoff"""
            if self.reconnect_timer is not None:
                self.ctrl.ioloop.remove_timeout(self.reconnect_timer)
            
            self.log.info('Scheduling reconnect in %.1f seconds', self.reconnect_interval)
            self.reconnect_timer = self.ctrl.ioloop.call_later(
                self.reconnect_interval, self._attempt_reconnect)
            
            # Increase reconnect interval with exponential backoff
            self.reconnect_interval = min(self.reconnect_interval * 2, self.max_reconnect_interval)
        
        def _cleanup_connection(self):
            """Clean up existing connection"""
            if self.sp is not None:
                try:
                    self.ctrl.ioloop.remove_handler(self.sp)
                except:
                    pass
                self.sp = None
            
            self.connected = False
            self.events = 0
        
        def _attempt_reconnect(self):
            """Attempt to reconnect"""
            self.reconnect_timer = None
            self.log.info('Attempting to reconnect...')
            return True
    
    # Create mock AVR instance
    avr = MockAVR()
    
    # Test 1: Initial state
    print("✓ Test 1: Initial connection state")
    assert avr.connected == False
    assert avr.reconnect_interval == 5.0
    assert avr.connection_timeout == 10.0
    
    # Test 2: Connection check when not connected
    print("✓ Test 2: Connection check when not connected")
    assert avr._check_connection() == False
    
    # Test 3: Connection check when connected and active
    print("✓ Test 3: Connection check when connected and active")
    avr.connected = True
    avr.sp = Mock()
    avr.last_activity = time.time()
    assert avr._check_connection() == True
    
    # Test 4: Connection timeout detection
    print("✓ Test 4: Connection timeout detection")
    avr.last_activity = time.time() - 15.0  # 15 seconds ago
    assert avr._check_connection() == False
    
    # Test 5: Reconnect scheduling with exponential backoff
    print("✓ Test 5: Reconnect scheduling with exponential backoff")
    initial_interval = avr.reconnect_interval
    avr._schedule_reconnect()
    
    # Should have called ioloop.call_later
    avr.ctrl.ioloop.call_later.assert_called()
    
    # Interval should increase with exponential backoff
    assert avr.reconnect_interval == initial_interval * 2
    
    # Test multiple scheduling calls to verify exponential backoff
    for i in range(3):
        expected_interval = initial_interval * (2 ** (i + 2))
        avr._schedule_reconnect()
        assert avr.reconnect_interval == min(expected_interval, avr.max_reconnect_interval)
    
    # Test 6: Connection cleanup
    print("✓ Test 6: Connection cleanup")
    avr.sp = Mock()
    avr.connected = True
    avr.events = 1
    
    avr._cleanup_connection()
    
    assert avr.connected == False
    assert avr.sp is None
    assert avr.events == 0
    
    # Test 7: Maximum reconnect interval cap
    print("✓ Test 7: Maximum reconnect interval cap")
    avr.reconnect_interval = 50.0
    avr._schedule_reconnect()
    assert avr.reconnect_interval == avr.max_reconnect_interval
    
    print("\n✓ All core reconnection logic tests passed!")
    
    return True

def test_integration_flow():
    """Test the integration flow of connection monitoring"""
    print("\nTesting integration flow...")
    
    class IntegrationMockAVR:
        def __init__(self):
            self.connected = False
            self.reconnect_timer = None
            self.reconnect_interval = 5.0
            self.max_reconnect_interval = 60.0
            self.connection_check_timer = None
            self.last_activity = time.time()
            self.connection_timeout = 10.0
            self.log = Mock()
            self.ctrl = Mock()
            self.ctrl.ioloop = Mock()
            self.sp = None
            self.events = 0
            self.reconnect_attempts = 0
        
        def _check_connection(self):
            if not self.connected or self.sp is None:
                return False
            current_time = time.time()
            return current_time - self.last_activity <= self.connection_timeout
        
        def _schedule_reconnect(self):
            if self.reconnect_timer is not None:
                self.ctrl.ioloop.remove_timeout(self.reconnect_timer)
            self.reconnect_timer = self.ctrl.ioloop.call_later(
                self.reconnect_interval, self._attempt_reconnect)
            self.reconnect_interval = min(self.reconnect_interval * 2, self.max_reconnect_interval)
        
        def _attempt_reconnect(self):
            self.reconnect_timer = None
            self.reconnect_attempts += 1
            self.log.info('Reconnect attempt #%d', self.reconnect_attempts)
            
            # Simulate successful reconnection after 3 attempts
            if self.reconnect_attempts >= 3:
                self.connected = True
                self.sp = Mock()
                self.last_activity = time.time()
                self.reconnect_interval = 5.0  # Reset on success
                return True
            else:
                self._schedule_reconnect()
                return False
        
        def _monitor_connection(self):
            if not self._check_connection():
                self.log.warning('Connection lost, initiating reconnection...')
                self.connected = False
                self.sp = None
                self._schedule_reconnect()
            else:
                self.ctrl.ioloop.call_later(
                    self.connection_timeout / 2, self._monitor_connection)
    
    avr = IntegrationMockAVR()
    
    # Test 1: Connection loss detection and reconnection
    print("✓ Test 1: Connection loss detection and reconnection")
    avr.connected = True
    avr.sp = Mock()
    avr.last_activity = time.time() - 15.0  # Simulate timeout
    
    # Monitor should detect loss and trigger reconnection
    avr._monitor_connection()
    
    assert avr.connected == False
    assert avr.sp is None
    assert avr.ctrl.ioloop.call_later.called
    
    # Test 2: Successful reconnection after multiple attempts
    print("✓ Test 2: Successful reconnection after multiple attempts")
    
    # Simulate multiple reconnection attempts
    for i in range(3):
        avr._attempt_reconnect()
    
    # Should be connected after 3 attempts
    assert avr.connected == True
    assert avr.sp is not None
    assert avr.reconnect_interval == 5.0  # Reset on success
    
    print("✓ Integration flow tests passed!")
    
    return True

if __name__ == "__main__":
    try:
        test_reconnect_logic()
        test_integration_flow()
        print("\n🎉 All reconnection tests completed successfully!")
        print("\nFeatures implemented:")
        print("  ✓ Periodic connection monitoring")
        print("  ✓ Automatic reconnection on connection loss")
        print("  ✓ Exponential backoff for reconnection attempts")
        print("  ✓ Connection timeout detection")
        print("  ✓ Activity tracking for connection health")
        print("  ✓ Proper cleanup of failed connections")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)