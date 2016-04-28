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

import ipaddr
from logging import getLogger
from functools import wraps

from django.conf import settings
from synnefo.db import transaction
from django.db.models import Q

from snf_django.lib import api
from snf_django.lib.api import faults
from synnefo.logic import utils
from synnefo.api import util

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
        network_id = int(network_id)
        network = Network.objects.select_for_update().get(id=network_id)
    except (ValueError, TypeError):
        raise api.faults.BadRequest("Malformed network ID")
    except Network.DoesNotExist:
        raise api.faults.ItemNotFound("No network found with that ID")

    if network.deleted:
        raise api.faults.BadRequest("Network has been deleted")

    if user_id != network.userid:
        raise api.faults.Forbidden("Forbidden operation")

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

    utils.check_name_length(name, Subnet.SUBNET_NAME_LENGTH, "Subnet "
                            "name is too long")
    sub = Subnet.objects.create(name=name, network=network, cidr=cidr,
                                ipversion=ipversion, gateway=gateway,
                                userid=network.userid, public=network.public,
                                dhcp=dhcp, host_routes=host_routes,
                                dns_nameservers=dns_nameservers)

    network.subnet_ids.append(sub.id)
    network.save()

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


def get_subnet(subnet_id, user_id, user_projects, for_update=False):
    """Return a Subnet instance or raise ItemNotFound."""

    try:
        objects = Subnet.objects.for_user(user_id, user_projects, public=True)
        if for_update:
            objects.select_for_update()
        return objects.get(id=subnet_id)
    except (ValueError, TypeError):
        raise faults.BadRequest("Invalid subnet ID '%s'" % subnet_id)
    except Subnet.DoesNotExist:
        raise faults.ItemNotFound("Subnet '%s' not found." % subnet_id)


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
        raise api.faults.Forbidden("Forbidden operation")

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
        if prefixlen > 29 or prefixlen < settings.MAX_CIDR_BLOCK:
            raise faults.OverLimit(
                message="Unsupported network size",
                details="Netmask must be in range: [%s, 29]" %
                settings.MAX_CIDR_BLOCK)
        if gateway:  # Check that gateway belongs to network
            try:
                gateway = ipaddr.IPv4Address(gateway)
            except ValueError:
                raise faults.BadRequest("Invalid network IPv4 gateway")
            if gateway not in network:
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
