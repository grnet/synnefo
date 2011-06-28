from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.cache import patch_vary_headers
from synnefo.db.models import SynnefoUser
from synnefo.aai.shibboleth import Tokens, register_shibboleth_user
import time

DONT_CHECK = ['/api/', '/invitations/login']

class SynnefoAuthMiddleware(object):

    def process_request(self, request):

        for path in DONT_CHECK:
            if request.path.startswith(path):
                return

        # Special case for testing purposes, delivers the cookie for the
        # test user on first access
        if settings.BYPASS_AUTHENTICATION and \
           request.GET.get('test') is not None:
            u = SynnefoUser.objects.get(
                auth_token='46e427d657b20defe352804f0eb6f8a2')
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
                return HttpResponseRedirect(settings.APP_INSTALL_URL +
                                            settings.LOGIN_PATH)
            # check user's auth token validity
            if (time.time() -
                time.mktime(user.auth_token_expires.timetuple())) > 0:
                # the user's token has expired, prompt to re-login
                return HttpResponseRedirect(settings.APP_INSTALL_URL + settings.LOGIN_PATH)

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
                    return HttpResponseRedirect(settings.APP_INSTALL_URL +
                                                settings.LOGIN_PATH)

        if settings.TEST and 'TEST-AAI' in request.META:
            return HttpResponseRedirect(settings.APP_INSTALL_URL + settings.LOGIN_PATH)

        if request.path.endswith(settings.LOGIN_PATH):
            # avoid redirect loops
            return
        else:
            # no authentication info found in headers, redirect back
            return HttpResponseRedirect(settings.APP_INSTALL_URL + settings.LOGIN_PATH)

    def process_response(self, request, response):
        # Tell proxies and other interested parties that the request varies
        # based on X-Auth-Token, to avoid caching of results
        patch_vary_headers(response, ('X-Auth-Token',))
        return response

    def _redirect_shib_auth_user(self, user):
        expire_fmt = user.auth_token_expires.strftime('%a, %d-%b-%Y %H:%M:%S %Z')

        response = HttpResponse()
        response.set_cookie('X-Auth-Token', value=user.auth_token, expires=expire_fmt, path='/')
        response['X-Auth-Token'] = user.auth_token
        response['Location'] = settings.APP_INSTALL_URL
        response.status_code = 302
        return response


def add_url_exception(url):
    if not url in DONT_CHECK:
        DONT_CHECK.append(url)
