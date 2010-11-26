# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8
#
# Copyright © 2010 Greek Research and Technology Network
#

from piston.handler import BaseHandler, AnonymousBaseHandler
from synnefo.api.faults import fault, noContent, accepted

VERSIONS = [
    {
        "status": "CURRENT",
        "id": "v1.0",
        "docURL" : "http://docs.rackspacecloud.com/servers/api/v1.0/cs-devguide-20090714.pdf ",
        "wadl" : "http://docs.rackspacecloud.com/servers/api/v1.0/application.wadl"
    },
]

class VersionHandler(AnonymousBaseHandler):
    allowed_methods = ('GET',)

    def read(self, request, number=None):
        if number is None:
            versions = map(lambda v: {
                        "status": v["status"],
                        "id": v["id"],
                    }, VERSIONS)
            return { "versions": versions }
        else:
            for version in VERSIONS:
                if version["id"] == number:
                    return { "version": version }
            return fault.itemNotFound


# XXX: incomplete
class ServerHandler(BaseHandler):
    def read(self, request, id=None):
        if id is None:
            return self.read_all(request)
        elif id is "detail":
            return self.read_all(request, detail=True)
        else:
            return self.read_one(request, id)

    def read_one(self, request, id):
        print ("server info %s" % id)
        return {}

    def read_all(self, request, detail=False):
        if not detail:
            print "server info all"
        else:
            print "server info all detail"
        return {}

    def create(self, request):
        return accepted

    def update(self, request, id):
        return noContent

    def delete(self, request, id):
        return accepted


class ServerAddressHandler(BaseHandler):
    allowed_methods = ('GET', 'PUT', 'DELETE')

    def read(self, request, id, type=None):
        """List IP addresses for a server"""
        if type is None:
            pass
        elif type == "private":
            pass
        elif type == "public":
            pass
        return {}

    def update(self, request, id, address):
        """Share an IP address to another in the group"""
        return accepted

    def delete(self, request, id, address):
        """Unshare an IP address"""
        return accepted


class ServerActionHandler(BaseHandler):
    allowed_methods = ('POST',)

    def create(self, request, id):
        """Reboot, rebuild, resize, confirm resized, revert resized"""
        print ("server action %s" % id)
        return accepted


class ServerBackupHandler(BaseHandler):
    """ Backup Schedules are not implemented yet, return notImplemented """
    allowed_methods = ('GET', 'POST', 'DELETE')

    def read(self, request, id):
        return fault.notImplemented

    def create(self, request, id):
        return fault.notImplemented

    def delete(self, request, id):
        return fault.notImplemented


class FlavorHandler(BaseHandler):
    allowed_methods = ('GET',)
    flavors = [
          {
            "id" : 1,
            "name" : "256 MB Server",
            "ram" : 256,
            "disk" : 10
          },
          {
            "id" : 2,
            "name" : "512 MB Server",
            "ram" : 512,
            "disk" : 20
          }
        ]

    def read(self, request, id=None):
        """
        List flavors or retrieve one

        Returns: OK
        Faults: cloudServersFault, serviceUnavailable, unauthorized,
                badRequest, itemNotFound
        """
        if id is None:
            simple = map(lambda v: {
                        "id": v["id"],
                        "name": v["name"],
                    }, self.flavors)
            return { "flavors": simple }
        elif id == "detail":
            return { "flavors": self.flavors }
        else:
            for flavor in self.flavors:
                if str(flavor["id"]) == id:
                    return { "flavor": flavor }
            return fault.itemNotFound


class ImageHandler(BaseHandler):
    allowed_methods = ('GET', 'POST')

    def read(self, request, id=None):
        """
        List images or retrieve one

        Returns: OK
        Faults: cloudServersFault, serviceUnavailable, unauthorized,
                badRequest, itemNotFound
        """
        if id is None:
            return {}
        elif id == "detail":
            return {}
        else:
            return fault.itemNotFound

    def create(self, request):
        """Create a new image"""
        return accepted
