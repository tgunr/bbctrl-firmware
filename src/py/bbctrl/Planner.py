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

import json
import math
import re
import time
from collections import deque

from . import Cmd
from .CommandQueue import *

try:
    from . import camotics # pylint: disable=no-name-in-module,import-error
    CAMOTICS_AVAILABLE = True
except ImportError as e:
    print('Error loading camotics:', str(e))
    CAMOTICS_AVAILABLE = False
    camotics = None

__all__ = ['Planner']


reLogLine = re.compile(
    r'^(?P<level>[A-Z])[0-9 ]:'
    r'((?P<file>[^:]+):)?'
    r'((?P<line>\d+):)?'
    r'((?P<column>\d+):)?'
    r'(?P<msg>.*)$')


def log_floats(o):
    if isinstance(o, float): return round(o, 2)
    if isinstance(o, dict): return {k: log_floats(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [log_floats(x) for x in o]
    return o


def log_json(o): return json.dumps(log_floats(o))


class Planner():
    def __init__(self, ctrl):
        self.ctrl          = ctrl
        self.log           = ctrl.log.get('Planner')
        self.cmdq          = CommandQueue(ctrl)
        self.end_callbacks = deque()
        self.planner       = None
        self.where         = ''

        ctrl.state.add_listener(self._update)

        try:
            self.reset(False)
            self._report_time()
        except Exception as e:
            self.log.exception()


    def is_busy(self): return self.is_running() or self.cmdq.is_active()


    def is_running(self):
        return self.planner is not None and self.planner.is_running()


    def get_config(self, with_start, with_limits):
        state     = self.ctrl.state
        config    = self.ctrl.config
        is_pwm    = config.get('tool-type') == 'PWM Spindle'
        deviation = config.get('max-deviation', 0.1)

        cfg = {
            # NOTE Must get current units not configured default units
            'default-units': 'METRIC' if state.get('metric') else 'IMPERIAL',
            'max-vel':         state.get_axis_vector('vm', 1000),
            'max-accel':       state.get_axis_vector('am', 1000000),
            'max-jerk':        state.get_axis_vector('jm', 1000000),
            'rapid-auto-off':  config.get('rapid-auto-off') and is_pwm,
            'max-blend-error': deviation,
            'max-merge-error': deviation,
            'max-arc-error':   deviation / 10,
            'junction-accel':  config.get('junction-accel'),
        }

        if with_limits:
            minLimit = state.get_soft_limit_vector('tn', -math.inf)
            maxLimit = state.get_soft_limit_vector('tm', math.inf)

            # If max <= min then no limit
            for axis in 'xyzabc':
                if maxLimit[axis] <= minLimit[axis]:
                    minLimit[axis], maxLimit[axis] = -math.inf, math.inf

            cfg['min-soft-limit'] = minLimit
            cfg['max-soft-limit'] = maxLimit

        if with_start:
            program_start = config.get('program-start')
            if program_start: cfg['program-start'] = program_start

        overrides = {}

        tool_change = config.get('tool-change')
        if tool_change: overrides['M6'] = tool_change

        program_end = config.get('program-end')
        if program_end:
            overrides['M2'] = program_end
            overrides['M30'] = program_end

        if overrides: cfg['overrides'] = overrides

        self.log.info('Config:' + log_json(cfg))

        return cfg


    def _update(self, update):
        if 'id' in update:
            id = update['id']
            if self.planner is not None:
                self.planner.set_active(id) # Release planner commands
            self.cmdq.release(id)       # Synchronize planner variables


    def _get_var_cb(self, name, units):
        value = 0

        if len(name) and name[0] == '_':
            value = self.ctrl.state.get(name[1:], 0)
            try:
                float(value)
                if units == 'IMPERIAL': value /= 25.4 # Assume metric
            except ValueError: value = 0

        self.log.info('Get: %s=%s (units=%s)' % (name, value, units))

        return value


    def _log_cb(self, line):
        line = line.strip()
        m = reLogLine.match(line)
        if not m: return

        level    = m.group('level')
        msg      = m.group('msg')
        filename = m.group('file')
        line     = m.group('line')
        column   = m.group('column')

        where = ':'.join(filter(None.__ne__, [filename, line, column]))

        if line is not None: line = int(line)
        if column is not None: column = int(column)

        if   level == 'I': self.log.info   (msg, where = where)
        elif level == 'D': self.log.debug  (msg, where = where)
        elif level == 'W': self.log.warning(msg, where = where)
        elif level == 'E': self.log.error  (msg, where = where)
        else: self.log.error('Could not parse planner log line: ' + line)


    def _add_message(self, text):
        self.ctrl.state.add_message(text)

        line = self.ctrl.state.get('line', 0)
        if 0 <= line: where = '%s:%d' % (self.where, line)
        else: where = self.where

        self.log.message(text, where = where)


    def _enqueue_set_cmd(self, id, name, value):
        self.log.info('set(#%d, %s, %s)', id, name, value)
        self.cmdq.enqueue(id, self.ctrl.state.set, name, value)


    def _report_time(self):
        state = self.ctrl.state.get('xx', '')

        if state in ('STOPPING', 'RUNNING') and self.move_start:
            delta = time.time() - self.move_start
            if self.move_time < delta: delta = self.move_time
            plan_time = self.current_plan_time + delta

            self.ctrl.state.set('plan_time', round(plan_time))

        elif state != 'HOLDING': self.ctrl.state.set('plan_time', 0)

        self.ctrl.ioloop.call_later(1, self._report_time)


    def _plan_time_restart(self):
        self.plan_time = self.ctrl.state.get('plan_time', 0)


    def _update_time(self, plan_time, move_time):
        self.current_plan_time = plan_time
        self.move_time = move_time
        self.move_start = time.time()


    def _enqueue_line_time(self, block):
        if block.get('first', False) or block.get('seeking', False): return

        # Sum move times
        move_time = sum(block['times']) / 1000 # To seconds

        self.cmdq.enqueue(block['id'], self._update_time, self.plan_time,
                          move_time)

        self.plan_time += move_time


    def _enqueue_dwell_time(self, block):
        self.cmdq.enqueue(block['id'], self._update_time, self.plan_time,
                          block['seconds'])
        self.plan_time += block['seconds']


    def __encode(self, block):
        type, id = block['type'], block['id']

        if type == 'start': return # ignore

        if type != 'set': self.log.info('Cmd:' + log_json(block))

        if type == 'line':
            self._enqueue_line_time(block)
            return Cmd.line(block['target'], block['exit-vel'],
                            block['max-accel'], block['max-jerk'],
                            block['times'], block.get('speeds', []))

        if type == 'set':
            name, value = block['name'], block['value']

            if name == 'message':
                self.cmdq.enqueue(id, self._add_message, value)

            if name in ['line', 'tool']: self._enqueue_set_cmd(id, name, value)

            if name == 'speed':
                self._enqueue_set_cmd(id, name, value)
                return Cmd.speed(value)

            if len(name) and name[0] == '_':
                # Don't queue axis positions, can be triggered by new position
                if len(name) != 2 or name[1] not in 'xyzabc':
                    self._enqueue_set_cmd(id, name[1:], value)

            if name == '_feed': # Must come after _enqueue_set_cmd() above
                return Cmd.set_sync('if', 1 / value if value else 0)

            if name[0:1] == '_' and name[1:2] in 'xyzabc':
                if name[2:] == '_home': return Cmd.set_axis(name[1], value)

                if name[2:] == '_homed':
                    motor = self.ctrl.state.find_motor(name[1])
                    if motor is not None:
                        return Cmd.set_sync('%dh' % motor, value)

            return

        if type == 'input':
            return Cmd.input(block['port'], block['mode'], block['timeout'])

        if type == 'output':
            return Cmd.output(block['port'], int(float(block['value'])))

        if type == 'dwell':
            self._enqueue_dwell_time(block)
            return Cmd.dwell(block['seconds'])

        if type == 'pause': return Cmd.pause(block['pause-type'])

        if type == 'seek':
            sw = self.ctrl.state.get_switch_id(block['switch'])
            return Cmd.seek(sw, block['active'], block['error'])

        if type == 'end':
            self.cmdq.enqueue(id, self._end_program, 'Program end')
            return '' # Blank command still sends command id

        raise Exception('Unknown planner command "%s"' % type)


    def _encode(self, block):
        cmd = self.__encode(block)

        if cmd is not None:
            # Enqueue id with no callback to track command activity
            self.cmdq.enqueue(block['id'], None)
            return Cmd.set_sync('id', block['id']) + '\n' + cmd


    def reset_times(self):
        self.move_start = 0
        self.move_time = 0
        self.plan_time = 0
        self.current_plan_time = 0


    def close(self):
        # Release planner callbacks
        if self.planner is not None:
            self.planner.set_resolver(None)
            if CAMOTICS_AVAILABLE:
                camotics.set_logger(None)


    def reset(self, stop = True):
        self._end_program('Program reset', True)
        if stop: self.ctrl.mach.stop()
<<<<<<< HEAD

        if not CAMOTICS_AVAILABLE:
            raise ImportError("Camotics module is required for motion planning but could not be imported. "
                            "Please ensure camotics is properly installed.")

        self.planner = camotics.Planner()
        self.planner.set_resolver(self._get_var_cb)
        # TODO logger is global and will not work correctly in demo mode
        camotics.set_logger(self._log_cb, 1, 'LinePlanner:3')
=======
        self.planner = None
        try:
            import camotics
            self.planner = camotics.Planner()
        except (ImportError, NameError):
            self.log.error('CAMotics not available')
        if self.planner is not None:
            self.planner.set_resolver(self._get_var_cb)
            # TODO logger is global and will not work correctly in demo mode
            camotics.set_logger(self._log_cb, 1, 'LinePlanner:3')
>>>>>>> c6a0e630340ffc26531cb57095df7ec9284c1903
        self.cmdq.clear()
        self.reset_times()
        self.ctrl.state.reset()


    def result(self, result): 
        if self.planner is not None:
            self.planner.synchronize(result)


    def _end_program(self, msg = None, end_all = False):
        self.ctrl.state.set('active_program', None)

        if end_all:
            while len(self.end_callbacks):
                self.end_callbacks.popleft()()

        else: self.end_callbacks.popleft()()

        if msg is not None: self.log.info(msg, time = True)


    def load(self, cb, path, mdi = None, with_start = True, with_limits = True):
        self.end_callbacks.append(cb)
        self.where = path
        self.log.info('Start: ' + path, time = True)
        self.ctrl.state.set('active_program', path)
        # Sync position
        if self.planner is not None:
            self.planner.set_position(self.ctrl.state.get_position())

        config = self.get_config(with_start, with_limits)
        if mdi is not None:
            if self.planner is not None:
                self.planner.load_string(mdi, config)
        else:
            if self.planner is not None:
                self.planner.load(self.ctrl.fs.realpath(path), config)

        self.reset_times()


    def stop(self):
        try:
            if self.planner is not None:
                self.planner.stop()
            self.cmdq.clear()
            self._end_program('Program stop', True)

        except:
            self.log.exception()
            self.reset()


    def restart(self):
        try:
            id = self.ctrl.state.get('id')
            position = self.ctrl.state.get_position()

            self.log.info('Planner restart: %d %s' % (id, log_json(position)))

            self.cmdq.clear()
            self.cmdq.release(id)
            self._plan_time_restart()
            if self.planner is not None:
                self.planner.restart(id, position)

        except:
            self.log.exception()
            self.stop()


    def next(self):
        try:
            if self.planner is not None:
                while self.planner.has_more():
                    cmd = self._encode(self.planner.next())
                    if cmd is not None: return cmd

        except RuntimeError as e:
            # Pass on the planner message
            self.log.error(str(e))
            self.stop()

        except:
            self.log.exception()
            self.stop()
