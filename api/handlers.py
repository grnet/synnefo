# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8
#
# Copyright Â© 2010 Greek Research and Technology Network
#

from django.conf import settings
from piston.handler import BaseHandler, AnonymousBaseHandler
from synnefo.api.faults import fault, noContent, accepted, created
from synnefo.api.helpers import instance_to_server, paginator
from synnefo.util.rapi import GanetiRapiClient, GanetiApiError
from synnefo.db.models import *
from util.rapi import GanetiRapiClient


try:
    rapi = GanetiRapiClient(*settings.GANETI_CLUSTER_INFO)
    rapi.GetVersion()
except:
    raise fault.serviceUnavailable
#If we can't connect to the rapi successfully, don't do anything
#TODO: add logging/admin alerting

backend_prefix_id = settings.BACKEND_PREFIX_ID

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
            raise fault.itemNotFound


class ServerHandler(BaseHandler):
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    def read(self, request, id=None):
        from time import sleep
        sleep(1)
        #TODO: delete the sleep once the mock objects are removed
        if id is None:
            return self.read_all(request)
        elif id == "detail":
            return self.read_all(request, detail=True)
        else:
            return self.read_one(request, id)

    def read_one(self, request, id):
        virtual_servers = VirtualMachine.objects.all()
        #get all VM's for now, FIX it to take the user's VMs only yet
        try:
            instance = rapi.GetInstance(id)
            servers = VirtualMachine.objects.all()[0]
            return { "server": instance_to_server(instance) }
        except GanetiApiError:
            raise fault.itemNotFound

    @paginator
    def read_all(self, request, detail=False):
        virtual_servers = VirtualMachine.objects.all()
        #get all VM's for now, FIX it to take the user's VMs only

        if not detail:
            virtual_servers = VirtualMachine.objects.filter(owner=User.objects.all()[0])
            return { "servers": [ { "id": s.id, "name": s.name } for s in virtual_servers ] }
        else:
            virtual_servers_list = [{'status': server.rsapi_state, 
                                     'flavorId': server.flavor.id, 
                                     'name': server.name, 
                                     'id': server.id, 
                                     'imageId': server.sourceimage.id, 
                                     'metadata': {'Server_Label': server.description, 
                                                  'hostId': '9e107d9d372bb6826bd81d3542a419d6',
                                                  'addresses': {'public': ['67.23.10.133'],
                                                                'private': ['10.176.42.17'],
                                                                }
                                                  }
                                    } for server in virtual_servers]
            #pass some fake data regarding ip, since we don't have any such data
            return { "servers":  virtual_servers_list }                


    def create(self, request):
        print 'create machine was called'
        rapi.CreateInstance('create', 'machine-unwebXYZ', 'plain', [{"size": 5120}], [{}], os='debootstrap+default', ip_check=False, name_check=False,pnode="store68", beparams={'auto_balance': True, 'vcpus': 2, 'memory': 1024})
        #TODO: replace with real data from request.POST
        return accepted

    def update(self, request, id):
        return noContent

    def delete(self, request, id):
        machine = 'machine-XXX' #VirtualMachine.objects.get(id=id_from_instance_name(id))
        print 'deleting machine %s' % machine
        rapi.DeleteInstance(machine.name)
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
    allowed_methods = ('POST', 'DELETE', 'GET', 'PUT')
#TODO: remove GET/PUT
    
    def read(self, request, id):
        return accepted

    def create(self, request, id):
        """Reboot, rebuild, resize, confirm resized, revert resized"""
        try:
            machine = VirtualMachine.objects.get(id=id)
        except:
            raise fault.itemNotFound
        reboot_request = request.POST.get('reboot', None)
        shutdown_request = request.POST.get('shutdown', None)
        if reboot_request:
            print 'reboot was asked, with options: %s' % reboot_request   
            rapi.RebootInstance(machine)
        elif shutdown_request:
            print 'shutdown was asked, with options: %s' % shutdown_request               
            rapi.ShutdownInstance(machine)
        return accepted


    def delete(self, request, id):
        """Delete an Instance"""
        return accepted

    def update(self, request, id):
        return noContent



#read is called on GET requests
#create is called on POST, and creates new objects, and should return them (or rc.CREATED.)
#update is called on PUT, and should update an existing product and return them (or rc.ALL_OK.)
#delete is called on DELETE, and should delete an existing object. Should not return anything, just rc.DELETED.'''


class ServerBackupHandler(BaseHandler):
    """ Backup Schedules are not implemented yet, return notImplemented """
    allowed_methods = ('GET', 'POST', 'DELETE')

    def read(self, request, id):
        raise fault.notImplemented

    def create(self, request, id):
        raise fault.notImplemented

    def delete(self, request, id):
        raise fault.notImplemented


class FlavorHandler(BaseHandler):
    allowed_methods = ('GET',)
    flavors = Flavor.objects.all()
    flavors = [ {'id': flavor.id, 'name': flavor.name, 'ram': flavor.ram, \
             'disk': flavor.disk} for flavor in flavors]

    def read(self, request, id=None):
        """
        List flavors or retrieve one

        Returns: OK
        Faults: cloudServersFault, serviceUnavailable, unauthorized,
                badRequest, itemNotFound
        """
        if id is None:
            simple = map(lambda v: {
                        "id": v['id'],
                        "name": v['name'],
                    }, self.flavors)
            return { "flavors": simple }
        elif id == "detail":
            return { "flavors": self.flavors }
        else:
            for flavor in self.flavors:
                if str(flavor['id']) == id:
                    return { "flavor": flavor }
            raise fault.itemNotFound


class ImageHandler(BaseHandler):
    allowed_methods = ('GET', 'POST')

    def read(self, request, id=None):
        """
        List images or retrieve one

        Returns: OK
        Faults: cloudServersFault, serviceUnavailable, unauthorized,
                badRequest, itemNotFound
        """
        images = Image.objects.all()
        images_list = [ {'created': image.created.isoformat(), 
                    'id': image.id,
                    'name': image.name,
                    'updated': image.updated.isoformat(),    
                    'description': image.description, 
                    'state': image.state, 
                    'vm_id': image.vm_id
                   } for image in images]
        if rapi: # Images info is stored in the DB. Ganeti is not aware of this
            if id == "detail":
                return { "images": images_list }
            elif id is None:
                return { "images": [ { "id": s['id'], "name": s['name'] } for s in images_list ] }
            else:
                try:
                    image = images.get(id=id)
                    return { "image":  {'created': image.created.isoformat(), 
                    'id': image.id,
                    'name': image.name,
                    'updated': image.updated.isoformat(),    
                    'description': image.description, 
                    'state': image.state, 
                    'vm_id': image.vm_id
                   } }
                except: 
                    raise fault.itemNotFound
        else:
            raise fault.serviceUnavailable

    def create(self, request):
        """Create a new image"""
        return accepted


class SharedIPGroupHandler(BaseHandler):
    allowed_methods = ('GET', 'POST', 'DELETE')

    def read(self, request, id=None):
        """List Shared IP Groups"""
        if id is None:
            return {}
        elif id == "detail":
            return {}
        else:
            raise fault.itemNotFound

    def create(self, request, id):
        """Creates a new Shared IP Group"""
        return created

    def delete(self, request, id):
        """Deletes a Shared IP Group"""
        return noContent


class VirtualMachineGroupHandler(BaseHandler):
    allowed_methods = ('GET', 'POST', 'DELETE')

    def read(self, request, id=None):
        """List Groups"""
        vmgroups = VirtualMachineGroup.objects.all() 
        vmgroups = [ {'id': vmgroup.id, \
              'name': vmgroup.name,  \
               'server_id': [machine.id for machine in vmgroup.machines.all()] \
               } for vmgroup in vmgroups]
        if rapi: # Group info is stored in the DB. Ganeti is not aware of this
            if id == "detail":
                return { "groups": vmgroups }
            elif id is None:
                return { "groups": [ { "id": s['id'], "name": s['name'] } for s in vmgroups ] }
            else:
                return { "groups": vmgroups[0] }


    def create(self, request, id):
        """Creates a Group"""
        return created

    def delete(self, request, id):
        """Deletes a  Group"""
        return noContent



class LimitHandler(BaseHandler):
    allowed_methods = ('GET',)

    # XXX: hookup with @throttle

    rate = [
        {
           "verb" : "POST",
           "URI" : "*",
           "regex" : ".*",
           "value" : 10,
           "remaining" : 2,
           "unit" : "MINUTE",
           "resetTime" : 1244425439
        },
        {
           "verb" : "POST",
           "URI" : "*/servers",
           "regex" : "^/servers",
           "value" : 25,
           "remaining" : 24,
           "unit" : "DAY",
           "resetTime" : 1244511839
        },
        {
           "verb" : "PUT",
           "URI" : "*",
           "regex" : ".*",
           "value" : 10,
           "remaining" : 2,
           "unit" : "MINUTE",
           "resetTime" : 1244425439
        },
        {
           "verb" : "GET",
           "URI" : "*",
           "regex" : ".*",
           "value" : 3,
           "remaining" : 3,
           "unit" : "MINUTE",
           "resetTime" : 1244425439
        },
        {
           "verb" : "DELETE",
           "URI" : "*",
           "regex" : ".*",
           "value" : 100,
           "remaining" : 100,
           "unit" : "MINUTE",
           "resetTime" : 1244425439
        }
    ]

    absolute = {
        "maxTotalRAMSize" : 51200,
        "maxIPGroups" : 50,
        "maxIPGroupMembers" : 25
    }

    def read(self, request):
        return { "limits": {
                "rate": self.rate,
                "absolute": self.absolute,
               }
            }
