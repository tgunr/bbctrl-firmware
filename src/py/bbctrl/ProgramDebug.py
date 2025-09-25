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

import re
from .Program import *

__all__ = ['ProgramDebug']


class ProgramDebug(Program):
    status = 'debugging'


    def __init__(self, ctrl, path):
        super().__init__(ctrl)
        self.path = path
        self.lines = []
        self.current_line = 0
        self.breakpoints = set()
        self.step_mode = True
        self.paused = True
        self.gcode_content = ''
        
        # Load and parse the G-code file
        self._load_file()
        self._parse_lines()


    def _load_file(self):
        """Load G-code file content"""
        try:
            realpath = self.ctrl.fs.realpath(self.path)
            with open(realpath, 'r') as f:
                self.gcode_content = f.read()
        except Exception as e:
            self.ctrl.log.get('Debug').error('Failed to load debug file %s: %s' % (self.path, e))
            raise


    def _parse_lines(self):
        """Parse G-code lines and identify executable vs comment lines"""
        self.lines = []
        for i, line in enumerate(self.gcode_content.split('\n')):
            line_info = {
                'number': i + 1,
                'content': line,
                'executable': self._is_executable_line(line.strip()),
                'original': line
            }
            self.lines.append(line_info)


    def _is_executable_line(self, line):
        """Determine if a line contains executable G-code"""
        if not line:
            return False
            
        # Remove leading/trailing whitespace
        line = line.strip()
        
        # Empty lines are not executable
        if not line:
            return False
            
        # Lines starting with semicolon are comments
        if line.startswith(';'):
            return False
            
        # Lines starting with parentheses are comments
        if line.startswith('(') and line.endswith(')'):
            return False
            
        # Lines that are only comments (after removing inline comments)
        # Remove inline comments (everything after semicolon or parentheses)
        clean_line = re.sub(r';.*$', '', line)  # Remove semicolon comments
        clean_line = re.sub(r'\([^)]*\)', '', clean_line)  # Remove parentheses comments
        clean_line = clean_line.strip()
        
        # If nothing left after removing comments, not executable
        if not clean_line:
            return False
            
        return True


    def start(self, mach, planner):
        """Start debug session"""
        self.ctrl.state.set('debug_mode', True)
        self.ctrl.state.set('debug_file', self.path)
        self.ctrl.state.set('debug_current_line', 0)
        self.ctrl.state.set('debug_breakpoints', list(self.breakpoints))
        
        # Find first executable line
        self.current_line = self._find_next_executable_line(0)
        if self.current_line is not None:
            self.ctrl.state.set('debug_current_line', self.current_line)
            
        self.ctrl.log.get('Debug').info('Started debugging %s' % self.path)
        return True


    def _find_next_executable_line(self, start_line):
        """Find the next executable line starting from start_line"""
        for i in range(start_line, len(self.lines)):
            if self.lines[i]['executable']:
                return i
        return None


    def _find_previous_executable_line(self, start_line):
        """Find the previous executable line before start_line"""
        for i in range(start_line - 1, -1, -1):
            if self.lines[i]['executable']:
                return i
        return None


    def step(self):
        """Execute current line and move to next executable line"""
        if self.current_line is None or self.current_line >= len(self.lines):
            return False
            
        current_line_info = self.lines[self.current_line]
        if current_line_info['executable']:
            # Execute the current line
            line_content = current_line_info['content'].strip()
            self.ctrl.log.get('Debug').info('Executing line %d: %s' % (self.current_line + 1, line_content))
            
            # Send to MDI for execution
            self.ctrl.mach.mdi(line_content, True)
            
        # Move to next executable line
        next_line = self._find_next_executable_line(self.current_line + 1)
        if next_line is not None:
            self.current_line = next_line
            self.ctrl.state.set('debug_current_line', self.current_line)
            return True
        else:
            # End of program
            self._end_debug_session()
            return False


    def skip(self):
        """Skip current line without executing and move to next executable line"""
        if self.current_line is None:
            return False
            
        current_line_info = self.lines[self.current_line]
        self.ctrl.log.get('Debug').info('Skipping line %d: %s' % (self.current_line + 1, current_line_info["content"].strip()))
        
        # Move to next executable line
        next_line = self._find_next_executable_line(self.current_line + 1)
        if next_line is not None:
            self.current_line = next_line
            self.ctrl.state.set('debug_current_line', self.current_line)
            return True
        else:
            # End of program
            self._end_debug_session()
            return False


    def skip_to(self, target_line_number):
        """Skip to specified line number (1-based)"""
        # Convert to 0-based index
        target_index = target_line_number - 1
        
        if target_index < 0 or target_index >= len(self.lines):
            raise ValueError('Line number %d is out of range' % target_line_number)
            
        # Find the next executable line at or after the target
        next_line = self._find_next_executable_line(target_index)
        if next_line is not None:
            self.current_line = next_line
            self.ctrl.state.set('debug_current_line', self.current_line)
            self.ctrl.log.get('Debug').info('Skipped to line %d' % (self.current_line + 1))
            return True
        else:
            # No executable lines found after target
            self._end_debug_session()
            return False


    def continue_execution(self):
        """Continue normal execution from current position"""
        if self.current_line is None:
            return False
            
        # Build G-code from current position to end
        remaining_lines = []
        for i in range(self.current_line, len(self.lines)):
            if self.lines[i]['executable']:
                remaining_lines.append(self.lines[i]['content'])
                
        if remaining_lines:
            # Execute remaining G-code as one block
            gcode_block = '\n'.join(remaining_lines)
            self.ctrl.log.get('Debug').info('Continuing execution from line %d' % (self.current_line + 1))
            self.ctrl.mach.mdi(gcode_block, True)
            
        self._end_debug_session()
        return True


    def set_breakpoint(self, line_number):
        """Set breakpoint at line number (1-based)"""
        # Convert to 0-based index
        line_index = line_number - 1
        
        if line_index < 0 or line_index >= len(self.lines):
            raise ValueError('Line number %d is out of range' % line_number)
            
        if not self.lines[line_index]['executable']:
            raise ValueError('Line %d is not executable' % line_number)
            
        self.breakpoints.add(line_index)
        self.ctrl.state.set('debug_breakpoints', list(self.breakpoints))
        self.ctrl.log.get('Debug').info('Breakpoint set at line %d' % line_number)


    def clear_breakpoint(self, line_number):
        """Clear breakpoint at line number (1-based)"""
        line_index = line_number - 1
        self.breakpoints.discard(line_index)
        self.ctrl.state.set('debug_breakpoints', list(self.breakpoints))
        self.ctrl.log.get('Debug').info('Breakpoint cleared at line %d' % line_number)


    def _end_debug_session(self):
        """End debug session and clean up"""
        self.ctrl.state.set('debug_mode', False)
        self.ctrl.state.set('debug_file', '')
        self.ctrl.state.set('debug_current_line', -1)
        self.ctrl.state.set('debug_breakpoints', [])
        self.ctrl.log.get('Debug').info('Debug session ended')


    def get_line_info(self, line_number):
        """Get information about a specific line (1-based)"""
        line_index = line_number - 1
        if line_index < 0 or line_index >= len(self.lines):
            return None
        return self.lines[line_index]


    def get_current_line_info(self):
        """Get information about current line"""
        if self.current_line is None:
            return None
        return self.lines[self.current_line]