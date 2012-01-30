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
from django.contrib.auth import authenticate
from django.contrib import messages

from astakos.im.target.util import prepare_response, requires_anonymous
from astakos.im.util import get_or_create_user, get_context
from astakos.im.models import AstakosUser, Invitation
from astakos.im.views import render_response, create_user
from astakos.im.backends import get_backend
from astakos.im.forms import LocalUserCreationForm, ThirdPartyUserCreationForm

class Tokens:
    # these are mapped by the Shibboleth SP software
    SHIB_EPPN = "HTTP_EPPN" # eduPersonPrincipalName
    SHIB_NAME = "HTTP_SHIB_INETORGPERSON_GIVENNAME"
    SHIB_SURNAME = "HTTP_SHIB_PERSON_SURNAME"
    SHIB_CN = "HTTP_SHIB_PERSON_COMMONNAME"
    SHIB_DISPLAYNAME = "HTTP_SHIB_INETORGPERSON_DISPLAYNAME"
    SHIB_EP_AFFILIATION = "HTTP_SHIB_EP_AFFILIATION"
    SHIB_SESSION_ID = "HTTP_SHIB_SESSION_ID"

@requires_anonymous
def login(request):
    # store invitation code and email
    request.session['email'] = request.GET.get('email')
    request.session['invitation_code'] = request.GET.get('code')

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
    
    next = request.GET.get('next')
    # check first if user with that identifier is registered
    user = None
    email = request.session.pop('email')
    
    if email:
        # signup mode
        if not reserved_screen_name(eppn):
            try:
                user = AstakosUser.objects.get(email = email)
            except AstakosUser.DoesNotExist, e:
                # register a new user
                first_name, space, last_name = realname.partition(' ')
                post_data = {'provider':'Shibboleth', 'first_name':first_name,
                                'last_name':last_name, 'affiliation':affiliation,
                                'third_party_identifier':eppn}
                form = ThirdPartyUserCreationForm({'email':email})
                return create_user(request, form, backend, post_data, next, template_name, extra_context)
        else:
            status = messages.ERROR
            message = '%s@shibboleth is already registered' % eppn
            messages.add_message(request, messages.ERROR, message)
    else:
        # login mode
        if user and user.is_active:
            #in order to login the user we must call authenticate first
            user = authenticate(email=user.email, auth_token=user.auth_token)
            return prepare_response(request, user, next)
        elif user and not user.is_active:
            messages.add_message(request, messages.ERROR, 'Inactive account: %s' % user.email)
    return render_response(template_name,
                   form = LocalUserCreationForm(),
                   context_instance=get_context(request, extra_context))

def reserved_identifier(identifier):
    try:
        AstakosUser.objects.get(provider='Shibboleth',
                                third_party_identifier=identifier)
        return True
    except AstakosUser.DoesNotExist, e:
        return False