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

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.core.validators import ValidationError
from astakos.im import transaction

from astakos.im.models import PendingThirdPartyUser, AstakosUser
from astakos.im.util import get_query, login_url
from astakos.im import messages as astakos_messages
from astakos.im import auth_providers
from astakos.im.util import prepare_response

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


def add_pending_auth_provider(request, third_party_token, provider):
    if third_party_token:
        # use requests to assign the account he just authenticated with with
        # a third party provider account
        try:
            pending = PendingThirdPartyUser.objects.get(
                token=third_party_token,
                provider=provider.module)
            provider = pending.get_provider()
            provider.add_to_user()
            pending.delete()
        except PendingThirdPartyUser.DoesNotExist:
            messages.error(request, provider.get_add_failed_msg)


def get_pending_key(request):
    third_party_token = get_query(request).get(
        'key', request.session.get('pending_key', False))
    if 'pending_key' in request.session:
        del request.session['pending_key']
    return third_party_token


def handle_third_party_signup(request, userid, provider_module,
                              third_party_key,
                              provider_info=None,
                              pending_user_params=None,
                              template="im/third_party_check_local.html",
                              extra_context=None):

    if provider_info is None:
        provider_info = {}

    if pending_user_params is None:
        pending_user_params = {}

    if extra_context is None:
        extra_context = {}

    # build provider module object
    provider_data = {
        'affiliation': pending_user_params.get('affiliation', provider_module),
        'info_data': provider_info
    }
    provider = auth_providers.get_provider(provider_module, request.user,
                                           userid, **provider_data)

    # user wants to add another third party login method
    if third_party_key:
        messages.error(request, provider.get_invalid_login_msg)
        return HttpResponseRedirect(reverse('login') + "?key=%s" %
                                    third_party_key)

    if not provider.get_create_policy:
        messages.error(request, provider.get_disabled_for_create_msg)
        return HttpResponseRedirect(reverse('login'))

    # TODO: this could be stored in session
    # TODO: create a management command to clean old PendingThirdPartyUser
    user, created = PendingThirdPartyUser.objects.get_or_create(
        third_party_identifier=userid,
        provider=provider_module,
    )

    # update pending user
    for param, value in pending_user_params.iteritems():
        setattr(user, param, value)

    user.info = json.dumps(provider_info)
    user.generate_token()

    # skip non required fields validation errors. Reset the field instead of
    # raising a validation exception.
    try:
        user.full_clean()
    except ValidationError, e:
        non_required_fields = ['email', 'first_name',
                               'last_name', 'affiliation']
        for field in e.message_dict.keys():
            if field in non_required_fields:
                setattr(user, field, None)

    user.save()

    extra_context['provider'] = provider.module
    extra_context['provider_title'] = provider.get_title_msg
    extra_context['token'] = user.token
    extra_context['signup_url'] = reverse('signup') + \
        "?third_party_token=%s" % user.token
    extra_context['add_url'] = reverse('index') + \
        "?key=%s#other-login-methods" % user.token
    extra_context['can_create'] = provider.get_create_policy
    extra_context['can_add'] = provider.get_add_policy

    return HttpResponseRedirect(extra_context['signup_url'])


@transaction.commit_on_success
def handle_third_party_login(request, provider_module, identifier,
                             provider_info=None, affiliation=None,
                             third_party_key=None):

    if not provider_info:
        provider_info = {}

    if not affiliation:
        affiliation = provider_module.title()

    next_redirect = request.GET.get(
        'next', request.session.get('next_url', None))

    if 'next_url' in request.session:
        del request.session['next_url']

    third_party_request_params = get_third_party_session_params(request)
    from_login = third_party_request_params.get('from_login', False)
    switch_from = third_party_request_params.get('switch_from', False)
    provider_data = {
        'affiliation': affiliation,
        'info': provider_info
    }

    provider = auth_providers.get_provider(provider_module, request.user,
                                           identifier, **provider_data)

    # an existing user accessed the view
    if request.user.is_authenticated():
        if request.user.has_auth_provider(provider.module,
                                          identifier=identifier):
            return HttpResponseRedirect(reverse('edit_profile'))

        if provider.verified_exists():
            provider.log("add failed (identifier exists to another user)")
            messages.error(request, provider.get_add_exists_msg)
            return HttpResponseRedirect(reverse('edit_profile'))

        # automatically add identifier provider to user
        if not switch_from and not provider.get_add_policy:
            # TODO: handle existing uuid message separately
            provider.log("user cannot add provider")
            messages.error(request, provider.get_add_failed_msg)
            return HttpResponseRedirect(reverse('edit_profile'))

        user = request.user
        if switch_from:
            existing_provider = \
                request.user.auth_providers.active().get(
                    pk=int(switch_from), module=provider_module).settings

            # this is not a provider removal so we don't not use
            # provider.remove_from_user. Use low level access to the provider
            # db instance.
            if not provider.verified_exists():
                if provider.get_add_policy:
                    existing_provider._instance.delete()
                    existing_provider.log("removed")
                    provider.add_to_user()
                    provider.log("added")
            else:
                messages.error(request, provider.get_add_exists_msg)
                return HttpResponseRedirect(reverse('edit_profile'))

            messages.success(request, provider.get_switch_success_msg)
            return HttpResponseRedirect(reverse('edit_profile'))

        provider.add_to_user()
        provider.log("added")
        provider = user.get_auth_provider(provider_module, identifier)
        messages.success(request, provider.get_added_msg)
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

    provider = user.get_auth_provider(provider_module, identifier)

    if user.is_active:
        if not provider.get_login_policy:
            messages.error(request, provider.get_login_disabled_msg)
            return HttpResponseRedirect(reverse('login'))

        # authenticate user
        response = prepare_response(request, user, next_redirect,
                                    'renew' in request.GET)

        messages.success(request, provider.get_login_success_msg)
        add_pending_auth_provider(request, third_party_key, provider)
        response.set_cookie('astakos_last_login_method', provider_module)
        provider.update_last_login_at()
        return response
    else:
        message = user.get_inactive_message(provider_module, identifier)
        messages.error(request, message)
        return HttpResponseRedirect(login_url(request))
