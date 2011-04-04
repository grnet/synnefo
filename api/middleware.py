from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from synnefo.api.errors import Unauthorized
from synnefo.db.models import SynnefoUser

class SynnefoAuthMiddleware(object):

    auth_token = "X-Auth-Token"
    auth_user  = "X-Auth-User"
    auth_key   = "X-Auth-Key"

    def process_request(self, request):

        if self.auth_token in request.META:
            #Retrieve user from DB or other caching mechanism
            user = SynnefoUser.objects.filter(auth_token = request.META[self.auth_token])
            if user is None :
                return HttpResponseRedirect(content='Athentication Required')
            request.user = user
            return

        #An authentication request
        if self.auth_user in request.META and 'X-Auth-Key' in request.META \
           and '/v1.0' == request.path and 'GET' == request.method:
            # This is here merely for compatibility with the Openstack API.
            # All normal users should authenticate through Sibbolleth. Admin
            # users or other selected users could use this as a bypass
            # mechanism
            user = SynnefoUser.objects.filter(username = request.META[self.auth_user])

            return HttpResponseRedirect(content= settings.SIBBOLLETH_HOST)

        return HttpResponseRedirect(content='Athentication Required')

#class HttpResponseAuthenticationRequired(HttpResponse):
#    status_code = 401