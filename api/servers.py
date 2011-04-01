#
# Copyright (c) 2010 Greek Research and Technology Network
#

from logging import getLogger

from django.conf import settings
from django.conf.urls.defaults import *
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson as json

from synnefo.api.actions import server_actions
from synnefo.api.errors import *
from synnefo.api.util import *
from synnefo.db.models import *
from synnefo.util.rapi import GanetiRapiClient
from synnefo.logic import backend, utils

log = getLogger('synnefo.api.servers')
rapi = GanetiRapiClient(*settings.GANETI_CLUSTER_INFO)

urlpatterns = patterns('synnefo.api.servers',
    (r'^(?:/|.json|.xml)?$', 'demux'),
    (r'^/detail(?:.json|.xml)?$', 'list_servers', {'detail': True}),
    (r'^/(\d+)(?:.json|.xml)?$', 'server_demux'),
    (r'^/(\d+)/action(?:.json|.xml)?$', 'server_action'),
    (r'^/(\d+)/ips(?:.json|.xml)?$', 'list_addresses'),
    (r'^/(\d+)/ips/(.+?)(?:.json|.xml)?$', 'list_addresses_by_network'),
)


def demux(request):
    if request.method == 'GET':
        return list_servers(request)
    elif request.method == 'POST':
        return create_server(request)
    else:
        fault = BadRequest()
        return render_fault(request, fault)

def server_demux(request, server_id):
    if request.method == 'GET':
        return get_server_details(request, server_id)
    elif request.method == 'PUT':
        return update_server_name(request, server_id)
    elif request.method == 'DELETE':
        return delete_server(request, server_id)
    else:
        fault = BadRequest()
        return render_fault(request, fault)


def address_to_dict(ipfour, ipsix):
    return {'id': 'public',
            'values': [{'version': 4, 'addr': ipfour}, {'version': 6, 'addr': ipsix}]}

def server_to_dict(server, detail=False):
    d = dict(id=server.id, name=server.name)
    if detail:
        d['status'] = utils.get_rsapi_state(server)
        d['progress'] = 100 if utils.get_rsapi_state(server) == 'ACTIVE' else 0
        d['hostId'] = server.hostid
        d['updated'] = server.updated.isoformat()
        d['created'] = server.created.isoformat()
        d['flavorRef'] = server.flavor.id
        d['imageRef'] = server.sourceimage.id
        #d['description'] = server.description       # XXX Not in OpenStack docs
        
        server_meta = server.virtualmachinemetadata_set.all()
        metadata = dict((meta.meta_key, meta.meta_value) for meta in server_meta)
        if metadata:
            d['metadata'] = {'values': metadata}
        
        addresses = [address_to_dict(server.ipfour, server.ipsix)]
        d['addresses'] = {'values': addresses}
    return d

def render_server(request, serverdict, status=200):
    if request.type == 'xml':
        data = render_to_string('server.xml', dict(server=serverdict, is_root=True))
    else:
        data = json.dumps({'server': serverdict})
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
    user_servers = VirtualMachine.objects.filter(owner=owner, deleted=False)
    servers = [server_to_dict(server, detail) for server in user_servers]
    
    if request.type == 'xml':
        data = render_to_string('list_servers.xml', dict(servers=servers, detail=detail))
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
        sourceimage = Image.objects.get(id=server['imageRef'])
        flavor = Flavor.objects.get(id=server['flavorRef'])
    except KeyError:
        raise BadRequest
    except Image.DoesNotExist:
        raise ItemNotFound
    except Flavor.DoesNotExist:
        raise ItemNotFound
    
    server = VirtualMachine.objects.create(
        name=name,
        owner=get_user(),
        sourceimage=sourceimage,
        ipfour='0.0.0.0',
        ipsix='::1',
        flavor=flavor)
                
    if request.META.get('SERVER_NAME', None) == 'testserver':
        name = 'test-server'
        dry_run = True
    else:
        name = server.backend_id
        dry_run = False
    
    jobId = rapi.CreateInstance(
        mode='create',
        name=name,
        disk_template='plain',
        disks=[{"size": 2000}],         #FIXME: Always ask for a 2GB disk for now
        nics=[{}],
        os='debootstrap+default',       #TODO: select OS from imageRef
        ip_check=False,
        name_check=False,
        pnode=rapi.GetNodes()[0],       #TODO: verify if this is necessary
        dry_run=dry_run,
        beparams=dict(auto_balance=True, vcpus=flavor.cpu, memory=flavor.ram))
    
    server.save()
        
    log.info('created vm with %s cpus, %s ram and %s storage' % (flavor.cpu, flavor.ram, flavor.disk))
    
    serverdict = server_to_dict(server, detail=True)
    serverdict['status'] = 'BUILD'
    serverdict['adminPass'] = random_password()
    return render_server(request, serverdict, status=202)

@api_method('GET')
def get_server_details(request, server_id):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       itemNotFound (404),
    #                       overLimit (413)
    
    try:
        server_id = int(server_id)
        server = VirtualMachine.objects.get(id=server_id)
    except VirtualMachine.DoesNotExist:
        raise ItemNotFound
    
    serverdict = server_to_dict(server, detail=True)
    return render_server(request, serverdict)

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
        server_id = int(server_id)
        server = VirtualMachine.objects.get(id=server_id)
    except KeyError:
        raise BadRequest
    except VirtualMachine.DoesNotExist:
        raise ItemNotFound
    
    server.name = name
    server.save()
    
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
    
    try:
        server_id = int(server_id)
        server = VirtualMachine.objects.get(id=server_id)
    except VirtualMachine.DoesNotExist:
        raise ItemNotFound
    
    backend.start_action(server, 'DESTROY')
    rapi.DeleteInstance(server.backend_id)
    return HttpResponse(status=204)

@api_method('POST')
def server_action(request, server_id):
    try:
        server_id = int(server_id)
        server = VirtualMachine.objects.get(id=server_id)
    except VirtualMachine.DoesNotExist:
        raise ItemNotFound

    req = get_request_dict(request)
    if len(req) != 1:
        raise BadRequest
    
    key = req.keys()[0]
    if key not in server_actions:
        raise BadRequest
    
    return server_actions[key](server, req[key])

@api_method('GET')
def list_addresses(request, server_id):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       overLimit (413)
    
    try:
        server_id = int(server_id)
        server = VirtualMachine.objects.get(id=server_id)
    except VirtualMachine.DoesNotExist:
        raise ItemNotFound
    
    addresses = [address_to_dict(server.ipfour, server.ipsix)]
    
    if request.type == 'xml':
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
    
    try:
        server_id = int(server_id)
        server = VirtualMachine.objects.get(id=server_id)
    except VirtualMachine.DoesNotExist:
        raise ItemNotFound
    
    if network_id != 'public':
        raise ItemNotFound
    
    address = address_to_dict(server.ipfour, server.ipsix)
    
    if request.type == 'xml':
        data = render_to_string('address.xml', {'address': address})
    else:
        data = json.dumps({'network': address})
    
    return HttpResponse(data, status=200)
