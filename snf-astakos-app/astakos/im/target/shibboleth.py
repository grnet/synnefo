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

import json

from django.http import HttpResponseBadRequest
from django.utils.translation import ugettext as _
from django.contrib import messages
from django.template import RequestContext
from django.views.decorators.http import require_http_methods
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import get_object_or_404

from urlparse import urlunsplit, urlsplit

from astakos.im.util import prepare_response, get_context, login_url
from astakos.im.views import (
    requires_anonymous, render_response, requires_auth_provider)
from astakos.im.settings import ENABLE_LOCAL_ACCOUNT_MIGRATION, BASEURL
from astakos.im.models import AstakosUser, PendingThirdPartyUser
from astakos.im.forms import LoginForm
from astakos.im.activation_backends import get_backend, SimpleBackend
from astakos.im import auth_providers
from astakos.im import settings
from astakos.im.target import add_pending_auth_provider, get_pending_key, \
    handle_third_party_signup, handle_third_party_login, init_third_party_session

import astakos.im.messages as astakos_messages
import logging

logger = logging.getLogger(__name__)


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


@requires_auth_provider('shibboleth', login=True)
@require_http_methods(["GET", "POST"])
def login(
    request,
    template='im/third_party_check_local.html',
    extra_context=None):

    init_third_party_session(request)
    extra_context = extra_context or {}

    tokens = request.META
    third_party_key = get_pending_key(request)

    shibboleth_headers = {}
    for token in dir(Tokens):
        if token == token.upper():
            shibboleth_headers[token] = tokens.get(token, 'NOT_SET')
    # log shibboleth headers
    # TODO: info -> debug
    logger.info("shibboleth request: %r" % shibboleth_headers)

    try:
        eppn = tokens.get(Tokens.SHIB_EPPN)
        if not eppn:
            raise KeyError(_(astakos_messages.SHIBBOLETH_MISSING_EPPN) % {
                'domain': settings.BASEURL,
                'contact_email': settings.DEFAULT_CONTACT_EMAIL
            })
        if Tokens.SHIB_DISPLAYNAME in tokens:
            realname = tokens[Tokens.SHIB_DISPLAYNAME]
        elif Tokens.SHIB_CN in tokens:
            realname = tokens[Tokens.SHIB_CN]
        elif Tokens.SHIB_NAME in tokens and Tokens.SHIB_SURNAME in tokens:
            realname = tokens[Tokens.SHIB_NAME] + ' ' + tokens[Tokens.SHIB_SURNAME]
        else:
            if settings.SHIBBOLETH_REQUIRE_NAME_INFO:
                raise KeyError(_(astakos_messages.SHIBBOLETH_MISSING_NAME))
            else:
                realname = ''

    except KeyError, e:
        # invalid shibboleth headers, redirect to login, display message
        messages.error(request, e.message)
        return HttpResponseRedirect(login_url(request))

    affiliation = tokens.get(Tokens.SHIB_EP_AFFILIATION, 'Shibboleth')
    email = tokens.get(Tokens.SHIB_MAIL, '')
    provider_info = {'eppn': eppn, 'email': email, 'name': realname}
    userid = eppn


    try:
        return handle_third_party_login(request, 'shibboleth',
                                        eppn, provider_info,
                                        affiliation, third_party_key)
    except AstakosUser.DoesNotExist, e:
        third_party_key = get_pending_key(request)
        user_info = {'affiliation': affiliation, 'realname': realname}
        return handle_third_party_signup(request, userid, 'shibboleth',
                                         third_party_key,
                                         provider_info,
                                         user_info,
                                         template,
                                         extra_context)

