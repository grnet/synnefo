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
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils.http import urlencode
from django.utils.cache import patch_vary_headers

from models import PithosUser
from shibboleth import Tokens, register_shibboleth_user
from util import create_auth_token


def login(request):
    """Register a user into the internal database
       and issue a token for subsequent requests.
       Users are authenticated by Shibboleth.
       
       Return the unique username and the token
       as 'X-Auth-User' and 'X-Auth-Token' headers,
       or redirect to the URL provided in 'next'
       with the 'user' and 'token' as parameters.
       
       Reissue the token even if it has not yet
       expired, if the 'reissue' parameter is present.
    """
    
    try:
        user = PithosUser.objects.get(uniq=request.META[Tokens.SHIB_EPPN])
    except:
        user = None
    if user is None:
        try:
            user = register_shibboleth_user(request.META)
        except:
            return HttpResponseBadRequest('Missing necessary Shibboleth headers')
    
    if 'reissue' in request.GET:
        create_auth_token(user)
    next = request.GET.get('next')
    if next is not None:
        # TODO: Avoid redirect loops.
        if '?' in next:
            next = next[:next.find('?')]
        next += '?' + urlencode({'user': user.uniq,
                                 'token': user.auth_token})
    
    response = HttpResponse()
    if not next:
        response['X-Auth-User'] = user.uniq
        response['X-Auth-Token'] = user.auth_token
        response.content = user.uniq + '\n' + user.auth_token + '\n'
        response.status_code = 200
    else:
        response['Location'] = next
        response.status_code = 302
    return response
