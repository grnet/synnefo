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

from django.conf import settings

from pithos.im.models import User


class AuthMiddleware(object):
    def process_request(self, request):
        request.user_obj = None
        request.user = None
        
        # Try to find token in a parameter, in a request header, or in a cookie.
        token = request.GET.get('X-Auth-Token', None)
        if not token:
            token = request.META.get('HTTP_X_AUTH_TOKEN', None)
        if not token:
            token = request.COOKIES.get('X-Auth-Token', None)
        if not token: # Back from an im login target.
            if request.GET.get('user', None):
                token = request.GET.get('token', None)
                if token:
                    request.set_auth_cookie = True
        if not token:
            return
        
        # Token was found, retrieve user from backing store.
        try:
            user = User.objects.get(auth_token=token)
        except:
            return
        
        # Check if the is active.
        if user.state != 'ACTIVE':
            return
        
        # Check if the token has expired.
        if (time() - mktime(user.auth_token_expires.timetuple())) > 0:
            return
        
        request.user_obj = user
        request.user = user.uniq

    def process_response(self, request, response):
        if getattr(request, 'user_obj', None) and getattr(request, 'set_auth_cookie', False):
            expire_fmt = request.user_obj.auth_token_expires.strftime('%a, %d-%b-%Y %H:%M:%S %Z')
            response.set_cookie('X-Auth-Token', value=request.user_obj.auth_token, expires=expire_fmt, path='/')
        return response
