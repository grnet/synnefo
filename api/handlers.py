# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8
#
# Copyright © 2010 Greek Research and Technology Network

import json
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
    {
        "status": "CURRENT",
        "id": "v1.0grnet1",
        "docURL" : "None yet",
        "wad1" : "None yet"
    }
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
        sleep(0.5)
        #TODO: delete the sleep once the mock objects are removed
        if id is None:
            return self.read_all(request)
        elif id == "detail":
            return self.read_all(request, detail=True)
        else:
            return self.read_one(request, id)

    def read_one(self, request, id):
        try:
            instance = VirtualMachine.objects.get(id=id)
            return { "server": instance } #FIXME
        except:
            raise fault.itemNotFound

    @paginator
    def read_all(self, request, detail=False):
        virtual_servers = VirtualMachine.objects.all()
        virtual_servers = [virtual_server for virtual_server in  virtual_servers if virtual_server.rsapi_state !="DELETED"]
        #get all VM's for now, FIX it to take the user's VMs only yet. also don't get deleted VM's

        if not detail:
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
        #TODO: add random pass, metadata       
        try:
            options_request = json.loads(request.POST.get('create', None)) #here we have the options for cpu, ram etc
            cpu = options_request.get('cpu','')
            ram = options_request.get('ram','')
            name = options_request.get('name','')
            storage = options_request.get('storage','')
            pnode = rapi.GetNodes()[0]
            rapi.CreateInstance('create', name, 'plain', [{"size": storage}], [{}], os='debootstrap+default', ip_check=False, name_check=False,pnode=pnode, beparams={'auto_balance': True, 'vcpus': cpu, 'memory': ram})
            return accepted
        except: # something bad happened. FIXME: return code
            return noContent

        #TODO: replace with real data from request.POST
        #TODO: create the VM in the database

    def update(self, request, id):
        return noContent

    def delete(self, request, id):
        try:
            instance = VirtualMachine.objects.get(id=id)
            print 'deleting machine %s' % instance.name
            instance._operstate = 'DESTROYED'
            return accepted
            #rapi.DeleteInstance(instance.name)
        except:
            raise fault.itemNotFound


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
            return noContent
        #FIXME: for now make a list with only one machine. This will be a list of machines (for the list view)
        reboot_request = request.POST.get('reboot', None)
        shutdown_request = request.POST.get('shutdown', None)
        start_request = request.POST.get('start', None)
        if reboot_request:
            return self.action_start([machine], 'reboot')          
        elif shutdown_request:
            return self.action_start([machine], 'shutdown')          
        elif start_request:
            return self.action_start([machine], 'start')          
        return noContent #FIXME: when does this happen?


    def delete(self, request, id):
        """Delete an Instance"""
        return accepted

    def update(self, request, id):
        return noContent

    def action_start(self, list_of_machines, action):
        if action == 'reboot':
            try:
                for machine in list_of_machines:
                    rapi.RebootInstance(machine)
                return accepted
            except: # something bad happened.
#FIXME: return code. Rackspace error response code(s): cloudServersFault (400, 500), serviceUnavailable (503), unauthorized(401), badRequest (400), badMediaType(415), itemNotFound (404), buildInProgress (409), overLimit (413)
                return noContent
        if action == 'shutdown':        
            try:
                for machine in list_of_machines:
                    rapi.ShutdownInstance(machine)
                return accepted
            except: # something bad happened. FIXME: return code
                return noContent
        if action == 'start':    
            try:
                for machine in list_of_machines:
                    rapi.StartupInstance(machine)
                return accepted
            except: # something bad happened. FIXME: return code
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


class DiskHandler(BaseHandler):
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    def read(self, request, id=None):
        """List Disks"""
        if id is None:
            return self.read_all(request)
        elif id == "detail":
            return self.read_all(request, detail=True)
        else:
            return self.read_one(request, id)

    def read_one(self, request, id):
        """List one Disk with the specified id with all details"""
        # FIXME Get detailed info from the DB 
        # for the Disk with the specified id
        try:
            disk = Disk.objects.get(pk=id)
            disk_details = {
                "id" : disk.id, 
                "name" : disk.name, 
                "size" : disk.size,
                "created" : disk.created, 
                "serverId" : disk.vm.id
            }
            return { "disks" : disk_details }
        except:
            raise fault.itemNotFound

    @paginator
    def read_all(self, request, detail=False):
        """List all Disks. If -detail- is set list them with all details"""
        if not detail:
            disks = Disk.objects.filter(owner=SynnefoUser.objects.all()[0])
            return { "disks": [ { "id": disk.id, "name": disk.name } for disk in disks ] }
        else:
            disks = Disk.objects.filter(owner=SynnefoUser.objects.all()[0])
            disks_details = [ {
                "id" : disk.id, 
                "name" : disk.name,
                "size" : disk.size,
                "created" : disk.created, 
                "serverId" : disk.vm.id,
            } for disk in disks ]
            return { "disks":  disks_details }                

    def create(self, request):
        """Create a new Disk"""
        # FIXME Create a partial DB entry, 
        # then call the backend for actual creation
        pass

    def update(self, request, id):
        """Rename the Disk with the specified id"""
        # FIXME Change the Disk's name in the DB
        pass

    def delete(self, request, id):
        """Destroy the Disk with the specified id"""
        # Call the backend for actual destruction
        pass
