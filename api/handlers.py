# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8
#
# Copyright © 2010 Greek Research and Technology Network

import simplejson as json
from django.conf import settings
from django.http import HttpResponse
from piston.handler import BaseHandler, AnonymousBaseHandler
from synnefo.api.faults import fault, noContent, accepted, created, notModified
from synnefo.api.helpers import instance_to_server, paginator
from synnefo.util.rapi import GanetiRapiClient, GanetiApiError, CertificateError
from synnefo.db.models import *
from time import sleep
import random
import string
import logging
from datetime import datetime, timedelta

log = logging.getLogger('synnefo.api.handlers')

try:
    rapi = GanetiRapiClient(*settings.GANETI_CLUSTER_INFO)
    rapi.GetVersion()
except Exception, e:
    log.exception('Unexpected error: %s' % e)
    raise fault.serviceUnavailable
#If we can't connect to the rapi successfully, don't do anything

VERSIONS = [
    {
        "status": "CURRENT",
        "id": "v1.0",
        "docURL" : "http://docs.rackspacecloud.com/servers/api/v1.0/cs-devguide-20110112.pdf",
        "wadl" : "http://docs.rackspacecloud.com/servers/api/v1.0/application.wadl"
    },
    {
        "status": "CURRENT",
        "id": "v1.1",
        "docURL" : "http://docs.openstack.org/openstack-compute/developer/content/",
        "wadl" : "None yet"
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
        try:
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
        except Exception, e:
            log.exception('Unexpected error: %s' % e)
            raise fault.serviceUnavailable


class ServerHandler(BaseHandler):
    """Handler responsible for the Servers

     handles the listing of Virtual Machines, Creates and Destroys VM's

     @HTTP methods: POST, DELETE, PUT, GET
     @Parameters: POST data with the create data (cpu, ram, etc)
     @Responses: HTTP 200 if successfully call rapi, 304 if not modified, itemNotFound or serviceUnavailable otherwise

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

            server = {'status': server.rsapi_state, 
                     'flavorRef': server.flavor.id, 
                     'name': server.name, 
                     'id': server.id, 
                     'imageRef': server.sourceimage.id,
                     'created': server.created, 
                     'updated': server.updated,
                     'hostId': server.hostid, 
                     'progress': server.rsapi_state == 'ACTIVE' and 100 or 0, 
                     #'metadata': {'Server_Label': server.description },
                     'metadata':[{'meta': { 'key': {metadata.meta_key: metadata.meta_value}}} for metadata in server.virtualmachinemetadata_set.all()],                                    
                     'addresses': {'public': { 'ip': {'addr': server.ipfour}, 'ip6': {'addr': server.ipsix}},'private': ''},      
                    }
            return { "server": server } 
        except VirtualMachine.DoesNotExist:
            raise fault.itemNotFound
        except VirtualMachine.MultipleObjectsReturned:
            raise fault.serviceUnavailable
        except Exception, e:
            log.exception('Unexpected error: %s' % e)
            raise fault.serviceUnavailable


    @paginator
    def read_all(self, request, detail=False):
        #changes_since should be on ISO 8601 format
        try:
            changes_since = request.GET.get("changes-since", 0)
            if changes_since:
                last_update = datetime.strptime(changes_since, "%Y-%m-%dT%H:%M:%S" )
                #return a badRequest if the changes_since is older than a limit
                if datetime.now() - last_update > timedelta(seconds=settings.POLL_LIMIT):
                    raise fault.badRequest        
                virtual_servers = VirtualMachine.objects.filter(updated__gt=last_update)
                if not len(virtual_servers):
                    return notModified
            else:
                virtual_servers = VirtualMachine.objects.filter(deleted=False)
            #get all VM's for now, FIX it to take the user's VMs only yet. also don't get deleted VM's
        except Exception, e:
            raise fault.badRequest        
        try:
            if not detail:
                return { "servers": [ { "id": s.id, "name": s.name } for s in virtual_servers ] }
            else:
                virtual_servers_list = [{'status': server.rsapi_state, 
                                         'flavorRef': server.flavor.id, 
                                         'name': server.name, 
                                         'id': server.id, 
                                         'created': server.created, 
                                         'updated': server.updated,
                                         'imageRef': server.sourceimage.id, 
                                         'hostId': server.hostid, 
                                         'progress': server.rsapi_state == 'ACTIVE' and 100 or 0, 
                                         #'metadata': {'Server_Label': server.description },
                                         'metadata':[{'meta': { 'key': {metadata.meta_key: metadata.meta_value}}} for metadata in server.virtualmachinemetadata_set.all()],                                    
                                         'addresses': {'public': { 'ip': {'addr': server.ipfour}, 'ip6': {'addr': server.ipsix}},'private': ''},      

                                        } for server in virtual_servers]
                #pass some fake data regarding ip, since we don't have any such data            
                return { "servers":  virtual_servers_list }                
        except Exception, e:
            log.exception('Unexpected error: %s' % e)
            raise fault.serviceUnavailable


    def create(self, request):
        """ Parse RackSpace API create request to generate rapi create request
        
            TODO: auto generate and set password
        """
        # Check if we have all the necessary data in the JSON request       
        try:
            server = json.loads(request.raw_post_data)['server']
            name = server['name']
            flavorRef = server['flavorRef']
            flavor = Flavor.objects.get(id=flavorRef)
            imageRef = server['imageRef']
            image = Image.objects.get(id=imageRef)
            metadata = server['metadata']
            personality = server.get('personality', None)
        except (Flavor.DoesNotExist, Image.DoesNotExist):
            raise fault.itemNotFound
        except (Flavor.MultipleObjectsReturned, Image.MultipleObjectsReturned):
            raise fault.serviceUnavailable
        except Exception as e:
            log.exception('Malformed create request: %s - %s' % (e, request.raw_post_data))    
            raise fault.badRequest

        # TODO: Proper Authn, Authz
        # Everything belongs to a single SynnefoUser for now.
        try:  	
            owner = SynnefoUser.objects.all()[0]
        except Exception as e:
            log.exception('Cannot find a single SynnefoUser in the DB: %s' % (e));
            raise fault.unauthorized

        # add the new VM to the local db
        try:
            vm = VirtualMachine.objects.create(sourceimage=image, ipfour='0.0.0.0', ipsix='::1', flavor=flavor, owner=owner)
        except Exception as e:
            log.exception("Can't save vm: %s" % e)
            raise fault.serviceUnavailable

        try:
            vm.name = name
            #vm.description = descr
            vm.save()            
            jobId = rapi.CreateInstance(
                'create',
                request.META['SERVER_NAME'] == 'testserver' and 'test-server' or vm.backend_id,
                'plain',
                # disk field of Flavor object is in GB, value specified here is in MB
                # FIXME: Always ask for a 2GB disk, current LVM physical groups are too small:
                # [{"size": flavor.disk * 1000}],
                [{"size": 2000}],
                [{}],
                #TODO: select OS from imageRef
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
            log.info('created vm with %s cpus, %s ram and %s storage' % (flavor.cpu, flavor.ram, flavor.disk))
        except (GanetiApiError, CertificateError) as e:
            log.exception('CreateInstance failed: %s' % e)
            vm.deleted = True
            vm.save()
            raise fault.serviceUnavailable
        except Exception as e:
            log.exception('Unexpected error: %s' % e)
            vm.deleted = True
            vm.save()
            raise fault.serviceUnavailable            
        

        ret = {'server': {
                'id' : vm.id,
                'name' : vm.name,
                "imageRef" : imageRef,
                "flavorRef" : flavorRef,
                "hostId" : vm.hostid,
                "progress" : 0,
                "status" : 'BUILD',
                "adminPass" : self.random_password(),
                "metadata" : {"My Server Name" : vm.name},
                "addresses" : {
                    "public" : [  ],
                    "private" : [  ],
                    },
                },
        }
        return HttpResponse(json.dumps(ret), mimetype="application/json", status=202)


    def random_password(self):
        "return random password"
        number_of_chars = 8
        possible_chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
        return ''.join(random.choice(possible_chars) for x in range(number_of_chars))


    def update(self, request, id):
        """Sets and updates Virtual Machine Metadata. 
 
        """
        try:
            metadata_request = json.loads(request.raw_post_data)['metadata']
            metadata_key = metadata_request.get('metadata_key')
            metadata_value = metadata_request.get('metadata_value')
 
            vm = VirtualMachine.objects.get(id=id)
            #we only update virtual machine's name atm
            if metadata_key == 'name':
                vm.name = metadata_value
                vm.save()
                return accepted
        except VirtualMachine.DoesNotExist:
            raise fault.itemNotFound
        except VirtualMachine.MultipleObjectsReturned:
            raise fault.serviceUnavailable
        except Exception, e:
            log.exception('Unexpected error: %s' % e)
            raise fault.serviceUnavailable

        raise fault.itemNotFound


    def delete(self, request, id):
        try:
            vm = VirtualMachine.objects.get(id=id)
            #TODO: set the status to DESTROYED
            vm.start_action('DESTROY')
            rapi.DeleteInstance(vm.backend_id)
            return accepted        
        except VirtualMachine.DoesNotExist:
            raise fault.itemNotFound
        except VirtualMachine.MultipleObjectsReturned:
            raise fault.serviceUnavailable
        except GanetiApiError, CertificateError:
            raise fault.serviceUnavailable
        except Exception, e:
            log.exception('Unexpected error: %s' % e)
            raise fault.serviceUnavailable



class ServerAddressHandler(BaseHandler):
    """Handler responsible for Server Addresses

     handles Reboot, Shutdown and Start actions. 

     @HTTP methods: GET
     @Parameters: Id of server and networkID (eg public, private)
     @Responses: HTTP 200 if successfully call rapi, itemNotFound, serviceUnavailable otherwise

    """
    allowed_methods = ('GET',)

    def read(self, request, id, networkID=None):
        """List IP addresses for a server"""

        try:
            server = VirtualMachine.objects.get(id=id)
            address =  {'public': { 'ip': {'addr': server.ipfour}, 'ip6': {'addr': server.ipsix}},'private': ''}                                          
        except VirtualMachine.DoesNotExist:
            raise fault.itemNotFound
        except VirtualMachine.MultipleObjectsReturned:
            raise fault.serviceUnavailable
        except Exception, e:
            log.exception('Unexpected error: %s' % e)
            raise fault.serviceUnavailable

        if networkID == "public":
            address = {'public': { 'ip': {'addr': server.ipfour}, 'ip6': {'addr': server.ipsix}}}                            
        elif networkID == "private":
            address = {'private': ''}    
        elif networkID != None:
            raise fault.badRequest
        return { "addresses": address } 



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
        
        try:
            requested_action = json.loads(request.raw_post_data)
            reboot_request = requested_action.get('reboot', None)
            shutdown_request = requested_action.get('shutdown', None)
            start_request = requested_action.get('start', None)
            #action not implemented
            action = reboot_request and 'REBOOT' or shutdown_request and 'STOP' or start_request and 'START'

            if not action:
                raise fault.notImplemented 
            #test if we can get the vm
            vm = VirtualMachine.objects.get(id=id)
            vm.start_action(action)

            if reboot_request:
                rapi.RebootInstance(vm.backend_id)
            elif shutdown_request:
                rapi.ShutdownInstance(vm.backend_id)
            elif start_request:
                rapi.StartupInstance(vm.backend_id)
            return accepted
        except VirtualMachine.DoesNotExist:
            raise fault.itemNotFound
        except VirtualMachine.MultipleObjectsReturned:
            raise fault.serviceUnavailable
        except GanetiApiError, CertificateError:
            raise fault.serviceUnavailable
        except Exception, e:
            log.exception('Unexpected error: %s' % e)
            raise fault.serviceUnavailable

    def delete(self, request, id):
        """Delete an Instance"""
        return accepted

    def update(self, request, id):
        raise fault.itemNotFound


class ServerBackupHandler(BaseHandler):
    """ Backup Schedules are not implemented yet, return notImplemented """
    allowed_methods = ('GET', 'POST', 'DELETE')

    def read(self, request, id):
        raise fault.notImplemented

    def create(self, request, id):
        raise fault.notImplemented

    def delete(self, request, id):
        raise fault.notImplemented


class ServerMetadataHandler(BaseHandler):
    """Handles Metadata of a specific Server

    the handler Lists, Creates, Updates and Deletes Metadata values

    @HTTP methods: POST, DELETE, PUT, GET
    @Parameters: POST data with key value pairs

    """
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    def read(self, request, id, key=None):
        """List metadata of the specific server"""
        if key is None:
            return self.read_allkeys(request, id)
        else:
            return self.read_onekey(request, id, key)

    def read_allkeys(self, request, id):
        """Returns all the key value pairs of the specified server"""
        try:
            server = VirtualMachine.objects.get(pk=id)
            return {
                "metadata": {
                    "values": [
                        {m.meta_key: m.meta_value} for m in server.virtualmachinemetadata_set.all()
                    ]
                }
            }
        except VirtualMachine.DoesNotExist:
            raise fault.itemNotFound
        except VirtualMachine.MultipleObjectsReturned:
            raise fault.serviceUnavailable
        except Exception, e:
            log.exception('Unexpected error: %s' % e)
            raise fault.serviceUnavailable
        
    def read_onekey(self, request, id, key):
        """Returns the specified metadata key of the specified server"""
        try:
            server = VirtualMachine.objects.get(pk=id)
            return {
                "metadata": {
                    "values": [
                        {m.meta_key: m.meta_value} for m in server.virtualmachinemetadata_set.filter(meta_key=key)
                    ]
                }
            }
        except VirtualMachineMetadata.DoesNotExist:
            raise fault.itemNotFound            
        except VirtualMachine.DoesNotExist:
            raise fault.itemNotFound
        except VirtualMachine.MultipleObjectsReturned:
            raise fault.serviceUnavailable
        except Exception, e:
            log.exception('Unexpected error: %s' % e)
            raise fault.serviceUnavailable

    def create(self, request, id, key=None):
        """Create or Update all metadata for the specified VM"""
        if key is not None:
            log.exception('The POST request should not pass a key in the URL')
            raise fault.badRequest
        try:
            metadata = json.loads(request.raw_post_data)['metadata']
        except Exception as e:
            log.exception('Malformed create request: %s - %s' % (e, request.raw_post_data))
            raise fault.badRequest

        try:
            vm = VirtualMachine.objects.get(pk=id)
            for x in metadata.keys():
                vm_meta, created = vm.virtualmachinemetadata_set.get_or_create(meta_key=x)
                vm_meta.meta_value = metadata[x] 
                vm_meta.save()
            return {
                "metadata": [{
                    "meta": { 
                        "key": {m.meta_key: m.meta_value}}} for m in vm.virtualmachinemetadata_set.all()]
            }        
        except VirtualMachine.DoesNotExist:
            raise fault.itemNotFound
        except VirtualMachine.MultipleObjectsReturned:
            raise fault.serviceUnavailable
        except VirtualMachineMetadata.DoesNotExist:
            raise fault.itemNotFound
        except VirtualMachineMetadata.MultipleObjectsReturned:
            raise fault.serviceUnavailable
        except Exception, e:
            log.exception('Unexpected error: %s' % e)
            raise fault.serviceUnavailable

    def update(self, request, id, key=None):
        """Update or Create the specified metadata key for the specified VM"""
        if key is None:
            log.exception('No metadata key specified in URL')
            raise fault.badRequest
        try:
            metadata = json.loads(request.raw_post_data)['meta']
            metadata_value = metadata[key]
        except Exception as e:
            log.exception('Malformed create request: %s - %s' % (e, request.raw_post_data))
            raise fault.badRequest

        try:
            server = VirtualMachine.objects.get(pk=id)
            vm_meta, created = server.virtualmachinemetadata_set.get_or_create(meta_key=key)
            vm_meta.meta_value = metadata_value 
            vm_meta.save()
            return {"meta": {vm_meta.meta_key: vm_meta.meta_value}}
        
        except VirtualMachine.DoesNotExist:
            raise fault.itemNotFound
        except VirtualMachine.MultipleObjectsReturned:
            raise fault.serviceUnavailable
        except VirtualMachineMetadata.DoesNotExist:
            raise fault.itemNotFound
        except VirtualMachineMetadata.MultipleObjectsReturned:
            raise fault.serviceUnavailable
        except Exception, e:
            log.exception('Unexpected error: %s' % e)
            raise fault.serviceUnavailable

    def delete(self, request, id, key=None):
        """Delete the specified metadata key"""
        if key is None:
            log.exception('No metadata key specified in URL')
            raise fault.badRequest
        try:
            server = VirtualMachine.objects.get(pk=id)
            server.virtualmachinemetadata_set.get(meta_key=key).delete()
        except VirtualMachineMetadata.DoesNotExist:
            raise fault.itemNotFound
        except VirtualMachine.DoesNotExist:
            raise fault.itemNotFound
        except VirtualMachineMetadata.MultipleObjectsReturned:
            raise fault.serviceUnavailable
        except VirtualMachine.MultipleObjectsReturned:
            raise fault.serviceUnavailable
        except Exception, e:
            log.exception('Unexpected error: %s' % e)
            raise fault.serviceUnavailable


class FlavorHandler(BaseHandler):
    """Handler responsible for Flavors

    """
    allowed_methods = ('GET',)

    def read(self, request, id=None):
        """
        List flavors or retrieve one

        Returns: OK
        Faults: cloudServersFault, serviceUnavailable, unauthorized,
                badRequest, itemNotFound
        """
        try:
            flavors = Flavor.objects.all()
            flavors = [ {'id': flavor.id, 'name': flavor.name, 'ram': flavor.ram, \
                     'disk': flavor.disk, 'cpu': flavor.cpu} for flavor in flavors]

            if id is None:
                simple = map(lambda v: {
                            "id": v['id'],
                            "name": v['name'],
                        }, flavors)
                return { "flavors": simple }
            elif id == "detail":
                return { "flavors": flavors }
            else:
                flavor = Flavor.objects.get(id=id)
                return { "flavor":  {
                    'id': flavor.id,
                    'name': flavor.name,
                    'ram': flavor.ram,
                    'disk': flavor.disk,  
                    'cpu': flavor.cpu,  
                   } }

        except Flavor.DoesNotExist:
            raise fault.itemNotFound
        except Flavor.MultipleObjectsReturned:
            raise fault.serviceUnavailable
        except Exception, e:
            log.exception('Unexpected error: %s' % e)
            raise fault.serviceUnavailable


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

        #changes_since should be on ISO 8601 format
        try:
            changes_since = request.GET.get("changes-since", 0)
            if changes_since:
                last_update = datetime.strptime(changes_since, "%Y-%m-%dT%H:%M:%S" )
                #return a badRequest if the changes_since is older than a limit
                if datetime.now() - last_update > timedelta(seconds=settings.POLL_LIMIT):
                    raise fault.badRequest        
                images = Image.objects.filter(updated__gt=last_update)
                if not len(images):
                    return notModified
            else:
                images = Image.objects.all()
        except Exception, e:
            raise fault.badRequest        
        try:
            images_list = [ {'created': image.created.isoformat(), 
                        'id': image.id,
                        'name': image.name,
                        'updated': image.updated.isoformat(),    
                        'status': image.state, 
                        'progress': image.state == 'ACTIVE' and 100 or 0, 
                        'size': image.size, 
                        'serverId': image.sourcevm and image.sourcevm.id or "",
                        #'metadata':[{'meta': { 'key': {metadata.meta_key: metadata.meta_value}}} for metadata in image.imagemetadata_set.all()]
                        'metadata':{'meta': { 'key': {'description': image.description}}},
                       } for image in images]
            # Images info is stored in the DB. Ganeti is not aware of this
            if id == "detail":
                return { "images": images_list }
            elif id is None:
                return { "images": [ { "id": s['id'], "name": s['name'] } for s in images_list ] }
            else:        
                image = images.get(id=id)
                return { "image":  {'created': image.created.isoformat(), 
                    'id': image.id,
                    'name': image.name,
                    'updated': image.updated.isoformat(),    
                    'description': image.description, 
                    'status': image.state, 
                    'progress': image.state == 'ACTIVE' and 100 or 0, 
                    'size': image.size, 
                    'serverId': image.sourcevm and image.sourcevm.id or "",
                    #'metadata':[{'meta': { 'key': {metadata.meta_key: metadata.meta_value}}} for metadata in image.imagemetadata_set.all()]
                    'metadata':{'meta': { 'key': {'description': image.description}}},
                   } }
        except Image.DoesNotExist:
                    raise fault.itemNotFound
        except Image.MultipleObjectsReturned:
                    raise fault.serviceUnavailable
        except Exception, e:
                    log.exception('Unexpected error: %s' % e)
                    raise fault.serviceUnavailable

    def create(self, request):
        """Create a new image"""
        return accepted


class ImageMetadataHandler(BaseHandler):
    """Handles Metadata of a specific Image

    the handler Lists, Creates, Updates and Deletes Metadata values

    @HTTP methods: POST, DELETE, PUT, GET
    @Parameters: POST data with key value pairs

    """
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    def read(self, request, id, key=None):
        """List metadata of the specific server"""
        if key is None:
            return self.read_allkeys(request, id)
        else:
            return self.read_onekey(request, id, key)

    def read_allkeys(self, request, id):
        """Returns all the key value pairs of the specified server"""
        try:
            image = Image.objects.get(pk=id)
            return {
                "metadata": [{
                    "meta": { 
                        "key": {m.meta_key: m.meta_value}}} for m in image.imagemetadata_set.all()]
            }
        except Image.DoesNotExist:
            raise fault.itemNotFound
        except Image.MultipleObjectsReturned:
            raise fault.serviceUnavailable
        except Exception, e:
            log.exception('Unexpected error: %s' % e)
            raise fault.serviceUnavailable
        
    def read_onekey(self, request, id, key):
        """Returns the specified metadata key of the specified server"""
        try:
            image = Image.objects.get(pk=id)
            return {
                "metadata": {
                    "values": [
                        {m.meta_key: m.meta_value} for m in image.imagemetadata_set.filter(meta_key=key)
                    ]
                }
            }
        except ImageMetadata.DoesNotExist:
            raise fault.itemNotFound            
        except Image.DoesNotExist:
            raise fault.itemNotFound
        except Image.MultipleObjectsReturned:
            raise fault.serviceUnavailable
        except Exception, e:
            log.exception('Unexpected error: %s' % e)
            raise fault.serviceUnavailable

    def create(self, request, id, key=None):
        """Create or Update all metadata for the specified Image"""
        if key is not None:
            log.exception('The POST request should not pass a key in the URL')
            raise fault.badRequest
        try:
            metadata = json.loads(request.raw_post_data)['metadata']
        except Exception as e:
            log.exception('Malformed create request: %s - %s' % (e, request.raw_post_data))
            raise fault.badRequest

        try:
            image = Image.objects.get(pk=id)
            for x in metadata.keys():
                img_meta, created = image.imagemetadata_set.get_or_create(meta_key=x)
                img_meta.meta_value = metadata[x] 
                img_meta.save()
            return {
                "metadata": [{
                    "meta": { 
                        "key": {m.meta_key: m.meta_value}}} for m in image.imagemetadata_set.all()]
            }        
        except Image.DoesNotExist:
            raise fault.itemNotFound
        except Image.MultipleObjectsReturned:
            raise fault.serviceUnavailable
        except ImageMetadata.DoesNotExist:
            raise fault.itemNotFound
        except ImageMetadata.MultipleObjectsReturned:
            raise fault.serviceUnavailable
        except Exception, e:
            log.exception('Unexpected error: %s' % e)
            raise fault.serviceUnavailable

    def update(self, request, id, key=None):
        """Update or Create the specified metadata key for the specified Image"""
        if key is None:
            log.exception('No metadata key specified in URL')
            raise fault.badRequest
        try:
            metadata = json.loads(request.raw_post_data)['meta']
            metadata_value = metadata[key]
        except Exception as e:
            log.exception('Malformed create request: %s - %s' % (e, request.raw_post_data))
            raise fault.badRequest

        try:
            image = Image.objects.get(pk=id)
            img_meta, created = image.imagemetadata_set.get_or_create(meta_key=key)
            img_meta.meta_value = metadata_value 
            img_meta.save()
            return {"meta": {img_meta.meta_key: img_meta.meta_value}}
        
        except Image.DoesNotExist:
            raise fault.itemNotFound
        except Image.MultipleObjectsReturned:
            raise fault.serviceUnavailable
        except ImageMetadata.DoesNotExist:
            raise fault.itemNotFound
        except ImageMetadata.MultipleObjectsReturned:
            raise fault.serviceUnavailable
        except Exception, e:
            log.exception('Unexpected error: %s' % e)
            raise fault.serviceUnavailable

    def delete(self, request, id, key=None):
        """Delete the specified metadata key"""
        if key is None:
            log.exception('No metadata key specified in URL')
            raise fault.badRequest
        try:
            image = Image.objects.get(pk=id)
            image.imagemetadata_set.get(meta_key=key).delete()
        except ImageMetadata.DoesNotExist:
            raise fault.itemNotFound
        except Image.DoesNotExist:
            raise fault.itemNotFound
        except ImageMetadata.MultipleObjectsReturned:
            raise fault.serviceUnavailable
        except Image.MultipleObjectsReturned:
            raise fault.serviceUnavailable
        except Exception, e:
            log.exception('Unexpected error: %s' % e)
            raise fault.serviceUnavailable


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
        raise fault.itemNotFound


class VirtualMachineGroupHandler(BaseHandler):
    """Handler responsible for Virtual Machine Groups

     creates, lists, deletes virtual machine groups

     @HTTP methods: GET, POST, DELETE
     @Parameters: POST data 
     @Responses: HTTP 202 if successfully get the Groups list, itemNotFound, serviceUnavailable otherwise

    """

    allowed_methods = ('GET', 'POST', 'DELETE')

    def read(self, request, id=None):
        """List Groups"""
        try:
            vmgroups = VirtualMachineGroup.objects.all() 
            vmgroups_list = [ {'id': vmgroup.id, \
                  'name': vmgroup.name,  \
                   'server_id': [machine.id for machine in vmgroup.machines.all()] \
                   } for vmgroup in vmgroups]
            # Group info is stored in the DB. Ganeti is not aware of this
            if id == "detail":
                return { "groups": vmgroups_list }
            elif id is None:
                return { "groups": [ { "id": s['id'], "name": s['name'] } for s in vmgroups_list ] }
            else:
                vmgroup = vmgroups.get(id=id)

                return { "group":  {'id': vmgroup.id, \
                  'name': vmgroup.name,  \
                   'server_id': [machine.id for machine in vmgroup.machines.all()] \
                   } }


        except VirtualMachineGroup.DoesNotExist:
                    raise fault.itemNotFound
        except VirtualMachineGroup.MultipleObjectsReturned:
                    raise fault.serviceUnavailable
        except Exception, e:
                    log.exception('Unexpected error: %s' % e)
                    raise fault.serviceUnavailable



    def create(self, request, id):
        """Creates a Group"""
        return created

    def delete(self, request, id):
        """Deletes a  Group"""
        raise fault.itemNotFound


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
