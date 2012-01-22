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

import datetime

from urlparse import urlsplit, urlunsplit
from urllib import quote

from django.http import HttpResponse
from django.utils.http import urlencode
from django.core.urlresolvers import reverse
from django.conf import settings
from django.contrib.auth import login

def prepare_response(request, user, next='', renew=False):
    """Return the unique username and the token
       as 'X-Auth-User' and 'X-Auth-Token' headers,
       or redirect to the URL provided in 'next'
       with the 'user' and 'token' as parameters.
       
       Reissue the token even if it has not yet
       expired, if the 'renew' parameter is present.
    """
    
    auth_token = user.auth_token
    auth_token_expires = user.auth_token_expires
    if renew or auth_token_expires < datetime.datetime.now():
        user.renew_token()
        user.save()
        
    if next:
        # TODO: Avoid redirect loops.
        parts = list(urlsplit(next))
        # Do not pass on user and token if we are on the same server.
        if parts[1] and request.get_host() != parts[1]:
            parts[3] = urlencode({'user': user.username, 'token': auth_token})
            next = urlunsplit(parts)
    
    if settings.FORCE_PROFILE_UPDATE and not user.is_verified:
        params = ''
        if next:
            params = '?' + urlencode({'next': next})
        next = reverse('astakos.im.views.edit_profile') + params
    
    # user login
    login(request, user)
    
    response = HttpResponse()
    if not next:
        response['X-Auth-User'] = user.username
        response['X-Auth-Token'] = auth_token
        response.content = user.username + '\n' + auth_token + '\n'
        response.status_code = 200
    else:
        response['Location'] = next
        response.status_code = 302
    return response
