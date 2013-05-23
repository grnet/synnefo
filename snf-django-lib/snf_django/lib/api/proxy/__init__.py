# Copyright 2012, 2013 GRNET S.A. All rights reserved.
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

from django.http import HttpResponse

from objpool.http import PooledHTTPConnection

from synnefo.lib import join_urls

from .utils import fix_header, forward_header

import urllib
import urlparse

# We use proxy to delegate requests to another domain. Sending host specific
# headers (Host, Cookie) may cause confusion to the server we proxy to.
#
# http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.10
# Connection and MUST NOT be communicated by proxies over further connections
EXCLUDE_HEADERS = ['Host', 'Cookie', 'Connection', 'X-Forwarded-Host']


def proxy(request, proxy_base=None, target_base=None):
    kwargs = {}

    if None in (proxy_base, target_base):
        m = "proxy() needs both proxy_base and target_base argument not None"
        raise AssertionError(m)

    parsed = urlparse.urlparse(target_base)
    target_base = '/' + parsed.path.strip('/')
    proxy_base = proxy_base.strip('/')

    # prepare headers
    headers = dict(map(lambda (k, v): fix_header(k, v),
                   filter(lambda (k, v): forward_header(k),
                          request.META.iteritems())))

    # set X-Forwarded-For, if already set, pass it through, otherwise set it
    # to the current request remote address
    SOURCE_IP = request.META.get('REMOTE_ADDR', None)
    if SOURCE_IP and not 'X-Forwarded-For' in headers:
        headers['X-Forwarded-For'] = SOURCE_IP

    # request.META remains cleanup
    for k in headers.keys():
        if '_' in k:
            headers.pop(k)

    for k in EXCLUDE_HEADERS:
        headers.pop(k, None)

    kwargs['headers'] = headers
    kwargs['body'] = request.raw_post_data

    path = request.path.lstrip('/')
    if path.startswith(proxy_base):
        m = "request path '{0}' does not start with proxy_base '{1}'"
        m = m.format(path, proxy_base)
    path = path.replace(proxy_base, '', 1)
    path = join_urls(target_base, path)
    with PooledHTTPConnection(parsed.netloc, parsed.scheme) as conn:
        conn.request(
            request.method,
            '?'.join([path, urllib.urlencode(request.GET)]), **kwargs)
        response = conn.getresponse()

        # turn httplib.HttpResponse to django.http.Response
        length = response.getheader('content-length', None)
        data = response.read(length)
        status = int(response.status)
        return HttpResponse(data, status=status)
