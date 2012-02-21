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

from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.utils.translation import ugettext as _
from django.contrib import messages
from django.utils.http import urlencode
from django.contrib.auth import login as auth_login, authenticate
from django.http import HttpResponse

from urllib import quote
from urlparse import urlunsplit, urlsplit

from astakos.im.settings import COOKIE_NAME, COOKIE_DOMAIN
from astakos.im.util import set_cookie

import logging

logger = logging.getLogger(__name__)

def login(request):
    """
    If the request user is authenticated, redirects to `next` request parameter
    if exists, otherwise redirects to astakos index page displaying an error
    message.
    If the request user is not authenticated, redirects to login in order to
    return back here after successful login.
    """
    if request.user.is_authenticated():
        next = request.GET.get('next')
        renew = request.GET.get('renew', None)
        if next:
            response = HttpResponse()
            if renew == '':
                request.user.renew_token()
                request.user.save()
                
                # authenticate before login
                user = authenticate(email=request.user.email, auth_token=request.user.auth_token)
                auth_login(request, user)
                set_cookie(response, user)
                logger.info('Token reset for %s' % request.user.email)
            parts = list(urlsplit(next))
            parts[3] = urlencode({'user': request.user.email, 'token': request.user.auth_token})
            url = urlunsplit(parts)
            response['Location'] = url
            response.status_code = 302
            return response
        else:
            msg = _('No next parameter')
            messages.add_message(request, messages.ERROR, msg)
            url = reverse('astakos.im.views.index')
            return redirect(url)
    else:
        # redirect to login with self as next
        url = reverse('astakos.im.views.index')
        url = '%s?next=%s' % (url, quote(request.build_absolute_uri()))
        return redirect(url)
