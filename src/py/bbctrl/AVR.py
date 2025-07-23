################################################################################
#                                                                              #
#                 This file is part of the Buildbotics firmware.               #
#                                                                              #
#        Copyright (c) 2015 - 2023, Buildbotics LLC, All rights reserved.      #
#                                                                              #
#         This Source describes Open Hardware and is licensed under the        #
#                                 CERN-OHL-S v2.                               #
#                                                                              #
#         You may redistribute and modify this Source and make products        #
#    using it under the terms of the CERN-OHL-S v2 (https:/cern.ch/cern-ohl).  #
#           This Source is distributed WITHOUT ANY EXPRESS OR IMPLIED          #
#    WARRANTY, INCLUDING OF MERCHANTABILITY, SATISFACTORY QUALITY AND FITNESS  #
#     FOR A PARTICULAR PURPOSE. Please see the CERN-OHL-S v2 for applicable    #
#                                  conditions.                                 #
#                                                                              #
#                Source location: https://github.com/buildbotics               #
#                                                                              #
#      As per CERN-OHL-S v2 section 4, should You produce hardware based on    #
#    these sources, You must maintain the Source Location clearly visible on   #
#    the external case of the CNC Controller or other product you make using   #
#                                  this Source.                                #
#                                                                              #
#                For more information, email info@buildbotics.com              #
#                                                                              #
################################################################################

import os
import time
import traceback
import ctypes
import math

# Optional runtime dependency: pyserial
# Provide a lightweight stub so that modules can still import AVR
# in environments where pyserial isn't installed (e.g. CI or doc generation).
# The real Serial implementation is only required when hardware
# access is needed.  Tests that merely import the module will succeed.
try:
    import serial  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    import types, sys
    serial = types.ModuleType("serial")                    # type: ignore
    class _DummySerial:                                    # pylint: disable=too-few-public-methods
        def __init__(self, *_, **__):
            pass
        # API subset used in AVR
        def nonblocking(self):            # noqa: D401
            pass
        def reset_output_buffer(self):
            pass
        def read(self, _n):               # noqa: D401
            return b""
        def write(self, _data):           # noqa: D401
            return 0
        def close(self):                  # noqa: D401
            pass
        in_waiting = 0                    # mimic property

    serial.Serial = _DummySerial          # type: ignore
    serial.SerialException = Exception    # type: ignore
    sys.modules["serial"] = serial

__all__ = ['AVR']


class _serial_struct(ctypes.Structure):
    _fields_ = [
        ('type',            ctypes.c_int),
        ('line',            ctypes.c_int),
        ('port',            ctypes.c_uint),
        ('irq',             ctypes.c_int),
        ('flags',           ctypes.c_int),
        ('xmit_fifo_size',  ctypes.c_int),
        ('custom_divisor',  ctypes.c_int),
        ('baud_base',       ctypes.c_int),
        ('close_delay',     ctypes.c_ushort),
        ('io_type',         ctypes.c_byte),
        ('reserved',        ctypes.c_byte),
        ('hub6',            ctypes.c_int),
        ('closing_wait',    ctypes.c_ushort),
        ('closing_wait2',   ctypes.c_ushort),
        ('iomem_base',      ctypes.c_char_p),
        ('iomem_reg_shift', ctypes.c_ushort),
        ('port_high',       ctypes.c_uint),
        ('iomap_base',      ctypes.c_ulong),
    ]


def _serial_set_low_latency(sp):
    import fcntl
    import termios

    ASYNCB_LOW_LATENCY = 13

    ss = _serial_struct()
    fcntl.ioctl(sp, termios.TIOCGSERIAL, ss)
    ss.flags |= 1 << ASYNCB_LOW_LATENCY # pylint: disable=no-member
    fcntl.ioctl(sp, termios.TIOCSSERIAL, ss)



class AVR(object):
    def __init__(self, ctrl):
        self.ctrl     = ctrl
        self.log      = ctrl.log.get('AVR')
        self.sp       = None
        self.i2c_addr = ctrl.args.avr_addr
        self.read_cb  = None
        self.write_cb = None
        self.events   = 0
        self.errors   = 0
        self.connected = False
        self.reconnect_timer = None
        self.reconnect_interval = 5.0  # Initial reconnect interval in seconds
        self.max_reconnect_interval = 60.0  # Maximum reconnect interval
        self.connection_check_timer = None
        self.last_activity = time.time()
        self.connection_timeout = 10.0  # Timeout for detecting lost connection


    def close(self):
        self.connected = False
        if self.reconnect_timer is not None:
            self.ctrl.ioloop.remove_timeout(self.reconnect_timer)
            self.reconnect_timer = None
        if self.connection_check_timer is not None:
            self.ctrl.ioloop.remove_timeout(self.connection_check_timer)
            self.connection_check_timer = None
        if self.sp is not None:
            try:
                self.sp.close()
            except:
                pass
            self.sp = None


    def flush_output(self):
        if self.sp is not None:
            self.sp.reset_output_buffer()


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


    def _attempt_reconnect(self):
        """Attempt to reconnect to the AVR"""
        self.reconnect_timer = None
        self.log.info('Attempting to reconnect to AVR...')
        
        try:
            self._cleanup_connection()
            self._start()
            
            if self.connected:
                self.log.info('Successfully reconnected to AVR')
                self.reconnect_interval = 5.0  # Reset reconnect interval on success
                self._start_connection_monitoring()
            else:
                self.log.warning('Reconnection attempt failed')
                self._schedule_reconnect()
                
        except Exception as e:
            self.log.error('Reconnection attempt failed: %s', e)
            self._schedule_reconnect()


    def _start_connection_monitoring(self):
        """Start periodic connection monitoring"""
        if self.connection_check_timer is not None:
            self.ctrl.ioloop.remove_timeout(self.connection_check_timer)
        
        self.connection_check_timer = self.ctrl.ioloop.call_later(
            self.connection_timeout / 2, self._monitor_connection)


    def _monitor_connection(self):
        """Monitor connection status and trigger reconnection if needed"""
        if not self._check_connection():
            self.log.warning('Connection lost, initiating reconnection...')
            self.connected = False
            self._cleanup_connection()
            self._schedule_reconnect()
        else:
            # Schedule next monitoring check
            self.connection_check_timer = self.ctrl.ioloop.call_later(
                self.connection_timeout / 2, self._monitor_connection)


    def _cleanup_connection(self):
        """Clean up existing connection"""
        if self.sp is not None:
            try:
                self.ctrl.ioloop.remove_handler(self.sp)
            except:
                pass
            try:
                self.sp.close()
            except:
                pass
            self.sp = None
        
        self.connected = False
        self.events = 0


    def _reset(self, active):
        try:
            gpio = '/sys/class/gpio/gpio27'

            if not os.path.exists(gpio):
                with open('/sys/class/gpio/export', 'w') as f: f.write('27\n')

            if active:
                with open(gpio + '/direction', 'w') as f: f.write('out\n')
                with open(gpio + '/value',     'w') as f: f.write('1\n')

            else:
                with open(gpio + '/direction', 'w') as f: f.write('in\n')

        except Exception as e:
            self.log.exception('Reset failed')


    def _start(self):
        self._reset(True)
        self._reset(False)

        try:
            self.sp = serial.Serial(self.ctrl.args.serial, self.ctrl.args.baud,
                                    rtscts = 1, timeout = 0, write_timeout = 0)
            self.sp.nonblocking()
            #_serial_set_low_latency(self.sp)

            self.ctrl.ioloop.add_handler(self.sp, self._serial_handler, 0)
            self.enable_read(True)
            self.connected = True
            self.last_activity = time.time()

        except Exception as e:
            self.sp = None
            self.connected = False
            self.log.warning('Failed to open serial port: %s', e)


    def set_handlers(self, read_cb, write_cb):
        if self.read_cb is not None or self.write_cb is not None:
            raise Exception('Handlers already set')

        self.read_cb  = read_cb
        self.write_cb = write_cb
        self._start()
        
        # Start connection monitoring if connection was successful
        if self.connected:
            self._start_connection_monitoring()
        else:
            # If initial connection failed, schedule reconnection
            self._schedule_reconnect()


    def update_events(self, events, enable):
        if self.sp is None: return

        if enable: self.events |= events
        else: self.events &= ~events

        self.ctrl.ioloop.update_handler(self.sp, self.events)


    def enable_write(self, enable):
        self.update_events(self.ctrl.ioloop.WRITE, enable)


    def enable_read(self, enable):
        self.update_events(self.ctrl.ioloop.READ, enable)


    def _serial_handler(self, fd, events):
        try:
            if self.ctrl.ioloop.READ & events:
                self.last_activity = time.time()  # Update activity timestamp
                self.read_cb(self.sp.read(self.sp.in_waiting))

            if self.ctrl.ioloop.WRITE & events:
                self.last_activity = time.time()  # Update activity timestamp
                self.write_cb(lambda data: self.sp.write(data))

            self.errors = 0

        except Exception as e:
            self.log.warning('Serial: %s', e)

            # Check if this is a connection error that requires reconnection
            if "device or resource busy" in str(e).lower() or "input/output error" in str(e).lower():
                self.log.error('Serial connection error detected, initiating reconnection...')
                self.connected = False
                self._cleanup_connection()
                self._schedule_reconnect()
                return

            # Delay next IO for other errors
            self.errors += 1
            delay = 0.1 * math.pow(2, min(6, self.errors))

            events = self.events
            self.update_events(events, False)

            self.ctrl.ioloop.call_later(delay, self.update_events, events, True)


    def i2c_command(self, cmd, byte = None, word = None, block = None):
        self.log.info('I2C: %s b=%s w=%s d=%s' % (cmd, byte, word, block))
        retry = 10
        cmd = ord(cmd[0])

        while True:
            try:
                self.ctrl.i2c.write(self.i2c_addr, cmd, byte, word, block)
                break

            except Exception as e:
                retry -= 1

                if retry:
                    self.log.warning('I2C failed, retrying: %s' % e)
                    time.sleep(0.25)
                    continue

                else:
                    self.log.error('I2C failed: %s' % e)
                    raise
