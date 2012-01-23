# Copyright 2011 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of GRNET S.A.

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.cache import patch_vary_headers
from synnefo.db.models import SynnefoUser
from synnefo.aai.shibboleth import Tokens, register_shibboleth_user
import time

DONT_CHECK = getattr(settings, "AAI_SKIP_AUTH_URLS", ['/api'])

class SynnefoAuthMiddleware(object):

    def process_request(self, request):

        for path in DONT_CHECK:
            if request.path.startswith(path):
                return

        # Special case for testing purposes, delivers the cookie for the
        # test user on first access
        if settings.BYPASS_AUTHENTICATION and \
           request.GET.get('test') is not None:
            try:
                u = SynnefoUser.objects.get(
                    auth_token=settings.BYPASS_AUTHENTICATION_SECRET_TOKEN)
            except SynnefoUser.DoesNotExist:
                raise Exception("No user found with token matching "
                                "BYPASS_AUTHENTICATION_SECRET_TOKEN.")
            return self._redirect_shib_auth_user(user = u)

        token = None

        # Try to find token in a cookie
        token = request.COOKIES.get('X-Auth-Token', None)

        # Try to find token in request header
        if not token:
            token = request.META.get('HTTP_X_AUTH_TOKEN', None)

        if token:
            # token was found, retrieve user from backing store
            try:
                user = SynnefoUser.objects.get(auth_token=token)

            except SynnefoUser.DoesNotExist:
                return HttpResponseRedirect(settings.LOGIN_URL)
            # check user's auth token validity
            if (time.time() -
                time.mktime(user.auth_token_expires.timetuple())) > 0:
                # the user's token has expired, prompt to re-login
                return HttpResponseRedirect(settings.LOGIN_URL)

            request.user = user
            return

        # token was not found but user authenticated by Shibboleth
        if Tokens.SHIB_EPPN in request.META and \
           Tokens.SHIB_SESSION_ID in request.META:
            try:
                user = SynnefoUser.objects.get(uniq=request.META[Tokens.SHIB_EPPN])
                return self._redirect_shib_auth_user(user)
            except SynnefoUser.DoesNotExist:
                if register_shibboleth_user(request.META):
                    user = SynnefoUser.objects.get(uniq=request.META[Tokens.SHIB_EPPN])
                    return self._redirect_shib_auth_user(user)
                else:
                    return HttpResponseRedirect(settings.LOGIN_URL)

        if settings.TEST and 'TEST-AAI' in request.META:
            return HttpResponseRedirect(settings.LOGIN_URL)

        if request.path.endswith(settings.LOGIN_URL):
            # avoid redirect loops
            return
        else:
            # no authentication info found in headers, redirect back
            return HttpResponseRedirect(settings.LOGIN_URL)

    def process_response(self, request, response):
        # Tell proxies and other interested parties that the request varies
        # based on X-Auth-Token, to avoid caching of results
        patch_vary_headers(response, ('X-Auth-Token',))
        return response

    def _redirect_shib_auth_user(self, user):
        expire_fmt = user.auth_token_expires.strftime('%a, %d-%b-%Y %H:%M:%S %Z')

        response = HttpResponse()
        response.set_cookie('X-Auth-Token', value=user.auth_token,
                            expires=expire_fmt, path='/')
        response['X-Auth-Token'] = user.auth_token
        response['Location'] = settings.APP_INSTALL_URL
        response.status_code = 302
        return response


def add_url_exception(url):
    if not url in DONT_CHECK:
        DONT_CHECK.append(url)
