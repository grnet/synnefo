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

import logging
import oauth2 as oauth
import cgi
import urllib

from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import HttpResponseRedirect, urlencode
from django.core.urlresolvers import reverse
from django.conf import settings as django_settings

from urlparse import urlunsplit, urlsplit, parse_qsl

from astakos.im.models import AstakosUser
from astakos.im import settings
from astakos.im.views.target import get_pending_key, \
    handle_third_party_signup, handle_third_party_login, \
    init_third_party_session
from astakos.im.views.decorators import cookie_fix, requires_auth_provider

logger = logging.getLogger(__name__)


def django_setting(key, default):
    return getattr(django_settings, 'TWITTER_%s' % key.upper, default)

request_token_url = django_setting(
    'request_token_url',
    'https://api.twitter.com/oauth/request_token')
access_token_url = django_setting(
    'access_token_url',
    'https://api.twitter.com/oauth/access_token')
authenticate_url = django_setting(
    'authenticate_url',
    'https://api.twitter.com/oauth/authenticate')


@requires_auth_provider('twitter')
@require_http_methods(["GET", "POST"])
@cookie_fix
def login(request):
    init_third_party_session(request)
    force_login = request.GET.get('force_login',
                                  settings.TWITTER_AUTH_FORCE_LOGIN)
    consumer = oauth.Consumer(settings.TWITTER_TOKEN,
                              settings.TWITTER_SECRET)
    client = oauth.Client(consumer)
    resp, content = client.request(request_token_url, "GET")
    if resp['status'] != '200':
        messages.error(request, 'Invalid Twitter response')
        logger.error("Invalid twitter response %s", resp)
        return HttpResponseRedirect(reverse('edit_profile'))

    oa_resp = dict(cgi.parse_qsl(content))
    if 'status' in oa_resp and oa_resp['status'] != '200':
        messages.error(request, 'Invalid Twitter response')
        logger.error("Invalid twitter response %s", resp)
        return HttpResponseRedirect(reverse('edit_profile'))

    request.session['request_token'] = dict(cgi.parse_qsl(content))
    params = {
        'oauth_token': request.session['request_token']['oauth_token'],
    }
    if force_login:
        params['force_login'] = 1

    if request.GET.get('key', None):
        request.session['pending_key'] = request.GET.get('key')

    if request.GET.get('next', None):
        request.session['next_url'] = request.GET.get('next')

    url = "%s?%s" % (authenticate_url, urllib.urlencode(params))
    return HttpResponseRedirect(url)


@requires_auth_provider('twitter', login=True)
@require_http_methods(["GET", "POST"])
@cookie_fix
def authenticated(request,
                  template='im/third_party_check_local.html',
                  extra_context=None):

    if extra_context is None:
        extra_context = {}

    consumer = oauth.Consumer(settings.TWITTER_TOKEN,
                              settings.TWITTER_SECRET)
    client = oauth.Client(consumer)

    if request.GET.get('denied'):
        return HttpResponseRedirect(reverse('edit_profile'))

    if not 'request_token' in request.session:
        messages.error(request, 'Twitter handshake failed')
        return HttpResponseRedirect(reverse('edit_profile'))

    token = oauth.Token(request.session['request_token']['oauth_token'],
                        request.session['request_token']['oauth_token_secret'])
    client = oauth.Client(consumer, token)

    # Step 2. Request the authorized access token from Twitter.
    parts = list(urlsplit(access_token_url))
    params = dict(parse_qsl(parts[3], keep_blank_values=True))
    oauth_verifier = request.GET.get('oauth_verifier')
    params['oauth_verifier'] = oauth_verifier
    parts[3] = urlencode(params)
    parameterized_url = urlunsplit(parts)

    resp, content = client.request(parameterized_url, "GET")

    if resp['status'] != '200':
        try:
            del request.session['request_token']
        except:
            pass
        messages.error(request, 'Invalid Twitter response')
        logger.error("Invalid twitter response %s", resp)
        return HttpResponseRedirect(reverse('edit_profile'))

    access_token = dict(cgi.parse_qsl(content))
    userid = access_token['user_id']
    username = access_token.get('screen_name', userid)
    provider_info = {'screen_name': username}
    affiliation = 'Twitter.com'

    try:
        return handle_third_party_login(request, 'twitter', userid,
                                        provider_info, affiliation)
    except AstakosUser.DoesNotExist, e:
        third_party_key = get_pending_key(request)
        user_info = {'affiliation': affiliation}
        return handle_third_party_signup(request, userid, 'twitter',
                                         third_party_key,
                                         provider_info,
                                         user_info,
                                         template,
                                         extra_context)
