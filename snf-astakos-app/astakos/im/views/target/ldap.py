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

from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import HttpResponseRedirect

from astakos.im.models import AstakosUser
from astakos.im import settings
from astakos.im.views.target import get_pending_key, \
    handle_third_party_signup, handle_third_party_login, \
    populate_user_attributes
from astakos.im.views.decorators import (cookie_fix, requires_auth_provider,
                                         requires_anonymous)
from ratelimit.decorators import ratelimit
from django.core.urlresolvers import reverse
from django.views.decorators.csrf import csrf_exempt
from astakos.im import auth_providers as auth
from astakos.im.views.util import render_response
from astakos.im.forms import LDAPLoginForm
from astakos.im.util import get_query, get_context
from astakos.im.views.im import handle_get_to_login_view
from django.shortcuts import render_to_response
from django.utils.encoding import smart_unicode
from astakos.im.views.decorators import login_required

import logging

retries = settings.RATELIMIT_RETRIES_ALLOWED - 1
rate = str(retries) + '/m'

logger = logging.getLogger(__name__)

LDAP_PROVIDER = auth.get_provider('ldap')


@requires_auth_provider('ldap')
@require_http_methods(["GET", "POST"])
@csrf_exempt
@requires_anonymous
@cookie_fix
@ratelimit(field='username', method='POST', rate=rate)
def login(request, template_name="im/login.html", on_failure='im/login.html',
          signup_template="/im/third_party_check_local.html",
          extra_context=None):
    """
    on_failure: the template name to render on login failure
    """
    if request.method == 'GET':
        return handle_get_to_login_view(request,
                                        primary_provider=LDAP_PROVIDER,
                                        login_form=LDAPLoginForm(request),
                                        template_name=template_name,
                                        extra_context=extra_context)

    # 'limited' attribute is used by recapatcha
    was_limited = getattr(request, 'limited', False)
    next = get_query(request).get('next', '')
    third_party_token = get_query(request).get('key', False)

    form = LDAPLoginForm(data=request.POST,
                         was_limited=was_limited,
                         request=request)
    provider = LDAP_PROVIDER

    if not form.is_valid():
        if third_party_token:
            messages.info(request, provider.get_login_to_add_msg)

        return render_to_response(
            on_failure,
            {'login_form': form,
             'next': next,
             'key': third_party_token},
            context_instance=get_context(request,
                                         primary_provider=LDAP_PROVIDER))

    # get the user from the cache
    user = form.ldap_user_cache
    provider = auth.get_provider('ldap', user)

    affiliation = 'LDAP'
    provider_info = dict(user.ldap_user.attrs)
    try:
        user_info = populate_user_attributes(provider, provider_info)
        user_id = user_info.pop('identifier')
    except (ValueError, KeyError):
        logger.exception("Failed to map attributes from LDAP provider."
                         " Provider attributes: %s", provider_info)
        msg = 'Invalid LDAP response. Please contact support.'
        messages.error(request, msg)
        return HttpResponseRedirect(reverse('login'))

    provider_info = dict([(k, smart_unicode(v, errors="ignore"))
                          for k, v in provider_info.items()
                          if k in provider.get_provider_info_attributes()])

    user_info['affiliation'] = affiliation

    if hasattr(user, 'groups'):
        # User will have groups if AUTH_LDAP_MIRROR_GROUPS option is set.
        user_info['groups'] = user.groups

    try:
        return handle_third_party_login(request, provider_module="ldap",
                                        identifier=user_id,
                                        provider_info=provider_info,
                                        affiliation=affiliation,
                                        user_info=user_info)
    except AstakosUser.DoesNotExist:
        third_party_key = get_pending_key(request)
        return handle_third_party_signup(request, user_id, 'ldap',
                                         third_party_key,
                                         provider_info,
                                         user_info,
                                         signup_template,
                                         extra_context)


@require_http_methods(["GET", "POST"])
@login_required
@cookie_fix
@requires_auth_provider('ldap', login=True)
def add(request, template_name='im/auth/ldap_add.html'):

    provider = auth.get_provider('ldap', request.user)

    # Check that provider's policy allows to add provider to account
    if not provider.get_add_policy:
        messages.error(request, provider.get_add_disabled_msg)
        return HttpResponseRedirect(reverse('edit_profile'))

    if request.method == "GET":
        return render_response(
            template_name,
            login_form=LDAPLoginForm(request=request),
            context_instance=get_context(request, provider=LDAP_PROVIDER)
        )

    form = LDAPLoginForm(data=request.POST,
                         request=request)

    if form.is_valid():
        provider = auth.get_provider('ldap', request.user)

        user = form.ldap_user_cache

        provider_info = dict(user.ldap_user.attrs)
        try:
            user_info = populate_user_attributes(provider, provider_info)
            user_id = user_info.pop('identifier')
        except (ValueError, KeyError):
            logger.exception("Failed to map attributes from LDAP provider."
                             " Provider attributes: %s", provider_info)
            msg = 'Invalid LDAP response. Please contact support.'
            messages.error(request, msg)
            return HttpResponseRedirect(reverse('login'))
        affiliation = 'LDAP'  # TODO: Add LDAP server name?
        user_info['affiliation'] = affiliation
        provider_info = dict([(k, smart_unicode(v, errors="ignore"))
                              for k, v in provider_info.items()
                              if k in provider.get_provider_info_attributes()])

        if hasattr(user, 'groups'):
            # User will have groups if AUTH_LDAP_MIRROR_GROUPS option is set.
            user_info['groups'] = user.groups

        return handle_third_party_login(request, provider_module="ldap",
                                        identifier=user_id,
                                        provider_info=provider_info,
                                        affiliation=affiliation,
                                        user_info=user_info)
    else:
        return render_response(
            template_name,
            form=LDAPLoginForm(request=request),
            context_instance=get_context(request, provider=LDAP_PROVIDER)
        )
