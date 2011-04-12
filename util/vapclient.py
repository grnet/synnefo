#!/usr/bin/env python
#

# Copyright (c) 2010 GRNET SA
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.

import sys
import socket

try:
    import simplejson as json
except ImportError:
    import json

CTRL_SOCKET = "/tmp/vncproxy.sock"

def request_forwarding(sport, daddr, dport, password):
    assert(len(password) > 0)
    req = {
        "source_port": int(sport),
        "destination_address": daddr,
        "destination_port": int(dport),
        "password": password
    }

    ctrl = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    ctrl.connect(CTRL_SOCKET)
    ctrl.send(json.dumps(req))

    response = ctrl.recv(1024)
    res = json.loads(response)
    return res

if __name__ == '__main__':
    res = request_forwarding(*sys.argv[1:])
    if res['status'] == "OK":
        sys.exit(0)
    else:
        sys.exit(1)
