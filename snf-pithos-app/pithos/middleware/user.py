# Copyright 2011 GRNET S.A. All rights reserved.
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
from httplib import HTTPConnection
from urllib import quote, unquote

from django.conf import settings
from django.utils import simplejson as json


def authenticate(authentication_host, token):
    con = HTTPConnection(authentication_host)
    kwargs = {}
    kwargs['headers'] = {}
    kwargs['headers']['X-Auth-Token'] = token
    kwargs['headers']['Content-Length'] = 0
    
    path = '/im/authenticate'
    con.request('GET', path, **kwargs)
    response = con.getresponse()
    
    headers = response.getheaders()
    headers = dict((unquote(h), unquote(v)) for h,v in headers)
    length = response.getheader('content-length', None)
    data = response.read(length)
    status = int(response.status)
    
    if status < 200 or status >= 300:
        raise Exception(data, int(response.status))
    
    return json.loads(data)

def get_user_from_token(token):
    if not token:
        return None
    
    users = settings.AUTHENTICATION_USERS
    if users is not None:
        try:
            return {'id': 0, 'uniq': users[token].decode('utf8')}
        except:
            return None
    
    host = settings.AUTHENTICATION_HOST
    try:
        return authenticate(host, token)
    except:
        return None

class UserMiddleware(object):
    def process_request(self, request):
        request.user = None
        request.user_uniq = None
        
        # Try to find token in a parameter, in a request header, or in a cookie.
        user = get_user_from_token(request.GET.get('X-Auth-Token'))
        if not user:
            user = get_user_from_token(request.META.get('HTTP_X_AUTH_TOKEN'))
        if not user:
            return
        
        request.user = user
        request.user_uniq = user['uniq']
