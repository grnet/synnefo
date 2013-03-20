# Copyright 2011-2012 GRNET S.A. All rights reserved.
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

import logging

from urlparse import urlparse
import urllib
import urllib2

from django.http import (
    HttpResponseNotFound, HttpResponseRedirect, HttpResponseBadRequest,
    HttpResponse)
from django.utils.http import urlencode
from django.views.decorators.csrf import csrf_exempt

from pithos.api.settings import (
    AUTHENTICATION_USERS, USER_LOGIN_URL, USER_FEEDBACK_URL, USER_CATALOG_URL)

from synnefo.lib.pool.http import get_http_connection

logger = logging.getLogger(__name__)


def delegate_to_login_service(request):
    url = USER_LOGIN_URL
    users = AUTHENTICATION_USERS
    if users or not url:
        return HttpResponseNotFound()

    p = urlparse(url)
    if request.is_secure():
        proto = 'https://'
    else:
        proto = 'http://'
    params = dict([(k, v) for k, v in request.GET.items()])
    uri = proto + p.netloc + p.path + '?' + urlencode(params)
    return HttpResponseRedirect(uri)


def proxy(request, url, headers=None, body=None):
    p = urlparse(url)

    kwargs = {}
    if headers is None:
        headers = {}
    kwargs["headers"] = headers
    kwargs['headers'].update(request.META)
    kwargs['body'] = body
    kwargs['headers'].setdefault('content-type', 'application/json')
    kwargs['headers'].setdefault('content-length', len(body) if body else 0)

    conn = get_http_connection(p.netloc, p.scheme)
    try:
        conn.request(request.method, p.path + '?' + p.query, **kwargs)
        response = conn.getresponse()
        length = response.getheader('content-length', None)
        data = response.read(length)
        status = int(response.status)
        return HttpResponse(data, status=status)
    finally:
        conn.close()

@csrf_exempt
def delegate_to_feedback_service(request):
    token = request.META.get('HTTP_X_AUTH_TOKEN')
    headers = {'X-Auth-Token': token}
    return proxy(
        request, USER_FEEDBACK_URL, headers=headers, body=request.raw_post_data)

@csrf_exempt
def delegate_to_user_catalogs_service(request):
    token = request.META.get('HTTP_X_AUTH_TOKEN')
    headers = {'X-Auth-Token': token, 'content-type': 'application/json'}
    return proxy(
        request, USER_CATALOG_URL, headers=headers, body=request.raw_post_data)
