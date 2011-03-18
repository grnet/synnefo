#
# Copyright (c) 2010 Greek Research and Technology Network
#

from synnefo.api.errors import *
from synnefo.api.util import *
from synnefo.db.models import *
from synnefo.util.rapi import GanetiRapiClient

from django.conf.urls.defaults import *
from django.http import HttpResponse
from django.template.loader import render_to_string

from logging import getLogger

import json


log = getLogger('synnefo.api.servers')
rapi = GanetiRapiClient(*settings.GANETI_CLUSTER_INFO)

urlpatterns = patterns('synnefo.api.servers',
    (r'^(?:/|.json|.xml)?$', 'demux'),
    (r'^/detail(?:.json|.xml)?$', 'list_servers', {'detail': True}),
    (r'^/(\d+)(?:.json|.xml)?$', 'server_demux'),
)


def demux(request):
    if request.method == 'GET':
        return list_servers(request)
    elif request.method == 'POST':
        return create_server(request)
    else:
        return HttpResponse(status=404)

def server_demux(request, server_id):
    if request.method == 'GET':
        return get_server_details(request, server_id)
    elif request.method == 'PUT':
        return update_server_name(request, server_id)
    elif request.method == 'DELETE':
        return delete_server(request, server_id)
    else:
        return HttpResponse(status=404)

def server_dict(vm, detail=False):
    d = dict(id=vm.id, name=vm.name)
    if detail:
        d['status'] = vm.rsapi_state
        d['progress'] = 100 if vm.rsapi_state == 'ACTIVE' else 0
        d['hostId'] = vm.hostid
        d['updated'] = vm.updated.isoformat()
        d['created'] = vm.created.isoformat()
        d['flavorId'] = vm.flavor.id            # XXX Should use flavorRef instead?
        d['imageId'] = vm.sourceimage.id        # XXX Should use imageRef instead?
        d['description'] = vm.description       # XXX Not in OpenStack docs
        
        vm_meta = vm.virtualmachinemetadata_set.all()
        metadata = dict((meta.meta_key, meta.meta_value) for meta in vm_meta)
        if metadata:
            d['metadata'] = dict(values=metadata)
        
        public_addrs = [dict(version=4, addr=vm.ipfour), dict(version=6, addr=vm.ipsix)]
        d['addresses'] = {'values': []}
        d['addresses']['values'].append({'id': 'public', 'values': public_addrs})
    return d

def render_server(server, request, status=200):
    if request.type == 'xml':
        mimetype = 'application/xml'
        data = render_to_string('server.xml', dict(server=server, is_root=True))
    else:
        mimetype = 'application/json'
        data = json.dumps({'server': server})
    return HttpResponse(data, mimetype=mimetype, status=status)    


@api_method
def list_servers(request, detail=False):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       overLimit (413)
    owner = get_user()
    vms = VirtualMachine.objects.filter(owner=owner, deleted=False)
    servers = [server_dict(vm, detail) for vm in vms]
    if request.type == 'xml':
        mimetype = 'application/xml'
        data = render_to_string('list_servers.xml', dict(servers=servers, detail=detail))
    else:
        mimetype = 'application/json'
        data = json.dumps({'servers': servers})
    return HttpResponse(data, mimetype=mimetype, status=200)

@api_method
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
        sourceimage = Image.objects.get(id=server['imageId'])
        flavor = Flavor.objects.get(id=server['flavorId'])
    except KeyError:
        raise BadRequest
    except Image.DoesNotExist:
        raise ItemNotFound
    except Flavor.DoesNotExist:
        raise ItemNotFound
    
    vm = VirtualMachine.objects.create(
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
        name = vm.backend_id
        dry_run = False
    
    jobId = rapi.CreateInstance(
        mode='create',
        name=name,
        disk_template='plain',
        disks=[{"size": 2000}],         #FIXME: Always ask for a 2GB disk for now
        nics=[{}],
        os='debootstrap+default',       #TODO: select OS from imageId
        ip_check=False,
        nam_check=False,
        pnode=rapi.GetNodes()[0],       #TODO: verify if this is necessary
        dry_run=dry_run,
        beparams=dict(auto_balance=True, vcpus=flavor.cpu, memory=flavor.ram))
    
    vm.save()
        
    log.info('created vm with %s cpus, %s ram and %s storage' % (flavor.cpu, flavor.ram, flavor.disk))
    
    server = server_dict(vm, detail=True)
    server['status'] = 'BUILD'
    server['adminPass'] = random_password()
    return render_server(server, request, status=202)

@api_method
def get_server_details(request, server_id):
    try:
        vm = VirtualMachine.objects.get(id=int(server_id))
    except VirtualMachine.DoesNotExist:
        raise NotFound
    
    server = server_dict(vm, detail=True)
    return render_server(server, request)

@api_method
def update_server_name(request, server_id):    
    req = get_request_dict(request)
    
    try:
        name = req['server']['name']
        vm = VirtualMachine.objects.get(id=int(server_id))
    except KeyError:
        raise BadRequest
    except VirtualMachine.DoesNotExist:
        raise NotFound
    
    vm.name = name
    vm.save()
    
    return HttpResponse(status=204)

@api_method
def delete_server(request, server_id):
    try:
        vm = VirtualMachine.objects.get(id=int(server_id))
    except VirtualMachine.DoesNotExist:
        raise NotFound
    
    vm.start_action('DESTROY')
    rapi.DeleteInstance(vm.backend_id)
    vm.state = 'DESTROYED'
    vm.save()
    return HttpResponse(status=204)
