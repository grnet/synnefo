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
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import get_object_or_404

from urlparse import urlunsplit, urlsplit

from astakos.im.util import prepare_response, get_context
from astakos.im.views import requires_anonymous, render_response, \
        requires_auth_provider
from astakos.im.settings import ENABLE_LOCAL_ACCOUNT_MIGRATION, BASEURL
from astakos.im.models import AstakosUser, PendingThirdPartyUser
from astakos.im.forms import LoginForm
from astakos.im.activation_backends import get_backend, SimpleBackend
from astakos.im import settings

import astakos.im.messages as astakos_messages

import logging

logger = logging.getLogger(__name__)

import oauth2 as oauth
import cgi

consumer = oauth.Consumer(settings.TWITTER_TOKEN, settings.TWITTER_SECRET)
client = oauth.Client(consumer)

request_token_url = 'http://twitter.com/oauth/request_token'
access_token_url = 'http://twitter.com/oauth/access_token'
authenticate_url = 'http://twitter.com/oauth/authenticate'


@requires_auth_provider('twitter', login=True)
@require_http_methods(["GET", "POST"])
def login(request):
    resp, content = client.request(request_token_url, "GET")
    if resp['status'] != '200':
        messages.error(request, 'Invalid Twitter response')
        return HttpResponseRedirect(reverse('edit_profile'))

    request.session['request_token'] = dict(cgi.parse_qsl(content))
    url = "%s?oauth_token=%s" % (authenticate_url,
        request.session['request_token']['oauth_token'])

    return HttpResponseRedirect(url)


@requires_auth_provider('twitter', login=True)
@require_http_methods(["GET", "POST"])
def authenticated(
    request,
    template='im/third_party_check_local.html',
    extra_context={}
):

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

    # an existing user accessed the view
    if request.user.is_authenticated():
        if request.user.has_auth_provider('twitter', identifier=userid):
            return HttpResponseRedirect(reverse('edit_profile'))

        # automatically add eppn provider to user
        user = request.user
        if not request.user.can_add_auth_provider('twitter',
                                                  identifier=userid):
            messages.error(request, 'Account already exists.')
            return HttpResponseRedirect(reverse('edit_profile'))

        user.add_auth_provider('twitter', identifier=userid)
        return HttpResponseRedirect(reverse('edit_profile'))

    try:
        # astakos user exists ?
        user = AstakosUser.objects.get_auth_provider_user(
            'twitter',
            identifier=userid
        )
        if user.is_active:
            # authenticate user
            return prepare_response(request,
                                    user,
                                    request.GET.get('next'),
                                    'renew' in request.GET)
        elif not user.activation_sent:
            message = _('Your request is pending activation')
			#TODO: use astakos_messages
            if not settings.MODERATION_ENABLED:
                url = user.get_resend_activation_url()
                msg_extra = _('<a href="%s">Resend activation email?</a>') % url
                message = message + u' ' + msg_extra

            messages.error(request, message)
            return HttpResponseRedirect(reverse('login'))

        else:
			#TODO: use astakos_messages
            message = _(u'Account disabled. Please contact support')
            messages.error(request, message)
            return HttpResponseRedirect(reverse('login'))

    except AstakosUser.DoesNotExist, e:
		#TODO: use astakos_messages
        # eppn not stored in astakos models, create pending profile
        user, created = PendingThirdPartyUser.objects.get_or_create(
            third_party_identifier=userid,
            provider='twitter',
        )
        # update pending user
        user.affiliation = 'Twitter'
        user.generate_token()
        user.save()

        extra_context['provider'] = 'twitter'
        extra_context['token'] = user.token
        extra_context['signup_url'] = reverse('twitter_signup', args=(user.token,))

        return render_response(
            template,
            context_instance=get_context(request, extra_context)
        )


@requires_auth_provider('twitter', login=True, create=True)
@require_http_methods(["GET"])
@requires_anonymous
def signup(
    request,
    token,
    backend=None,
    on_creation_template='im/third_party_registration.html',
    extra_context={}):

    extra_context = extra_context or {}
    if not token:
		#TODO: use astakos_messages
        return HttpResponseBadRequest(_('Missing key parameter.'))

    pending = get_object_or_404(PendingThirdPartyUser, token=token)
    d = pending.__dict__
    d.pop('_state', None)
    d.pop('id', None)
    d.pop('token', None)
    d.pop('created', None)
    user = AstakosUser(**d)

    try:
        backend = backend or get_backend(request)
    except ImproperlyConfigured, e:
        messages.error(request, e)
    else:
        extra_context['form'] = backend.get_signup_form(
            provider='twitter',
            instance=user
        )

    extra_context['provider'] = 'twitter'
    extra_context['third_party_token'] = token
    return render_response(
            on_creation_template,
            context_instance=get_context(request, extra_context)
    )

