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

from logging import getLogger
from snf_django.lib import api

from django.conf.urls import patterns
from django.http import HttpResponse
from django.utils import simplejson as json
from django.db.models import Q

from snf_django.lib.api import utils
from synnefo.db.models import Subnet
from synnefo.logic import subnets
from synnefo.api import util

import ipaddr

log = getLogger(__name__)


urlpatterns = patterns(
    'synnefo.api.subnets',
    (r'^(?:/|.json|.xml)?$', 'demux'),
    (r'^/detail(?:.json|.xml)?$', 'list_subnets', {'detail': True}),
    (r'^/([-\w]+)(?:/|.json|.xml)?$', 'subnet_demux'))


def demux(request):
    if request.method == 'GET':
        return list_subnets(request)
    elif request.method == 'POST':
        return create_subnet(request)
    else:
        return api.api_method_not_allowed(request, allowed_methods=['GET',
                                                                    'POST'])


def subnet_demux(request, sub_id):
    if request.method == 'GET':
        return get_subnet(request, sub_id)
    elif request.method == 'DELETE':
        return delete_subnet(request, sub_id)
    elif request.method == 'PUT':
        return update_subnet(request, sub_id)
    else:
        return api.api_method_not_allowed(request, allowed_methods=['GET',
                                                                    'DELETE',
                                                                    'PUT'])


@api.api_method(http_method='GET', user_required=True, logger=log)
def list_subnets(request, detail=True):
    """List all subnets of a user"""

    subnets_list = Subnet.objects.for_user(request.user_uniq,
                                           request.user_projects,
                                           public=True).order_by('id')
    subnets_list = subnets_list.prefetch_related("ip_pools")

    subnets_list = api.utils.filter_modified_since(request,
                                                   objects=subnets_list)

    subnets_dict = [subnet_to_dict(sub) for sub in subnets_list]

    data = json.dumps({'subnets': subnets_dict})

    return HttpResponse(data, status=200)


@api.api_method(http_method='POST', user_required=True, logger=log)
def create_subnet(request):
    """Create a subnet
    network_id and the desired cidr are mandatory, everything else is optional

    """
    dictionary = utils.get_json_body(request)
    user_id = request.user_uniq
    log.info('create subnet user: %s request: %s', user_id, dictionary)

    try:
        subnet = dictionary['subnet']
        network_id = subnet['network_id']
        cidr = subnet['cidr']
    except KeyError:
        raise api.faults.BadRequest("Malformed request")

    name = subnet.get('name', None)
    ipversion = subnet.get('ip_version', 4)

    allocation_pools = subnet.get('allocation_pools', None)
    if allocation_pools is not None:
        allocation_pools = parse_ip_pools(allocation_pools)

    try:
        cidr_ip = ipaddr.IPNetwork(cidr)
    except ValueError:
        raise api.faults.BadRequest("Malformed CIDR '%s'" % cidr)

    # If no gateway is specified, send an empty string, because None is used
    # if the user wants no gateway at all
    gateway = subnet.get('gateway_ip', "")
    if gateway is "":
        gateway = str(cidr_ip.network + 1)

    dhcp = subnet.get('enable_dhcp', True)
    slaac = subnet.get('enable_slaac', None)

    if ipversion == 6:
        if slaac is not None:
            dhcp = check_boolean_value(slaac, "enable_slaac")
        else:
            dhcp = check_boolean_value(dhcp, "dhcp")
    else:
        dhcp = check_boolean_value(dhcp, "dhcp")

    dns = subnet.get('dns_nameservers', None)
    hosts = subnet.get('host_routes', None)

    sub = subnets.create_subnet(network_id=network_id,
                                cidr=cidr,
                                name=name,
                                ipversion=ipversion,
                                gateway=gateway,
                                dhcp=dhcp,
                                slaac=slaac,
                                dns_nameservers=dns,
                                allocation_pools=allocation_pools,
                                host_routes=hosts,
                                user_id=user_id)

    subnet_dict = subnet_to_dict(sub)
    data = json.dumps({'subnet': subnet_dict})
    return HttpResponse(data, status=201)


@api.api_method(http_method='GET', user_required=True, logger=log)
def get_subnet(request, sub_id):
    """Show info of a specific subnet"""
    user_id = request.user_uniq
    subnet = subnets.get_subnet(sub_id, user_id, request.user_projects)

    subnet_dict = subnet_to_dict(subnet)
    data = json.dumps({'subnet': subnet_dict})
    return HttpResponse(data, status=200)


@api.api_method(http_method='DELETE', user_required=True, logger=log)
def delete_subnet(request, sub_id):
    """Delete a subnet, raises BadRequest
    A subnet is deleted ONLY when the network that it belongs to is deleted

    """
    raise api.faults.BadRequest("Deletion of a subnet is not supported")


@api.api_method(http_method='PUT', user_required=True, logger=log)
def update_subnet(request, sub_id):
    """Update the fields of a subnet
    Only the name can be updated, everything else returns BadRequest

    """

    dictionary = utils.get_json_body(request)
    user_id = request.user_uniq

    try:
        subnet = dictionary['subnet']
    except KeyError:
        raise api.faults.BadRequest("Malformed request")

    if len(subnet) != 1 or "name" not in subnet:
        raise api.faults.BadRequest("Only the name of a subnet can be updated")

    name = subnet.get("name", None)

    subnet_dict = subnet_to_dict(subnets.update_subnet(sub_id, name, user_id))
    data = json.dumps({'subnet': subnet_dict})
    return HttpResponse(data, status=200)


#Utility functions
def subnet_to_dict(subnet):
    """Returns a dictionary containing the info of a subnet"""
    dns = check_empty_lists(subnet.dns_nameservers)
    hosts = check_empty_lists(subnet.host_routes)

    allocation_pools = [render_ip_pool(pool)
                        for pool in subnet.ip_pools.all()]

    d = {'id': str(subnet.id),
         'network_id': str(subnet.network_id),
         'name': subnet.name if subnet.name is not None else "",
         'tenant_id': subnet.userid,
         'user_id': subnet.userid,
         'public': subnet.public,
         'gateway_ip': subnet.gateway,
         'ip_version': subnet.ipversion,
         'cidr': subnet.cidr,
         'enable_dhcp': subnet.dhcp,
         'dns_nameservers': dns,
         'host_routes': hosts,
         'allocation_pools': allocation_pools,
         'deleted': subnet.deleted}

    if subnet.ipversion == 6:
        d['enable_slaac'] = subnet.dhcp

    d['links'] = util.subnet_to_links(subnet.id)

    return d


def render_ip_pool(pool):
    network = ipaddr.IPNetwork(pool.base).network
    start = str(network + pool.offset)
    end = str(network + pool.offset + pool.size - 1)
    return {"start": start, "end": end}


def parse_ip_pools(pools):
    """Convert [{'start': '192.168.42.1', 'end': '192.168.42.15'},
             {'start': '192.168.42.30', 'end': '192.168.42.60'}]
    to
            [(IPv4Address("192.168.42.1"), IPv4Address("192.168.42.15")),
             (IPv4Address("192.168.42.30"), IPv4Address("192.168.42.60"))]

    """
    try:
        return sorted([(ipaddr.IPv4Address(p["start"]),
                        ipaddr.IPv4Address(p["end"])) for p in pools])
    except KeyError:
        raise api.faults.BadRequest("Malformed allocation pool.")
    except ipaddr.AddressValueError:
        raise api.faults.BadRequest("Allocation pools contain invalid IPv4"
                                    " address")


def check_empty_lists(value):
    """Check if value is Null/None, in which case we return an empty list"""
    if value is None:
        return []
    return value


def check_boolean_value(value, key):
    """Check if dhcp value is in acceptable values"""
    if value not in [True, False]:
        raise api.faults.BadRequest("Malformed request, %s must "
                                    "be True or False" % key)
    return value
