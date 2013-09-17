# Copyright 2011-2013 GRNET S.A. All rights reserved.
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

from django import dispatch
from django.conf import settings
from django.conf.urls.defaults import patterns
from django.db import transaction
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson as json

from snf_django.lib import api
from snf_django.lib.api import faults, utils
from synnefo.api import util
from synnefo.api.actions import server_actions
from synnefo.db.models import (VirtualMachine, VirtualMachineMetadata,
                               NetworkInterface)
from synnefo.logic.backend import create_instance, delete_instance
from synnefo.logic.utils import get_rsapi_state
from synnefo.logic.backend_allocator import BackendAllocator
from synnefo import quotas

# server creation signal
server_created = dispatch.Signal(providing_args=["created_vm_params"])

from logging import getLogger
log = getLogger(__name__)

urlpatterns = patterns(
    'synnefo.api.servers',
    (r'^(?:/|.json|.xml)?$', 'demux'),
    (r'^/detail(?:.json|.xml)?$', 'list_servers', {'detail': True}),
    (r'^/(\d+)(?:.json|.xml)?$', 'server_demux'),
    (r'^/(\d+)/action(?:.json|.xml)?$', 'server_action'),
    (r'^/(\d+)/ips(?:.json|.xml)?$', 'list_addresses'),
    (r'^/(\d+)/ips/(.+?)(?:.json|.xml)?$', 'list_addresses_by_network'),
    (r'^/(\d+)/metadata(?:.json|.xml)?$', 'metadata_demux'),
    (r'^/(\d+)/metadata/(.+?)(?:.json|.xml)?$', 'metadata_item_demux'),
    (r'^/(\d+)/stats(?:.json|.xml)?$', 'server_stats'),
    (r'^/(\d+)/diagnostics(?:.json)?$', 'get_server_diagnostics'),
)


def demux(request):
    if request.method == 'GET':
        return list_servers(request)
    elif request.method == 'POST':
        return create_server(request)
    else:
        return api.api_method_not_allowed(request)


def server_demux(request, server_id):
    if request.method == 'GET':
        return get_server_details(request, server_id)
    elif request.method == 'PUT':
        return update_server_name(request, server_id)
    elif request.method == 'DELETE':
        return delete_server(request, server_id)
    else:
        return api.api_method_not_allowed(request)


def metadata_demux(request, server_id):
    if request.method == 'GET':
        return list_metadata(request, server_id)
    elif request.method == 'POST':
        return update_metadata(request, server_id)
    else:
        return api.api_method_not_allowed(request)


def metadata_item_demux(request, server_id, key):
    if request.method == 'GET':
        return get_metadata_item(request, server_id, key)
    elif request.method == 'PUT':
        return create_metadata_item(request, server_id, key)
    elif request.method == 'DELETE':
        return delete_metadata_item(request, server_id, key)
    else:
        return api.api_method_not_allowed(request)


def nic_to_dict(nic):
    d = {'id': util.construct_nic_id(nic),
         'network_id': str(nic.network.id),
         'mac_address': nic.mac,
         'ipv4': nic.ipv4 if nic.ipv4 else None,
         'ipv6': nic.ipv6 if nic.ipv6 else None}

    if nic.firewall_profile:
        d['firewallProfile'] = nic.firewall_profile
    return d


def nics_to_addresses(nics):
    addresses = {}
    for nic in nics:
        net_nics = []
        net_nics.append({"version": 4,
                         "addr": nic.ipv4,
                         "OS-EXT-IPS:type": "fixed"})
        if nic.ipv6:
            net_nics.append({"version": 6,
                             "addr": nic.ipv6,
                             "OS-EXT-IPS:type": "fixed"})
        addresses[nic.network.id] = net_nics
    return addresses


def vm_to_dict(vm, detail=False):
    d = dict(id=vm.id, name=vm.name)
    d['links'] = util.vm_to_links(vm.id)
    if detail:
        d['user_id'] = vm.userid
        d['tenant_id'] = vm.userid
        d['status'] = get_rsapi_state(vm)
        d['progress'] = 100 if get_rsapi_state(vm) == 'ACTIVE' \
            else vm.buildpercentage
        d['hostId'] = vm.hostid
        d['updated'] = utils.isoformat(vm.updated)
        d['created'] = utils.isoformat(vm.created)
        d['flavor'] = {"id": vm.flavor.id,
                       "links": util.flavor_to_links(vm.flavor.id)}
        d['image'] = {"id": vm.imageid,
                      "links": util.image_to_links(vm.imageid)}
        d['suspended'] = vm.suspended

        metadata = dict((m.meta_key, m.meta_value) for m in vm.metadata.all())
        d['metadata'] = metadata

        vm_nics = vm.nics.filter(state="ACTIVE").order_by("index")
        attachments = map(nic_to_dict, vm_nics)
        d['attachments'] = attachments
        d['addresses'] = nics_to_addresses(vm_nics)

        # include the latest vm diagnostic, if set
        diagnostic = vm.get_last_diagnostic()
        if diagnostic:
            d['diagnostics'] = diagnostics_to_dict([diagnostic])
        else:
            d['diagnostics'] = []
        # Fixed
        d["security_groups"] = [{"name": "default"}]
        d["key_name"] = None
        d["config_drive"] = ""
        d["accessIPv4"] = ""
        d["accessIPv6"] = ""

    return d


def diagnostics_to_dict(diagnostics):
    """
    Extract api data from diagnostics QuerySet.
    """
    entries = list()

    for diagnostic in diagnostics:
        # format source date if set
        formatted_source_date = None
        if diagnostic.source_date:
            formatted_source_date = utils.isoformat(diagnostic.source_date)

        entry = {
            'source': diagnostic.source,
            'created': utils.isoformat(diagnostic.created),
            'message': diagnostic.message,
            'details': diagnostic.details,
            'level': diagnostic.level,
        }

        if formatted_source_date:
            entry['source_date'] = formatted_source_date

        entries.append(entry)

    return entries


def render_server(request, server, status=200):
    if request.serialization == 'xml':
        data = render_to_string('server.xml', {
            'server': server,
            'is_root': True})
    else:
        data = json.dumps({'server': server})
    return HttpResponse(data, status=status)


def render_diagnostics(request, diagnostics_dict, status=200):
    """
    Render diagnostics dictionary to json response.
    """
    return HttpResponse(json.dumps(diagnostics_dict), status=status)


@api.api_method(http_method='GET', user_required=True, logger=log)
def get_server_diagnostics(request, server_id):
    """
    Virtual machine diagnostics api view.
    """
    log.debug('server_diagnostics %s', server_id)
    vm = util.get_vm(server_id, request.user_uniq)
    diagnostics = diagnostics_to_dict(vm.diagnostics.all())
    return render_diagnostics(request, diagnostics)


@api.api_method(http_method='GET', user_required=True, logger=log)
def list_servers(request, detail=False):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       overLimit (413)

    log.debug('list_servers detail=%s', detail)
    user_vms = VirtualMachine.objects.filter(userid=request.user_uniq)

    since = utils.isoparse(request.GET.get('changes-since'))

    if since:
        user_vms = user_vms.filter(updated__gte=since)
        if not user_vms:
            return HttpResponse(status=304)
    else:
        user_vms = user_vms.filter(deleted=False)

    servers = [vm_to_dict(server, detail)
               for server in user_vms.order_by('id')]

    if request.serialization == 'xml':
        data = render_to_string('list_servers.xml', {
            'servers': servers,
            'detail': detail})
    else:
        data = json.dumps({'servers': servers})

    return HttpResponse(data, status=200)


@api.api_method(http_method='POST', user_required=True, logger=log)
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
    req = utils.get_request_dict(request)
    log.info('create_server %s', req)
    user_id = request.user_uniq

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

    # Verify that personalities are well-formed
    util.verify_personality(personality)
    # Get image information
    image = util.get_image_dict(image_id, user_id)
    # Get flavor (ensure it is active)
    flavor = util.get_flavor(flavor_id, include_deleted=False)
    # Generate password
    password = util.random_password()

    vm = do_create_server(user_id, name, password, flavor, image,
                          metadata=metadata, personality=personality)

    server = vm_to_dict(vm, detail=True)
    server['status'] = 'BUILD'
    server['adminPass'] = password

    response = render_server(request, server, status=202)

    return response


@transaction.commit_manually
def do_create_server(userid, name, password, flavor, image, metadata={},
                     personality=[], network=None, backend=None):
    # Fix flavor for archipelago
    disk_template, provider = util.get_flavor_provider(flavor)
    if provider:
        flavor.disk_template = disk_template
        flavor.disk_provider = provider
        flavor.disk_origin = image['checksum']
        image['backend_id'] = 'null'
    else:
        flavor.disk_provider = None
        flavor.disk_origin = None

    try:
        if backend is None:
            # Allocate backend to host the server.
            backend_allocator = BackendAllocator()
            backend = backend_allocator.allocate(userid, flavor)
            if backend is None:
                log.error("No available backend for VM with flavor %s", flavor)
                raise faults.ServiceUnavailable("No available backends")

        if network is None:
            # Allocate IP from public network
            (network, address) = util.get_public_ip(backend)
            nic = {'ip': address, 'network': network.backend_id}
        else:
            address = util.get_network_free_address(network)

        # We must save the VM instance now, so that it gets a valid
        # vm.backend_vm_id.
        vm = VirtualMachine.objects.create(
            name=name,
            backend=backend,
            userid=userid,
            imageid=image["id"],
            flavor=flavor,
            action="CREATE")

        log.info("Created entry in DB for VM '%s'", vm)

        # Create VM's public NIC. Do not wait notification form ganeti hooks to
        # create this NIC, because if the hooks never run (e.g. building error)
        # the VM's public IP address will never be released!
        NetworkInterface.objects.create(machine=vm, network=network, index=0,
                                        ipv4=address, state="BUILDING")

        # Also we must create the VM metadata in the same transaction.
        for key, val in metadata.items():
            VirtualMachineMetadata.objects.create(
                meta_key=key,
                meta_value=val,
                vm=vm)
        # Issue commission to Quotaholder and accept it since at the end of
        # this transaction the VirtualMachine object will be created in the DB.
        # Note: the following call does a commit!
        quotas.issue_and_accept_commission(vm)
    except:
        transaction.rollback()
        raise
    else:
        transaction.commit()

    try:
        vm = VirtualMachine.objects.select_for_update().get(id=vm.id)
        # dispatch server created signal needed to trigger the 'vmapi', which
        # enriches the vm object with the 'config_url' attribute which must be
        # passed to the Ganeti job.
        server_created.send(sender=vm, created_vm_params={
            'img_id': image['backend_id'],
            'img_passwd': password,
            'img_format': str(image['format']),
            'img_personality': json.dumps(personality),
            'img_properties': json.dumps(image['metadata']),
        })

        jobID = create_instance(vm, nic, flavor, image)
        # At this point the job is enqueued in the Ganeti backend
        vm.backendjobid = jobID
        vm.save()
        transaction.commit()
        log.info("User %s created VM %s, NIC %s, Backend %s, JobID %s",
                 userid, vm, nic, backend, str(jobID))
    except:
        # If an exception is raised, then the user will never get the VM id.
        # So, the VM must be marked as 'deleted'. We do not delete the VM row
        # from DB, because the job may have been enqueued to Ganeti. We must
        # also release the VM resources.
        if not vm.deleted:  # just an extra check for reconciliation...
            vm.deleted = True
            vm.operstate = "ERROR"
            vm.backendlogmsg = "Error while enqueuing job to Ganeti."
            vm.save()
            # The following call performs commit.
            quotas.issue_and_accept_commission(vm, delete=True)
        raise

    return vm


@api.api_method(http_method='GET', user_required=True, logger=log)
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


@api.api_method(http_method='PUT', user_required=True, logger=log)
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

    req = utils.get_request_dict(request)
    log.info('update_server_name %s %s', server_id, req)

    try:
        name = req['server']['name']
    except (TypeError, KeyError):
        raise faults.BadRequest("Malformed request")

    vm = util.get_vm(server_id, request.user_uniq, for_update=True,
                     non_suspended=True)
    vm.name = name
    vm.save()

    return HttpResponse(status=204)


@api.api_method(http_method='DELETE', user_required=True, logger=log)
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
    vm = util.get_vm(server_id, request.user_uniq, for_update=True,
                     non_suspended=True)
    start_action(vm, 'DESTROY')
    delete_instance(vm)
    return HttpResponse(status=204)


# additional server actions
ARBITRARY_ACTIONS = ['console', 'firewallProfile']


@api.api_method(http_method='POST', user_required=True, logger=log)
def server_action(request, server_id):
    req = utils.get_request_dict(request)
    log.debug('server_action %s %s', server_id, req)

    if len(req) != 1:
        raise faults.BadRequest("Malformed request")

    # Do not allow any action on deleted or suspended VMs
    vm = util.get_vm(server_id, request.user_uniq, for_update=True,
                     non_deleted=True, non_suspended=True)

    try:
        key = req.keys()[0]
        if key not in ARBITRARY_ACTIONS:
            start_action(vm, key_to_action(key))
        val = req[key]
        assert isinstance(val, dict)
        return server_actions[key](request, vm, val)
    except KeyError:
        raise faults.BadRequest("Unknown action")
    except AssertionError:
        raise faults.BadRequest("Invalid argument")


def key_to_action(key):
    """Map HTTP request key to a VM Action"""
    if key == "shutdown":
        return "STOP"
    if key == "delete":
        return "DESTROY"
    if key in ARBITRARY_ACTIONS:
        return None
    else:
        return key.upper()


def start_action(vm, action):
    log.debug("Applying action %s to VM %s", action, vm)
    if not action:
        return

    if not action in [x[0] for x in VirtualMachine.ACTIONS]:
        raise faults.ServiceUnavailable("Action %s not supported" % action)

    # No actions to deleted VMs
    if vm.deleted:
        raise faults.BadRequest("VirtualMachine has been deleted.")

    # No actions to machines being built. They may be destroyed, however.
    if vm.operstate == 'BUILD' and action != 'DESTROY':
        raise faults.BuildInProgress("Server is being build.")

    vm.action = action
    vm.backendjobid = None
    vm.backendopcode = None
    vm.backendjobstatus = None
    vm.backendlogmsg = None

    vm.save()


@api.api_method(http_method='GET', user_required=True, logger=log)
def list_addresses(request, server_id):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       overLimit (413)

    log.debug('list_addresses %s', server_id)
    vm = util.get_vm(server_id, request.user_uniq)
    attachments = [nic_to_dict(nic) for nic in vm.nics.all()]
    addresses = nics_to_addresses(vm.nics.all())

    if request.serialization == 'xml':
        data = render_to_string('list_addresses.xml', {'addresses': addresses})
    else:
        data = json.dumps({'addresses': addresses, 'attachments': attachments})

    return HttpResponse(data, status=200)


@api.api_method(http_method='GET', user_required=True, logger=log)
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
    nics = machine.nics.filter(network=network).all()
    addresses = nics_to_addresses(nics)

    if request.serialization == 'xml':
        data = render_to_string('address.xml', {'addresses': addresses})
    else:
        data = json.dumps({'network': addresses})

    return HttpResponse(data, status=200)


@api.api_method(http_method='GET', user_required=True, logger=log)
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
    return util.render_metadata(request, metadata, use_values=False,
                                status=200)


@api.api_method(http_method='POST', user_required=True, logger=log)
def update_metadata(request, server_id):
    # Normal Response Code: 201
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       buildInProgress (409),
    #                       badMediaType(415),
    #                       overLimit (413)

    req = utils.get_request_dict(request)
    log.info('update_server_metadata %s %s', server_id, req)
    vm = util.get_vm(server_id, request.user_uniq, non_suspended=True)
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


@api.api_method(http_method='GET', user_required=True, logger=log)
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


@api.api_method(http_method='PUT', user_required=True, logger=log)
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

    req = utils.get_request_dict(request)
    log.info('create_server_metadata_item %s %s %s', server_id, key, req)
    vm = util.get_vm(server_id, request.user_uniq, non_suspended=True)
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


@api.api_method(http_method='DELETE', user_required=True, logger=log)
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
    vm = util.get_vm(server_id, request.user_uniq, non_suspended=True)
    meta = util.get_vm_meta(vm, key)
    meta.delete()
    vm.save()
    return HttpResponse(status=204)


@api.api_method(http_method='GET', user_required=True, logger=log)
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
