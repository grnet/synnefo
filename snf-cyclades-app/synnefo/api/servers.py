# Copyright 2011-2012 GRNET S.A. All rights reserved.
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

from base64 import b64decode

from django.conf import settings
from django.conf.urls.defaults import patterns
from django.db import transaction
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson as json

from synnefo.api import faults, util
from synnefo.api.actions import server_actions
from synnefo.api.common import method_not_allowed
from synnefo.db.models import VirtualMachine, VirtualMachineMetadata
from synnefo.logic.backend import create_instance, delete_instance
from synnefo.logic.utils import get_rsapi_state
from synnefo.logic.rapi import GanetiApiError
from synnefo.logic.backend_allocator import BackendAllocator
from random import choice


from logging import getLogger
log = getLogger('synnefo.api')

urlpatterns = patterns('synnefo.api.servers',
    (r'^(?:/|.json|.xml)?$', 'demux'),
    (r'^/detail(?:.json|.xml)?$', 'list_servers', {'detail': True}),
    (r'^/(\d+)(?:.json|.xml)?$', 'server_demux'),
    (r'^/(\d+)/action(?:.json|.xml)?$', 'server_action'),
    (r'^/(\d+)/ips(?:.json|.xml)?$', 'list_addresses'),
    (r'^/(\d+)/ips/(.+?)(?:.json|.xml)?$', 'list_addresses_by_network'),
    (r'^/(\d+)/meta(?:.json|.xml)?$', 'metadata_demux'),
    (r'^/(\d+)/meta/(.+?)(?:.json|.xml)?$', 'metadata_item_demux'),
    (r'^/(\d+)/stats(?:.json|.xml)?$', 'server_stats'),
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
    d = {'id': util.construct_nic_id(nic),
         'network_id': str(nic.network.id),
         'mac_address': nic.mac,
         'ipv4': nic.ipv4 if nic.ipv4 else None,
         'ipv6': nic.ipv6 if nic.ipv6 else None}

    if nic.firewall_profile:
        d['firewallProfile'] = nic.firewall_profile
    return d


def vm_to_dict(vm, detail=False):
    d = dict(id=vm.id, name=vm.name)
    if detail:
        d['status'] = get_rsapi_state(vm)
        d['progress'] = 100 if get_rsapi_state(vm) == 'ACTIVE' \
                        else vm.buildpercentage
        d['hostId'] = vm.hostid
        d['updated'] = util.isoformat(vm.updated)
        d['created'] = util.isoformat(vm.created)
        d['flavorRef'] = vm.flavor.id
        d['imageRef'] = vm.imageid

        metadata = dict((m.meta_key, m.meta_value) for m in vm.metadata.all())
        if metadata:
            d['metadata'] = {'values': metadata}

        attachments = [nic_to_dict(nic) for nic in vm.nics.all()]
        if attachments:
            d['attachments'] = {'values': attachments}
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

    log.debug('list_servers detail=%s', detail)
    user_vms = VirtualMachine.objects.filter(userid=request.user_uniq)

    since = util.isoparse(request.GET.get('changes-since'))
    if since:
        user_vms = user_vms.filter(updated__gte=since)
        if not user_vms:
            return HttpResponse(status=304)
    else:
        user_vms = user_vms.filter(deleted=False)

    servers = [vm_to_dict(server, detail) for server in user_vms]

    if request.serialization == 'xml':
        data = render_to_string('list_servers.xml', {
            'servers': servers,
            'detail': detail})
    else:
        data = json.dumps({'servers': {'values': servers}})

    return HttpResponse(data, status=200)


@util.api_method('POST')
# Use manual transactions. Backend and IP pool allocations need exclusive
# access (SELECT..FOR UPDATE). Running create_server with commit_on_success
# would result in backends and public networks to be locked until the job is
# sent to the Ganeti backend.
@transaction.commit_manually
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
    try:
        req = util.get_request_dict(request)
        log.info('create_server %s', req)

        try:
            server = req['server']
            name = server['name']
            metadata = server.get('metadata', {})
            assert isinstance(metadata, dict)
            image_id = server['imageRef']
            flavor_id = server['flavorRef']
            personality = server.get('personality', [])
            assert isinstance(personality, list)
        except (KeyError, AssertionError):
            raise faults.BadRequest("Malformed request")

        if len(personality) > settings.MAX_PERSONALITY:
            raise faults.OverLimit("Maximum number of personalities exceeded")

        for p in personality:
            # Verify that personalities are well-formed
            try:
                assert isinstance(p, dict)
                keys = set(p.keys())
                allowed = set(['contents', 'group', 'mode', 'owner', 'path'])
                assert keys.issubset(allowed)
                contents = p['contents']
                if len(contents) > settings.MAX_PERSONALITY_SIZE:
                    # No need to decode if contents already exceed limit
                    raise faults.OverLimit("Maximum size of personality exceeded")
                if len(b64decode(contents)) > settings.MAX_PERSONALITY_SIZE:
                    raise faults.OverLimit("Maximum size of personality exceeded")
            except AssertionError:
                raise faults.BadRequest("Malformed personality in request")

        image = {}
        img = util.get_image(image_id, request.user_uniq)
        properties = img.get('properties', {})
        image['backend_id'] = img['location']
        image['format'] = img['disk_format']
        image['metadata'] = dict((key.upper(), val) \
                                 for key, val in properties.items())

        flavor = util.get_flavor(flavor_id)
        password = util.random_password()

        count = VirtualMachine.objects.filter(userid=request.user_uniq,
                                              deleted=False).count()

        # get user limit
        vms_limit_for_user = \
            settings.VMS_USER_QUOTA.get(request.user_uniq,
                    settings.MAX_VMS_PER_USER)

        if count >= vms_limit_for_user:
            raise faults.OverLimit("Server count limit exceeded for your account.")

        backend_allocator = BackendAllocator()
        backend = backend_allocator.allocate(request.user_uniq, flavor)

        if backend is None:
            log.error("No available backends for VM with flavor %s", flavor)
            raise Exception("No available backends")
    except:
        transaction.rollback()
        raise
    else:
        transaction.commit()

    try:
        if settings.PUBLIC_ROUTED_USE_POOL:
            (network, address) = util.allocate_public_address(backend)
            if address is None:
                log.error("Public networks of backend %s are full", backend)
                raise faults.OverLimit("Can not allocate IP for new machine."
                                       " Public networks are full.")
            nic = {'ip': address, 'network': network.backend_id}
        else:
            network = choice(list(util.backend_public_networks(backend)))
            nic = {'ip': 'pool', 'network': network.backend_id}
    except:
        transaction.rollback()
        raise
    else:
        transaction.commit()

    try:
        # We must save the VM instance now, so that it gets a valid
        # vm.backend_vm_id.
        vm = VirtualMachine.objects.create(
            name=name,
            backend=backend,
            userid=request.user_uniq,
            imageid=image_id,
            flavor=flavor)

        try:
            jobID = create_instance(vm, nic, flavor, image, password, personality)
        except GanetiApiError:
            vm.delete()
            raise

        log.info("User %s created VM %s, NIC %s, Backend %s, JobID %s",
                request.user_uniq, vm, nic, backend, str(jobID))

        vm.backendjobid = jobID
        vm.save()

        for key, val in metadata.items():
            VirtualMachineMetadata.objects.create(
                meta_key=key,
                meta_value=val,
                vm=vm)

        server = vm_to_dict(vm, detail=True)
        server['status'] = 'BUILD'
        server['adminPass'] = password

        respsone = render_server(request, server, status=202)
    except:
        transaction.rollback()
        raise
    else:
        transaction.commit()

    return respsone


@util.api_method('GET')
def get_server_details(request, server_id):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       itemNotFound (404),
    #                       overLimit (413)

    log.debug('get_server_details %s', server_id)
    vm = util.get_vm(server_id, request.user_uniq)
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
    log.info('update_server_name %s %s', server_id, req)

    try:
        name = req['server']['name']
    except (TypeError, KeyError):
        raise faults.BadRequest("Malformed request")

    vm = util.get_vm(server_id, request.user_uniq)
    vm.name = name
    vm.save()

    return HttpResponse(status=204)


@util.api_method('DELETE')
@transaction.commit_on_success
def delete_server(request, server_id):
    # Normal Response Codes: 204
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       buildInProgress (409),
    #                       overLimit (413)

    log.info('delete_server %s', server_id)
    vm = util.get_vm(server_id, request.user_uniq)
    delete_instance(vm)
    return HttpResponse(status=204)


@util.api_method('POST')
def server_action(request, server_id):
    req = util.get_request_dict(request)
    log.debug('server_action %s %s', server_id, req)
    vm = util.get_vm(server_id, request.user_uniq)
    if len(req) != 1:
        raise faults.BadRequest("Malformed request")

    key = req.keys()[0]
    val = req[key]

    try:
        assert isinstance(val, dict)
        return server_actions[key](request, vm, req[key])
    except KeyError:
        raise faults.BadRequest("Unknown action")
    except AssertionError:
        raise faults.BadRequest("Invalid argument")


@util.api_method('GET')
def list_addresses(request, server_id):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       overLimit (413)

    log.debug('list_addresses %s', server_id)
    vm = util.get_vm(server_id, request.user_uniq)
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

    log.debug('list_addresses_by_network %s %s', server_id, network_id)
    machine = util.get_vm(server_id, request.user_uniq)
    network = util.get_network(network_id, request.user_uniq)
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

    log.debug('list_server_metadata %s', server_id)
    vm = util.get_vm(server_id, request.user_uniq)
    metadata = dict((m.meta_key, m.meta_value) for m in vm.metadata.all())
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

    req = util.get_request_dict(request)
    log.info('update_server_metadata %s %s', server_id, req)
    vm = util.get_vm(server_id, request.user_uniq)
    try:
        metadata = req['metadata']
        assert isinstance(metadata, dict)
    except (KeyError, AssertionError):
        raise faults.BadRequest("Malformed request")

    for key, val in metadata.items():
        meta, created = vm.metadata.get_or_create(meta_key=key)
        meta.meta_value = val
        meta.save()

    vm.save()
    vm_meta = dict((m.meta_key, m.meta_value) for m in vm.metadata.all())
    return util.render_metadata(request, vm_meta, status=201)


@util.api_method('GET')
def get_metadata_item(request, server_id, key):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       itemNotFound (404),
    #                       badRequest (400),
    #                       overLimit (413)

    log.debug('get_server_metadata_item %s %s', server_id, key)
    vm = util.get_vm(server_id, request.user_uniq)
    meta = util.get_vm_meta(vm, key)
    d = {meta.meta_key: meta.meta_value}
    return util.render_meta(request, d, status=200)


@util.api_method('PUT')
@transaction.commit_on_success
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

    req = util.get_request_dict(request)
    log.info('create_server_metadata_item %s %s %s', server_id, key, req)
    vm = util.get_vm(server_id, request.user_uniq)
    try:
        metadict = req['meta']
        assert isinstance(metadict, dict)
        assert len(metadict) == 1
        assert key in metadict
    except (KeyError, AssertionError):
        raise faults.BadRequest("Malformed request")

    meta, created = VirtualMachineMetadata.objects.get_or_create(
        meta_key=key,
        vm=vm)

    meta.meta_value = metadict[key]
    meta.save()
    vm.save()
    d = {meta.meta_key: meta.meta_value}
    return util.render_meta(request, d, status=201)


@util.api_method('DELETE')
@transaction.commit_on_success
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

    log.info('delete_server_metadata_item %s %s', server_id, key)
    vm = util.get_vm(server_id, request.user_uniq)
    meta = util.get_vm_meta(vm, key)
    meta.delete()
    vm.save()
    return HttpResponse(status=204)


@util.api_method('GET')
def server_stats(request, server_id):
    # Normal Response Codes: 200
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       itemNotFound (404),
    #                       overLimit (413)

    log.debug('server_stats %s', server_id)
    vm = util.get_vm(server_id, request.user_uniq)
    #secret = util.encrypt(vm.backend_vm_id)
    secret = vm.backend_vm_id      # XXX disable backend id encryption

    stats = {
        'serverRef': vm.id,
        'refresh': settings.STATS_REFRESH_PERIOD,
        'cpuBar': settings.CPU_BAR_GRAPH_URL % secret,
        'cpuTimeSeries': settings.CPU_TIMESERIES_GRAPH_URL % secret,
        'netBar': settings.NET_BAR_GRAPH_URL % secret,
        'netTimeSeries': settings.NET_TIMESERIES_GRAPH_URL % secret}

    if request.serialization == 'xml':
        data = render_to_string('server_stats.xml', stats)
    else:
        data = json.dumps({'stats': stats})

    return HttpResponse(data, status=200)
