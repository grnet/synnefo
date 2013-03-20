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

from django.contrib import messages
from django.utils.translation import ugettext as _
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

from astakos.im.models import PendingThirdPartyUser, AstakosUser
from astakos.im.util import get_query, login_url
from astakos.im import messages as astakos_messages
from astakos.im import auth_providers
from astakos.im.util import prepare_response, get_context
from astakos.im.views import requires_anonymous, render_response
import logging

logger = logging.getLogger(__name__)


def init_third_party_session(request):
    params = dict(request.GET.items())
    request.session['third_party_request_params'] = params


def get_third_party_session_params(request):
    if 'third_party_request_params' in request.session:
        params = request.session['third_party_request_params']
        del request.session['third_party_request_params']
        return params
    return {}


def add_pending_auth_provider(request, third_party_token):
    if third_party_token:
        # use requests to assign the account he just authenticated with with
        # a third party provider account
        try:
            request.user.add_pending_auth_provider(third_party_token)
        except PendingThirdPartyUser.DoesNotExist:
            messages.error(request, _(astakos_messages.AUTH_PROVIDER_ADD_FAILED))


def get_pending_key(request):
    third_party_token = get_query(request).get('key', request.session.get('pending_key', False))
    if 'pending_key' in request.session:
        del request.session['pending_key']
    return third_party_token


def handle_third_party_signup(request, userid, provider_module, third_party_key,
                              provider_info={},
                              pending_user_params={},
                              template="im/third_party_check_local.html",
                              extra_context={}):

    # user wants to add another third party login method
    if third_party_key:
        messages.error(request, _(astakos_messages.AUTH_PROVIDER_INVALID_LOGIN))
        return HttpResponseRedirect(reverse('login') + "?key=%s" % third_party_key)

    provider = auth_providers.get_provider(provider_module)
    if not provider.is_available_for_create():
        logger.info('%s signup is disabled.' %
                    (provider_module,))
        messages.error(request,
                       _(astakos_messages.AUTH_PROVIDER_INVALID_LOGIN)
                       % {'provider_name': provider.get_title_display,
                          'provider': provider_module})
        return HttpResponseRedirect(reverse('login'))

    # identifier not stored in astakos models, create pending profile
    user, created = PendingThirdPartyUser.objects.get_or_create(
        third_party_identifier=userid,
        provider=provider_module,
    )
    # update pending user
    for param, value in pending_user_params.iteritems():
        setattr(user, param, value)

    user.info = json.dumps(provider_info)
    user.generate_token()
    user.save()

    extra_context['provider'] = provider_module
    extra_context['provider_title'] = provider.get_title_display
    extra_context['token'] = user.token
    extra_context['signup_url'] = reverse('signup') + \
                                "?third_party_token=%s" % user.token
    extra_context['add_url'] = reverse('index') + \
                                "?key=%s#other-login-methods" % user.token
    extra_context['can_create'] = provider.is_available_for_create()
    extra_context['can_add'] = provider.is_available_for_add()

    return HttpResponseRedirect(extra_context['signup_url'])
    #return render_response(
        #template,
        #context_instance=get_context(request, extra_context)
    #)



def handle_third_party_login(request, provider_module, identifier,
                             provider_info=None, affiliation=None,
                             third_party_key=None):

    if not provider_info:
        provider_info = {}

    if not affiliation:
        affiliation = provider_module.title()

    next_redirect = request.GET.get('next', request.session.get('next_url', None))
    if 'next_url' in request.session:
        del request.session['next_url']

    third_party_request_params = get_third_party_session_params(request)
    from_login = third_party_request_params.get('from_login', False)

    # an existing user accessed the view
    if request.user.is_authenticated():

        if request.user.has_auth_provider(provider_module, identifier=identifier):
            return HttpResponseRedirect(reverse('edit_profile'))

        # automatically add identifier provider to user
        user = request.user
        if not request.user.can_add_auth_provider(provider_module,
                                                  identifier=identifier):
            logger.info('%s failed to add %s: %r' % \
                        (user.log_display, provider_module, provider_info))
            # TODO: handle existing uuid message separately
            messages.error(request, _(astakos_messages.AUTH_PROVIDER_ADD_FAILED) +
                          u' ' + _(astakos_messages.AUTH_PROVIDER_ADD_EXISTS))
            return HttpResponseRedirect(reverse('edit_profile'))

        user.add_auth_provider(provider_module, identifier=identifier,
                               affiliation=affiliation,
                               provider_info=provider_info)
        logger.info('%s added %s: %r' % \
                    (user.log_display, provider_module, provider_info))
        provider = auth_providers.get_provider(provider_module)
        message = _(astakos_messages.AUTH_PROVIDER_ADDED) % provider.get_method_prompt_display
        messages.success(request, message)
        return HttpResponseRedirect(reverse('edit_profile'))

    # astakos user exists ?
    try:
        user = AstakosUser.objects.get_auth_provider_user(
            provider_module,
            identifier=identifier,
            user__email_verified=True,
        )
    except AstakosUser.DoesNotExist:
        # TODO: add a message ? redirec to login ?
        if astakos_messages.AUTH_PROVIDER_SIGNUP_FROM_LOGIN:
            messages.warning(request,
                             astakos_messages.AUTH_PROVIDER_SIGNUP_FROM_LOGIN)
        raise

    if not third_party_key:
        third_party_key = get_pending_key(request)

    if user.is_active:
        # authenticate user
        response = prepare_response(request,
                                user,
                                next_redirect,
                                'renew' in request.GET)
        provider = auth_providers.get_provider(provider_module)
        messages.success(request, _(astakos_messages.LOGIN_SUCCESS) %
                         _(provider.get_login_message_display))
        add_pending_auth_provider(request, third_party_key)
        response.set_cookie('astakos_last_login_method', provider_module)
        return response
    else:
        message = user.get_inactive_message()
        messages.error(request, message)
        return HttpResponseRedirect(login_url(request))

