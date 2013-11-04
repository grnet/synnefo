import logging

from snf_django.lib.api import faults
from django.db import transaction
from synnefo import quotas
from synnefo.db import pools
from synnefo.db.models import (IPPoolTable, IPAddress)
log = logging.getLogger(__name__)


def allocate_ip_from_pools(pool_rows, userid, address=None, floating_ip=False):
    """Try to allocate a value from a number of pools.

    This function takes as argument a number of PoolTable objects and tries to
    allocate a value from them. If all pools are empty EmptyPool is raised.
    If an address is specified and does not belong to any of the pools,
    InvalidValue is raised.

    """
    for pool_row in pool_rows:
        pool = pool_row.pool
        try:
            value = pool.get(value=address)
            pool.save()
            subnet = pool_row.subnet
            ipaddress = IPAddress.objects.create(subnet=subnet,
                                                 network=subnet.network,
                                                 userid=userid,
                                                 address=value,
                                                 floating_ip=floating_ip)
            return ipaddress
        except pools.EmptyPool:
            pass
        except pools.InvalidValue:
            pass
    if address is None:
        raise pools.EmptyPool("No more IP addresses available on pools %s" %
                              pool_rows)
    else:
        raise pools.InvalidValue("Address %s does not belong to pools %s" %
                                 (address, pool_rows))


def allocate_ip(network, userid, address=None, floating_ip=False):
    """Try to allocate an IP from networks IP pools."""
    if network.action == "DESTROY":
        raise faults.Conflict("Can not allocate IP. Network %s is being"
                              " deleted" % network.id)
    ip_pools = IPPoolTable.objects.select_for_update()\
        .filter(subnet__network=network)
    try:
        return allocate_ip_from_pools(ip_pools, userid, address=address,
                                      floating_ip=floating_ip)
    except pools.EmptyPool:
        raise faults.Conflict("No more IP addresses available on network %s"
                              % network.id)
    except pools.ValueNotAvailable:
        raise faults.Conflict("IP address %s is already used." % address)
    except pools.InvalidValue:
        raise faults.BadRequest("Address %s does not belong to network %s" %
                                (address, network.id))


def allocate_public_ip(userid, floating_ip=False, backend=None):
    """Try to allocate a public or floating IP address.

    Try to allocate a a public IPv4 address from one of the available networks.
    If 'floating_ip' is set, only networks which are floating IP pools will be
    used and the IPAddress that will be created will be marked as a floating
    IP. If 'backend' is set, only the networks that exist in this backend will
    be used.

    """

    ip_pool_rows = IPPoolTable.objects.select_for_update()\
        .prefetch_related("subnet__network")\
        .filter(subnet__deleted=False)\
        .filter(subnet__network__deleted=False)\
        .filter(subnet__network__public=True)\
        .filter(subnet__network__drained=False)
    if floating_ip:
        ip_pool_rows = ip_pool_rows\
            .filter(subnet__network__floating_ip_pool=True)
    if backend is not None:
        ip_pool_rows = ip_pool_rows\
            .filter(subnet__network__backend_networks__backend=backend)

    try:
        return allocate_ip_from_pools(ip_pool_rows, userid,
                                      floating_ip=floating_ip)
    except pools.EmptyPool:
        ip_type = "floating" if floating_ip else "public"
        log_msg = "Failed to allocate a %s IP. Reason:" % ip_type
        if ip_pool_rows:
            log_msg += " No network exists."
        else:
            log_msg += " All network are full."
        if backend is not None:
            log_msg += " Backend: %s" % backend
        log.error(log_msg)
        exception_msg = "Can not allocate a %s IP address." % ip_type
        if floating_ip:
            raise faults.Conflict(exception_msg)
        else:
            raise faults.ServiceUnavailable(exception_msg)


@transaction.commit_on_success
def create_floating_ip(userid, network=None, address=None):
    if network is None:
        floating_ip = allocate_public_ip(userid, floating_ip=True)
    else:
        if not network.floating_ip_pool:
            msg = ("Can not allocate floating IP. Network %s is"
                   " not a floating IP pool.")
            raise faults.Conflict(msg % network.id)
        if network.action == "DESTROY":
            msg = "Can not allocate floating IP. Network %s is being deleted."
            raise faults.Conflict(msg % network.id)

        # Allocate the floating IP
        floating_ip = allocate_ip(network, userid, address=address,
                                  floating_ip=True)

    # Issue commission (quotas)
    quotas.issue_and_accept_commission(floating_ip)
    transaction.commit()

    log.info("Created floating IP '%s' for user IP '%s'", floating_ip, userid)

    return floating_ip


@transaction.commit_on_success
def delete_floating_ip(floating_ip):
    if floating_ip.nic:
        # This is safe, you also need for_update to attach floating IP to
        # instance.
        msg = "Floating IP '%s' is attached to instance." % floating_ip.id
        raise faults.Conflict(msg)

    # Return the address of the floating IP back to pool
    floating_ip.release_address()
    # And mark the floating IP as deleted
    floating_ip.deleted = True
    floating_ip.save()
    # Release quota for floating IP
    quotas.issue_and_accept_commission(floating_ip, delete=True)
    transaction.commit()
    # Delete the floating IP from DB
    log.info("Deleted floating IP '%s' of user '%s", floating_ip,
             floating_ip.userid)
    floating_ip.delete()
