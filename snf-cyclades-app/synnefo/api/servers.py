# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.conf import settings
from django.conf.urls import patterns

from django.db import transaction
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson as json

from snf_django.lib import api
from snf_django.lib.api import faults, utils

from synnefo.api import util
from synnefo.db.models import (VirtualMachine, VirtualMachineMetadata)
from synnefo.logic import servers, utils as logic_utils, server_attachments
from synnefo.volume.util import get_volume

from logging import getLogger
log = getLogger(__name__)

urlpatterns = patterns(
    'synnefo.api.servers',
    (r'^(?:/|.json|.xml)?$', 'demux'),
    (r'^/detail(?:.json|.xml)?$', 'list_servers', {'detail': True}),
    (r'^/(\d+)(?:.json|.xml)?$', 'server_demux'),
    (r'^/(\d+)/action(?:.json|.xml)?$', 'demux_server_action'),
    (r'^/(\d+)/ips(?:.json|.xml)?$', 'list_addresses'),
    (r'^/(\d+)/ips/(.+?)(?:.json|.xml)?$', 'list_addresses_by_network'),
    (r'^/(\d+)/metadata(?:.json|.xml)?$', 'metadata_demux'),
    (r'^/(\d+)/metadata/(.+?)(?:.json|.xml)?$', 'metadata_item_demux'),
    (r'^/(\d+)/stats(?:.json|.xml)?$', 'server_stats'),
    (r'^/(\d+)/diagnostics(?:.json)?$', 'get_server_diagnostics'),
    (r'^/(\d+)/os-volume_attachments(?:.json)?$', 'demux_volumes'),
    (r'^/(\d+)/os-volume_attachments/(\d+)(?:.json)?$', 'demux_volumes_item'),
)

VOLUME_SOURCE_TYPES = [
    "image",
    "volume",
    "blank"
]

if settings.CYCLADES_SNAPSHOTS_ENABLED:
    # If snapshots are enabled, add 'snapshot' to the list of allowed sources
    # for a new block device.
    VOLUME_SOURCE_TYPES.append("snapshot")


def demux(request):
    if request.method == 'GET':
        return list_servers(request)
    elif request.method == 'POST':
        return create_server(request)
    else:
        return api.api_method_not_allowed(request,
                                          allowed_methods=['GET', 'POST'])


def server_demux(request, server_id):
    if request.method == 'GET':
        return get_server_details(request, server_id)
    elif request.method == 'PUT':
        return update_server_name(request, server_id)
    elif request.method == 'DELETE':
        return delete_server(request, server_id)
    else:
        return api.api_method_not_allowed(request,
                                          allowed_methods=['GET',
                                                           'PUT',
                                                           'DELETE'])


def metadata_demux(request, server_id):
    if request.method == 'GET':
        return list_metadata(request, server_id)
    elif request.method == 'POST':
        return update_metadata(request, server_id)
    else:
        return api.api_method_not_allowed(request,
                                          allowed_methods=['GET', 'POST'])


def metadata_item_demux(request, server_id, key):
    if request.method == 'GET':
        return get_metadata_item(request, server_id, key)
    elif request.method == 'PUT':
        return create_metadata_item(request, server_id, key)
    elif request.method == 'DELETE':
        return delete_metadata_item(request, server_id, key)
    else:
        return api.api_method_not_allowed(request,
                                          allowed_methods=['GET',
                                                           'PUT',
                                                           'DELETE'])


def demux_volumes(request, server_id):
    if request.method == 'GET':
        return get_volumes(request, server_id)
    elif request.method == 'POST':
        return attach_volume(request, server_id)
    else:
        return api.api_method_not_allowed(request,
                                          allowed_methods=['GET', 'POST'])


def demux_volumes_item(request, server_id, volume_id):
    if request.method == 'GET':
        return get_volume_info(request, server_id, volume_id)
    elif request.method == 'DELETE':
        return detach_volume(request, server_id, volume_id)
    else:
        return api.api_method_not_allowed(request,
                                          allowed_methods=['GET', 'DELETE'])


def nic_to_attachments(nic):
    """Convert a NIC object to 'attachments attribute.

    Convert a NIC object to match the format of 'attachments' attribute of the
    response to the /servers API call.

    NOTE: The 'ips' of the NIC object have been prefetched in order to avoid DB
    queries. No subsequent queries for 'ips' (like filtering) should be
    performed because this will return in a new DB query.

    """
    d = {'id': nic.id,
         'network_id': str(nic.network_id),
         'mac_address': nic.mac,
         'ipv4': '',
         'ipv6': ''}

    if nic.firewall_profile:
        d['firewallProfile'] = nic.firewall_profile

    for ip in nic.ips.all():
        if not ip.deleted:
            ip_type = "floating" if ip.floating_ip else "fixed"
            if ip.ipversion == 4:
                d["ipv4"] = ip.address
                d["OS-EXT-IPS:type"] = ip_type
            else:
                d["ipv6"] = ip.address
                d["OS-EXT-IPS:type"] = ip_type
    return d


def attachments_to_addresses(attachments):
    """Convert 'attachments' attribute to 'addresses'.

    Convert a a list of 'attachments' attribute to a list of 'addresses'
    attribute, as expected in the response to /servers API call.

    """
    addresses = {}
    for nic in attachments:
        net_addrs = []
        if nic["ipv4"]:
            net_addrs.append({"version": 4,
                              "addr": nic["ipv4"],
                              "OS-EXT-IPS:type": nic["OS-EXT-IPS:type"]})
        if nic["ipv6"]:
            net_addrs.append({"version": 6,
                              "addr": nic["ipv6"],
                              "OS-EXT-IPS:type": nic["OS-EXT-IPS:type"]})
        addresses[nic["network_id"]] = net_addrs
    return addresses


def vm_to_dict(vm, detail=False):
    d = dict(id=vm.id, name=vm.name)
    d['links'] = util.vm_to_links(vm.id)
    if detail:
        d['user_id'] = vm.userid
        d['tenant_id'] = vm.project
        d['status'] = logic_utils.get_rsapi_state(vm)
        d['SNF:task_state'] = logic_utils.get_task_state(vm)
        d['progress'] = 100 if d['status'] == 'ACTIVE' else vm.buildpercentage
        d['hostId'] = vm.hostid
        d['updated'] = utils.isoformat(vm.updated)
        d['created'] = utils.isoformat(vm.created)
        d['flavor'] = {"id": vm.flavor_id,
                       "links": util.flavor_to_links(vm.flavor_id)}
        d['image'] = {"id": vm.imageid,
                      "links": util.image_to_links(vm.imageid)}
        d['suspended'] = vm.suspended

        metadata = dict((m.meta_key, m.meta_value) for m in vm.metadata.all())
        d['metadata'] = metadata

        nics = vm.nics.all()
        active_nics = filter(lambda nic: nic.state == "ACTIVE", nics)
        active_nics.sort(key=lambda nic: nic.id)
        attachments = map(nic_to_attachments, active_nics)
        d['attachments'] = attachments
        d['addresses'] = attachments_to_addresses(attachments)

        d['volumes'] = [v.id for v in vm.volumes.order_by('id')]

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
        fqdn = get_server_fqdn(vm, active_nics)
        d["SNF:fqdn"] = fqdn
        d["SNF:port_forwarding"] = get_server_port_forwarding(vm, active_nics,
                                                              fqdn)
        d['deleted'] = vm.deleted
    return d


def get_server_public_ip(vm_nics, version=4):
    """Get the first public IP address of a server.

    NOTE: 'vm_nics' objects have prefetched the ips
    """
    for nic in vm_nics:
        for ip in nic.ips.all():
            if nic.public and ip.ipversion == version:
                return ip
    return None


def get_server_fqdn(vm, vm_nics):
    fqdn_setting = settings.CYCLADES_SERVERS_FQDN
    if fqdn_setting is None:
        return None
    elif isinstance(fqdn_setting, basestring):
        return fqdn_setting % {"id": vm.id}
    else:
        msg = ("Invalid setting: CYCLADES_SERVERS_FQDN."
               " Value must be a string.")
        raise faults.InternalServerError(msg)


def get_server_port_forwarding(vm, vm_nics, fqdn):
    """Create API 'port_forwarding' attribute from corresponding setting.

    Create the 'port_forwarding' API vm attribute based on the corresponding
    setting (CYCLADES_PORT_FORWARDING), which can be either a tuple
    of the form (host, port) or a callable object returning such tuple. In
    case of callable object, must be called with the following arguments:
    * ip_address
    * server_id
    * fqdn
    * owner UUID

    NOTE: 'vm_nics' objects have prefetched the ips
    """
    port_forwarding = {}
    public_ip = get_server_public_ip(vm_nics)
    if public_ip is None:
        return port_forwarding
    for dport, to_dest in settings.CYCLADES_PORT_FORWARDING.items():
        if hasattr(to_dest, "__call__"):
            to_dest = to_dest(public_ip.address, vm.id, fqdn, vm.userid)
        msg = ("Invalid setting: CYCLADES_PORT_FOWARDING."
               " Value must be a tuple of two elements (host, port).")
        if not isinstance(to_dest, tuple) or len(to_dest) != 2:
                raise faults.InternalServerError(msg)
        else:
            try:
                host, port = to_dest
            except (TypeError, ValueError):
                raise faults.InternalServerError(msg)

        port_forwarding[dport] = {"host": host, "port": str(port)}
    return port_forwarding


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
    if detail:
        user_vms = user_vms.prefetch_related("nics__ips", "metadata")

    user_vms = utils.filter_modified_since(request, objects=user_vms)

    servers_dict = [vm_to_dict(server, detail)
                    for server in user_vms.order_by('id')]

    if request.serialization == 'xml':
        data = render_to_string('list_servers.xml', {
            'servers': servers_dict,
            'detail': detail})
    else:
        data = json.dumps({'servers': servers_dict})

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
    req = utils.get_json_body(request)
    user_id = request.user_uniq
    log.info('create_server user: %s request: %s', user_id, req)

    try:
        server = req['server']
        name = server['name']
        metadata = server.get('metadata', {})
        assert isinstance(metadata, dict)
        image_id = server['imageRef']
        flavor_id = server['flavorRef']
        personality = server.get('personality', [])
        assert isinstance(personality, list)
        networks = server.get("networks")
        if networks is not None:
            assert isinstance(networks, list)
        project = server.get("project")
    except (KeyError, AssertionError):
        raise faults.BadRequest("Malformed request")

    volumes = None
    dev_map = server.get("block_device_mapping_v2")
    if dev_map is not None:
        volumes = parse_block_device_mapping(dev_map)

    # Verify that personalities are well-formed
    util.verify_personality(personality)
    # Get flavor (ensure it is active)
    flavor = util.get_flavor(flavor_id, include_deleted=False)
    if not flavor.allow_create:
        msg = ("It is not allowed to create a server from flavor with id '%d',"
               " see 'allow_create' flavor attribute")
        raise faults.Forbidden(msg % flavor.id)
    # Generate password
    password = util.random_password()

    vm = servers.create(user_id, name, password, flavor, image_id,
                        metadata=metadata, personality=personality,
                        project=project, networks=networks, volumes=volumes)

    server = vm_to_dict(vm, detail=True)
    server['status'] = 'BUILD'
    server['adminPass'] = password

    response = render_server(request, server, status=202)

    return response


def parse_block_device_mapping(dev_map):
    """Parse 'block_device_mapping_v2' attribute"""
    if not isinstance(dev_map, list):
        raise faults.BadRequest("Block Device Mapping is Invalid")
    return [_parse_block_device(device) for device in dev_map]


def _parse_block_device(device):
    """Parse and validate a block device mapping"""
    if not isinstance(device, dict):
        raise faults.BadRequest("Block Device Mapping is Invalid")

    # Validate source type
    source_type = device.get("source_type")
    if source_type is None:
        raise faults.BadRequest("Block Device Mapping is Invalid: Invalid"
                                " source_type field")
    elif source_type not in VOLUME_SOURCE_TYPES:
        raise faults.BadRequest("Block Device Mapping is Invalid: source_type"
                                " must be on of %s"
                                % ", ".join(VOLUME_SOURCE_TYPES))

    # Validate source UUID
    uuid = device.get("uuid")
    if uuid is None and source_type != "blank":
        raise faults.BadRequest("Block Device Mapping is Invalid: uuid of"
                                " %s is missing" % source_type)

    # Validate volume size
    size = device.get("volume_size")
    if size is not None:
        try:
            size = int(size)
        except (TypeError, ValueError):
            raise faults.BadRequest("Block Device Mapping is Invalid: Invalid"
                                    " size field")

    # Validate 'delete_on_termination'
    delete_on_termination = device.get("delete_on_termination")
    if delete_on_termination is not None:
        if not isinstance(delete_on_termination, bool):
            raise faults.BadRequest("Block Device Mapping is Invalid: Invalid"
                                    " delete_on_termination field")
    else:
        if source_type == "volume":
            delete_on_termination = False
        else:
            delete_on_termination = True

    # Unused API Attributes
    # boot_index = device.get("boot_index")
    # destination_type = device.get("destination_type")

    return {"source_type": source_type,
            "source_uuid": uuid,
            "size": size,
            "delete_on_termination": delete_on_termination}


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
    vm = util.get_vm(server_id, request.user_uniq,
                     prefetch_related=["nics__ips", "metadata"])
    server = vm_to_dict(vm, detail=True)
    return render_server(request, server)


@api.api_method(http_method='PUT', user_required=True, logger=log)
@transaction.commit_on_success
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

    req = utils.get_json_body(request)
    log.info('update_server_name %s %s', server_id, req)

    req = utils.get_attribute(req, "server", attr_type=dict, required=True)
    name = utils.get_attribute(req, "name", attr_type=basestring,
                               required=True)

    vm = util.get_vm(server_id, request.user_uniq, for_update=True,
                     non_suspended=True, non_deleted=True)

    servers.rename(vm, new_name=name)

    return HttpResponse(status=204)


@api.api_method(http_method='DELETE', user_required=True, logger=log)
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
                     non_suspended=True, non_deleted=True)
    vm = servers.destroy(vm)
    return HttpResponse(status=204)


# additional server actions
ARBITRARY_ACTIONS = ['console', 'firewallProfile', 'reassign']


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


@api.api_method(http_method='POST', user_required=True, logger=log)
@transaction.commit_on_success
def demux_server_action(request, server_id):
    req = utils.get_json_body(request)
    log.debug('server_action %s %s', server_id, req)

    if not isinstance(req, dict) and len(req) != 1:
        raise faults.BadRequest("Malformed request")

    # Do not allow any action on deleted or suspended VMs
    vm = util.get_vm(server_id, request.user_uniq, for_update=True,
                     non_deleted=True, non_suspended=True)

    action = req.keys()[0]
    if not isinstance(action, basestring):
        raise faults.BadRequest("Malformed Request. Invalid action.")

    if key_to_action(action) not in [x[0] for x in VirtualMachine.ACTIONS]:
        if action not in ARBITRARY_ACTIONS:
            raise faults.BadRequest("Action %s not supported" % action)
    action_args = utils.get_attribute(req, action, required=True,
                                      attr_type=dict)

    return server_actions[action](request, vm, action_args)


@api.api_method(http_method='GET', user_required=True, logger=log)
def list_addresses(request, server_id):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       overLimit (413)

    log.debug('list_addresses %s', server_id)
    vm = util.get_vm(server_id, request.user_uniq,
                     prefetch_related="nics__ips")
    attachments = [nic_to_attachments(nic)
                   for nic in vm.nics.filter(state="ACTIVE")]
    addresses = attachments_to_addresses(attachments)

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
    nics = machine.nics.filter(network=network, state="ACTIVE")
    addresses = attachments_to_addresses(map(nic_to_attachments, nics))

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
@transaction.commit_on_success
def update_metadata(request, server_id):
    # Normal Response Code: 201
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       buildInProgress (409),
    #                       badMediaType(415),
    #                       overLimit (413)

    req = utils.get_json_body(request)
    log.info('update_server_metadata %s %s', server_id, req)
    vm = util.get_vm(server_id, request.user_uniq, non_suspended=True,
                     non_deleted=True)
    metadata = utils.get_attribute(req, "metadata", required=True,
                                   attr_type=dict)

    for key, val in metadata.items():
        if not isinstance(key, (basestring, int)) or\
           not isinstance(val, (basestring, int)):
            raise faults.BadRequest("Malformed Request. Invalid metadata.")
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

    req = utils.get_json_body(request)
    log.info('create_server_metadata_item %s %s %s', server_id, key, req)
    vm = util.get_vm(server_id, request.user_uniq, non_suspended=True,
                     non_deleted=True)
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
    vm = util.get_vm(server_id, request.user_uniq, non_suspended=True,
                     non_deleted=True)
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
    secret = util.stats_encrypt(vm.backend_vm_id)

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


# ACTIONS


server_actions = {}
network_actions = {}


def server_action(name):
    '''Decorator for functions implementing server actions.
    `name` is the key in the dict passed by the client.
    '''

    def decorator(func):
        server_actions[name] = func
        return func
    return decorator


def network_action(name):
    '''Decorator for functions implementing network actions.
    `name` is the key in the dict passed by the client.
    '''

    def decorator(func):
        network_actions[name] = func
        return func
    return decorator


@server_action('start')
def start(request, vm, args):
    # Normal Response Code: 202
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404)
    vm = servers.start(vm)
    return HttpResponse(status=202)


@server_action('shutdown')
def shutdown(request, vm, args):
    # Normal Response Code: 202
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404)
    vm = servers.stop(vm)
    return HttpResponse(status=202)


@server_action('reboot')
def reboot(request, vm, args):
    # Normal Response Code: 202
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       buildInProgress (409),
    #                       overLimit (413)

    reboot_type = args.get("type", "SOFT")
    if reboot_type not in ["SOFT", "HARD"]:
        raise faults.BadRequest("Invalid 'type' attribute.")
    vm = servers.reboot(vm, reboot_type=reboot_type)
    return HttpResponse(status=202)


@server_action('firewallProfile')
def set_firewall_profile(request, vm, args):
    # Normal Response Code: 200
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       buildInProgress (409),
    #                       overLimit (413)
    profile = args.get("profile")
    if profile is None:
        raise faults.BadRequest("Missing 'profile' attribute")
    nic_id = args.get("nic")
    if nic_id is None:
        raise faults.BadRequest("Missing 'nic' attribute")
    nic = util.get_vm_nic(vm, nic_id)
    servers.set_firewall_profile(vm, profile=profile, nic=nic)
    return HttpResponse(status=202)


@server_action('resize')
def resize(request, vm, args):
    # Normal Response Code: 202
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       buildInProgress (409),
    #                       serverCapacityUnavailable (503),
    #                       overLimit (413),
    #                       resizeNotAllowed (403)
    flavor_id = args.get("flavorRef")
    if flavor_id is None:
        raise faults.BadRequest("Missing 'flavorRef' attribute.")
    flavor = util.get_flavor(flavor_id=flavor_id, include_deleted=False)
    servers.resize(vm, flavor=flavor)
    return HttpResponse(status=202)


@server_action('console')
def get_console(request, vm, args):
    # Normal Response Code: 200
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       buildInProgress (409),
    #                       overLimit (413)

    log.info("Get console  VM %s: %s", vm, args)

    console_type = args.get("type")
    if console_type is None:
        raise faults.BadRequest("No console 'type' specified.")
    elif console_type != "vnc":
        raise faults.BadRequest("Console 'type' can only be 'vnc'.")
    console_info = servers.console(vm, console_type)

    if request.serialization == 'xml':
        mimetype = 'application/xml'
        data = render_to_string('console.xml', {'console': console_info})
    else:
        mimetype = 'application/json'
        data = json.dumps({'console': console_info})

    return HttpResponse(data, mimetype=mimetype, status=200)


@server_action('changePassword')
def change_password(request, vm, args):
    raise faults.NotImplemented('Changing password is not supported.')


@server_action('rebuild')
def rebuild(request, vm, args):
    raise faults.NotImplemented('Rebuild not supported.')


@server_action('confirmResize')
def confirm_resize(request, vm, args):
    raise faults.NotImplemented('Resize not supported.')


@server_action('revertResize')
def revert_resize(request, vm, args):
    raise faults.NotImplemented('Resize not supported.')


@server_action('reassign')
def reassign(request, vm, args):
    project = args.get("project")
    if project is None:
        raise faults.BadRequest("Missing 'project' attribute.")
    servers.reassign(vm, project)
    return HttpResponse(status=200)


@network_action('add')
@transaction.commit_on_success
def add(request, net, args):
    # Normal Response Code: 202
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       buildInProgress (409),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       overLimit (413)
    server_id = args.get('serverRef', None)
    if not server_id:
        raise faults.BadRequest('Malformed Request.')

    vm = util.get_vm(server_id, request.user_uniq, non_suspended=True,
                     non_deleted=True)
    servers.connect(vm, network=net)
    return HttpResponse(status=202)


@network_action('remove')
@transaction.commit_on_success
def remove(request, net, args):
    # Normal Response Code: 202
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       overLimit (413)

    attachment = args.get("attachment")
    if attachment is None:
        raise faults.BadRequest("Missing 'attachment' attribute.")
    try:
        nic_id = int(attachment)
    except (ValueError, TypeError):
        raise faults.BadRequest("Invalid 'attachment' attribute.")

    nic = util.get_nic(nic_id=nic_id)
    server_id = nic.machine_id
    vm = util.get_vm(server_id, request.user_uniq, non_suspended=True,
                     non_deleted=True)

    servers.disconnect(vm, nic)

    return HttpResponse(status=202)


@server_action("addFloatingIp")
def add_floating_ip(request, vm, args):
    address = args.get("address")
    if address is None:
        raise faults.BadRequest("Missing 'address' attribute")

    userid = vm.userid
    floating_ip = util.get_floating_ip_by_address(userid, address,
                                                  for_update=True)
    servers.create_port(userid, floating_ip.network, machine=vm,
                        user_ipaddress=floating_ip)
    return HttpResponse(status=202)


@server_action("removeFloatingIp")
def remove_floating_ip(request, vm, args):
    address = args.get("address")
    if address is None:
        raise faults.BadRequest("Missing 'address' attribute")
    floating_ip = util.get_floating_ip_by_address(vm.userid, address,
                                                  for_update=True)
    if floating_ip.nic is None:
        raise faults.BadRequest("Floating IP %s not attached to instance"
                                % address)
    servers.delete_port(floating_ip.nic)
    return HttpResponse(status=202)


def volume_to_attachment(volume):
    return {"id": volume.id,
            "volumeId": volume.id,
            "serverId": volume.machine_id,
            "device": ""}  # TODO: What device to return?


@api.api_method(http_method='GET', user_required=True, logger=log)
def get_volumes(request, server_id):
    log.debug("get_volumes server_id %s", server_id)
    vm = util.get_vm(server_id, request.user_uniq, for_update=False)

    # TODO: Filter attachments!!
    volumes = vm.volumes.filter(deleted=False).order_by("id")
    attachments = [volume_to_attachment(v) for v in volumes]

    data = json.dumps({'volumeAttachments': attachments})
    return HttpResponse(data, status=200)
    pass


@api.api_method(http_method='GET', user_required=True, logger=log)
def get_volume_info(request, server_id, volume_id):
    log.debug("get_volume_info server_id %s volume_id", server_id, volume_id)
    user_id = request.user_uniq
    vm = util.get_vm(server_id, user_id)
    volume = get_volume(user_id, volume_id, for_update=False, non_deleted=True,
                        exception=faults.BadRequest)
    servers._check_attachment(vm, volume)
    attachment = volume_to_attachment(volume)
    data = json.dumps({'volumeAttachment': attachment})
    return HttpResponse(data, status=200)


@api.api_method(http_method='POST', user_required=True, logger=log)
def attach_volume(request, server_id):
    req = utils.get_json_body(request)
    log.debug("attach_volume server_id %s request", server_id, req)
    user_id = request.user_uniq
    vm = util.get_vm(server_id, user_id, for_update=True, non_deleted=True)

    attachment_dict = api.utils.get_attribute(req, "volumeAttachment",
                                              required=True)
    # Get volume
    volume_id = api.utils.get_attribute(attachment_dict, "volumeId")
    volume = get_volume(user_id, volume_id, for_update=True, non_deleted=True,
                        exception=faults.BadRequest)
    vm = server_attachments.attach_volume(vm, volume)
    attachment = volume_to_attachment(volume)
    data = json.dumps({'volumeAttachment': attachment})

    return HttpResponse(data, status=202)


@api.api_method(http_method='DELETE', user_required=True, logger=log)
def detach_volume(request, server_id, volume_id):
    log.debug("detach_volume server_id %s volume_id", server_id, volume_id)
    user_id = request.user_uniq
    vm = util.get_vm(server_id, user_id, non_deleted=True)
    volume = get_volume(user_id, volume_id, for_update=True, non_deleted=True,
                        exception=faults.BadRequest)
    vm = server_attachments.detach_volume(vm, volume)
    # TODO: Check volume state, send job to detach volume
    return HttpResponse(status=202)
