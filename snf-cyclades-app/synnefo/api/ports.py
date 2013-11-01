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

#from django.conf import settings
import ipaddr
from django.conf.urls import patterns
from django.http import HttpResponse
from django.utils import simplejson as json
from django.db import transaction
from django.template.loader import render_to_string

from snf_django.lib import api
from snf_django.lib.api import faults

from synnefo.api import util
from synnefo.db.models import NetworkInterface
from synnefo.logic import servers

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
        return api.api_method_not_allowed(request)


def port_demux(request, port_id):

    if request.method == 'GET':
        return get_port_details(request, port_id)
    elif request.method == 'DELETE':
        return delete_port(request, port_id)
    elif request.method == 'PUT':
        return update_port(request, port_id)
    else:
        return api.api_method_not_allowed(request)


@api.api_method(http_method='GET', user_required=True, logger=log)
def list_ports(request, detail=False):

    log.debug('list_ports detail=%s', detail)

    user_ports = NetworkInterface.objects.filter(
        machine__userid=request.user_uniq)

    port_dicts = [port_to_dict(port, detail)
                  for port in user_ports.order_by('id')]

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
    req = api.utils.get_request_dict(request)
    log.info('create_port %s', req)

    port_dict = api.utils.get_attribute(req, "port")
    net_id = api.utils.get_attribute(port_dict, "network_id")

    network = util.get_network(net_id, user_id, non_deleted=True)

    # Check if the request contains a valid IPv4 address
    fixed_ips = api.utils.get_attribute(port_dict, "fixed_ips", required=False)
    if fixed_ips is not None and len(fixed_ips) > 0:
        if len(fixed_ips) > 1:
            msg = "'fixed_ips' attribute must contain only one fixed IP."
            raise faults.BadRequest(msg)
        fixed_ip_address = fixed_ips[0].get("ip_address")
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

    ipaddress = None
    if network.public:
        # Creating a port to a public network is only allowed if the user has
        # already a floating IP address in this network which is specified
        # as the fixed IP address of the port
        if fixed_ip_address is None:
            msg = ("'fixed_ips' attribute must contain a floating IP address"
                   " in order to connect to a public network.")
            raise faults.BadRequest(msg)
        ipaddress = util.get_floating_ip_by_address(user_id, fixed_ip_address,
                                                    for_update=True)
    elif fixed_ip_address:
        ipaddress = util.allocate_ip(network, user_id,
                                     address=fixed_ip_address)

    device_id = api.utils.get_attribute(port_dict, "device_id", required=False)
    vm = None
    if device_id is not None:
        vm = util.get_vm(device_id, user_id, for_update=True, non_deleted=True,
                         non_suspended=True)

    name = api.utils.get_attribute(port_dict, "name", required=False)
    if name is None:
        name = ""

    security_groups = api.utils.get_attribute(port_dict,
                                              "security_groups",
                                              required=False)
    #validate security groups
    # like get security group from db
    sg_list = []
    if security_groups:
        for gid in security_groups:
            sg = util.get_security_group(int(gid))
            sg_list.append(sg)

    new_port = servers.create_port(user_id, network, use_ipaddress=ipaddress,
                                   machine=vm)

    response = render_port(request, port_to_dict(new_port), status=201)

    return response


@api.api_method(http_method='GET', user_required=True, logger=log)
def get_port_details(request, port_id):
    log.debug('get_port_details %s', port_id)
    port = util.get_port(port_id, request.user_uniq)
    return render_port(request, port_to_dict(port))


@api.api_method(http_method='PUT', user_required=True, logger=log)
def update_port(request, port_id):
    '''
    You can update only name, security_groups
    '''
    port = util.get_port(port_id, request.user_uniq, for_update=True)
    req = api.utils.get_request_dict(request)

    port_info = api.utils.get_attribute(req, "port", required=True)
    name = api.utils.get_attribute(port_info, "name", required=False)

    if name:
        port.name = name

    security_groups = api.utils.get_attribute(port_info, "security_groups",
                                              required=False)
    if security_groups:
        sg_list = []
        #validate security groups
        for gid in security_groups:
            sg = util.get_security_group(int(gid))
            sg_list.append(sg)

        #clear the old security groups
        port.security_groups.clear()

        #add the new groups
        port.security_groups.add(*sg_list)

    port.save()
    return render_port(request, port_to_dict(port), 200)


@api.api_method(http_method='DELETE', user_required=True, logger=log)
@transaction.commit_on_success
def delete_port(request, port_id):
    log.info('delete_port %s', port_id)
    user_id = request.user_uniq
    port = util.get_port(port_id, user_id, for_update=True)
    servers.delete_port(port)
    return HttpResponse(status=204)

#util functions


def port_to_dict(port, detail=True):
    d = {'id': str(port.id), 'name': port.name}
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
        d['network_id'] = str(port.network.id)
        d['updated'] = api.utils.isoformat(port.updated)
        d['created'] = api.utils.isoformat(port.created)
        d['fixed_ips'] = []
        for ip in port.ips.all():
            d['fixed_ips'].append({"ip_address": ip.address,
                                   "subnet": str(ip.subnet.id)})
        sg_list = list(port.security_groups.values_list('id', flat=True))
        d['security_groups'] = map(str, sg_list)

    return d


def render_port(request, portdict, status=200):
    if request.serialization == 'xml':
        data = render_to_string('port.xml', {'port': portdict})
    else:
        data = json.dumps({'port': portdict})
    return HttpResponse(data, status=status)
