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
from astakos.im.views import requires_anonymous, render_response, \
        requires_auth_provider
from astakos.im.settings import ENABLE_LOCAL_ACCOUNT_MIGRATION, BASEURL
from astakos.im.models import AstakosUser, PendingThirdPartyUser
from astakos.im.forms import LoginForm
from astakos.im.activation_backends import get_backend, SimpleBackend
from astakos.im import settings
from astakos.im import auth_providers
from astakos.im.target import add_pending_auth_provider, get_pending_key, \
    handle_third_party_signup, handle_third_party_login, init_third_party_session
from astakos.im.decorators import cookie_fix

import logging
import time
import astakos.im.messages as astakos_messages
import urlparse
import urllib

logger = logging.getLogger(__name__)

import oauth2 as oauth
import cgi

signature_method = oauth.SignatureMethod_HMAC_SHA1()

OAUTH_CONSUMER_KEY = settings.GOOGLE_CLIENT_ID
OAUTH_CONSUMER_SECRET = settings.GOOGLE_SECRET

token_scope = 'https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/userinfo.email'
authenticate_url = 'https://accounts.google.com/o/oauth2/auth'
access_token_url = 'https://www.googleapis.com/oauth2/v1/tokeninfo'
request_token_url = 'https://accounts.google.com/o/oauth2/token'


def get_redirect_uri():
    return "%s%s" % (settings.BASEURL,
                     reverse('astakos.im.target.google.authenticated'))


@requires_auth_provider('google')
@require_http_methods(["GET", "POST"])
def login(request):
    init_third_party_session(request)
    params = {
        'scope': token_scope,
        'response_type': 'code',
        'redirect_uri': get_redirect_uri(),
        'client_id': settings.GOOGLE_CLIENT_ID
    }
    force_login = request.GET.get('force_login', request.GET.get('from_login',
                                                                 True))
    if force_login:
        params['approval_prompt'] = 'force'

    if request.GET.get('key', None):
        request.session['pending_key'] = request.GET.get('key')

    if request.GET.get('next', None):
        request.session['next_url'] = request.GET.get('next')

    url = "%s?%s" % (authenticate_url, urllib.urlencode(params))
    return HttpResponseRedirect(url)


@requires_auth_provider('google')
@require_http_methods(["GET", "POST"])
@cookie_fix
def authenticated(
    request,
    template='im/third_party_check_local.html',
    extra_context=None
):

    if extra_context is None:
        extra_context = {}

    if request.GET.get('error', None):
        return HttpResponseRedirect(reverse('edit_profile'))

    # TODO: Handle errors, e.g. error=access_denied
    try:
        consumer = oauth.Consumer(key=OAUTH_CONSUMER_KEY,
                                  secret=OAUTH_CONSUMER_SECRET)
        client = oauth.Client(consumer)

        code = request.GET.get('code', None)
        params = {
            'code': code,
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_SECRET,
            'redirect_uri': get_redirect_uri(),
            'grant_type': 'authorization_code'
        }
        get_token_url = "%s" % (request_token_url,)
        resp, content = client.request(get_token_url, "POST",
                                       body=urllib.urlencode(params))
        token = json.loads(content).get('access_token', None)

        resp, content = client.request("%s?access_token=%s" %
                                       (access_token_url, token), "GET")
        access_token_data = json.loads(content)
    except Exception:
        messages.error(request, _('Invalid Google response. Please '
                                  'contact support'))
        return HttpResponseRedirect(reverse('edit_profile'))

    if not access_token_data.get('user_id', None):
        messages.error(request, _('Invalid Google response. Please contact '
                                  ' support'))
        return HttpResponseRedirect(reverse('edit_profile'))

    userid = access_token_data['user_id']
    provider_info = access_token_data
    affiliation = 'Google.com'

    try:
        return handle_third_party_login(request, 'google', userid,
                                        provider_info, affiliation)
    except AstakosUser.DoesNotExist:
        third_party_key = get_pending_key(request)
        user_info = {'affiliation': affiliation}
        return handle_third_party_signup(request, userid, 'google',
                                         third_party_key,
                                         provider_info,
                                         user_info,
                                         template,
                                         extra_context)
