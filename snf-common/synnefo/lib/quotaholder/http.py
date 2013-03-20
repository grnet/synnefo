# Copyright 2012 GRNET S.A. All rights reserved.
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

from synnefo.lib.commissioning import Callpoint, CallError
from synnefo.lib.pool.http import get_http_connection
from .api import QuotaholderAPI

from json import loads as json_loads, dumps as json_dumps
import logging
from urlparse import urlparse

logger = logging.getLogger(__name__)


class QuotaholderClient(Callpoint):

    api_spec = QuotaholderAPI()

    def __init__(self, base_url, token='', poolsize=1000):
        super(QuotaholderClient, self).__init__()
        self._url = base_url
        parsed = urlparse(base_url)
        self._netloc = parsed.netloc
        self._scheme = parsed.scheme
        basepath = parsed.path
        if not basepath.endswith('/'):
            basepath += '/'
        self._basepath = basepath
        self._token = token
        self._poolsize = poolsize

    def do_make_call(self, api_call, data):

        gettable = ['list', 'get', 'read']
        method = ('GET' if any(api_call.startswith(x) for x in gettable)
                  else 'POST')

        path = self._basepath + api_call
        json_data = json_dumps(data)

        logger.debug("%s %s\n%s\n<<<\n", method, path, json_data[:128])
        headers = {'X-Auth-Token': self._token}
        conn = get_http_connection(scheme=self._scheme, netloc=self._netloc,
                                   pool_size=self._poolsize)
        try:
            conn.request(method, path, body=json_data, headers=headers)
            resp = conn.getresponse()
        finally:
            conn.close()

        logger.debug(">>>\nStatus: %s", resp.status)

        body = resp.read()
        logger.debug("\n%s\n<<<\n", body[:128] if body else None)

        status = int(resp.status)
        if status == 200:
            return json_loads(body)
        else:
            try:
                error = json_loads(body)
            except ValueError:
                exc = CallError(body, call_error='ValueError')
            else:
                exc = CallError.from_dict(error)
            raise exc
