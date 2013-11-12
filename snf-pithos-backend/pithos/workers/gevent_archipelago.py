# -*- coding: utf-8 -
#
# Copyright 2013 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.


from __future__ import with_statement

import os
import sys
from datetime import datetime

# workaround on osx, disable kqueue
if sys.platform == "darwin":
    os.environ['EVENT_NOKQUEUE'] = "1"

try:
    import gevent
except ImportError:
    raise RuntimeError("You need gevent installed to use this worker.")
from gevent.pool import Pool
from gevent.server import StreamServer
from gevent import pywsgi
from gevent import select

import gunicorn
from gunicorn.workers.async import AsyncWorker

VERSION = "gevent/%s gunicorn/%s" % (gevent.__version__, gunicorn.__version__)

BASE_WSGI_ENV = {
    'GATEWAY_INTERFACE': 'CGI/1.1',
    'SERVER_SOFTWARE': VERSION,
    'SCRIPT_NAME': '',
    'wsgi.version': (1, 0),
    'wsgi.multithread': False,
    'wsgi.multiprocess': False,
    'wsgi.run_once': False
}


class GeventArchipelagoWorker(AsyncWorker):

    server_class = None
    wsgi_handler = None

    def __init__(self, *args, **kwargs):
        super(GeventArchipelagoWorker, self).__init__(*args, **kwargs)
        self.worker_id = args[0]

    @classmethod
    def setup(cls):
        from gevent import monkey
        monkey.noisy = False
        monkey.patch_all()

    def timeout_ctx(self):
        return gevent.Timeout(self.cfg.keepalive, False)

    def run(self):
        self.socket.setblocking(1)

        pool = Pool(self.worker_connections)
        if self.server_class is not None:
            server = self.server_class(
                self.socket, application=self.wsgi, spawn=pool, log=self.log,
                handler_class=self.wsgi_handler)
        else:
            server = StreamServer(self.socket, handle=self.handle, spawn=pool)

        server.start()
        try:
            while self.alive:
                self.notify()
                if self.ppid != os.getppid():
                    self.log.info("Parent changed, shutting down: %s", self)
                    break

                gevent.sleep(1.0)

        except KeyboardInterrupt:
            pass

        try:
            # Try to stop connections until timeout
            self.notify()
            server.stop(timeout=self.cfg.graceful_timeout)
        except:
            pass

    def handle_request(self, *args):
        try:
            super(GeventArchipelagoWorker, self).handle_request(*args)
        except gevent.GreenletExit:
            pass

    if gevent.version_info[0] == 0:

        def init_process(self):
            #gevent 0.13 and older doesn't reinitialize dns for us after
            #forking here's the workaround
            import gevent.core
            gevent.core.dns_shutdown(fail_requests=1)
            gevent.core.dns_init()
            super(GeventArchipelagoWorker, self).init_process()


class GeventResponse(object):

    status = None
    headers = None
    response_length = None

    def __init__(self, status, headers, clength):
        self.status = status
        self.headers = headers
        self.response_length = clength


class PyWSGIHandler(pywsgi.WSGIHandler):

    def log_request(self):
        start = datetime.fromtimestamp(self.time_start)
        finish = datetime.fromtimestamp(self.time_finish)
        response_time = finish - start
        resp = GeventResponse(self.status, self.response_headers,
                              self.response_length)
        req_headers = [h.split(":", 1) for h in self.headers.headers]
        self.server.log.access(resp, req_headers, self.environ, response_time)

    def get_environ(self):
        env = super(PyWSGIHandler, self).get_environ()
        env['gunicorn.sock'] = self.socket
        env['RAW_URI'] = self.path
        return env


class PyWSGIServer(pywsgi.WSGIServer):
    base_env = BASE_WSGI_ENV


class GeventPyWSGIWorker(GeventArchipelagoWorker):
    "The Gevent StreamServer based workers."
    server_class = PyWSGIServer
    wsgi_handler = PyWSGIHandler
