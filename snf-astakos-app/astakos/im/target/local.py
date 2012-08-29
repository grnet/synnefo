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

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib import messages
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt

from astakos.im.util import prepare_response, get_query
from astakos.im.views import requires_anonymous
from astakos.im.forms import LoginForm
from astakos.im.settings import RATELIMIT_RETRIES_ALLOWED

from ratelimit.decorators import ratelimit

retries = RATELIMIT_RETRIES_ALLOWED-1
rate = str(retries)+'/m'

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
        request=request
    )
    next = get_query(request).get('next', '')
    if not form.is_valid():
        return render_to_response(on_failure,
                                  {'login_form':form,
                                   'next':next},
                                  context_instance=RequestContext(request))
    # get the user from the cash
    user = form.user_cache
    
    message = None
    if not user:
        message = _('Cannot authenticate account')
    elif not user.is_active:
        message = _('Inactive account')
    if message:
        messages.error(request, message)
        return render_to_response(on_failure,
                                  {'form':form},
                                  context_instance=RequestContext(request))
    
    return prepare_response(request, user, next)
