# Copyright 2011 GRNET S.A. All rights reserved.
# 
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
# 
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
# 
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# 
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

import logging

from django.conf.urls.defaults import patterns
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson as json

from synnefo.api import util
from synnefo.api.actions import server_actions
from synnefo.api.common import method_not_allowed
from synnefo.api.faults import BadRequest, ItemNotFound, ServiceUnavailable
from synnefo.db.models import VirtualMachine, VirtualMachineMetadata
from synnefo.logic.backend import create_instance, delete_instance
from synnefo.logic.utils import get_rsapi_state
from synnefo.util.rapi import GanetiApiError


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


def nic_to_dict(nic):
    network = nic.network
    network_id = str(network.id) if not network.public else 'public'
    d = {'id': network_id, 'name': network.name, 'mac': nic.mac}
    if nic.firewall_profile:
        d['firewallProfile'] = nic.firewall_profile
    if nic.ipv4 or nic.ipv6:
        d['values'] = []
        if nic.ipv4:
            d['values'].append({'version': 4, 'addr': nic.ipv4})
        if nic.ipv6:
            d['values'].append({'version': 6, 'addr': nic.ipv6})
    return d

def metadata_to_dict(vm):
    vm_meta = vm.virtualmachinemetadata_set.all()
    return dict((meta.meta_key, meta.meta_value) for meta in vm_meta)

def vm_to_dict(vm, detail=False):
    d = dict(id=vm.id, name=vm.name)
    if detail:
        d['status'] = get_rsapi_state(vm)
        d['progress'] = 100 if get_rsapi_state(vm) == 'ACTIVE' else 0
        d['hostId'] = vm.hostid
        d['updated'] = util.isoformat(vm.updated)
        d['created'] = util.isoformat(vm.created)
        d['flavorRef'] = vm.flavor.id
        d['imageRef'] = vm.sourceimage.id

        metadata = metadata_to_dict(vm)
        if metadata:
            d['metadata'] = {'values': metadata}

        addresses = [nic_to_dict(nic) for nic in vm.nics.all()]
        if addresses:
            d['addresses'] = {'values': addresses}
    return d


def render_server(request, server, status=200):
    if request.serialization == 'xml':
        data = render_to_string('server.xml', {
            'server': server,
            'is_root': True})
    else:
        data = json.dumps({'server': server})
    return HttpResponse(data, status=status)


@util.api_method('GET')
def list_servers(request, detail=False):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       overLimit (413)

    since = util.isoparse(request.GET.get('changes-since'))

    if since:
        user_vms = VirtualMachine.objects.filter(owner=request.user,
                                                updated__gte=since)
        if not user_vms:
            return HttpResponse(status=304)
    else:
        user_vms = VirtualMachine.objects.filter(owner=request.user,
                                                deleted=False)
    
    servers = [vm_to_dict(server, detail) for server in user_vms]

    if request.serialization == 'xml':
        data = render_to_string('list_servers.xml', {
            'servers': servers,
            'detail': detail})
    else:
        data = json.dumps({'servers': {'values': servers}})

    return HttpResponse(data, status=200)

@util.api_method('POST')
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

    req = util.get_request_dict(request)
    owner = request.user
    
    try:
        server = req['server']
        name = server['name']
        metadata = server.get('metadata', {})
        assert isinstance(metadata, dict)
        image_id = server['imageRef']
        flavor_id = server['flavorRef']
    except (KeyError, AssertionError):
        raise BadRequest('Malformed request.')
    
    image = util.get_image(image_id, owner)
    flavor = util.get_flavor(flavor_id)
    password = util.random_password()
    
    # We must save the VM instance now, so that it gets a valid vm.backend_id.
    vm = VirtualMachine.objects.create(
        name=name,
        owner=owner,
        sourceimage=image,
        flavor=flavor)
    
    try:
        create_instance(vm, flavor, image, password)
    except GanetiApiError:
        vm.delete()
        raise ServiceUnavailable('Could not create server.')

    for key, val in metadata.items():
        VirtualMachineMetadata.objects.create(
            meta_key=key,
            meta_value=val,
            vm=vm)
    
    logging.info('created vm with %s cpus, %s ram and %s storage',
                    flavor.cpu, flavor.ram, flavor.disk)

    server = vm_to_dict(vm, detail=True)
    server['status'] = 'BUILD'
    server['adminPass'] = password
    return render_server(request, server, status=202)

@util.api_method('GET')
def get_server_details(request, server_id):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       itemNotFound (404),
    #                       overLimit (413)

    vm = util.get_vm(server_id, request.user)
    server = vm_to_dict(vm, detail=True)
    return render_server(request, server)

@util.api_method('PUT')
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

    req = util.get_request_dict(request)

    try:
        name = req['server']['name']
    except (TypeError, KeyError):
        raise BadRequest('Malformed request.')

    vm = util.get_vm(server_id, request.user)
    vm.name = name
    vm.save()

    return HttpResponse(status=204)

@util.api_method('DELETE')
def delete_server(request, server_id):
    # Normal Response Codes: 204
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       buildInProgress (409),
    #                       overLimit (413)

    vm = util.get_vm(server_id, request.user)
    delete_instance(vm)
    return HttpResponse(status=204)

@util.api_method('POST')
def server_action(request, server_id):
    vm = util.get_vm(server_id, request.user)
    req = util.get_request_dict(request)
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

@util.api_method('GET')
def list_addresses(request, server_id):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       overLimit (413)

    vm = util.get_vm(server_id, request.user)
    addresses = [nic_to_dict(nic) for nic in vm.nics.all()]
    
    if request.serialization == 'xml':
        data = render_to_string('list_addresses.xml', {'addresses': addresses})
    else:
        data = json.dumps({'addresses': {'values': addresses}})

    return HttpResponse(data, status=200)

@util.api_method('GET')
def list_addresses_by_network(request, server_id, network_id):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       itemNotFound (404),
    #                       overLimit (413)
    
    owner = request.user
    machine = util.get_vm(server_id, owner)
    network = util.get_network(network_id, owner)
    nic = util.get_nic(machine, network)
    address = nic_to_dict(nic)
    
    if request.serialization == 'xml':
        data = render_to_string('address.xml', {'address': address})
    else:
        data = json.dumps({'network': address})

    return HttpResponse(data, status=200)

@util.api_method('GET')
def list_metadata(request, server_id):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       overLimit (413)

    vm = util.get_vm(server_id, request.user)
    metadata = metadata_to_dict(vm)
    return util.render_metadata(request, metadata, use_values=True, status=200)

@util.api_method('POST')
def update_metadata(request, server_id):
    # Normal Response Code: 201
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       buildInProgress (409),
    #                       badMediaType(415),
    #                       overLimit (413)

    vm = util.get_vm(server_id, request.user)
    req = util.get_request_dict(request)
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
    
    if updated:
        vm.save()
    
    return util.render_metadata(request, updated, status=201)

@util.api_method('GET')
def get_metadata_item(request, server_id, key):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       itemNotFound (404),
    #                       badRequest (400),
    #                       overLimit (413)

    vm = util.get_vm(server_id, request.user)
    meta = util.get_vm_meta(vm, key)
    return util.render_meta(request, meta, status=200)

@util.api_method('PUT')
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

    vm = util.get_vm(server_id, request.user)
    req = util.get_request_dict(request)
    try:
        metadict = req['meta']
        assert isinstance(metadict, dict)
        assert len(metadict) == 1
        assert key in metadict
    except (KeyError, AssertionError):
        raise BadRequest('Malformed request.')
    
    meta, created = VirtualMachineMetadata.objects.get_or_create(
        meta_key=key,
        vm=vm)
    
    meta.meta_value = metadict[key]
    meta.save()
    vm.save()
    return util.render_meta(request, meta, status=201)

@util.api_method('DELETE')
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

    vm = util.get_vm(server_id, request.user)
    meta = util.get_vm_meta(vm, key)
    meta.delete()
    vm.save()
    return HttpResponse(status=204)
