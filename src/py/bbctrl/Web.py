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
import sys
import json
import tornado
import sockjs.tornado
import datetime
import shutil
import tarfile
import subprocess
import socket
import time
from tornado.web import HTTPError
from tornado import web, gen
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor

from . import util
from .Log import *
from .APIHandler import *
from .RequestHandler import *
from .Camera import *
from .MonitorTemp import *
from .AuthHandler import *
from .FileSystemHandler import *
from .Ctrl import *
from udevevent import UDevEvent

__all__ = ['Web']


def upgrade_command(ctrl, cmd):
    ctrl.lcd.goodbye('Upgrading firmware')
    subprocess.Popen(['systemd-run', '--unit=bbctrl-update', '--scope',
                      '--slice=bbctrl-update'] + cmd)


class RebootHandler(APIHandler):
    def put(self):
        self.authorize()
        self.get_ctrl().lcd.goodbye('Rebooting...')
        subprocess.Popen('reboot')


class StateHandler(APIHandler):
    def get(self, path):
        if path is None or path == '' or path == '/':
            self.write_json(self.get_ctrl().state.snapshot())
        else: self.write_json(self.get_ctrl().state.get(path[1:]))



class LogHandler(RequestHandler):
    def get(self):
        with open(self.get_ctrl().log.get_path(), 'r') as f:
            self.write(f.read())


    def set_default_headers(self):
        fmt = socket.gethostname() + '-%Y%m%d-%H%M%S.log'
        filename = datetime.datetime.now().strftime(fmt)
        self.set_header('Content-Disposition', 'filename="%s"' % filename)
        self.set_header('Content-Type', 'text/plain')


class MessageAckHandler(APIHandler):
    def put(self, id):
        self.get_ctrl().state.ack_message(int(id))


class BugReportHandler(RequestHandler):
    executor = ThreadPoolExecutor(max_workers = 4)


    def get_files(self):
        files = []

        def check_add(path, arcname = None):
            if os.path.isfile(path):
                if arcname is None: arcname = path
                files.append((path, self.basename + '/' + arcname))

        def check_add_basename(path):
            check_add(path, os.path.basename(path))

        ctrl = self.get_ctrl()
        path = ctrl.log.get_path()
        check_add_basename(path)
        for i in range(1, 8):
            check_add_basename('%s.%d' % (path, i))
        check_add_basename('/var/log/syslog')
        check_add(ctrl.config.get_path())
        # TODO Add recently run programs

        return files


    @run_on_executor
    def task(self):
        import tarfile, io

        files = self.get_files()

        buf = io.BytesIO()
        tar = tarfile.open(mode = 'w:bz2', fileobj = buf)
        for path, name in files: tar.add(path, name)
        tar.close()

        return buf.getvalue()


    @gen.coroutine
    def get(self):
        self.authorize()
        res = yield self.task()
        self.write(res)


    def set_default_headers(self):
        fmt = socket.gethostname() + '-%Y%m%d-%H%M%S'
        self.basename = datetime.datetime.now().strftime(fmt)
        filename = self.basename + '.tar.bz2'
        self.set_header('Content-Disposition', 'filename="%s"' % filename)
        self.set_header('Content-Type', 'application/x-bzip2')


class HostnameHandler(APIHandler):
    def get(self): self.write_json(socket.gethostname())


    def put(self):
        self.not_demo()
        self.authorize()

        hostname = self.require_arg('hostname')
        r = subprocess.call(['/usr/local/bin/sethostname', hostname.strip()])
        if r: raise HTTPError(400, 'Failed to set hostname')


class WifiHandler(APIHandler):
    def put(self, device, action):
        self.not_demo()
        self.authorize()

        try:
            args = self.json if self.json else {}
            getattr(self.get_ctrl().net, action)(device, **args)

        except Exception as e:
            self.get_ctrl().log.exception('Wifi handler')


class ConfigDownloadHandler(APIHandler):
    def set_default_headers(self):
        # NOTE get_ctrl() not accessible from here because it needs get_cookie()
        filename = util.get_config_filename()
        self.set_header('Content-Type', 'application/octet-stream')
        self.set_header('Content-Disposition',
                        'attachment; filename="%s"' % filename)

    def get(self):
        self.write_json(self.get_ctrl().config.load(), pretty = True)



class ConfigHandler(APIHandler):
    def get(self, action):
        if action == 'load': self.write_json(self.get_ctrl().config.load())
        else: raise HTTPError(400, 'Invalid config action')


    def put(self, action):
        self.authorize()
        if   action == 'save':   self.get_ctrl().config.save(self.json)
        elif action == 'reset':  self.get_ctrl().config.reset()
        elif action == 'backup': self.get_ctrl().config.backup()
        else: raise HTTPError(400, 'Invalid config action')


class FirmwareUpdateHandler(APIHandler):
    def put(self):
        self.authorize()

        if not os.path.exists('firmware'): os.mkdir('firmware')
        target = 'firmware/update.tar.bz2'

        if 'firmware' in self.request.files:
            firmware = self.request.files['firmware'][0]

            with open(target, 'wb') as f:
                f.write(firmware['body'])

        elif 'path' in self.json:
            path = self.get_ctrl().fs.realpath(self.json['path'])

            if not os.path.exists(path):
                raise HTTPError(404, 'Firmware file not found')

            if path != target: shutil.copyfile(path, target)

        else: raise HTTPError(400, 'Need "firmware" or "path"')

        upgrade_command(self.get_ctrl(), ['/usr/local/bin/update-bbctrl'])


class UpgradeHandler(APIHandler):
    def put(self):
        self.authorize()
        upgrade_command(self.get_ctrl(), ['/usr/local/bin/upgrade-bbctrl'])


class USBEjectHandler(APIHandler):
    def put(self, path):
        subprocess.Popen(['/usr/local/bin/eject-usb', '/media/' + path])


class MacroHandler(APIHandler):
    def put(self, macro):
        macros = self.get_ctrl().config.get('macros')

        macro = int(macro)
        if macro < 0 or len(macros) < macro:
            raise HTTPError(404, 'Invalid macro id %d' % macro)

        path = 'Home/' + macros[macro - 1]['path']

        if not self.get_ctrl().fs.exists(path):
            raise HTTPError(404, 'Macro file not found')

        self.get_ctrl().mach.start(path)


class PathHandler(APIHandler):
    @gen.coroutine
    def get(self, dataType, path, *args):
        if not os.path.exists(self.get_ctrl().fs.realpath(path)):
            raise HTTPError(404, 'File not found')

        preplanner = self.get_ctrl().preplanner
        future = preplanner.get_plan(path)

        try:
            delta = datetime.timedelta(seconds = 1)
            data = yield gen.with_timeout(delta, future)

        except gen.TimeoutError:
            progress = preplanner.get_plan_progress(path)
            self.write_json(dict(progress = progress))
            return

        try:
            if data is None: return
            meta, positions, speeds = data

            if dataType == 'positions': data = positions
            elif dataType == 'speeds': data = speeds
            else:
                self.write_json(meta)
                return

            filename = os.path.basename(path) + '-' + dataType + '.gz'
            self.set_header('Content-Disposition', 'filename="%s"' % filename)
            self.set_header('Content-Type', 'application/octet-stream')
            self.set_header('Content-Encoding', 'gzip')
            self.set_header('Content-Length', str(len(data)))

            # Respond with chunks to avoid long delays
            SIZE = 102400
            chunks = [data[i:i + SIZE] for i in range(0, len(data), SIZE)]
            for chunk in chunks:
                self.write(chunk)
                yield self.flush()

        except tornado.iostream.StreamClosedError as e: pass


class HomeHandler(APIHandler):
    def put(self, axis, action, *args):
        if axis is not None: axis = ord(axis[1:2].lower())

        if action == '/set':
            position = self.require_arg('position')
            self.get_ctrl().mach.home(axis, position)

        elif action == '/clear': self.get_ctrl().mach.unhome(axis)
        else: self.get_ctrl().mach.home(axis)


class StartHandler(APIHandler):
    def put(self, path):
        path = self.get_ctrl().fs.validate_path(path)
        self.get_ctrl().mach.start(path)


class ActivateHandler(APIHandler):
    def put(self, path):
        path = self.get_ctrl().fs.validate_path(path)
        self.get_ctrl().state.set('active_program', path)


class EStopHandler(APIHandler):
    def put(self): self.get_ctrl().mach.estop()


class ClearHandler(APIHandler):
    def put(self): self.get_ctrl().mach.clear()


class StopHandler(APIHandler):
    def put(self): self.get_ctrl().mach.stop()


class PauseHandler(APIHandler):
    def put(self): self.get_ctrl().mach.pause()


class UnpauseHandler(APIHandler):
    def put(self): self.get_ctrl().mach.unpause()


class OptionalPauseHandler(APIHandler):
    def put(self): self.get_ctrl().mach.optional_pause()


class StepHandler(APIHandler):
    def put(self): self.get_ctrl().mach.step()


class PositionHandler(APIHandler):
    def put(self, axis):
        self.get_ctrl().mach.set_position(axis, float(self.json['position']))


class OverrideFeedHandler(APIHandler):
    def put(self, value): self.get_ctrl().mach.override_feed(float(value))


class OverrideSpeedHandler(APIHandler):
    def put(self, value): self.get_ctrl().mach.override_speed(float(value))


class ModbusReadHandler(APIHandler):
    def put(self):
        self.get_ctrl().mach.modbus_read(int(self.json['address']))


class ModbusWriteHandler(APIHandler):
    def put(self):
        self.get_ctrl().mach.modbus_write(int(self.json['address']),
                                    int(self.json['value']))


class JogHandler(APIHandler):
    def put(self):
        # Handle possible out of order jog command processing
        if 'ts' in self.json:
            ts = self.json['ts']
            id = self.get_cookie('bbctrl-client-id')

            if not hasattr(self.app, 'last_jog'):
                self.app.last_jog = {}

            last = self.app.last_jog.get(id, 0)
            self.app.last_jog[id] = ts

            if ts < last: return # Out of order

        self.get_ctrl().mach.jog(self.json)


class KeyboardHandler(APIHandler):
    def set_keyboard(self, show):
        signal = 'SIGUSR' + ('1' if show else '2')
        subprocess.call(['killall', '-' + signal, 'bbkbd'])


    def put(self, cmd, *args):
        show = cmd == 'show'
        enabled = self.get_ctrl().config.get('virtual-keyboard-enabled', True)
        if enabled or not show: self.set_keyboard(show)


# Base class for Web Socket connections
class ClientConnection(object):
    def __init__(self, app):
        self.app = app
        self.count = 0


    def heartbeat(self):
        self.timer = self.app.ioloop.call_later(3, self.heartbeat)
        self.send({'heartbeat': self.count})
        self.count += 1


    def send(self, msg): raise HTTPError(400, 'Not implemented')


    def on_open(self, id = None):
        self.ctrl = self.app.get_ctrl(id)

        self.ctrl.state.add_listener(self.send)
        self.ctrl.log.add_listener(self.send)
        self.is_open = True
        self.heartbeat()
        self.app.opened(self.ctrl)


    def on_close(self):
        self.app.ioloop.remove_timeout(self.timer)
        self.ctrl.state.remove_listener(self.send)
        self.ctrl.log.remove_listener(self.send)
        self.is_open = False
        self.app.closed(self.ctrl)


    def on_message(self, data): self.ctrl.mach.mdi(data)


# Used by CAMotics
class WSConnection(ClientConnection, tornado.websocket.WebSocketHandler):
    def __init__(self, app, request, **kwargs):
        ClientConnection.__init__(self, app)
        tornado.websocket.WebSocketHandler.__init__(
            self, app, request, **kwargs)

    def check_origin(self, origin): return True
    def send(self, msg): self.write_message(msg)
    def open(self): self.on_open()


# Used by Web frontend
class SockJSConnection(ClientConnection, sockjs.tornado.SockJSConnection):
    def __init__(self, session):
        ClientConnection.__init__(self, session.server.app)
        sockjs.tornado.SockJSConnection.__init__(self, session)

    def send(self, msg):
        try:
            sockjs.tornado.SockJSConnection.send(self, msg)
        except Exception as e:
            self.app.log.get('Web').error('Error sending message: %s' % str(e))

    def on_open(self, info):
        cookie = info.get_cookie('bbctrl-client-id')
        if cookie is None: 
            self.send(dict(sid = ''))  # Trigger client reset
        else:
            id = cookie.value
            ip = info.ip
            if 'X-Real-IP' in info.headers: ip = info.headers['X-Real-IP']
            
            ctrl = self.app.get_ctrl(id)
            ctrl.log.get('Web').info('Connection from %s' % ip)
            
            # Reset timeout
            ctrl.clear_timeout()
            
            # Call parent on_open
            super().on_open(id)

    def on_close(self):
        try:
            super().on_close()
        except Exception as e:
            self.app.log.get('Web').error('Error closing connection: %s' % str(e))


class StaticFileHandler(tornado.web.StaticFileHandler):
    def set_extra_headers(self, path):
        self.set_header('Cache-Control',
                        'no-store, no-cache, must-revalidate, max-age=0')


class Web(tornado.web.Application):
    def __init__(self, args, ioloop):
        self.args   = args
        self.ioloop = ioloop
        self.udevev = UDevEvent(ioloop)
        self.ctrls  = {}

        self.udevev.log = self._get_log('udevevent.log').get('UDev')

        # Init camera
        if not args.disable_camera:
            log = self._get_log('camera.log')
            self.camera = Camera(ioloop, self.udevev, args, log.get('Camera'))
        else: self.camera = None

        # Init controller
        if not self.args.demo:
            self.get_ctrl()
            self.monitor = MonitorTemp(self)

        handlers = [
            (r'/websocket',                     WSConnection),
            (r'/api/auth/(login|password)',     AuthHandler),
            (r'/api/state(/.*)?',               StateHandler),
            (r'/api/log',                       LogHandler),
            (r'/api/message/(\d+)/ack',         MessageAckHandler),
            (r'/api/bugreport',                 BugReportHandler),
            (r'/api/reboot',                    RebootHandler),
            (r'/api/hostname',                  HostnameHandler),
            (r'/api/wifi/([^/]+)/(scan|connect|forget|disconnect)',
             WifiHandler),
            (r'/api/config/download',           ConfigDownloadHandler),
            (r'/api/config/(load|save|reset|backup)',
             ConfigHandler),
            (r'/api/firmware/update',           FirmwareUpdateHandler),
            (r'/api/upgrade',                   UpgradeHandler),
            (r'/api/usb/eject/(.*)',            USBEjectHandler),
            (r'/api/fs/(.*)',                   FileSystemHandler),
            (r'/api/file',                      FileSystemHandler), # Compat
            (r'/api/macro/(\d+)',               MacroHandler),
            (r'/api/(path)/(.*)',               PathHandler),
            (r'/api/(positions)/(.*)',          PathHandler),
            (r'/api/(speeds)/(.*)',             PathHandler),
            (r'/api/home(/[xyzabcXYZABC]((/set)|(/clear))?)?', HomeHandler),
            (r'/api/start/(.*)',                StartHandler),
            (r'/api/activate/(.*)',             ActivateHandler),
            (r'/api/estop',                     EStopHandler),
            (r'/api/clear',                     ClearHandler),
            (r'/api/stop',                      StopHandler),
            (r'/api/pause',                     PauseHandler),
            (r'/api/unpause',                   UnpauseHandler),
            (r'/api/pause/optional',            OptionalPauseHandler),
            (r'/api/step',                      StepHandler),
            (r'/api/position/([xyzabcXYZABC])', PositionHandler),
            (r'/api/override/feed/([\d.]+)',    OverrideFeedHandler),
            (r'/api/override/speed/([\d.]+)',   OverrideSpeedHandler),
            (r'/api/modbus/read',               ModbusReadHandler),
            (r'/api/modbus/write',              ModbusWriteHandler),
            (r'/api/jog',                       JogHandler),
            (r'/api/video',                     VideoHandler),
            (r'/api/keyboard/((show)|(hide))',  KeyboardHandler),
            (r'/(.*)',                          StaticFileHandler, {
                'path': util.get_resource('http/'),
                'default_filename': 'index.html'
            }),
        ]

        router = sockjs.tornado.SockJSRouter(SockJSConnection, '/sockjs')
        router.app = self

        tornado.web.Application.__init__(self, router.urls + handlers)

        try:
            self.listen(args.port, address = args.addr)

        except Exception as e:
            raise Exception('Failed to bind %s:%d: %s' % (
                args.addr, args.port, e))

        print('Listening on http://%s:%d/' % (args.addr, args.port))


    def _get_log(self, path):
        if self.args.demo: return Log(self.args, self.ioloop, path)
        return self.get_ctrl().log


    def get_image_resource(self, name):
        return util.get_resource('http/images/%s.jpg' % name)


    def opened(self, ctrl):
        ctrl.clear_timeout()
        ctrl.log.get('Web').info('Connection opened')


    def closed(self, ctrl):
        # Don't time out clients in demo mode
        if not self.args.demo:
            ctrl.set_timeout(self._reap_ctrl, ctrl)
        ctrl.log.get('Web').info('Connection closed')


    def _reap_ctrl(self, ctrl):
        ctrl.log.get('Web').info('Reaping controller')
        ctrl.close()
        del self.ctrls[ctrl.id]


    def get_ctrl(self, id = None):
        if not id or not self.args.demo: id = ''

        if not id in self.ctrls:
            ctrl = Ctrl(self.args, self.ioloop, self.udevev, id)
            self.ctrls[id] = ctrl
            ctrl.log.get('Web').info('Created new controller')

        else: 
            ctrl = self.ctrls[id]
            ctrl.log.get('Web').info('Using existing controller')

        return ctrl


    # Override default logger
    def log_request(self, handler):
        ctrl = self.get_ctrl(handler.get_cookie('bbctrl-client-id'))
        log = ctrl.log.get('Web')
        log.info("%d %s", handler.get_status(), handler._request_summary())
