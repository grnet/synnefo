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

from pithos.im.models import User


def get_user_from_token(token):
    try:
        return User.objects.get(auth_token=token)
    except User.DoesNotExist:
        return None


class AuthMiddleware(object):
    def process_request(self, request):
        request.user = None
        request.user_uniq = None
        
        # Try to find token in a parameter, in a request header, or in a cookie.
        user = get_user_from_token(request.GET.get('X-Auth-Token'))
        if not user:
            user = get_user_from_token(request.META.get('HTTP_X_AUTH_TOKEN'))
        if not user:
            # Back from an im login target.
            if request.GET.get('user', None):
                token = request.GET.get('token', None)
                if token:
                    request.set_auth_cookie = True
                user = get_user_from_token(token)
            if not user:
                cookie_value = request.COOKIES.get('_pithos2_a')
                if cookie_value and '|' in cookie_value:
                    token = cookie_value.split('|', 1)[1]
                    user = get_user_from_token(token)
        if not user:
            return
        
        # Check if the is active.
        if user.state != 'ACTIVE':
            return
        
        # Check if the token has expired.
        if (time() - mktime(user.auth_token_expires.timetuple())) > 0:
            return
        
        request.user = user
        request.user_uniq = user.uniq
    
    def process_response(self, request, response):
        if getattr(request, 'user', None) and getattr(request, 'set_auth_cookie', False):
            expire_fmt = request.user.auth_token_expires.strftime('%a, %d-%b-%Y %H:%M:%S %Z')
            cookie_value = request.user.uniq + '|' + request.user.auth_token
            response.set_cookie('_pithos2_a', value=cookie_value, expires=expire_fmt, path='/')
        return response
