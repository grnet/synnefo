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
from functools import wraps
from django.db import transaction

from snf_django.lib.api import faults
from synnefo.api import util
from synnefo import quotas
from synnefo.db.models import Network
from synnefo.db.utils import validate_mac
from synnefo.db.pools import EmptyPool
from synnefo.logic import backend

from logging import getLogger
log = getLogger(__name__)


def validate_network_action(network, action):
    if network.deleted:
        raise faults.BadRequest("Network has been deleted.")


def network_command(action):
    def decorator(func):
        @wraps(func)
        @transaction.commit_on_success()
        def wrapper(network, *args, **kwargs):
            validate_network_action(network, action)
            return func(network, *args, **kwargs)
        return wrapper
    return decorator


@transaction.commit_on_success
def create(user_id, name, flavor, subnet=None, gateway=None, subnet6=None,
           gateway6=None, public=False, dhcp=True, link=None, mac_prefix=None,
           mode=None, floating_ip_pool=False, tags=None):
    if flavor is None:
        raise faults.BadRequest("Missing request parameter 'type'")
    elif flavor not in Network.FLAVORS.keys():
        raise faults.BadRequest("Invalid network type '%s'" % flavor)

    if mac_prefix is not None and flavor == "MAC_FILTERED":
        raise faults.BadRequest("Can not override MAC_FILTERED mac-prefix")
    if link is not None and flavor == "PHYSICAL_VLAN":
        raise faults.BadRequest("Can not override PHYSICAL_VLAN link")

    if subnet is None and floating_ip_pool:
        raise faults.BadRequest("IPv6 only networks can not be"
                                " pools.")
    # Check that network parameters are valid
    util.validate_network_params(subnet, gateway, subnet6, gateway6)

    try:
        fmode, flink, fmac_prefix, ftags = util.values_from_flavor(flavor)
    except EmptyPool:
        log.error("Failed to allocate resources for network of type: %s",
                  flavor)
        msg = "Failed to allocate resources for network."
        raise faults.ServiceUnavailable(msg)

    mode = mode or fmode
    link = link or flink
    mac_prefix = mac_prefix or fmac_prefix
    tags = tags or ftags

    validate_mac(mac_prefix + "0:00:00:00")

    network = Network.objects.create(
        name=name,
        userid=user_id,
        subnet=subnet,
        subnet6=subnet6,
        gateway=gateway,
        gateway6=gateway6,
        dhcp=dhcp,
        flavor=flavor,
        mode=mode,
        link=link,
        mac_prefix=mac_prefix,
        tags=tags,
        public=public,
        floating_ip_pool=floating_ip_pool,
        action='CREATE',
        state='ACTIVE')

    # Issue commission to Quotaholder and accept it since at the end of
    # this transaction the Network object will be created in the DB.
    # Note: the following call does a commit!
    if not public:
        quotas.issue_and_accept_commission(network)
    return network


@network_command("RENAME")
def rename(network, name):
    network.name = name
    network.save()
    return network


@network_command("DESTROY")
def delete(network):
    if network.machines.exists():
        raise faults.NetworkInUse("Can not delete network. Servers connected"
                                  " to this network exists.")
    if network.floating_ips.filter(deleted=False).exists():
        msg = "Can not delete netowrk. Network has allocated floating IPs."
        raise faults.NetworkInUse(msg)

    network.action = "DESTROY"
    network.save()

    # Delete network to all backends that exists
    backend_networks = network.backend_networks.exclude(operstate="DELETED")
    for bnet in backend_networks:
        backend.delete_network(network, bnet.backend)
    # If network does not exist in any backend, update the network state
    if not backend_networks:
        backend.update_network_state(network)
    return network
