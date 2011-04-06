from time import time
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from synnefo.db.models import SynnefoUser
from synnefo.logic.shibboleth import Tokens, register_shibboleth_user

class SynnefoAuthMiddleware(object):

    auth_token = "X-Auth-Token"
    auth_user  = "X-Auth-User"
    auth_key   = "X-Auth-Key"

    def process_request(self, request):

        if self.auth_token in request.META:
            #Retrieve user from DB or other caching mechanism
            user = SynnefoUser.objects.filter(auth_token = request.META[self.auth_token])
            if user is None :
                return HttpResponseRedirect(settings.SHIBBOLETH_HOST)
            request.user = user
            return

        #A user authenticated by Shibboleth
        if Tokens.SIB_EDU_PERSON_PRINCIPAL_NAME in request.META:
            #TODO: We must somehow make sure that we only process
            #      SIB headers when coming from a URL whitelist,
            #      or a similar for of restriction
            if request.get_host() not in settings.SHIBBOLETH_WHITELIST.keys():
                return HttpResponseRedirect(settings.SHIBBOLETH_HOST)

            user = None
            try:
                user = SynnefoUser.objects.get(
                    uniq = request.META[Tokens.SIB_EDU_PERSON_PRINCIPAL_NAME])
            except SynnefoUser.DoesNotExist:
                pass

            #No user with this id could be found in the database
            if user is None:
                #Try to register incoming user
                if register_shibboleth_user(request.META):
                    #Registration succeded, user allowed to proceed
                    return
                #Registration failed, redirect to Shibboleth
                return HttpResponseRedirect(settings.SHIBBOLETH_HOST)

            #At this point, the user has been identified in our database
            #Check user's auth token
            if time() - user.auth_token_created > settings.AUTH_TOKEN_DURATION * 3600:
                #The user's token has expired, re-login
                return HttpResponseRedirect(settings.SHIBBOLETH_HOST)

            #User and authentication token valid, user allowed to proceed
            return
            
        #An API authentication request
        if self.auth_user in request.META and 'X-Auth-Key' in request.META \
           and '/v1.1' == request.path and 'GET' == request.method:
            # This is here merely for compatibility with the Openstack API.
            # All normal users should authenticate through Sibbolleth. Admin
            # users or other selected users could use this as a bypass
            # mechanism
            user = SynnefoUser.objects.filter(username = request.META[self.auth_user])
            
            return HttpResponseRedirect(settings.SHIBBOLETH_HOST)

        #No authentication info found in headers, redirect to Shibboleth
        return HttpResponseRedirect(settings.SHIBBOLETH_HOST)

    def process_response(self, request, response):
        #Tell proxies and other interested parties that the
        #request varies based on the auth token, to avoid
        #caching of results
        response['Vary'] = self.auth_key
        return response

#class HttpResponseAuthenticationRequired(HttpResponse):
#    status_code = 401