# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8
#
# Copyright © 2010 Greek Research and Technology Network

import simplejson as json
from django.conf import settings
from django.http import HttpResponse
from piston.handler import BaseHandler, AnonymousBaseHandler
from synnefo.api.faults import fault, noContent, accepted, created
from synnefo.api.helpers import instance_to_server, paginator
from synnefo.util.rapi import GanetiRapiClient, GanetiApiError, CertificateError
from synnefo.db.models import *
from time import sleep
import logging

log = logging.getLogger('synnefo.api.handlers')

try:
    rapi = GanetiRapiClient(*settings.GANETI_CLUSTER_INFO)
    rapi.GetVersion()
except Exception, e:
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

#read is called on GET requests
#create is called on POST, and creates new objects
#update is called on PUT, and should update an existing product
#delete is called on DELETE, and should delete an existing object


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
    """Handler responsible for the Servers

     handles the listing of Virtual Machines, Creates and Destroys VM's

     @HTTP methods: POST, DELETE, PUT, GET
     @Parameters: POST data with the create data (cpu, ram, etc)
     @Responses: HTTP 202 if successfully call rapi, itemNotFound, serviceUnavailable otherwise

    """
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
            server = VirtualMachine.objects.get(id=id)
        except VirtualMachine.DoesNotExist:
            raise fault.itemNotFound
        except VirtualMachine.MultipleObjectsReturned:
            raise fault.serviceUnavailable
        except Exception, e:
            raise fault.serviceUnavailable

        server = {'status': server.rsapi_state, 
                                     'flavorId': server.flavor.id, 
                                     'name': server.name, 
                                     'id': server.id, 
                                     'imageId': server.sourceimage.id, 
                                     'hostId': server.hostid, 
                                     #'metadata': {'Server_Label': server.description },
                                     'metadata':[{'meta': { 'key': {metadata.meta_key: metadata.meta_value}}} for metadata in server.virtualmachinemetadata_set.all()],                                    
                                     'addresses': {'public': { 'ip': {'addr': server.ipfour}, 'ip6': {'addr': server.ipsix}},'private': ''},      
                }
        return { "server": server } 


    @paginator
    def read_all(self, request, detail=False):
        virtual_servers = VirtualMachine.objects.filter(deleted=False) 
        #get all VM's for now, FIX it to take the user's VMs only yet. also don't get deleted VM's

        if not detail:
            return { "servers": [ { "id": s.id, "name": s.name } for s in virtual_servers ] }
        else:
            virtual_servers_list = [{'status': server.rsapi_state, 
                                     'flavorId': server.flavor.id, 
                                     'name': server.name, 
                                     'id': server.id, 
                                     'imageId': server.sourceimage.id, 
                                     'hostId': server.hostid, 
                                     #'metadata': {'Server_Label': server.description },
                                     'metadata':[{'meta': { 'key': {metadata.meta_key: metadata.meta_value}}} for metadata in server.virtualmachinemetadata_set.all()],                                    
                                     'addresses': {'public': { 'ip': {'addr': server.ipfour}, 'ip6': {'addr': server.ipsix}},'private': ''},      

                                    } for server in virtual_servers]
            #pass some fake data regarding ip, since we don't have any such data            
            return { "servers":  virtual_servers_list }                


    def create(self, request):
        """ Parse RackSpace API create request to generate rapi create request
        
            TODO: auto generate and set password
        """
        #Check if we have all the necessary data in the JSON request       
        try:
            server = json.loads(request.raw_post_data)['server']
            descr = server['name']
            flavorId = server['flavorId']
            flavor = Flavor.objects.get(id=flavorId)
            imageId = server['imageId']
            metadata = server['metadata']
            personality = server.get('personality', None)
        except Exception as e:
            log.error('Malformed create request: %s - %s' % (e, request.raw_post_data))    
            raise fault.badRequest

        # add the new VM to the local db
        try:
            vm = VirtualMachine.objects.create(sourceimage=Image.objects.get(id=imageId),ipfour='0.0.0.0',flavor_id=flavorId)
        except Exception as e:
            log.error("Can't save vm: %s" % e)
            raise fault.serviceUnavailable

        try:
            vm.name = 'snf-%s' % vm.id
            vm.description = descr
            vm.save()            
            jobId = rapi.CreateInstance(
                'create',
                request.META['SERVER_NAME'] == 'testserver' and 'test-server' or 'snf-%s' % vm.id,
                'plain',
                [{"size": flavor.disk}],
                [{}],
                # TODO: select OS from imageId
                os='debootstrap+default',
                ip_check=False,
                name_check=False,
                #TODO: verify if this is necessary
                pnode = rapi.GetNodes()[0],
                # Dry run when called by unit tests
                dry_run = request.META['SERVER_NAME'] == 'testserver',
                beparams={
                            'auto_balance': True,
                            'vcpus': flavor.cpu,
                            'memory': flavor.ram,
                        },
                )
        except (GanetiApiError, CertificateError) as e:
            log.error('CreateInstance failed: %s' % e)
            vm.deleted = True
            vm.save()
            raise fault.serviceUnavailable
        except Exception as e:
            log.error('Unexpected error: %s' % e)
            vm.deleted = True
            vm.save()
            raise fault.notImplemented            
        

        # take a power nap but don't forget to poll the ganeti job right after
        sleep(1)
        job = rapi.GetJobStatus(jobId)
        
        if job['status'] == 'error':
            log.error('Create Job failed: %s' % job['opresult'])
            raise fault.badRequest
        elif job['status'] in ['running', 'success', 'queued', 'waiting']:
            log.info('creating instance %s' % job['ops'][0]['instance_name'])     
            #import pdb;pdb.set_trace()
            # Build the response
            status = job['status'] == 'running' and 'BUILD' or 'ACTIVE';
            ret = {'server': {
                    'id' : vm.id,
                    'name' : vm.name,
                    "imageId" : imageId,
                    "flavorId" : flavorId,
                    "hostId" : vm.hostid,
                    "progress" : 0,
                    "status" : status,
                    "adminPass" : "GFf1j9aP",
                    "metadata" : {"My Server Name" : vm.description},
                    "addresses" : {
                        "public" : [  ],
                        "private" : [  ],
                        },
                    },
            }
            return HttpResponse(json.dumps(ret), mimetype="application/json", status=202)
        else:
            # TODO: handle all possible job statuses
            log.error('Unhandled job status: %s' % job['status'])
            return fault.notImplemented

    def update(self, request, id):
        return noContent

    def delete(self, request, id):
        try:
            vm = VirtualMachine.objects.get(id=id)
        except VirtualMachine.DoesNotExist:
            raise fault.itemNotFound
        except VirtualMachine.MultipleObjectsReturned:
            raise fault.serviceUnavailable
        except Exception, e:
            raise fault.serviceUnavailable

        #TODO: set the status to DESTROYED
        try:
            vm.start_action('DESTROY')
        except Exception, e:
            raise fault.serviceUnavailable

        try:
            rapi.DeleteInstance(vm.backend_id)
        except GanetiApiError, CertificateError:
            raise fault.serviceUnavailable
        except Exception, e:
            raise fault.serviceUnavailable

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
    """Handler responsible for Server Actions

     handles Reboot, Shutdown and Start actions. 

     @HTTP methods: POST, DELETE, PUT
     @Parameters: POST data with the action (reboot, shutdown, start)
     @Responses: HTTP 202 if successfully call rapi, itemNotFound, serviceUnavailable otherwise

    """

    allowed_methods = ('POST', 'DELETE',  'PUT')

    def create(self, request, id):
        """Reboot, Shutdown, Start virtual machine"""
        
        requested_action = json.loads(request.raw_post_data)
        reboot_request = requested_action.get('reboot', None)
        shutdown_request = requested_action.get('shutdown', None)
        start_request = requested_action.get('start', None)
        #action not implemented
        action = reboot_request and 'REBOOT' or shutdown_request and 'SUSPEND' or start_request and 'START'
        if not action:
            raise fault.notImplemented 
        #test if we can get the vm
        try:
            vm = VirtualMachine.objects.get(id=id)
        except VirtualMachine.DoesNotExist:
            raise fault.itemNotFound
        except VirtualMachine.MultipleObjectsReturned:
            raise fault.serviceUnavailable
        except Exception, e:
            raise fault.serviceUnavailable

        try:
            vm.start_action(action)
        except Exception, e:
            raise fault.serviceUnavailable

        try:
            if reboot_request:
                rapi.RebootInstance(vm.backend_id)
            elif shutdown_request:
                rapi.ShutdownInstance(vm.backend_id)
            elif start_request:
                rapi.StartupInstance(vm.backend_id)
            return accepted
        except GanetiApiError, CertificateError:
            raise fault.serviceUnavailable
        except Exception, e:
            raise fault.serviceUnavailable

    def delete(self, request, id):
        """Delete an Instance"""
        return accepted

    def update(self, request, id):
        return noContent




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
             'disk': flavor.disk, 'cpu': flavor.cpu} for flavor in flavors]

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
    """Handler responsible for Images

     handles the listing, creation and delete of Images. 

     @HTTP methods: GET, POST
     @Parameters: POST data 
     @Responses: HTTP 202 if successfully create Image or get the Images list, itemNotFound, serviceUnavailable otherwise

    """


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
                    'status': image.state, 
                    'size': image.size, 
                    'serverId': image.sourcevm and image.sourcevm.id or ""
                   } for image in images]
        if rapi: # Images info is stored in the DB. Ganeti is not aware of this
            if id == "detail":
                return { "images": images_list }
            elif id is None:
                return { "images": [ { "id": s['id'], "name": s['name'] } for s in images_list ] }
            else:
                try:
                    image = images.get(id=id)
                except Image.DoesNotExist:
                    raise fault.itemNotFound
                except Image.MultipleObjectsReturned:
                    raise fault.serviceUnavailable
                except Exception, e:
                    raise fault.serviceUnavailable

                return { "image":  {'created': image.created.isoformat(), 
                    'id': image.id,
                    'name': image.name,
                    'updated': image.updated.isoformat(),    
                    'description': image.description, 
                    'status': image.state, 
                    'size': image.size, 
                    'serverId': image.sourcevm and image.sourcevm.id or ""
                   } }

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
