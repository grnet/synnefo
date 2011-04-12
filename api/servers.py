#
# Copyright (c) 2010 Greek Research and Technology Network
#

from django.conf import settings
from django.conf.urls.defaults import patterns
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson as json

from synnefo.api.actions import server_actions
from synnefo.api.common import method_not_allowed
from synnefo.api.faults import BadRequest, ItemNotFound
from synnefo.api.util import *
from synnefo.db.models import Image, Flavor, VirtualMachine, VirtualMachineMetadata
from synnefo.logic.utils import get_rsapi_state
from synnefo.util.rapi import GanetiRapiClient, GanetiApiError
from synnefo.logic import backend

import logging


rapi = GanetiRapiClient(*settings.GANETI_CLUSTER_INFO)

urlpatterns = patterns('synnefo.api.servers',
    (r'^(?:/|.json|.xml)?$', 'demux'),
    (r'^/detail(?:.json|.xml)?$', 'list_servers', {'detail': True}),
    (r'^/(\d+)(?:.json|.xml)?$', 'server_demux'),
    (r'^/(\d+)/action(?:.json|.xml)?$', 'server_action'),
    (r'^/(\d+)/ips(?:.json|.xml)?$', 'list_addresses'),
    (r'^/(\d+)/ips/(.+?)(?:.json|.xml)?$', 'list_addresses_by_network'),
    (r'^/(\d+)/meta(?:.json|.xml)?$', 'metadata_demux'),
    (r'^/(\d+)/meta/(.+?)(?:.json|.xml)?$', 'metadata_item_demux'),
)


def demux(request):
    if request.method == 'GET':
        return list_servers(request)
    elif request.method == 'POST':
        return create_server(request)
    else:
        return method_not_allowed(request)

def server_demux(request, server_id):
    if request.method == 'GET':
        return get_server_details(request, server_id)
    elif request.method == 'PUT':
        return update_server_name(request, server_id)
    elif request.method == 'DELETE':
        return delete_server(request, server_id)
    else:
        return method_not_allowed(request)

def metadata_demux(request, server_id):
    if request.method == 'GET':
        return list_metadata(request, server_id)
    elif request.method == 'POST':
        return update_metadata(request, server_id)
    else:
        return method_not_allowed(request)

def metadata_item_demux(request, server_id, key):
    if request.method == 'GET':
        return get_metadata_item(request, server_id, key)
    elif request.method == 'PUT':
        return create_metadata_item(request, server_id, key)
    elif request.method == 'DELETE':
        return delete_metadata_item(request, server_id, key)
    else:
        return method_not_allowed(request)


def address_to_dict(ipfour, ipsix):
    return {'id': 'public',
            'values': [{'version': 4, 'addr': ipfour}, {'version': 6, 'addr': ipsix}]}

def metadata_to_dict(vm):
    vm_meta = vm.virtualmachinemetadata_set.all()
    return dict((meta.meta_key, meta.meta_value) for meta in vm_meta)

def vm_to_dict(vm, detail=False):
    d = dict(id=vm.id, name=vm.name)
    if detail:
        d['status'] = get_rsapi_state(vm)
        d['progress'] = 100 if get_rsapi_state(vm) == 'ACTIVE' else 0
        d['hostId'] = vm.hostid
        d['updated'] = isoformat(vm.updated)
        d['created'] = isoformat(vm.created)
        d['flavorRef'] = vm.flavor.id
        d['imageRef'] = vm.sourceimage.id
        
        metadata = metadata_to_dict(vm)
        if metadata:
            d['metadata'] = {'values': metadata}
        
        addresses = [address_to_dict(vm.ipfour, vm.ipsix)]
        d['addresses'] = {'values': addresses}
    return d


def render_server(request, server, status=200):
    if request.serialization == 'xml':
        data = render_to_string('server.xml', {'server': server, 'is_root': True})
    else:
        data = json.dumps({'server': server})
    return HttpResponse(data, status=status)
    

@api_method('GET')
def list_servers(request, detail=False):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       overLimit (413)
    
    owner = get_user()
    since = isoparse(request.GET.get('changes-since'))
    
    if since:
        user_vms = VirtualMachine.objects.filter(updated__gte=since)
        if not user_vms:
            return HttpResponse(status=304)
    else:
        user_vms = VirtualMachine.objects.filter(owner=owner, deleted=False)
    servers = [vm_to_dict(server, detail) for server in user_vms]
    
    if request.serialization == 'xml':
        data = render_to_string('list_servers.xml', {'servers': servers, 'detail': detail})
    else:
        data = json.dumps({'servers': {'values': servers}})
    
    return HttpResponse(data, status=200)

@api_method('POST')
def create_server(request):
    # Normal Response Code: 202
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       badRequest (400),
    #                       serverCapacityUnavailable (503),
    #                       overLimit (413)
    
    req = get_request_dict(request)
    
    try:
        server = req['server']
        name = server['name']
        metadata = server.get('metadata', {})
        assert isinstance(metadata, dict)
        sourceimage = Image.objects.get(id=server['imageRef'])
        flavor = Flavor.objects.get(id=server['flavorRef'])
    except (KeyError, AssertionError):
        raise BadRequest('Malformed request.')
    except Image.DoesNotExist:
        raise ItemNotFound
    except Flavor.DoesNotExist:
        raise ItemNotFound
    
    vm = VirtualMachine(
        name=name,
        owner=get_user(),
        sourceimage=sourceimage,
        ipfour='0.0.0.0',
        ipsix='::1',
        flavor=flavor)

    # Pick a random password for the VM.
    # FIXME: This must be passed to the Ganeti OS provider via CreateInstance()
    passwd = random_password()

    # We *must* save the VM instance now,
    # so that it gets a vm.id and vm.backend_id is valid.
    vm.save() 

    if request.META.get('SERVER_NAME', None) == 'testserver':
        backend_name = 'test-server'
        dry_run = True
    else:
        backend_name = vm.backend_id
        dry_run = False
    
    try:
        jobId = rapi.CreateInstance(
            mode='create',
            name=backend_name,
            disk_template='plain',
            disks=[{"size": 2000}],         #FIXME: Always ask for a 2GB disk for now
            nics=[{}],
            os='debootstrap+default',       #TODO: select OS from imageRef
            ip_check=False,
            name_check=False,
            pnode=rapi.GetNodes()[0],       #TODO: verify if this is necessary
            dry_run=dry_run,
            beparams=dict(auto_balance=True, vcpus=flavor.cpu, memory=flavor.ram))
    except GanetiApiError:
        vm.delete()
        raise ServiceUnavailable('Could not create server.')
        
    for key, val in metadata.items():
        VirtualMachineMetadata.objects.create(meta_key=key, meta_value=val, vm=vm)
    
    logging.info('created vm with %s cpus, %s ram and %s storage' % (flavor.cpu, flavor.ram, flavor.disk))
    
    server = vm_to_dict(vm, detail=True)
    server['status'] = 'BUILD'
    server['adminPass'] = passwd
    return render_server(request, server, status=202)

@api_method('GET')
def get_server_details(request, server_id):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       itemNotFound (404),
    #                       overLimit (413)
    
    vm = get_vm(server_id)
    server = vm_to_dict(vm, detail=True)
    return render_server(request, server)

@api_method('PUT')
def update_server_name(request, server_id):
    # Normal Response Code: 204
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       buildInProgress (409),
    #                       overLimit (413)
    
    req = get_request_dict(request)
    
    try:
        name = req['server']['name']
    except KeyError:
        raise BadRequest('Malformed request.')
    
    vm = get_vm(server_id)
    vm.name = name
    vm.save()
    
    return HttpResponse(status=204)

@api_method('DELETE')
def delete_server(request, server_id):
    # Normal Response Codes: 204
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       buildInProgress (409),
    #                       overLimit (413)
    
    vm = get_vm(server_id)
    backend.start_action(vm, 'DESTROY')
    rapi.DeleteInstance(vm.backend_id)
    return HttpResponse(status=204)

@api_method('POST')
def server_action(request, server_id):
    vm = get_vm(server_id)
    req = get_request_dict(request)
    if len(req) != 1:
        raise BadRequest('Malformed request.')
    
    key = req.keys()[0]
    val = req[key]
    
    try:
        assert isinstance(val, dict)
        return server_actions[key](request, vm, req[key])
    except KeyError:
        raise BadRequest('Unknown action.')
    except AssertionError:
        raise BadRequest('Invalid argument.')

@api_method('GET')
def list_addresses(request, server_id):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       overLimit (413)
    
    vm = get_vm(server_id)
    addresses = [address_to_dict(vm.ipfour, vm.ipsix)]
    
    if request.serialization == 'xml':
        data = render_to_string('list_addresses.xml', {'addresses': addresses})
    else:
        data = json.dumps({'addresses': {'values': addresses}})
    
    return HttpResponse(data, status=200)

@api_method('GET')
def list_addresses_by_network(request, server_id, network_id):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       itemNotFound (404),
    #                       overLimit (413)
    
    vm = get_vm(server_id)
    if network_id != 'public':
        raise ItemNotFound('Unknown network.')
    
    address = address_to_dict(vm.ipfour, vm.ipsix)
    
    if request.serialization == 'xml':
        data = render_to_string('address.xml', {'address': address})
    else:
        data = json.dumps({'network': address})
    
    return HttpResponse(data, status=200)

@api_method('GET')
def list_metadata(request, server_id):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       overLimit (413)

    vm = get_vm(server_id)
    metadata = metadata_to_dict(vm)
    return render_metadata(request, metadata, use_values=True, status=200)

@api_method('POST')
def update_metadata(request, server_id):
    # Normal Response Code: 201
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       buildInProgress (409),
    #                       badMediaType(415),
    #                       overLimit (413)

    vm = get_vm(server_id)
    req = get_request_dict(request)
    try:
        metadata = req['metadata']
        assert isinstance(metadata, dict)
    except (KeyError, AssertionError):
        raise BadRequest('Malformed request.')
    
    updated = {}
    
    for key, val in metadata.items():
        try:
            meta = VirtualMachineMetadata.objects.get(meta_key=key, vm=vm)
            meta.meta_value = val
            meta.save()
            updated[key] = val
        except VirtualMachineMetadata.DoesNotExist:
            pass    # Ignore non-existent metadata
    
    return render_metadata(request, metadata, status=201)

@api_method('GET')
def get_metadata_item(request, server_id, key):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       itemNotFound (404),
    #                       badRequest (400),
    #                       overLimit (413)

    meta = get_vm_meta(server_id, key)
    return render_meta(request, meta, status=200)

@api_method('PUT')
def create_metadata_item(request, server_id, key):
    # Normal Response Code: 201
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       itemNotFound (404),
    #                       badRequest (400),
    #                       buildInProgress (409),
    #                       badMediaType(415),
    #                       overLimit (413)

    vm = get_vm(server_id)
    req = get_request_dict(request)
    try:
        metadict = req['meta']
        assert isinstance(metadict, dict)
        assert len(metadict) == 1
        assert key in metadict
    except (KeyError, AssertionError):
        raise BadRequest('Malformed request.')
    
    meta, created = VirtualMachineMetadata.objects.get_or_create(meta_key=key, vm=vm)
    meta.meta_value = metadict[key]
    meta.save()
    return render_meta(request, meta, status=201)

@api_method('DELETE')
def delete_metadata_item(request, server_id, key):
    # Normal Response Code: 204
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       itemNotFound (404),
    #                       badRequest (400),
    #                       buildInProgress (409),
    #                       badMediaType(415),
    #                       overLimit (413),

    meta = get_vm_meta(server_id, key)
    meta.delete()
    return HttpResponse(status=204)
