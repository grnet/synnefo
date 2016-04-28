# Copyright (C) 2010-2015 GRNET S.A. and individual contributors
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

#from django.conf import settings
import ipaddr
from django.conf.urls import patterns
from django.http import HttpResponse
from django.utils import simplejson as json
from synnefo.db import transaction
from django.template.loader import render_to_string

from snf_django.lib import api
from snf_django.lib.api import faults

from synnefo.api import util
from synnefo.db.models import NetworkInterface
from synnefo.logic import servers, ips

from logging import getLogger

log = getLogger(__name__)

urlpatterns = patterns(
    'synnefo.api.ports',
    (r'^(?:/|.json|.xml)?$', 'demux'),
    (r'^/detail(?:.json|.xml)?$', 'list_ports', {'detail': True}),
    (r'^/([-\w]+)(?:/|.json|.xml)?$', 'port_demux'))


def demux(request):
    if request.method == 'GET':
        return list_ports(request)
    elif request.method == 'POST':
        return create_port(request)
    else:
        return api.api_method_not_allowed(request, allowed_methods=['GET',
                                                                    'POST'])


def port_demux(request, port_id):

    if request.method == 'GET':
        return get_port_details(request, port_id)
    elif request.method == 'DELETE':
        return delete_port(request, port_id)
    elif request.method == 'PUT':
        return update_port(request, port_id)
    else:
        return api.api_method_not_allowed(request, allowed_methods=['GET',
                                                                    'DELETE',
                                                                    'PUT'])


@api.api_method(http_method='GET', user_required=True, logger=log)
def list_ports(request, detail=True):
    ports = NetworkInterface.objects.for_user(userid=request.user_uniq,
                                              projects=request.user_projects)
    if detail:
        ports = ports.prefetch_related("ips")

    port_dicts = [port_to_dict(port, detail)
                  for port in ports.order_by('id')]

    if request.serialization == 'xml':
        data = render_to_string('list_ports.xml', {
            "ports": port_dicts})
    else:
        data = json.dumps({'ports': port_dicts})

    return HttpResponse(data, status=200)


@api.api_method(http_method='POST', user_required=True, logger=log)
@transaction.commit_on_success
def create_port(request):
    user_id = request.user_uniq
    req = api.utils.get_json_body(request)

    log.debug("User: %s, Action: create_port, Request: %s",
              user_id, req)

    port_dict = api.utils.get_attribute(req, "port", attr_type=dict)
    net_id = api.utils.get_attribute(port_dict, "network_id",
                                     attr_type=(basestring, int))

    device_id = api.utils.get_attribute(port_dict, "device_id", required=False,
                                        attr_type=(basestring, int))
    vm = None
    if device_id is not None:
        vm = util.get_vm(device_id, user_id, request.user_projects,
                         for_update=True, non_deleted=True, non_suspended=True)

    # Check if the request contains a valid IPv4 address
    fixed_ips = api.utils.get_attribute(port_dict, "fixed_ips", required=False,
                                        attr_type=list)
    if fixed_ips is not None and len(fixed_ips) > 0:
        if len(fixed_ips) > 1:
            msg = "'fixed_ips' attribute must contain only one fixed IP."
            raise faults.BadRequest(msg)
        fixed_ip = fixed_ips[0]
        if not isinstance(fixed_ip, dict):
            raise faults.BadRequest("Invalid 'fixed_ips' field.")
        fixed_ip_address = fixed_ip.get("ip_address")
        if fixed_ip_address is not None:
            try:
                ip = ipaddr.IPAddress(fixed_ip_address)
                if ip.version == 6:
                    msg = "'ip_address' can be only an IPv4 address'"
                    raise faults.BadRequest(msg)
            except ValueError:
                msg = "%s is not a valid IPv4 Address" % fixed_ip_address
                raise faults.BadRequest(msg)
    else:
        fixed_ip_address = None

    network = util.get_network(net_id, user_id, request.user_projects,
                               non_deleted=True, for_update=True)

    ipaddress = None
    if network.public:
        # Creating a port to a public network is only allowed if the user has
        # already a floating IP address in this network which is specified
        # as the fixed IP address of the port
        if fixed_ip_address is None:
            msg = ("'fixed_ips' attribute must contain a floating IP address"
                   " in order to connect to a public network.")
            raise faults.BadRequest(msg)
        ipaddress = util.get_floating_ip_by_address(user_id,
                                                    request.user_projects,
                                                    fixed_ip_address,
                                                    for_update=True)
    elif fixed_ip_address:
        ipaddress = ips.allocate_ip(network, user_id,
                                    address=fixed_ip_address)

    name = api.utils.get_attribute(port_dict, "name", required=False,
                                   attr_type=basestring)
    if name is None:
        name = ""

    security_groups = api.utils.get_attribute(port_dict,
                                              "security_groups",
                                              required=False,
                                              attr_type=list)
    #validate security groups
    # like get security group from db
    sg_list = []
    if security_groups:
        for gid in security_groups:
            try:
                sg = util.get_security_group(int(gid))
            except (KeyError, ValueError):
                raise faults.BadRequest("Invalid 'security_groups' field.")
            sg_list.append(sg)

    new_port = servers.create_port(user_id, network, use_ipaddress=ipaddress,
                                   machine=vm, name=name)

    log.info("User %s created port %s, network: %s, machine: %s, ip: %s",
             user_id, new_port.id, network, vm, ipaddress)

    response = render_port(request, port_to_dict(new_port), status=201)

    return response


@api.api_method(http_method='GET', user_required=True, logger=log)
def get_port_details(request, port_id):
    port = util.get_port(port_id, request.user_uniq, request.user_projects)
    return render_port(request, port_to_dict(port))


@api.api_method(http_method='PUT', user_required=True, logger=log)
def update_port(request, port_id):
    '''
    You can update only name, security_groups
    '''
    port = util.get_port(port_id, request.user_uniq, request.user_projects,
                         for_update=True)
    req = api.utils.get_json_body(request)

    log.debug("User %s, Port %s, Action: update, Request: %s",
              request.user_uniq, port_id, req)

    port_info = api.utils.get_attribute(req, "port", required=True,
                                        attr_type=dict)
    name = api.utils.get_attribute(port_info, "name", required=False,
                                   attr_type=basestring)

    if name:
        port.name = name

    security_groups = api.utils.get_attribute(port_info, "security_groups",
                                              required=False, attr_type=list)

    if security_groups:
        sg_list = []
        #validate security groups
        for gid in security_groups:
            try:
                sg = util.get_security_group(int(gid))
            except (KeyError, ValueError):
                raise faults.BadRequest("Invalid 'security_groups' field.")
            sg_list.append(sg)

        #clear the old security groups
        port.security_groups.clear()

        #add the new groups
        port.security_groups.add(*sg_list)
    port.save()

    log.info("User %s updated port %s", request.user_uniq, port.id)

    return render_port(request, port_to_dict(port), 200)


@api.api_method(http_method='DELETE', user_required=True, logger=log)
@transaction.commit_on_success
def delete_port(request, port_id):
    log.info('delete_port %s', port_id)
    user_id = request.user_uniq
    port = util.get_port(port_id, user_id, request.user_projects,
                         for_update=True)

    # Deleting port that is connected to a public network is allowed only if
    # the port has an associated floating IP address.
    if port.network.public and not port.ips.filter(floating_ip=True,
                                                   deleted=False).exists():
        raise faults.Forbidden("Cannot disconnect from public network.")

    vm = port.machine
    if vm is not None and vm.suspended:
        raise faults.Forbidden("Administratively Suspended VM.")

    servers.delete_port(port)

    log.info("User %s deleted port %s", user_id, port_id)

    return HttpResponse(status=204)

#util functions


def port_to_dict(port, detail=True):
    d = {'id': str(port.id), 'name': port.name}
    d['links'] = util.port_to_links(port.id)
    if detail:
        user_id = port.userid
        machine_id = port.machine_id
        d['user_id'] = user_id
        d['tenant_id'] = user_id
        d['device_id'] = str(machine_id) if machine_id else None
        # TODO: Change this based on the status of VM
        d['admin_state_up'] = True
        d['mac_address'] = port.mac
        d['status'] = port.state
        d['device_owner'] = port.device_owner
        d['network_id'] = str(port.network_id)
        d['updated'] = api.utils.isoformat(port.updated)
        d['created'] = api.utils.isoformat(port.created)
        d['fixed_ips'] = []
        for ip in port.ips.all():
            d['fixed_ips'].append({"ip_address": ip.address,
                                   "subnet": str(ip.subnet_id)})
        # Avoid extra queries until security groups are implemented!
        #sg_list = list(port.security_groups.values_list('id', flat=True))
        d['security_groups'] = []

    return d


def render_port(request, portdict, status=200):
    if request.serialization == 'xml':
        data = render_to_string('port.xml', {'port': portdict})
    else:
        data = json.dumps({'port': portdict})
    return HttpResponse(data, status=status)
