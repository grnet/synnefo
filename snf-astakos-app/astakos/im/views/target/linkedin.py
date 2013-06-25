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
import logging
import oauth2 as oauth
import cgi

from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.conf import settings as django_settings

from astakos.im.models import AstakosUser
from astakos.im import settings
from astakos.im.views.target import get_pending_key, \
    handle_third_party_signup, handle_third_party_login, \
    init_third_party_session
from astakos.im.views.decorators import cookie_fix, \
    requires_auth_provider

logger = logging.getLogger(__name__)


def django_setting(key, default):
    return getattr(django_settings, 'GOOGLE_%s' % key.upper, default)

token_scope = 'r_basicprofile+r_emailaddress'
request_token_url = django_setting(
    'request_token_url',
    'https://api.linkedin.com/uas/oauth/requestToken?scope=' + token_scope)
access_token_url = django_setting(
    'access_token_url',
    'https://api.linkedin.com/uas/oauth/accessToken')
authenticate_url = django_setting(
    'authenticate_url',
    'https://www.linkedin.com/uas/oauth/authorize')


@requires_auth_provider('linkedin')
@require_http_methods(["GET", "POST"])
@cookie_fix
def login(request):
    init_third_party_session(request)
    consumer = oauth.Consumer(settings.LINKEDIN_TOKEN,
                              settings.LINKEDIN_SECRET)
    client = oauth.Client(consumer)
    resp, content = client.request(request_token_url, "GET")
    if resp['status'] != '200':
        messages.error(request, 'Invalid linkedin response')
        return HttpResponseRedirect(reverse('edit_profile'))

    request_token = dict(cgi.parse_qsl(content))
    request.session['request_token'] = request_token

    url = request_token.get('xoauth_request_auth_url') + \
        "?oauth_token=%s" % request_token.get('oauth_token')

    if request.GET.get('key', None):
        request.session['pending_key'] = request.GET.get('key')

    if request.GET.get('next', None):
        request.session['next_url'] = request.GET.get('next')

    return HttpResponseRedirect(url)


@requires_auth_provider('linkedin', login=True)
@require_http_methods(["GET", "POST"])
@cookie_fix
def authenticated(
    request,
    template='im/third_party_check_local.html',
    extra_context=None
):

    if extra_context is None:
        extra_context = {}

    consumer = oauth.Consumer(settings.LINKEDIN_TOKEN,
                              settings.LINKEDIN_SECRET)
    client = oauth.Client(consumer)

    if request.GET.get('denied'):
        return HttpResponseRedirect(reverse('edit_profile'))

    if not 'request_token' in request.session:
        messages.error(request, 'linkedin handshake failed')
        return HttpResponseRedirect(reverse('edit_profile'))

    token = oauth.Token(request.session['request_token']['oauth_token'],
        request.session['request_token']['oauth_token_secret'])
    token.set_verifier(request.GET.get('oauth_verifier'))
    client = oauth.Client(consumer, token)
    resp, content = client.request(access_token_url, "POST")
    if resp['status'] != '200':
        try:
            del request.session['request_token']
        except:
            pass
        messages.error(request, 'Invalid linkedin token response')
        return HttpResponseRedirect(reverse('edit_profile'))
    access_token = dict(cgi.parse_qsl(content))

    token = oauth.Token(access_token['oauth_token'],
        access_token['oauth_token_secret'])
    client = oauth.Client(consumer, token)
    resp, content = client.request("http://api.linkedin.com/v1/people/~:(id,first-name,last-name,industry,email-address)?format=json", "GET")
    if resp['status'] != '200':
        try:
            del request.session['request_token']
        except:
            pass
        messages.error(request, 'Invalid linkedin profile response')
        return HttpResponseRedirect(reverse('edit_profile'))

    profile_data = json.loads(content)
    userid = profile_data['id']
    username = profile_data.get('emailAddress', None)
    realname = profile_data.get('firstName', '') + ' ' + profile_data.get('lastName', '')
    provider_info = profile_data
    affiliation = 'LinkedIn.com'


    try:
        return handle_third_party_login(request, 'linkedin', userid,
                                        provider_info, affiliation)
    except AstakosUser.DoesNotExist, e:
        third_party_key = get_pending_key(request)
        user_info = {'affiliation': affiliation, 'realname': realname}
        return handle_third_party_signup(request, userid, 'linkedin',
                                         third_party_key,
                                         provider_info,
                                         user_info,
                                         template,
                                         extra_context)

