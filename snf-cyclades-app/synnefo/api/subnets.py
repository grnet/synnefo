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
from synnefo.db.models import Subnet, Network
from synnefo.logic import networks

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
    log.debug('list_subnets')

    user_subnets = Subnet.objects.filter(network__userid=request.user_uniq)
    subnets_dict = [subnet_to_dict(sub)
                    for sub in user_subnets.order_by('id')]
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
    user_id = request.user_uniq

    try:
        subnet = dictionary['subnet']
        network_id = subnet['network_id']
        cidr = subnet['cidr']
    except KeyError:
        raise api.faults.BadRequest("Malformed request")

    try:
        network = Network.objects.get(id=network_id)
    except Network.DoesNotExist:
        raise api.faults.ItemNotFound("No networks found with that id")

    if user_id != network.userid:
        raise api.faults.Unauthorized("Unauthorized operation")

    ipversion = subnet.get('ip_version', 4)
    if ipversion not in [4, 6]:
        raise api.faults.BadRequest("Malformed IP version type")

    # Returns the first available IP in the subnet
    if ipversion == 6:
        potential_gateway = str(IPv6Network(cidr).network + 1)
        check_number_of_subnets(network, 6)
    else:
        potential_gateway = str(IPv4Network(cidr).network + 1)
        check_number_of_subnets(network, 4)

    gateway = subnet.get('gateway_ip', potential_gateway)

    if ipversion == 6:
        networks.validate_network_params(None, None, cidr, gateway)
        slac = subnet.get('slac', None)
        if slac is not None:
            dhcp = check_dhcp_value(slac)
        else:
            dhcp = check_dhcp_value(subnet.get('enable_dhcp', True))
    else:
        networks.validate_network_params(cidr, gateway)
        dhcp = check_dhcp_value(subnet.get('enable_dhcp', True))

    name = check_name_length(subnet.get('name', None))

    dns = subnet.get('dns_nameservers', None)
    hosts = subnet.get('host_routes', None)

    gateway_ip = IPAddress(gateway)
    cidr_ip = IPNetwork(cidr)

    allocation_pools = subnet.get('allocation_pools', None)

    if allocation_pools:
        if ipversion == 6:
            raise api.faults.Conflict("Can't allocate an IP Pool in IPv6")
        pools = parse_ip_pools(allocation_pools)
        validate_subpools(pools, cidr_ip, gateway_ip)
    else:
        # FIX ME
        pass

    # FIX ME
    try:
        sub = Subnet.objects.create(name=name, network=network, cidr=cidr,
                                    ipversion=ipversion, gateway=gateway,
                                    dhcp=dhcp, host_routes=hosts,
                                    dns_nameservers=dns)
    except:
        raise
        return "Error"

    subnet_dict = subnet_to_dict(sub)
    data = json.dumps({'subnet': subnet_dict})
    return HttpResponse(data, status=200)


@api.api_method(http_method='GET', user_required=True, logger=log)
def get_subnet(request, sub_id):
    """Show info of a specific subnet"""
    log.debug('get_subnet %s', sub_id)
    user_id = request.user_uniq

    try:
        subnet = Subnet.objects.get(id=sub_id)
    except Subnet.DoesNotExist:
        raise api.faults.ItemNotFound("Subnet not found")

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
    log.info('Update subnet %s', dictionary)
    user_id = request.user_uniq

    try:
        subnet = dictionary['subnet']
    except KeyError:
        raise api.faults.BadRequest("Malformed request")

    original_subnet = get_subnet_fromdb(sub_id, user_id)
    original_dict = subnet_to_dict(original_subnet)

    if len(subnet) != 1:
        raise api.faults.BadRequest("Only the name of subnet can be updated")

    name = subnet.get("name", None)

    if not name:
        raise api.faults.BadRequest("Only the name of subnet can be updated")

    #if subnet.get('ip_version', None):
    #    raise api.faults.BadRequest("Malformed request, ip_version cannot be "
    #                                "updated")
    #if subnet.get('cidr', None):
    #    raise api.faults.BadRequest("Malformed request, cidr cannot be "
    #                                "updated")
    #if subnet.get('allocation_pools', None):
    #    raise api.faults.BadRequest("Malformed request, allocation pools "
    #                                "cannot be updated")
    #
    # Check if request contained host/dns information
    #check_for_hosts_dns(subnet)
    #
    #name = subnet.get('name', original_dict['name'])
    check_name_length(name)

    #dhcp = subnet.get('enable_dhcp', original_dict['enable_dhcp'])
    #check_dhcp_value(dhcp)
    #
    #gateway = subnet.get('gateway_ip', original_dict['gateway_ip'])
    #FIX ME, check if IP is in use
    #if original_dict['ip_version'] == 6:
    #    networks.validate_network_params(None, None, original_dict['cidr'],
    #                                     gateway)
    #else:
    #    networks.validate_network_params(original_dict['cidr'], gateway)
    #
    try:
        #original_subnet.gateway = gateway
        original_subnet.name = name
        #original_subnet.dhcp = dhcp
        original_subnet.save()
    except:
        #Fix me
        return "Unknown Error"

    subnet_dict = subnet_to_dict(original_subnet)
    data = json.dumps({'subnet': subnet_dict})
    return HttpResponse(data, status=200)


#Utility functions
def subnet_to_dict(subnet):
    """Returns a dictionary containing the info of a subnet"""
    # FIX ME, allocation pools
    dictionary = dict({'id': subnet.id, 'network_id': subnet.network.id,
                       'name': subnet.name, 'tenant_id': subnet.network.userid,
                       'gateway_ip': subnet.gateway,
                       'ip_version': subnet.ipversion, 'cidr': subnet.cidr,
                       'enable_dhcp': subnet.dhcp,
                       'dns_nameservers': subnet.dns_nameservers,
                       'host_routes': subnet.host_routes,
                       'allocation_pools': []})

    if subnet.ipversion == 6:
        dictionary['slac'] = subnet.dhcp

    return dictionary


def check_number_of_subnets(network, version):
    """Check if a user can add a subnet in a network"""
    if network.subnets.filter(ipversion=version):
        raise api.faults.BadRequest("Only one subnet of IPv4/IPv6 per "
                                    "network is allowed")


def check_dhcp_value(dhcp):
    """Check if dhcp value is in acceptable values"""
    if dhcp not in [True, False]:
        raise api.faults.BadRequest("Malformed request, enable_dhcp/slac must "
                                    "be True or False")
    return dhcp


def check_name_length(name):
    """Check if the length of a name is within acceptable value"""
    if len(str(name)) > Subnet.SUBNET_NAME_LENGTH:
        raise api.faults.BadRequest("Subnet name too long")
    return name


def check_for_hosts_dns(subnet):
    """
    Check if a request contains host_routes or dns_nameservers options
    Expects the request in a dictionary format
    """
    if subnet.get('host_routes', None):
        raise api.faults.BadRequest("Setting host routes isn't supported")
    if subnet.get('dns_nameservers', None):
        raise api.faults.BadRequest("Setting dns nameservers isn't supported")


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
        raise api.faults.ItemNotFound('Subnet not found.')


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
        asd = [pool["start"], pool["end"]]
        pool_list.append(asd)
    return pool_list


def validate_subpools(pools, cidr, gateway):
    """
    Validate the given IP pools are inside the cidr range
    Validate there are no overlaps in the given pools
    Input must be a list containing a sublist with start/end ranges as strings
    [["192.168.42.1", "192.168.42.15"], ["192.168.42.30", "192.168.42.60"]]
    """
    pool_list = list()
    for pool in pools:
        pool_list.append(map(lambda a: IPAddress(a), pool))
    pool_list = sorted(pool_list)

    if pool_list[0][0] <= cidr.network:
        raise api.faults.Conflict("IP Pool out of bounds")
    elif pool_list[-1][1] >= cidr.broadcast:
        raise api.faults.Conflict("IP Pool out of bounds")

    for start, end in pool_list:
        if start >= end:
            raise api.faults.Conflict("Invalid IP pool range")
        # Raise BadRequest if gateway is inside the pool range
        if not (gateway < start or gateway > end):
            raise api.faults.Conflict("Gateway cannot be in pool range")

    # Check if there is a conflict between the IP Poll ranges
    end = cidr.network
    for pool in pool_list:
        if end >= pool[1]:
            raise api.faults.Conflict("IP Pool range conflict")
        end = pool[1]
