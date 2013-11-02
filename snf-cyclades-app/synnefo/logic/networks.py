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
from synnefo.db.models import Network, Backend
from synnefo.db.utils import validate_mac
from synnefo.db.pools import EmptyPool
from synnefo.logic import backend as backend_mod, subnets

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
def create(userid, name, flavor, subnet=None, gateway=None, subnet6=None,
           gateway6=None, public=False, dhcp=True, link=None, mac_prefix=None,
           mode=None, floating_ip_pool=False, tags=None, backends=None,
           lazy_create=True):
    if flavor is None:
        raise faults.BadRequest("Missing request parameter 'type'")
    elif flavor not in Network.FLAVORS.keys():
        raise faults.BadRequest("Invalid network type '%s'" % flavor)

    if mac_prefix is not None and flavor == "MAC_FILTERED":
        raise faults.BadRequest("Can not override MAC_FILTERED mac-prefix")
    if link is not None and flavor == "PHYSICAL_VLAN":
        raise faults.BadRequest("Can not override PHYSICAL_VLAN link")

    if subnet is None and floating_ip_pool:
        raise faults.BadRequest("IPv6 only networks can not be floating"
                                " pools.")
    # Check that network parameters are valid
    subnets.validate_subnet_params(subnet, gateway, subnet6, gateway6)

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

    if (flavor == "IP_LESS_ROUTED" and
       Network.objects.filter(deleted=False, mode=mode, link=link).exists()):
        msg = "Link '%s' is already used." % link
        raise faults.BadRequest(msg)

    validate_mac(mac_prefix + "0:00:00:00")

    network = Network.objects.create(
        name=name,
        userid=userid,
        flavor=flavor,
        mode=mode,
        link=link,
        mac_prefix=mac_prefix,
        tags=tags,
        public=public,
        external_router=public,
        floating_ip_pool=floating_ip_pool,
        action='CREATE',
        state='ACTIVE')

    if subnet:
        subnets._create_subnet(network.id, cidr=subnet, name="", ipversion=4,
                               gateway=gateway, dhcp=dhcp, user_id=userid)
    if subnet6:
        subnets._create_subnet(network.id, cidr=subnet6, name="", ipversion=6,
                               gateway=gateway6, dhcp=dhcp, user_id=userid)

    # Issue commission to Quotaholder and accept it since at the end of
    # this transaction the Network object will be created in the DB.
    # Note: the following call does a commit!
    if not public:
        quotas.issue_and_accept_commission(network)

    if not lazy_create:
        if floating_ip_pool:
            backends = Backend.objects.filter(offline=False)
        elif backends is None:
            backends = []

        for bend in backends:
            network.create_backend_network(bend)
            backend_mod.create_network(network=network, backend=bend,
                                       connect=True)
    return network


@network_command("RENAME")
def rename(network, name):
    network.name = name
    network.save()
    return network


@network_command("DESTROY")
def delete(network):
    if network.nics.exists():
        raise faults.Conflict("Can not delete network. There are ports still"
                              " configured on network network %s" % network.id)
    if network.ips.filter(deleted=False, floating_ip=True).exists():
        msg = "Can not delete netowrk. Network has allocated floating IPs."
        raise faults.Conflict(msg)

    network.action = "DESTROY"
    network.save()

    # Delete network to all backends that exists
    for bnet in network.backend_networks.exclude(operstate="DELETED"):
        backend_mod.delete_network(network, bnet.backend)
    else:
        # If network does not exist in any backend, update the network state
        backend_mod.update_network_state(network)
    return network
