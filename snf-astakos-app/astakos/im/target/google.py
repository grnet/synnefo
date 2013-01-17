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
    handle_third_party_signup

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

consumer = oauth.Consumer(key=OAUTH_CONSUMER_KEY, secret=OAUTH_CONSUMER_SECRET)
client = oauth.Client(consumer)

token_scope = 'https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/userinfo.email'
authenticate_url = 'https://accounts.google.com/o/oauth2/auth'
access_token_url = 'https://www.googleapis.com/oauth2/v1/tokeninfo'
request_token_url = 'https://accounts.google.com/o/oauth2/token'


def get_redirect_uri():
    return "%s%s" % (settings.BASEURL,
                   reverse('astakos.im.target.google.authenticated'))

@requires_auth_provider('google', login=True)
@require_http_methods(["GET", "POST"])
def login(request):
    params = {
        'scope': token_scope,
        'response_type': 'code',
        'redirect_uri': get_redirect_uri(),
        'client_id': settings.GOOGLE_CLIENT_ID
    }
    force_login = request.GET.get('force_login', False)
    if force_login:
        params['approval_prompt'] = 'force'

    if request.GET.get('key', None):
        request.session['pending_key'] = request.GET.get('key')

    if request.GET.get('next', None):
        request.session['next_url'] = request.GET.get('next')

    url = "%s?%s" % (authenticate_url, urllib.urlencode(params))
    return HttpResponseRedirect(url)


@requires_auth_provider('google', login=True)
@require_http_methods(["GET", "POST"])
def authenticated(
    request,
    template='im/third_party_check_local.html',
    extra_context={}
):

    next_url = None
    if 'next_url' in request.session:
        next_url = request.session['next_url']
        del request.session['next_url']

    if request.GET.get('error', None):
        return HttpResponseRedirect(reverse('edit_profile'))

    # TODO: Handle errors, e.g. error=access_denied
    try:
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

        resp, content = client.request("%s?access_token=%s" % (access_token_url,
                                                               token) , "GET")
        access_token_data = json.loads(content)
    except Exception, e:
        messages.error(request, 'Invalid Google response. Please contact support')
        return HttpResponseRedirect(reverse('edit_profile'))

    if not access_token_data.get('user_id', None):
        messages.error(request, 'Invalid Google response. Please contact support')
        return HttpResponseRedirect(reverse('edit_profile'))

    userid = access_token_data['user_id']
    username = access_token_data.get('email', None)
    provider_info = access_token_data
    affiliation = 'Google.com'

    third_party_key = get_pending_key(request)

    # an existing user accessed the view
    if request.user.is_authenticated():
        if request.user.has_auth_provider('google', identifier=userid):
            return HttpResponseRedirect(reverse('edit_profile'))

        # automatically add eppn provider to user
        user = request.user
        if not request.user.can_add_auth_provider('google',
                                                  identifier=userid):
            # TODO: handle existing uuid message separately
            messages.error(request, _(astakos_messages.AUTH_PROVIDER_ADD_FAILED) +
                          u' ' + _(astakos_messages.AUTH_PROVIDER_ADD_EXISTS))
            return HttpResponseRedirect(reverse('edit_profile'))

        user.add_auth_provider('google', identifier=userid,
                               affiliation=affiliation,
                               provider_info=provider_info)
        messages.success(request, astakos_messages.AUTH_PROVIDER_ADDED)
        return HttpResponseRedirect(reverse('edit_profile'))

    try:
        # astakos user exists ?
        user = AstakosUser.objects.get_auth_provider_user(
            'google',
            identifier=userid
        )
        if user.is_active:
            # authenticate user
            response = prepare_response(request,
                                    user,
                                    next_url,
                                    'renew' in request.GET)

            provider = auth_providers.get_provider('google')
            messages.success(request, _(astakos_messages.LOGIN_SUCCESS) %
                             _(provider.get_login_message_display))
            add_pending_auth_provider(request, third_party_key)
            response.set_cookie('astakos_last_login_method', 'google')
            return response
        else:
            message = user.get_inactive_message()
            messages.error(request, message)
            return HttpResponseRedirect(login_url(request))

    except AstakosUser.DoesNotExist, e:
        user_info = {'affiliation': affiliation}
        return handle_third_party_signup(request, userid, 'google',
                                         third_party_key,
                                         provider_info,
                                         user_info,
                                         template,
                                         extra_context)

