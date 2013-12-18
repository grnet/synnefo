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

import ipaddr
from logging import getLogger
from functools import wraps

from django.conf import settings
from django.db import transaction
from django.db.models import Q

from snf_django.lib import api
from snf_django.lib.api import faults
from synnefo.logic import utils

from synnefo.db.models import Subnet, Network, IPPoolTable

log = getLogger(__name__)


def subnet_command(action):
    def decorator(func):
        @wraps(func)
        @transaction.commit_on_success()
        def wrapper(subnet, *args, **kwargs):
            return func(subnet, *args, **kwargs)
        return wrapper
    return decorator


def list_subnets(user_id):
    """List all subnets of a user"""
    log.debug('list_subnets %s', user_id)

    query = (((Q(network__userid=user_id) & Q(network__public=False)) |
              Q(network__public=True)) & Q(deleted=False))
    user_subnets = Subnet.objects.filter(query)
    return user_subnets


@transaction.commit_on_success
def create_subnet(*args, **kwargs):
    return _create_subnet(*args, **kwargs)


def _create_subnet(network_id, user_id, cidr, name, ipversion=4, gateway=None,
                   dhcp=True, slaac=True, dns_nameservers=None,
                   allocation_pools=None, host_routes=None):
    """Create a subnet

    network_id and the desired cidr are mandatory, everything else is optional

    """
    try:
        network = Network.objects.get(id=network_id)
    except Network.DoesNotExist:
        raise api.faults.ItemNotFound("No network found with that id")

    if network.deleted:
        raise api.faults.BadRequest("Network has been deleted")

    if user_id != network.userid:
        raise api.faults.Unauthorized("Unauthorized operation")

    if ipversion not in [4, 6]:
        raise api.faults.BadRequest("Malformed IP version type")

    check_number_of_subnets(network, ipversion)

    if network.backend_networks.exists():
        raise api.faults.BadRequest("Cannot create subnet in network %s, VMs"
                                    " are already connected to this network" %
                                    network_id)

    try:
        cidr_ip = ipaddr.IPNetwork(cidr)
    except ValueError:
        raise api.faults.BadRequest("Malformed CIDR")

    if ipversion == 6:
        validate_subnet_params(subnet6=cidr, gateway6=gateway)
    else:
        validate_subnet_params(subnet=cidr, gateway=gateway)

    name = utils.check_name_length(name, Subnet.SUBNET_NAME_LENGTH, "Subnet "
                                   "name is too long")
    sub = Subnet.objects.create(name=name, network=network, cidr=cidr,
                                ipversion=ipversion, gateway=gateway,
                                dhcp=dhcp, host_routes=host_routes,
                                dns_nameservers=dns_nameservers)

    gateway_ip = ipaddr.IPAddress(gateway) if gateway else None

    if allocation_pools is not None:
        if ipversion == 6:
            raise api.faults.Conflict("Can't allocate an IP Pool in IPv6")
    elif ipversion == 4:
        # Check if the gateway is the first IP of the subnet, or the last. In
        # that case create a single ip pool.
        if gateway_ip:
            if int(gateway_ip) - int(cidr_ip) == 1:
                allocation_pools = [(gateway_ip + 1, cidr_ip.broadcast - 1)]
            elif int(cidr_ip.broadcast) - int(gateway_ip) == 1:
                allocation_pools = [(cidr_ip.network + 1, gateway_ip - 1)]
            else:
                # If the gateway isn't the first available ip, create two
                # different ip pools adjacent to said ip
                allocation_pools = [(cidr_ip.network + 1, gateway_ip - 1),
                                    (gateway_ip + 1, cidr_ip.broadcast - 1)]
        else:
            allocation_pools = [(cidr_ip.network + 1, cidr_ip.broadcast - 1)]

    if allocation_pools:
        # Validate the allocation pools
        validate_pools(allocation_pools, cidr_ip, gateway_ip)
        create_ip_pools(allocation_pools, cidr_ip, sub)

    return sub


def get_subnet(sub_id):
    """Show info of a specific subnet"""
    log.debug('get_subnet %s', sub_id)
    try:
        subnets = Subnet.objects
        return subnets.get(id=sub_id)
    except Subnet.DoesNotExist:
        raise api.faults.ItemNotFound("Subnet not found")


def delete_subnet():
    """Delete a subnet, raises BadRequest
    A subnet is deleted ONLY when the network that it belongs to is deleted

    """
    raise api.faults.BadRequest("Deletion of a subnet is not supported")


@transaction.commit_on_success
def update_subnet(sub_id, name, user_id):
    """Update the fields of a subnet
    Only the name can be updated

    """
    log.info('Update subnet %s, name %s' % (sub_id, name))

    try:
        subnet = Subnet.objects.get(id=sub_id)
    except:
        raise api.faults.ItemNotFound("Subnet not found")

    if user_id != subnet.network.userid:
        raise api.faults.Unauthorized("Unauthorized operation")

    utils.check_name_length(name, Subnet.SUBNET_NAME_LENGTH, "Subnet name is "
                            " too long")

    subnet.name = name
    subnet.save()

    return subnet


#Utility functions
def create_ip_pools(pools, cidr, subnet):
    """Create IP Pools in the database"""
    return [_create_ip_pool(pool, cidr, subnet) for pool in pools]


def _create_ip_pool(pool, cidr, subnet):
    size = int(pool[1]) - int(pool[0]) + 1
    base = str(cidr)
    offset = int(pool[0]) - int(cidr.network)
    return IPPoolTable.objects.create(size=size, offset=offset,
                                      base=base, subnet=subnet)


def check_number_of_subnets(network, version):
    """Check if a user can add a subnet in a network"""
    if network.subnets.filter(ipversion=version):
        raise api.faults.BadRequest("Only one subnet of IPv4/IPv6 per "
                                    "network is allowed")


def validate_pools(pool_list, cidr, gateway):
    """Validate IP Pools

    Validate the given IP pools are inside the cidr range
    Validate there are no overlaps in the given pools
    Finally, validate the gateway isn't in the given ip pools
    Input must be a list containing a sublist with start/end ranges as
    ipaddr.IPAddress items eg.,
    [[IPv4Address('192.168.42.11'), IPv4Address('192.168.42.15')],
     [IPv4Address('192.168.42.30'), IPv4Address('192.168.42.60')]]

    """
    if pool_list[0][0] <= cidr.network:
        raise api.faults.Conflict("IP Pool out of bounds")
    elif pool_list[-1][1] >= cidr.broadcast:
        raise api.faults.Conflict("IP Pool out of bounds")

    for start, end in pool_list:
        if start > end:
            raise api.faults.Conflict("Invalid IP pool range")
        # Raise BadRequest if gateway is inside the pool range
        if gateway:
            if not (gateway < start or gateway > end):
                raise api.faults.Conflict("Gateway cannot be in pool range")

    # Check if there is a conflict between the IP Pool ranges
    end = cidr.network
    for pool in pool_list:
        if end >= pool[0]:
            raise api.faults.Conflict("IP Pool range conflict")
        end = pool[1]


def validate_subnet_params(subnet=None, gateway=None, subnet6=None,
                           gateway6=None):
    if subnet:
        try:
            # Use strict option to not all subnets with host bits set
            network = ipaddr.IPv4Network(subnet, strict=True)
        except ValueError:
            raise faults.BadRequest("Invalid network IPv4 subnet")

        # Check that network size is allowed!
        prefixlen = network.prefixlen
        if prefixlen > 29 or prefixlen <= settings.MAX_CIDR_BLOCK:
            raise faults.OverLimit(
                message="Unsupported network size",
                details="Netmask must be in range: (%s, 29]" %
                settings.MAX_CIDR_BLOCK)
        if gateway:  # Check that gateway belongs to network
            try:
                gateway = ipaddr.IPv4Address(gateway)
            except ValueError:
                raise faults.BadRequest("Invalid network IPv4 gateway")
            if not gateway in network:
                raise faults.BadRequest("Invalid network IPv4 gateway")

    if subnet6:
        try:
            # Use strict option to not all subnets with host bits set
            network6 = ipaddr.IPv6Network(subnet6, strict=True)
        except ValueError:
            raise faults.BadRequest("Invalid network IPv6 subnet")
        # Check that network6 is an /64 subnet, because this is imposed by
        # 'mac2eui64' utiity.
        if network6.prefixlen != 64:
            msg = ("Unsupported IPv6 subnet size. Network netmask must be"
                   " /64")
            raise faults.BadRequest(msg)
        if gateway6:
            try:
                gateway6 = ipaddr.IPv6Address(gateway6)
            except ValueError:
                raise faults.BadRequest("Invalid network IPv6 gateway")
            if not gateway6 in network6:
                raise faults.BadRequest("Invalid network IPv6 gateway")


def parse_allocation_pools(allocation_pools):
    alloc = list()
    for pool in allocation_pools:
        try:
            start, end = pool.split(',')
            alloc.append([ipaddr.IPv4Address(start),
                          ipaddr.IPv4Address(end)])
        except ValueError:
            raise faults.BadRequest("Malformed IPv4 address")

    return alloc
