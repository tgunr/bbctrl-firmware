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

from .IOLoop import *
from .Log import *
from .Events import *
from .State import *
from .Config import *
from .AVREmu import *
from .AVR import *
from .I2C import *
from .LCD import *
from .Mach import *
from .Preplanner import *
from .FileSystem import *
from .Network import *
from .Jog import *
from .Pwr import *
from .MainLCDPage import *
from .IPLCDPage import *

__all__ = ['Ctrl']


class Ctrl:
    def __init__(self, args, ioloop, udevev, id):
        self.args     = args
        self.ioloop   = IOLoop(ioloop)
        self.udevev   = udevev
        self.id       = id
        self.timeout  = None # Used in demo mode
        self.sessions = {}

        if id:
            if not os.path.exists(id): os.mkdir(id)
            self.root = './' + id
        else: self.root = '.'

        # Start log
        if args.demo: log_path = self.get_path(filename = 'bbctrl.log')
        else: log_path = args.log
        self.log = Log(args, self.ioloop, log_path)

        self.events = Events(self)
        self.state  = State(self)
        self.config = Config(self)

        self.log.get('Ctrl').info('Starting %s' % self.id)

        try:
            self.log.get('Ctrl').info('Initializing AVR...')
            if args.demo: self.avr = AVREmu(self)
            else: self.avr = AVR(self)

            self.log.get('Ctrl').info('Initializing I2C...')
            self.i2c = I2C(args.i2c_port, args.demo)
            self.log.get('Ctrl').info('Initializing LCD...')
            self.lcd = LCD(self)
            self.log.get('Ctrl').info('Initializing Mach...')
            self.mach = Mach(self, self.avr)
            self.log.get('Ctrl').info('Initializing Preplanner...')
            self.preplanner = Preplanner(self)
            self.log.get('Ctrl').info('Initializing FileSystem...')
            self.fs = FileSystem(self)
            self.log.get('Ctrl').info('FileSystem initialized successfully')
            self.log.get('Ctrl').info('Initializing Network...')
            self.net = Network(self)
            if not args.demo:
                self.log.get('Ctrl').info('Initializing Jog...')
                self.jog = Jog(self)
            self.log.get('Ctrl').info('Initializing Pwr...')
            self.pwr = Pwr(self)

            self.log.get('Ctrl').info('Connecting Mach...')
            self.mach.connect()

            self.log.get('Ctrl').info('Adding LCD pages...')
            self.lcd.add_new_page(MainLCDPage(self))
            self.lcd.add_new_page(IPLCDPage(self.lcd))
            
            self.log.get('Ctrl').info('Controller initialization completed successfully')

        except Exception as e:
            self.log.get('Ctrl').exception('Exception during controller initialization: %s' % str(e))
            raise


    def __del__(self): print('Ctrl deleted')


    def get_authorized(self, sid): return self.sessions.get(sid, False)


    def set_authorized(self, sid, auth = True):
        if id: self.sessions[sid] = auth


    def clear_timeout(self):
        if self.timeout is not None: self.ioloop.remove_timeout(self.timeout)
        self.timeout = None


    def set_timeout(self, cb, *args, **kwargs):
        self.clear_timeout()
        t = self.args.client_timeout
        self.timeout = self.ioloop.call_later(t, cb, *args, **kwargs)


    def get_path(self, dir = None, filename = None):
        path = self.root if dir is None else (self.root + '/' + dir)
        return path if filename is None else (path + '/' + filename)


    def get_plan(self, filename = None):
        return self.get_path('plans', filename)


    def configure(self):
        # Called from Comm.py after AVR vars are loaded
        # Indirectly configures state via calls to config() and the AVR
        self.config.reload()
        self.state.init()
        self.mach.set('be', 1) # Enable buffers


    def ready(self):
        # This is used to synchronize the start of the preplanner
        self.preplanner.start()


    def close(self):
        self.log.get('Ctrl').info('Closing %s' % self.id)
        self.ioloop.close()
        self.avr.close()
        self.mach.planner.close()
