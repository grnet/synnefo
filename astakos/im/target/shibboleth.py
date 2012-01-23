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

from django.http import HttpResponseBadRequest
from django.core.urlresolvers import reverse
from django.contrib.auth import authenticate

from astakos.im.target.util import prepare_response
from astakos.im.util import get_or_create_user


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
    
    affiliation = tokens.get(Tokens.SHIB_EP_AFFILIATION, '')
    
    user = get_or_create_user(username, realname=realname, affiliation=affiliation, level=0, email=eppn)
    # in order to login the user we must call authenticate first
    user = authenticate(username=user.username, auth_token=user.auth_token)
    return prepare_response(request,
                            user,
                            request.GET.get('next'),
                            'renew' in request.GET)
