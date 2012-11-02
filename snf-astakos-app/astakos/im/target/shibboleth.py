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
from django.utils.translation import ugettext as _
from django.contrib import messages
from django.template import RequestContext
from django.views.decorators.http import require_http_methods

from astakos.im.util import prepare_response, get_context
from astakos.im.views import requires_anonymous, render_response
from astakos.im.models import AstakosUser
from astakos.im.forms import LoginForm
from astakos.im.activation_backends import get_backend, SimpleBackend


class Tokens:
    # these are mapped by the Shibboleth SP software
    SHIB_EPPN = "HTTP_EPPN"  # eduPersonPrincipalName
    SHIB_NAME = "HTTP_SHIB_INETORGPERSON_GIVENNAME"
    SHIB_SURNAME = "HTTP_SHIB_PERSON_SURNAME"
    SHIB_CN = "HTTP_SHIB_PERSON_COMMONNAME"
    SHIB_DISPLAYNAME = "HTTP_SHIB_INETORGPERSON_DISPLAYNAME"
    SHIB_EP_AFFILIATION = "HTTP_SHIB_EP_AFFILIATION"
    SHIB_SESSION_ID = "HTTP_SHIB_SESSION_ID"
    SHIB_MAIL = "HTTP_SHIB_MAIL"


@require_http_methods(["GET", "POST"])
@requires_anonymous
def login(request, backend=None, on_login_template='im/login.html',
          on_creation_template='im/third_party_registration.html',
          extra_context=None):
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
    email = tokens.get(Tokens.SHIB_MAIL, None)

    try:
        user = AstakosUser.objects.get(provider='shibboleth',
                                       third_party_identifier=eppn)
        if user.is_active:
            return prepare_response(request,
                                    user,
                                    request.GET.get('next'),
                                    'renew' in request.GET)
        else:
            message = _('Inactive account')
            messages.error(request, message)
            return render_response(on_login_template,
                                   login_form=LoginForm(request=request),
                                   context_instance=RequestContext(request))
    except AstakosUser.DoesNotExist, e:
        user = AstakosUser(third_party_identifier=eppn, realname=realname,
                           affiliation=affiliation, provider='shibboleth',
                           email=email)
        try:
            if not backend:
                backend = get_backend(request)
            form = backend.get_signup_form(
                provider='shibboleth', instance=user)
        except Exception, e:
            form = SimpleBackend(request).get_signup_form(
                provider='shibboleth',
                instance=user)
            messages.error(request, e)
        return render_response(on_creation_template,
                               signup_form=form,
                               provider='shibboleth',
                               context_instance=get_context(request,
                                                            extra_context))
