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

from time import time, mktime
from urlparse import urlparse
from urllib import quote, unquote

from django.conf import settings
from django.utils import simplejson as json

from synnefo.lib.pool.http import get_http_connection


def authenticate(token, authentication_url='http://127.0.0.1:8000/im/authenticate'):
    p = urlparse(authentication_url)

    kwargs = {}
    kwargs['headers'] = {}
    kwargs['headers']['X-Auth-Token'] = token
    kwargs['headers']['Content-Length'] = 0

    conn = get_http_connection(p.netloc, p.scheme)
    try:
        conn.request('GET', p.path, **kwargs)
        response = conn.getresponse()
        headers = response.getheaders()
        headers = dict((unquote(h), unquote(v)) for h,v in headers)
        length = response.getheader('content-length', None)
        data = response.read(length)
        status = int(response.status)
    finally:
        conn.close()

    if status < 200 or status >= 300:
        raise Exception(data, status)
    
    return json.loads(data)

def user_for_token(token, authentication_url, override_users):
    if not token:
        return None

    if override_users:
        try:
            return {'uniq': override_users[token].decode('utf8')}
        except:
            return None

    try:
        return authenticate(token, authentication_url)
    except Exception, e:
        # In case of Unauthorized response return None
        if e.args and e.args[-1] == 401:
            return None
        raise e

def get_user(request, authentication_url='http://127.0.0.1:8000/im/authenticate', override_users={}, fallback_token=None):
    request.user = None
    request.user_uniq = None

    # Try to find token in a parameter or in a request header.
    user = user_for_token(request.GET.get('X-Auth-Token'), authentication_url, override_users)
    if not user:
        user = user_for_token(request.META.get('HTTP_X_AUTH_TOKEN'), authentication_url, override_users)
    if not user:
        user = user_for_token(fallback_token, authentication_url, override_users)
    if not user:
        return

    request.user = user
    request.user_uniq = user['uniq']


def get_token_from_cookie(request, cookiename):
    """
    Extract token from the cookie name provided. Cookie should be in the same
    form as astakos service sets its cookie contents::

        <user_uniq>|<user_token>
    """
    try:
        cookie_content = unquote(request.COOKIES.get(cookiename, None))
        return cookie_content.split("|")[1]
    except AttributeError:
        pass

    return None
