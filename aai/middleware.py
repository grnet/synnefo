from time import time
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
        if self.auth_token in request.META:
            user = None
            #Retrieve user from DB or other caching mechanism
            try:
                user = SynnefoUser.objects.get(auth_token = request.META[self.auth_token])
            except SynnefoUser.DoesNotExist:
                return HttpResponseRedirect(settings.APP_INSTALL_URL + settings.LOGIN_PATH)

            #Check user's auth token
            if (time.time() -
                time.mktime(user.auth_token_created.timetuple()) +
                settings.AUTH_TOKEN_DURATION * 3600) > 0:
                #The user's token has expired, re-login
                return HttpResponseRedirect(settings.APP_INSTALL_URL + settings.LOGIN_PATH)

            request.user = user
            return

        #A user authenticated by Shibboleth, must include a uniq id
        if Tokens.SIB_EPPN in request.META:
            #We must somehow make sure that we only process
            #SIB headers when coming from a URL whitelist,
            #or a similar form of restriction
            #if request.get_host() not in settings.SHIBBOLETH_WHITELIST.keys():
            #    return HttpResponseRedirect(settings.APP_INSTALL_URL + settings.LOGIN_PATH)

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
                    response = HttpResponse()
                    response[self.auth_token] = user.auth_token
                    response['Location'] = settings.APP_INSTALL_URL 
                    response.status_code = 302
                    return response
                else:
                    return HttpResponseRedirect(settings.APP_INSTALL_URL + settings.LOGIN_PATH)

            #User and authentication token valid, user allowed to proceed
            return

        #An API authentication request
        if self.auth_user in request.META and self.auth_key in request.META and 'GET' == request.method:
            # This is here merely for compatibility with the Openstack API.
            # All normal users should authenticate through Sibbolleth. Admin
            # users or other selected users could use this as a bypass
            # mechanism
            user = SynnefoUser.objects\
                    .filter(name = request.META[self.auth_user]) \
                    .filter(uniq = request.META[self.auth_key])

            response = HttpResponse()
            if user.count() <= 0:
                response.status_code = 401
            else:
                response.status_code = 204
                response['X-Auth-Token'] = user[0].auth_token
                #TODO: set the following fields when we do have this info
                response['X-Server-Management-Url'] = ""
                response['X-Storage-Url'] = ""
                response['X-CDN-Management-Url'] = ""
            return response

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

