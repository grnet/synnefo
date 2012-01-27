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

import json

from httplib import HTTPConnection, HTTPSConnection
from urlparse import urlparse

from django.conf import settings
from django.utils.cache import patch_vary_headers


class ApiAuthMiddleware(object):
    def process_request(self, request):
        request.user = None
        
        token = request.GET.get('X-Auth-Token')
        if not token:
            token = request.META.get('HTTP_X_AUTH_TOKEN')
        if not token:
            token = request.COOKIES.get('X-Auth-Token')
        
        if not token:
            return
        
        p = urlparse(settings.ASTAKOS_URL)
        if p.scheme == 'https':
            conn = HTTPSConnection(p.netloc)
        else:
            conn = HTTPConnection(p.netloc)
        
        headers = {'X-Auth-Token': token}
        conn.request('GET', p.path, headers=headers)
        resp = conn.getresponse()
        if resp.status != 200:
            return
        
        try:
            reply = json.loads(resp.read())
            assert 'uniq' in reply
            assert 'username' in reply
        except (ValueError, AssertionError):
            return
        
        request.user = reply['uniq']
        request.username = reply['username']
    
    def process_response(self, request, response):
        # Tell proxies and other interested parties that the request varies
        # based on X-Auth-Token, to avoid caching of results
        patch_vary_headers(response, ('X-Auth-Token',))
        return response
