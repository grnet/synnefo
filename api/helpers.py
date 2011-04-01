# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8
#
# Copyright © 2010 Greek Research and Technology Network
#

# XXX: most of the keys below are dummy
from synnefo.api.errors import Unauthorized

def instance_to_server(instance):
    server = {
            "id": instance["name"],
            "name": instance["name"],
            "hostId": instance["pnode"],
            "imageRef": 1,
            "flavorRef": 1,
            "addresses": {
                "public": [ ],
                "private": [ ],
                },
            "metadata": { }
    }
    if instance["status"] == "running":
        server["status"] = "ACTIVE"
    elif instance["status"] == "ADMIN_down":
        server["status"] = "SUSPENDED"
    else:
        server["status"] = "UNKNOWN"

    return server


def paginator(func):
    """
    A dummy paginator decorator that uses limit/offset query parameters to
    limit the result set of a view. The view must return a dict with a single
    key and an iterable for its value.

    This doesn't actually speed up the internal processing, but it's useful to
    easily provide compatibility for the API
    """
    def inner_func(self, request, *args, **kwargs):
        resp = func(self, request, *args, **kwargs)
        if 'limit' not in request.GET or 'offset' not in request.GET:
            return resp

        # handle structures such as { '
        if len(resp.keys()) != 1:
            return resp
        key = resp.keys()[0]
        full = resp.values()[0]

        try:
            limit = int(request.GET['limit'])
            offset = int(request.GET['offset'])
            if offset < 0:
                raise ValueError
            if limit < 0:
                raise ValueError
            limit = limit + offset
            partial = full[offset:limit]
            return { key: partial }
        except (ValueError, TypeError):
            return { key: [] }

    return inner_func

def authenticate(func):
    """
    Custom authentication filter supporting the OpenStack API protocol.

    All API methods are required to go through this. Temporarily implemented as
    a decorator until we find a way to apply it to all incoming requests.
    """
    def inner(self, request, *args, **kwargs):
        if 'X-Auth-Token' in request.META:
            return func(self, request, *args, **kwargs)

        #An authentication request
        if 'X-Auth-User' in request.META and 'X-Auth-Key' in request.META \
           and '/v1.0' == request.path and 'GET' == request.method:
            #Do authenticate or redirect
            return

        raise Unauthorized

    return inner