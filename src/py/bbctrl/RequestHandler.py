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

import traceback
from tornado.web import HTTPError
import tornado.web

from .Log import *

__all__ = ['RequestHandler']


class RequestHandler(tornado.web.RequestHandler):
    def __init__(self, app, request, **kwargs):
        super().__init__(app, request, **kwargs)
        self.app = app
        self.set_cors_headers()


    def get_ctrl(self):
        return self.app.get_ctrl(self.get_cookie('bbctrl-client-id'))


    def get_log(self, name = 'API'): return self.get_ctrl().log.get(name)
    def get_events(self): return self.get_ctrl().events


    def is_authorized(self):
        if not self.get_ctrl().config.get('admin', {}).get('admin-password-enabled', False):
            return True
        sid = self.get_cookie('bbctrl-sid')
        return self.get_ctrl().get_authorized(sid)


    def authorize(self):
        if not self.is_authorized(): raise HTTPError(401, 'Unauthorized')


    def not_demo(self):
        if self.get_ctrl().args.demo:
            raise HTTPError(400, 'Not supported in demo mode')


    def emit(self, event, *args, **kwargs):
        self.get_events().emit(event, *args, **kwargs)


    # Override exception logging
    def log_exception(self, typ, value, tb):
        if (isinstance(value, HTTPError) and
            400 <= value.status_code and value.status_code < 500): return

        log = self.get_log()
        log.set_level(Log.DEBUG)

        log.error(str(value))
        trace = ''.join(traceback.format_exception(typ, value, tb))
        log.debug(trace)


    def options(self, *args):
        self.set_status(204)
        self.finish()


    def set_cors_headers(self):
        origin = self.request.headers.get('Origin', '')
        origins = self.get_ctrl().config.get('cors-origins', '').split()
        if origin and origin in origins:
            self.set_header('Access-Control-Allow-Origin', origin)
            self.set_header(
                'Access-Control-Allow-Headers', 'DNT,User-Agent,' +
                'X-Requested-With,If-Modified-Since,Cache-Control,' +
                'Content-Type,Range,Set-Cookie,Authorization')
            self.set_header(
                'Access-Control-Allow-Methods',
                'POST,PUT,GET,OPTIONS,DELETE')
