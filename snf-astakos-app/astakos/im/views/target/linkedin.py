# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
    _url = ("http://api.linkedin.com/v1/people/~:(id,first-name,last-name,"
            "industry,email-address)?format=json")
    resp, content = client.request(_url, "GET")
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
    realname = profile_data.get('firstName', '') + ' ' + profile_data.get(
        'lastName', '')
    provider_info = profile_data
    affiliation = 'LinkedIn.com'
    user_info = {'affiliation': affiliation, 'realname': realname}

    try:
        return handle_third_party_login(request, 'linkedin', userid,
                                        provider_info, affiliation,
                                        user_info=user_info)
    except AstakosUser.DoesNotExist, e:
        third_party_key = get_pending_key(request)
        return handle_third_party_signup(request, userid, 'linkedin',
                                         third_party_key,
                                         provider_info,
                                         user_info,
                                         template,
                                         extra_context)
