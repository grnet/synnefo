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
from synnefo.db.models import SynnefoUser
from synnefo.aai.shibboleth import Tokens, register_shibboleth_user
import time

class SynnefoAuthMiddleware(object):

    auth_token = "X-Auth-Token"
    auth_user  = "X-Auth-User"
    auth_key   = "X-Auth-Key"

    def process_request(self, request):
        if request.path.startswith('/api/') :
            return

        if request.path.startswith('/invitations/login') :
            return

        # Special case for testing purposes, delivers the cookie for the
        # test user on first access
        if settings.BYPASS_AUTHENTICATION and \
           request.GET.get('test') is not None:
            u = SynnefoUser.objects.get(
                auth_token='46e427d657b20defe352804f0eb6f8a2')
            return self._redirect_shib_auth_user(user = u)

        token = None
        #Try to find token in a cookie
        try:
            token = request.COOKIES['X-Auth-Token']
        except Exception:
            pass

        #Try to find token in request header
        if not token:
            token = request.META.get('HTTP_X_AUTH_TOKEN', None)

        if token:
            user = None
            #Retrieve user from DB or other caching mechanism
            try:
                user = SynnefoUser.objects.get(auth_token=token)
            except SynnefoUser.DoesNotExist:
                return HttpResponseRedirect(settings.APP_INSTALL_URL + settings.LOGIN_PATH)

            #Check user's auth token
            if (time.time() -
                time.mktime(user.auth_token_expires.timetuple())) > 0:
                #The user's token has expired, re-login
                return HttpResponseRedirect(settings.APP_INSTALL_URL + settings.LOGIN_PATH)

            request.user = user
            return

        #A user authenticated by Shibboleth, must include a uniq id
        if Tokens.SIB_EPPN in request.META and Tokens.SIB_SESSION_ID in request.META:
            user = None
            try:
                user = SynnefoUser.objects.get(
                    uniq = request.META[Tokens.SIB_EPPN])
            except SynnefoUser.DoesNotExist:
                pass

            #No user with this id could be found in the database
            if user is None:
                #Attempt to register the incoming user
                if register_shibboleth_user(request.META):
                    user = SynnefoUser.objects.get(
                        uniq = request.META[Tokens.SIB_EPPN])
                    return self._redirect_shib_auth_user(user)
                else:
                    return HttpResponseRedirect(settings.APP_INSTALL_URL + settings.LOGIN_PATH)

            #User and authentication token valid, user allowed to proceed
            return self._redirect_shib_auth_user(user)

        if settings.TEST:
            if 'TEST-AAI' in request.META:
                return HttpResponseRedirect(settings.APP_INSTALL_URL + settings.LOGIN_PATH)
        else:
            #Avoid redirect loops
            if request.path.endswith(settings.LOGIN_PATH): 
                return
            else :
                #No authentication info found in headers, redirect to Shibboleth
                return HttpResponseRedirect(settings.APP_INSTALL_URL + settings.LOGIN_PATH)

    def process_response(self, request, response):
        #Tell proxies and other interested parties that the
        #request varies based on the auth token, to avoid
        #caching of results
        response['Vary'] = self.auth_token
        return response

    def _redirect_shib_auth_user(self, user):
        expire_fmt = user.auth_token_expires.strftime('%a, %d-%b-%Y %H:%M:%S %Z')

        response = HttpResponse()

        response.set_cookie('X-Auth-Token', value=user.auth_token, expires = expire_fmt, path='/')
        response[self.auth_token] = user.auth_token
        response['Location'] = settings.APP_INSTALL_URL
        response.status_code = 302
        return response
