# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8
#
# Copyright © 2010 Greek Research and Technology Network
#

from django.contrib.auth.models import User, AnonymousUser
from synnefo.api.faults import fault

# XXX: we need to add a Vary X-Auth-Token, somehow
# XXX: or use a standard auth middleware instead?
#      but watch out for CSRF issues:
#      http://andrew.io/weblog/2010/01/django-piston-and-handling-csrf-tokens/

class TokenAuthentication(object):
    def is_authenticated(self, request):
        token = request.META.get('HTTP_X_AUTH_TOKEN', None)
        if not token:
            return False

        # XXX: lookup token in models and set request.user
        if token:
            request.user = AnonymousUser()
            return True

    def challenge(self):
        return fault.unauthorized

