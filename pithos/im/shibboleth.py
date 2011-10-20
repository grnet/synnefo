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

from django.http import HttpResponse, HttpResponseBadRequest
from django.utils.http import urlencode
#from django.utils.cache import patch_vary_headers

from models import User


class Tokens:
    # these are mapped by the Shibboleth SP software
    SHIB_EPPN = "HTTP_EPPN" # eduPersonPrincipalName
    SHIB_NAME = "HTTP_SHIB_INETORGPERSON_GIVENNAME"
    SHIB_SURNAME = "HTTP_SHIB_PERSON_SURNAME"
    SHIB_CN = "HTTP_SHIB_PERSON_COMMONNAME"
    SHIB_DISPLAYNAME = "HTTP_SHIB_INETORGPERSON_DISPLAYNAME"
    SHIB_EP_AFFILIATION = "HTTP_SHIB_EP_AFFILIATION"
    SHIB_SESSION_ID = "HTTP_SHIB_SESSION_ID"


def login(request):
    """Register a user into the internal database
       and issue a token for subsequent requests.
       Users are authenticated by Shibboleth.
       
       Return the unique username and the token
       as 'X-Auth-User' and 'X-Auth-Token' headers,
       or redirect to the URL provided in 'next'
       with the 'user' and 'token' as parameters.
       
       Reissue the token even if it has not yet
       expired, if the 'renew' parameter is present.
    """
    
    try:
        user = User.objects.get(uniq=request.META[Tokens.SHIB_EPPN])
    except:
        user = None
    if user is None:
        tokens = request.META
        
        try:
            eppn = tokens[Tokens.SHIB_EPPN]
        except KeyError:
            return HttpResponseBadRequest("Missing unique token in request")
        
        if Tokens.SHIB_DISPLAYNAME in tokens:
            realname = tokens[Tokens.SHIB_DISPLAYNAME]
        elif Tokens.SHIB_CN in tokens:
            realname = tokens[Tokens.SHIB_CN]
        elif Tokens.SHIB_NAME in tokens and Tokens.SHIB_SURNAME in tokens:
            realname = tokens[Tokens.SHIB_NAME] + ' ' + tokens[Tokens.SHIB_SURNAME]
        else:
            return HttpResponseBadRequest("Missing user name in request")
        
        user = User()
        user.uniq = eppn
        user.realname = realname
        user.affiliation = tokens.get(Tokens.SHIB_EP_AFFILIATION, '')
        user.renew_token()
        user.save()
    
    if 'renew' in request.GET or user.auth_token_expires < datetime.datetime.now():
        user.renew_token()
        user.save()
    next = request.GET.get('next')
    if next is not None:
        # TODO: Avoid redirect loops.
        parts = list(urlsplit(next))
        parts[3] = urlencode({'user': user.uniq, 'token': user.auth_token})
        next = urlunsplit(parts)
    
    response = HttpResponse()
    # TODO: Cookie should only be set at the client side...
    expire_fmt = user.auth_token_expires.strftime('%a, %d-%b-%Y %H:%M:%S %Z')
    response.set_cookie('X-Auth-Token', value=user.auth_token, expires=expire_fmt, path='/')
    if not next:
        response['X-Auth-User'] = user.uniq
        response['X-Auth-Token'] = user.auth_token
        response.content = user.uniq + '\n' + user.auth_token + '\n'
        response.status_code = 200
    else:
        response['Location'] = next
        response.status_code = 302
    return response
