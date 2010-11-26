# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8
#
# Copyright © 2010 Greek Research and Technology Network
#

from piston.handler import AnonymousBaseHandler
from django.http import HttpResponse
from django.core.urlresolvers import reverse

CURRENT_SERVER_VERSION = 'v1.0'

class AuthHandler(AnonymousBaseHandler):
    allowed_methods = ('GET',)

    def read(self, request):
        user = request.META.get('HTTP_X_AUTH_USER', None)
        key = request.META.get('HTTP_X_AUTH_KEY', None)
        if user is None or key is None:
            return HttpResponse(status=401)

        response = HttpResponse(status=204)

        # dummy auth
        response['X-Auth-Token'] = 'dummy-token'

        # return X-Server-Management's URL
        url = reverse('synnefo.api.urls.version_handler',
                kwargs={'number': CURRENT_SERVER_VERSION})
        url = request.build_absolute_uri(url)

        response['X-Server-Management-Url'] = url

        return response
