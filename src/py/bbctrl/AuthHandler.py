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

import subprocess
import secrets
import crypt
from tornado.web import HTTPError

from .APIHandler import *

__all__ = ['AuthHandler']


def call_get_output(cmd):
  p = subprocess.Popen(cmd, stdout = subprocess.PIPE)
  s = p.communicate()[0].decode('utf-8')
  if p.returncode: raise HTTPError(400, 'Command failed')
  return s


def get_username():
  return call_get_output(['getent', 'passwd', '1000']).split(':')[0]


class AuthHandler(APIHandler):
  def not_found(self): raise HTTPError(404, 'Method not found')
  def  try_call(self, method): getattr(self, method, self.not_found)()
  def       get(self, action): self.try_call('get_'    + action)
  def       put(self, action): self.try_call('put_'    + action)
  def    delete(self, action): self.try_call('delete_' + action)


  def get_login(self): self.write_json(self.is_authorized())


  def put_login(self):
    self.not_demo()

    password = self.require_arg('password')

    # Get current password hash from shadow
    s = call_get_output(['getent', 'shadow', get_username()])
    shadow_hash = s.split(':')[1]

    # Verify password using crypt
    if crypt.crypt(password, shadow_hash) != shadow_hash:
      raise HTTPError(401, 'Wrong password')

    sid = secrets.token_urlsafe(16)
    self.set_cookie('bbctrl-sid', sid, samesite = 'Strict')
    self.get_ctrl().set_authorized(sid)


  def delete_login(self):
    self.not_demo()
    self.authorize()

    sid = self.get_cookie('bbctrl-sid')
    self.get_ctrl().set_authorized(sid, False)


  def put_password(self):
    self.not_demo()
    self.authorize()

    password = self.require_arg('password')

    # Set password
    s = ('%s:%s' % (get_username(), password)).encode('utf-8')
    p = subprocess.Popen(['chpasswd', '-c', 'MD5'], stdin = subprocess.PIPE)
    p.communicate(input = s)

    if p.returncode: raise HTTPError(401, 'Failed to set password')
