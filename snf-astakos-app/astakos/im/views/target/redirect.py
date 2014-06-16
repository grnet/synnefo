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

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.utils.http import urlencode
from django.contrib.auth import authenticate
from django.http import (
    HttpResponse, HttpResponseBadRequest, HttpResponseForbidden)
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_http_methods

from urlparse import urlunsplit, urlsplit, parse_qsl

from astakos.im.util import restrict_next
from astakos.im.user_utils import login as auth_login, logout
from astakos.im.views.decorators import cookie_fix

import astakos.im.messages as astakos_messages
from astakos.im.settings import REDIRECT_ALLOWED_SCHEMES

import logging

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
@cookie_fix
def login(request):
    """
    If there is no ``next`` request parameter redirects to astakos index page
    displaying an error message.
    If the request user is authenticated and has signed the approval terms,
    redirects to `next` request parameter. If not, redirects to approval terms
    in order to return back here after agreeing with the terms.
    Otherwise, redirects to login in order to return back here after successful
    login.
    """
    next = request.GET.get('next')
    if not next:
        return HttpResponseBadRequest('Missing next parameter')

    if not restrict_next(next, allowed_schemes=REDIRECT_ALLOWED_SCHEMES):
        return HttpResponseForbidden(_(
            astakos_messages.NOT_ALLOWED_NEXT_PARAM))
    force = request.GET.get('force', None)
    response = HttpResponse()
    if force == '' and request.user.is_authenticated():
        logout(request)

    if request.user.is_authenticated():
        # if user has not signed the approval terms
        # redirect to approval terms with next the request path
        if not request.user.signed_terms:
            # first build next parameter
            parts = list(urlsplit(request.build_absolute_uri()))
            params = dict(parse_qsl(parts[3], keep_blank_values=True))
            parts[3] = urlencode(params)
            next = urlunsplit(parts)

            # build url location
            parts[2] = reverse('latest_terms')
            params = {'next': next}
            parts[3] = urlencode(params)
            url = urlunsplit(parts)
            response['Location'] = url
            response.status_code = 302
            return response
        renew = request.GET.get('renew', None)
        if renew == '':
            request.user.renew_token(
                flush_sessions=True,
                current_key=request.session.session_key
            )
            try:
                request.user.save()
            except ValidationError, e:
                return HttpResponseBadRequest(e)
            # authenticate before login
            user = authenticate(
                username=request.user.username,
                auth_token=request.user.auth_token
            )
            auth_login(request, user)
            logger.info('Token reset for %s' % user.username)
        parts = list(urlsplit(next))
        parts[3] = urlencode({
            'uuid': request.user.uuid,
            'token': request.user.auth_token
        })
        url = urlunsplit(parts)
        response['Location'] = url
        response.status_code = 302
        return response
    else:
        # redirect to login with next the request path

        # first build next parameter
        parts = list(urlsplit(request.build_absolute_uri()))
        params = dict(parse_qsl(parts[3], keep_blank_values=True))
        # delete force parameter
        if 'force' in params:
            del params['force']
        parts[3] = urlencode(params)
        next = urlunsplit(parts)

        # build url location
        parts[2] = reverse('login')
        params = {'next': next}
        parts[3] = urlencode(params)
        url = urlunsplit(parts)
        response['Location'] = url
        response.status_code = 302
        return response
