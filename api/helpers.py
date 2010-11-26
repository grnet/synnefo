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
