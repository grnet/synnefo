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

from astakos.im.models import PendingThirdPartyUser
from astakos.im.util import get_query
from astakos.im import messages as astakos_messages
from astakos.im import auth_providers
from astakos.im.util import prepare_response, get_context
from astakos.im.views import requires_anonymous, render_response


def add_pending_auth_provider(request, third_party_token):

    if third_party_token:
        # use requests to assign the account he just authenticated with with
        # a third party provider account
        try:
            request.user.add_pending_auth_provider(third_party_token)
            messages.success(request, _(astakos_messages.AUTH_PROVIDER_ADDED))
        except PendingThirdPartyUser.DoesNotExist:
            messages.error(request, _(astakos_messages.AUTH_PROVIDER_ADD_FAILED))


def get_pending_key(request):

    third_party_token = get_query(request).get('key', False)
    if not third_party_token:
        third_party_token = request.session.get('pending_key', None)
        if third_party_token:
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
        messages.error(request,
                       _(astakos_messages.AUTH_PROVIDER_INVALID_LOGIN))
        return HttpResponseRedirect(reverse('login'))

    # eppn not stored in astakos models, create pending profile
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

