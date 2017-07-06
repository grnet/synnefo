# Copyright (C) 2010-2017 GRNET S.A. and individual contributors
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

from functools import wraps
from synnefo.db import transaction
from django.conf import settings

from snf_django.lib.api import faults
from synnefo.api import util
from synnefo import quotas
from synnefo.db.models import Network, Backend
from synnefo.db.utils import validate_mac
from synnefo.db.pools import EmptyPool
from synnefo.logic import backend as backend_mod
from synnefo.logic import utils

from logging import getLogger
log = getLogger(__name__)


def validate_network_action(network, action):
    if network.deleted:
        raise faults.BadRequest("Network has been deleted.")
    if action in ["DRAIN", "UNDRAIN"]:
        if not network.public:
            raise faults.BadRequest("Network is not public.")
        if action == "DRAIN" and network.drained:
            raise faults.BadRequest("Network is drained.")
        if action == "UNDRAIN" and not network.drained:
            raise faults.BadRequest("Network is not drained.")


def network_command(action):
    def decorator(func):
        @wraps(func)
        def wrapper(network, *args, **kwargs):
            validate_network_action(network, action)
            return func(network, *args, **kwargs)
        return wrapper
    return decorator


@transaction.atomic_context
def create(userid, name, flavor, link=None, mac_prefix=None, mode=None,
           floating_ip_pool=False, tags=None, public=False, drained=False,
           project=None, shared_to_project=False, atomic_context=None):
    if flavor is None:
        raise faults.BadRequest("Missing request parameter 'type'")
    elif flavor not in Network.FLAVORS.keys():
        raise faults.BadRequest("Invalid network type '%s'" % flavor)

    if mac_prefix is not None and flavor == "MAC_FILTERED":
        raise faults.BadRequest("Cannot override MAC_FILTERED mac-prefix")
    if link is not None and flavor == "PHYSICAL_VLAN":
        raise faults.BadRequest("Cannot override PHYSICAL_VLAN link")

    utils.check_name_length(name, Network.NETWORK_NAME_LENGTH, "Network name "
                            "is too long")

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

    # Check that given link is unique!
    if (link is not None and flavor == "IP_LESS_ROUTED" and
       Network.objects.filter(deleted=False, mode=mode, link=link).exists()):
        msg = "Link '%s' is already used." % link
        raise faults.BadRequest(msg)

    if project is None:
        project = userid

    network = Network.objects.create(
        name=name,
        userid=userid,
        project=project,
        shared_to_project=shared_to_project,
        flavor=flavor,
        mode=mode,
        link=link,
        mac_prefix=mac_prefix,
        tags=tags,
        public=public,
        external_router=public,
        floating_ip_pool=floating_ip_pool,
        action='CREATE',
        state='ACTIVE',
        drained=drained)

    if link is None:
        network.link = "%slink-%d" % (settings.BACKEND_PREFIX_ID, network.id)
        network.save()

    # Issue commission to Quotaholder and accept it since at the end of
    # this transaction the Network object will be created in the DB.
    if not public:
        quotas.issue_and_accept_commission(
            network, atomic_context=atomic_context)

    return network


def create_network_in_backends(network):
    job_ids = []
    for bend in Backend.objects.filter(offline=False):
        network.create_backend_network(bend)
        jobs = backend_mod.create_network(network=network, backend=bend,
                                          connect=True)
        job_ids.extend(jobs)
    return job_ids


@transaction.atomic
def drain(network_id, credentials):
    if not credentials.is_admin:
        raise faults.Forbidden("Cannot set network's drained flag.")
    network = util.get_network(network_id, credentials,
                               for_update=True, non_deleted=True)
    validate_network_action(network, "DRAIN")
    log.info("Draining %s", network)
    network.drained = True
    network.save()


@transaction.atomic
def undrain(network_id, credentials):
    if not credentials.is_admin:
        raise faults.Forbidden("Cannot unset network's drained flag.")
    network = util.get_network(network_id, credentials,
                               for_update=True, non_deleted=True)
    validate_network_action(network, "UNDRAIN")
    log.info("Undraining %s", network)
    network.drained = False
    network.save()


@transaction.atomic
def rename(network_id, name, credentials):
    network = util.get_network(network_id, credentials,
                               for_update=True, non_deleted=True)
    if network.public:
        raise faults.Forbidden("Cannot rename the public network.")
    return _rename(network, name)


def _rename(network, name):
    validate_network_action(network, "RENAME")
    utils.check_name_length(name, Network.NETWORK_NAME_LENGTH, "Network name "
                            "is too long")
    network.name = name
    network.save()
    return network


@transaction.atomic_context
def delete(network_id, credentials, atomic_context=None):
    network = util.get_network(network_id, credentials,
                               for_update=True, non_deleted=True)
    if network.public and not credentials.is_admin:
        raise faults.Forbidden("Cannot delete the public network.")

    validate_network_action(network, "DESTROY")

    if network.nics.exists():
        raise faults.Conflict("Cannot delete network. There are ports still"
                              " configured on network network %s" % network.id)
    if network.ips.filter(deleted=False, floating_ip=True).exists():
        msg = "Cannot delete netowrk. Network has allocated floating IPs."
        raise faults.Conflict(msg)

    network.action = "DESTROY"
    # Mark network as drained to prevent automatic allocation of
    # public/floating IPs while the network is being deleted
    if network.public:
        network.drained = True
    network.save()

    # Delete network to all backends that exists
    for bnet in network.backend_networks.exclude(operstate="DELETED"):
        backend_mod.delete_network(network, bnet.backend)
    else:
        # If network does not exist in any backend, update the network state
        backend_mod.update_network_state(
            network, atomic_context=atomic_context)
    return network


@transaction.atomic_context
def reassign(network_id, project, shared_to_project, credentials,
             atomic_context=None):
    network = util.get_network(network_id, credentials,
                               for_update=True, non_deleted=True)

    if network.public:
        raise faults.Forbidden("Cannot reassign public network")

    if credentials.userid != network.userid:
        raise faults.Forbidden("Action 'reassign' is allowed only to the owner"
                               " of the network.")

    validate_network_action(network, "REASSIGN")
    if network.project == project:
        if network.shared_to_project != shared_to_project:
            log.info("%s network %s to project %s",
                "Sharing" if shared_to_project else "Unsharing",
                network, project)
            network.shared_to_project = shared_to_project
            network.save()
    else:
        action_fields = {"to_project": project, "from_project": network.project}
        log.info("Reassigning network %s from project %s to %s, shared: %s",
                network, network.project, project, shared_to_project)
        network.project = project
        network.shared_to_project = shared_to_project
        network.save()
        quotas.issue_and_accept_commission(network, action="REASSIGN",
                                           action_fields=action_fields,
                                           atomic_context=atomic_context)
    return network
