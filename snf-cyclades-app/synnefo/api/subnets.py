# Copyright 2013 GRNET S.A. All rights reserved.
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

from logging import getLogger
from snf_django.lib import api
from snf_django.lib.api import faults

from django.conf.urls import patterns
from django.http import HttpResponse
from django.utils import simplejson as json

from snf_django.lib.api import utils
from synnefo.db.models import Subnet, Network, IPPoolTable
from synnefo.logic import networks, subnets

from ipaddr import IPv4Network, IPv6Network, IPv4Address, IPAddress, IPNetwork

log = getLogger(__name__)


urlpatterns = patterns(
    'synnefo.api.subnets',
    (r'^(?:/|.json|.xml)?$', 'demux'),
    (r'^/([-\w]+)(?:/|.json|.xml)?$', 'subnet_demux'))


def demux(request):
    if request.method == 'GET':
        return list_subnets(request)
    elif request.method == 'POST':
        return create_subnet(request)
    else:
        return api.api_method_not_allowed(request)


def subnet_demux(request, sub_id):
    if request.method == 'GET':
        return get_subnet(request, sub_id)
    elif request.method == 'DELETE':
        return delete_subnet(request, sub_id)
    elif request.method == 'PUT':
        return update_subnet(request, sub_id)
    else:
        return api.api_method_not_allowed(request)


@api.api_method(http_method='GET', user_required=True, logger=log)
def list_subnets(request):
    """List all subnets of a user"""
    subnet_list = subnets.list_subnets(request.user_uniq)
    subnets_dict = [subnet_to_dict(sub)
                    for sub in subnet_list.order_by('id')]

    data = json.dumps({'subnets': subnets_dict})

    return HttpResponse(data, status=200)


@api.api_method(http_method='POST', user_required=True, logger=log)
def create_subnet(request):
    """
    Create a subnet
    network_id and the desired cidr are mandatory, everything else is optional
    """
    dictionary = utils.get_request_dict(request)
    log.info('create subnet %s', dictionary)

    try:
        subnet = dictionary['subnet']
        network_id = subnet['network_id']
        cidr = subnet['cidr']
    except KeyError:
        raise api.faults.BadRequest("Malformed request")

    allocation_pools = subnet.get('allocation_pools', None)
    if allocation_pools is not None:
        pool = parse_ip_pools(allocation_pools)
        allocation_pools = string_to_ipaddr(pool)

    name = subnet.get('name', None)
    ipversion = subnet.get('ip_version', 4)
    gateway = subnet.get('gateway_ip', None)
    dhcp = subnet.get('enable_dhcp', True)
    slac = subnet.get('enable_slac', None)
    dns = subnet.get('dns_nameservers', None)
    hosts = subnet.get('host_routes', None)

    sub = subnets.create_subnet(network_id=network_id,
                                cidr=cidr,
                                name=name,
                                ipversion=ipversion,
                                gateway=gateway,
                                dhcp=dhcp,
                                slac=slac,
                                dns_nameservers=dns,
                                allocation_pools=allocation_pools,
                                host_routes=hosts,
                                user_id=request.user_uniq)

    subnet_dict = subnet_to_dict(sub)
    data = json.dumps({'subnet': subnet_dict})
    return HttpResponse(data, status=200)


@api.api_method(http_method='GET', user_required=True, logger=log)
def get_subnet(request, sub_id):
    """Show info of a specific subnet"""
    user_id = request.user_uniq
    subnet = subnets.get_subnet(sub_id)

    if subnet.network.userid != user_id:
        raise api.failts.Unauthorized("You're not allowed to view this subnet")

    subnet_dict = subnet_to_dict(subnet)
    data = json.dumps({'subnet': subnet_dict})
    return HttpResponse(data, status=200)


@api.api_method(http_method='DELETE', user_required=True, logger=log)
def delete_subnet(request, sub_id):
    """
    Delete a subnet, raises BadRequest
    A subnet is deleted ONLY when the network that it belongs to is deleted
    """
    raise api.faults.BadRequest("Deletion of a subnet is not supported")


@api.api_method(http_method='PUT', user_required=True, logger=log)
def update_subnet(request, sub_id):
    """
    Update the fields of a subnet
    Only the name can be updated, everything else returns BadRequest
    """

    dictionary = utils.get_request_dict(request)
    user_id = request.user_uniq

    try:
        subnet = dictionary['subnet']
    except KeyError:
        raise api.faults.BadRequest("Malformed request")

    if len(subnet) != 1 or "name" not in subnet:
        raise api.faults.BadRequest("Only the name of subnet can be updated")

    name = subnet.get("name", None)

    subnet_dict = subnet_to_dict(subnets.update_subnet(sub_id, name))
    data = json.dumps({'subnet': subnet_dict})
    return HttpResponse(data, status=200)


#Utility functions
def subnet_to_dict(subnet):
    """Returns a dictionary containing the info of a subnet"""
    dns = check_empty_lists(subnet.dns_nameservers)
    hosts = check_empty_lists(subnet.host_routes)
    allocation_pools = subnet.ip_pools.all()
    pools = list()

    if allocation_pools:
        for pool in allocation_pools:
            cidr = IPNetwork(pool.base)
            start = str(cidr.network + pool.offset)
            end = str(cidr.network + pool.offset + pool.size - 1)
            pools.append({"start": start, "end": end})

    dictionary = dict({'id': str(subnet.id),
                       'network_id': str(subnet.network.id),
                       'name': subnet.name if subnet.name is not None else "",
                       'tenant_id': subnet.network.userid,
                       'user_id': subnet.network.userid,
                       'gateway_ip': subnet.gateway,
                       'ip_version': subnet.ipversion,
                       'cidr': subnet.cidr,
                       'enable_dhcp': subnet.dhcp,
                       'dns_nameservers': dns,
                       'host_routes': hosts,
                       'allocation_pools': pools if pools is not None else []})

    if subnet.ipversion == 6:
        dictionary['enable_slac'] = subnet.dhcp

    return dictionary


def string_to_ipaddr(pools):
    """
    Convert [["192.168.42.1", "192.168.42.15"],
            ["192.168.42.30", "192.168.42.60"]]
    to
            [[IPv4Address('192.168.42.1'), IPv4Address('192.168.42.15')],
            [IPv4Address('192.168.42.30'), IPv4Address('192.168.42.60')]]
    and sort the output
    """
    pool_list = [(map(lambda ip_str: IPAddress(ip_str), pool))
                 for pool in pools]
    pool_list.sort()
    return pool_list


def check_empty_lists(value):
    """Check if value is Null/None, in which case we return an empty list"""
    if value is None:
        return []
    return value


def check_name_length(name):
    """Check if the length of a name is within acceptable value"""
    if len(str(name)) > Subnet.SUBNET_NAME_LENGTH:
        raise api.faults.BadRequest("Subnet name too long")
    return name


def get_subnet_fromdb(subnet_id, user_id, for_update=False):
    """
    Return a Subnet instance or raise ItemNotFound.
    This is the same as util.get_network
    """
    try:
        subnet_id = int(subnet_id)
        if for_update:
            return Subnet.objects.select_for_update().get(id=subnet_id,
                                                          network__userid=
                                                          user_id)
        return Subnet.objects.get(id=subnet_id, network__userid=user_id)
    except (ValueError, Subnet.DoesNotExist):
        raise api.faults.ItemNotFound('Subnet not found')


def parse_ip_pools(pools):
    """
    Convert [{'start': '192.168.42.1', 'end': '192.168.42.15'},
             {'start': '192.168.42.30', 'end': '192.168.42.60'}]
    to
            [["192.168.42.1", "192.168.42.15"],
             ["192.168.42.30", "192.168.42.60"]]
    """
    pool_list = list()
    for pool in pools:
        parse = [pool["start"], pool["end"]]
        pool_list.append(parse)
    return pool_list
