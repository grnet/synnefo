from synnefo.api.errors import Unauthorized
from synnefo.db.models import SynnefoUser

class SynnefoAuthMiddleware(object):

    auth_token = "X-Auth-Token"
    auth_user  = "X-Auth-User"
    auth_key   = "X-Auth-Key"

    def process_request(self, request):
        if self.auth_token in request.META:
            #Retrieve user from DB
            user = SynnefoUser.objects.get(request.META.get(self.auth_token))
            if user is None :
                return
            request.user = user

        #An authentication request
        if self.auth_user in request.META and 'X-Auth-Key' in request.META \
           and '/v1.0' == request.path and 'GET' == request.method:
            #Do authenticate or redirect
            return

        raise Unauthorized