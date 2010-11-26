# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8
#
# Copyright © 2010 Greek Research and Technology Network
#

# XXX: most of the keys below are dummy
def instance_to_server(instance):
    server = {
            "id": instance["name"],
            "name": instance["name"],
            "hostId": instance["pnode"],
            "imageId": 1,
            "flavorId": 1,
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
