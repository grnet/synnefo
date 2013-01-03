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
        requires_auth_provider, required_auth_methods_assigned
from astakos.im.settings import ENABLE_LOCAL_ACCOUNT_MIGRATION, BASEURL
from astakos.im.models import AstakosUser, PendingThirdPartyUser
from astakos.im.forms import LoginForm
from astakos.im.activation_backends import get_backend, SimpleBackend
from astakos.im import settings
from astakos.im import auth_providers
from astakos.im.target import add_pending_auth_provider, get_pending_key, \
    handle_third_party_signup

import astakos.im.messages as astakos_messages

import logging

logger = logging.getLogger(__name__)

import oauth2 as oauth
import cgi
import urllib

consumer = oauth.Consumer(settings.TWITTER_TOKEN, settings.TWITTER_SECRET)
client = oauth.Client(consumer)

request_token_url = 'http://twitter.com/oauth/request_token'
access_token_url = 'http://twitter.com/oauth/access_token'
authenticate_url = 'http://twitter.com/oauth/authenticate'

@requires_auth_provider('twitter', login=True)
@require_http_methods(["GET", "POST"])
def login(request):
    force_login = request.GET.get('force_login',
                                  settings.TWITTER_AUTH_FORCE_LOGIN)
    resp, content = client.request(request_token_url, "GET")
    if resp['status'] != '200':
        messages.error(request, 'Invalid Twitter response')
        return HttpResponseRedirect(reverse('edit_profile'))

    request.session['request_token'] = dict(cgi.parse_qsl(content))
    params = {
        'oauth_token': request.session['request_token']['oauth_token'],
    }
    if force_login:
        params['force_login'] = 1

    if request.GET.get('key', None):
        request.session['pending_key'] = request.GET.get('key')


    url = "%s?%s" % (authenticate_url, urllib.urlencode(params))

    return HttpResponseRedirect(url)


@requires_auth_provider('twitter', login=True)
@require_http_methods(["GET", "POST"])
def authenticated(
    request,
    template='im/third_party_check_local.html',
    extra_context={}):

    if request.GET.get('denied'):
        return HttpResponseRedirect(reverse('edit_profile'))

    if not 'request_token' in request.session:
        messages.error(request, 'Twitter handshake failed')
        return HttpResponseRedirect(reverse('edit_profile'))

    token = oauth.Token(request.session['request_token']['oauth_token'],
        request.session['request_token']['oauth_token_secret'])
    client = oauth.Client(consumer, token)

    # Step 2. Request the authorized access token from Twitter.
    resp, content = client.request(access_token_url, "GET")
    if resp['status'] != '200':
        try:
            del request.session['request_token']
        except:
            pass
        messages.error(request, 'Invalid Twitter response')
        return HttpResponseRedirect(reverse('edit_profile'))

    access_token = dict(cgi.parse_qsl(content))
    userid = access_token['user_id']
    username = access_token.get('screen_name', userid)
    provider_info = {'screen_name': username}
    affiliation = 'Twitter.com'

    third_party_key = get_pending_key(request)

    # an existing user accessed the view
    if request.user.is_authenticated():
        if request.user.has_auth_provider('twitter', identifier=userid):
            return HttpResponseRedirect(reverse('edit_profile'))

        # automatically add eppn provider to user
        user = request.user
        if not request.user.can_add_auth_provider('twitter',
                                                  identifier=userid):
            # TODO: handle existing uuid message separately
            messages.error(request, _(astakos_messages.AUTH_PROVIDER_ADD_FAILED) +
                          u' ' + _(astakos_messages.AUTH_PROVIDER_ADD_EXISTS))
            return HttpResponseRedirect(reverse('edit_profile'))

        user.add_auth_provider('twitter', identifier=userid,
                               affiliation=affiliation,
                               provider_info=provider_info)
        messages.success(request, astakos_messages.AUTH_PROVIDER_ADDED)
        return HttpResponseRedirect(reverse('edit_profile'))

    try:
        # astakos user exists ?
        user = AstakosUser.objects.get_auth_provider_user(
            'twitter',
            identifier=userid
        )
        if user.is_active:
            # authenticate user
            response = prepare_response(request,
                                    user,
                                    request.GET.get('next'),
                                    'renew' in request.GET)
            messages.success(request, _(astakos_messages.LOGIN_SUCCESS))
            add_pending_auth_provider(request, third_party_key)
            response.set_cookie('astakos_last_login_method', 'twitter')
            return response
        else:
            message = user.get_inactive_message()
            messages.error(request, message)
            return HttpResponseRedirect(login_url(request))

    except AstakosUser.DoesNotExist, e:
        user_info = {'affiliation': affiliation}
        return handle_third_party_signup(request, userid, 'twitter',
                                         third_party_key,
                                         provider_info,
                                         user_info,
                                         template,
                                         extra_context)

