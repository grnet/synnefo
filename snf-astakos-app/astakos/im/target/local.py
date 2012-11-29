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

from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib import messages
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required

from astakos.im.util import prepare_response, get_query
from astakos.im.views import requires_anonymous, signed_terms_required
from astakos.im.models import PendingThirdPartyUser
from astakos.im.forms import LoginForm, ExtendedPasswordChangeForm
from astakos.im.settings import RATELIMIT_RETRIES_ALLOWED
from astakos.im.settings import ENABLE_LOCAL_ACCOUNT_MIGRATION

import astakos.im.messages as astakos_messages

from ratelimit.decorators import ratelimit

retries = RATELIMIT_RETRIES_ALLOWED - 1
rate = str(retries) + '/m'


@require_http_methods(["GET", "POST"])
@csrf_exempt
@requires_anonymous
@ratelimit(field='username', method='POST', rate=rate)
def login(request, on_failure='im/login.html'):
    """
    on_failure: the template name to render on login failure
    """
    was_limited = getattr(request, 'limited', False)
    form = LoginForm(data=request.POST,
                     was_limited=was_limited,
                     request=request)
    next = get_query(request).get('next', '')
    username = get_query(request).get('key')
    
    if not form.is_valid():
        return render_to_response(
            on_failure,
            {'login_form':form,
             'next':next,
             'key':username},
            context_instance=RequestContext(request)
        )
    # get the user from the cash
    user = form.user_cache

    message = None
    if not user:
        message = _(astakos_messages.ACCOUNT_AUTHENTICATION_FAILED)
    elif not user.is_active:
        if not user.activation_sent:
            message = _(astakos_messages.ACCOUNT_PENDING_ACTIVATION)
        else:
            send_activation_url = reverse('send_activation', kwargs={'user_id':user.id})
            message = _(astakos_messages.ACCOUNT_RESEND_ACTIVATION) % locals()
    elif user.provider not in ('local', ''):
        message = _(astakos_messages.NO_LOCAL_AUTH)
    
    if message:
        messages.error(request, message)
        return render_to_response(on_failure,
                                  {'login_form':form},
                                  context_instance=RequestContext(request))
    
    # hook for switching account to use third party authentication
    if ENABLE_LOCAL_ACCOUNT_MIGRATION and username:
        try:
            new = PendingThirdPartyUser.objects.get(
                username=username)
        except:
            messages.error(
                request,
                _(astakos_messages.SWITCH_ACCOUNT_FAILURE)
            )
            return render_to_response(
                on_failure,
                {'login_form':form,
                 'next':next},
                context_instance=RequestContext(request)
            )
        else:
            user.provider = new.provider
            user.third_party_identifier = new.third_party_identifier
            user.save()
            new.delete()
            messages.success(
                request,
                _(astakos_messages.SWITCH_ACCOUNT_SUCCESS_WITH_PROVIDER) % user.__dict__
            )
    return prepare_response(request, user, next)

@require_http_methods(["GET", "POST"])
@signed_terms_required
@login_required
def password_change(request, template_name='registration/password_change_form.html',
                    post_change_redirect=None, password_change_form=ExtendedPasswordChangeForm):
    if post_change_redirect is None:
        post_change_redirect = reverse('django.contrib.auth.views.password_change_done')
    if request.method == "POST":
        form = password_change_form(
            user=request.user,
            data=request.POST,
            session_key=request.session.session_key
        )
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(post_change_redirect)
    else:
        form = password_change_form(user=request.user)
    return render_to_response(template_name, {
        'form': form,
    }, context_instance=RequestContext(request))
