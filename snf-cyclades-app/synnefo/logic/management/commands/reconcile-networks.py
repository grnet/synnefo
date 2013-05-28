# Copyright 2011-2012 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of GRNET S.A.
#
"""Reconciliation management command

Management command to reconcile the contents of the Synnefo DB with
the state of the Ganeti backend. See docstring on top of
logic/reconciliation.py for a description of reconciliation rules.

"""
import sys
import datetime
import bitarray

from optparse import make_option

from synnefo.settings import PUBLIC_USE_POOL
from django.core.management.base import BaseCommand
from django.db import transaction

from synnefo.db.models import Backend, Network, BackendNetwork
from synnefo.db.pools import IPPool
from synnefo.logic import reconciliation, utils
from synnefo.logic import backend as backend_mod

fix = False
write = sys.stdout.write


class Command(BaseCommand):
    help = """Reconcile contents of Synnefo DB with state of Ganeti backend

Network reconciliation can detect and fix the following cases:
    - Missing database entries for a network in a Ganeti backend
    - Stale database networks, which do no exist in the Ganeti backend
    - Missing Ganeti networks
    - Ganeti networks that are not connected to all Ganeti nodegroups
    - Networks that have unsynced state
    - Networks that have unsynced IP pools
    - Orphan networks in the Ganeti backend
"""

    can_import_settings = True
    output_transaction = True  # The management command runs inside
                               # an SQL transaction
    option_list = BaseCommand.option_list + (
        make_option('--fix-all', action='store_true',
                    dest='fix', default=False,
                    help='Fix all issues.'),
        make_option('--conflicting-ips', action='store_true',
                    dest='conflicting_ips', default=False,
                    help='Detect conflicting ips')
    )

    def handle(self, **options):
        global fix, write
        fix = options['fix']
        write = self.stdout.write
        self.verbosity = int(options['verbosity'])
        conflicting_ips = options['conflicting_ips']
        reconcile_networks(conflicting_ips)


def reconcile_networks(conflicting_ips=False):
    # Get models from DB
    backends = Backend.objects.exclude(offline=True)
    networks = Network.objects.filter(deleted=False)

    # Get info from all ganeti backends
    ganeti_networks = {}
    ganeti_hanging_networks = {}
    for b in backends:
        g_nets = reconciliation.get_networks_from_ganeti(b)
        ganeti_networks[b] = g_nets
        g_hanging_nets = reconciliation.hanging_networks(b, g_nets)
        ganeti_hanging_networks[b] = g_hanging_nets

    # Perform reconciliation for each network
    for network in networks:
        ip_available_maps = []
        ip_reserved_maps = []
        uses_pool = not network.public or PUBLIC_USE_POOL
        for bend in backends:
            bnet = get_backend_network(network, bend)
            gnet = ganeti_networks[bend].get(network.id)
            if not bnet:
                if network.floating_ip_pool:
                    # Network is a floating IP pool and does not exist in
                    # backend. We need to create it
                    bnet = reconcile_parted_network(network, bend)
                elif not gnet:
                    # Network does not exist either in Ganeti nor in BD.
                    continue
                else:
                    # Network exists in Ganeti and not in DB.
                    if network.action != "DESTROY" and not network.public:
                        bnet = reconcile_parted_network(network, bend)

            if not gnet:
                # Network does not exist in Ganeti. If the network action is
                # DESTROY, we have to mark as deleted in DB, else we have to
                # create it in Ganeti.
                if network.action == "DESTROY":
                    if bnet.operstate != "DELETED":
                        reconcile_stale_network(bnet)
                else:
                    reconcile_missing_network(network, bend)
                # Skip rest reconciliation!
                continue

            try:
                hanging_groups = ganeti_hanging_networks[bend][network.id]
            except KeyError:
                # Network is connected to all nodegroups
                hanging_groups = []

            if hanging_groups:
                # CASE-3: Ganeti networks not connected to all nodegroups
                reconcile_hanging_groups(network, bend, hanging_groups)
                continue

            if bnet.operstate != 'ACTIVE':
                # CASE-4: Unsynced network state. At this point the network
                # exists and is connected to all nodes so is must be active!
                reconcile_unsynced_network(network, bend, bnet)

            if uses_pool:
                # Get ganeti IP Pools
                available_map, reserved_map = get_network_pool(gnet)
                ip_available_maps.append(available_map)
                ip_reserved_maps.append(reserved_map)

        if uses_pool and (ip_available_maps or ip_reserved_maps):
            # CASE-5: Unsynced IP Pools
            reconcile_ip_pools(network, ip_available_maps, ip_reserved_maps)

        if conflicting_ips:
            detect_conflicting_ips()

    # CASE-6: Orphan networks
    reconcile_orphan_networks(networks, ganeti_networks)


def get_backend_network(network, backend):
    try:
        return BackendNetwork.objects.get(network=network, backend=backend)
    except BackendNetwork.DoesNotExist:
        return None


def reconcile_parted_network(network, backend):
    write("D: Missing DB entry for network %s in backend %s\n" %
          (network, backend))
    if fix:
        network.create_backend_network(backend)
        write("F: Created DB entry\n")
        bnet = get_backend_network(network, backend)
        return bnet


def reconcile_stale_network(backend_network):
    write("D: Stale DB entry for network %s in backend %s\n" %
          (backend_network.network, backend_network.backend))
    if fix:
        etime = datetime.datetime.now()
        backend_mod.process_network_status(backend_network, etime, 0,
                                           "OP_NETWORK_REMOVE",
                                           "success",
                                           "Reconciliation simulated event")
        write("F: Reconciled event: OP_NETWORK_REMOVE\n")


def reconcile_missing_network(network, backend):
    write("D: Missing Ganeti network %s in backend %s\n" %
          (network, backend))
    if fix:
        backend_mod.create_network(network, backend)
        write("F: Issued OP_NETWORK_CONNECT\n")


def reconcile_hanging_groups(network, backend, hanging_groups):
    write('D: Network %s in backend %s is not connected to '
          'the following groups:\n' % (network, backend))
    write('-  ' + '\n-  '.join(hanging_groups) + '\n')
    if fix:
        for group in hanging_groups:
            write('F: Connecting network %s to nodegroup %s\n'
                  % (network, group))
            backend_mod.connect_network(network, backend, depends=[],
                                        group=group)


def reconcile_unsynced_network(network, backend, backend_network):
    write("D: Unsynced network %s in backend %s\n" % (network, backend))
    if fix:
        write("F: Issuing OP_NETWORK_CONNECT\n")
        etime = datetime.datetime.now()
        backend_mod.process_network_status(backend_network, etime, 0,
                                           "OP_NETWORK_CONNECT",
                                           "success",
                                           "Reconciliation simulated eventd")


@transaction.commit_on_success
def reconcile_ip_pools(network, available_maps, reserved_maps):
    available_map = reduce(lambda x, y: x & y, available_maps)
    reserved_map = reduce(lambda x, y: x & y, reserved_maps)

    pool = network.get_pool()
    # Temporary release unused floating IPs
    temp_pool = network.get_pool()
    used_ips = network.nics.values_list("ipv4", flat=True)
    unused_static_ips = network.floating_ips.exclude(ipv4__in=used_ips)
    map(lambda ip: temp_pool.put(ip.ipv4), unused_static_ips)
    if temp_pool.available != available_map:
        write("D: Unsynced available map of network %s:\n"
              "\tDB: %r\n\tGB: %r\n" %
              (network, temp_pool.available.to01(), available_map.to01()))
        if fix:
            pool.available = available_map
            # Release unsued floating IPs, as they are not included in the
            # available map
            map(lambda ip: pool.reserve(ip.ipv4), unused_static_ips)
            pool.save()
    if pool.reserved != reserved_map:
        write("D: Unsynced reserved map of network %s:\n"
              "\tDB: %r\n\tGB: %r\n" %
              (network, pool.reserved.to01(), reserved_map.to01()))
        if fix:
            pool.reserved = reserved_map
            pool.save()


def detect_conflicting_ips(network):
    """Detect NIC's that have the same IP in the same network."""
    machine_ips = network.nics.all().values_list('ipv4', 'machine')
    ips = map(lambda x: x[0], machine_ips)
    distinct_ips = set(ips)
    if len(distinct_ips) < len(ips):
        for i in distinct_ips:
            ips.remove(i)
        for i in ips:
            machines = [utils.id_to_instance_name(x[1])
                        for x in machine_ips if x[0] == i]
            write('D: Conflicting IP:%s Machines: %s\n' %
                  (i, ', '.join(machines)))


def reconcile_orphan_networks(db_networks, ganeti_networks):
    # Detect Orphan Networks in Ganeti
    db_network_ids = set([net.id for net in db_networks])
    for back_end, ganeti_networks in ganeti_networks.items():
        ganeti_network_ids = set(ganeti_networks.keys())
        orphans = ganeti_network_ids - db_network_ids

        if len(orphans) > 0:
            write('D: Orphan Networks in backend %s:\n' % back_end.clustername)
            write('-  ' + '\n-  '.join([str(o) for o in orphans]) + '\n')
            if fix:
                for net_id in orphans:
                    write('Disconnecting and deleting network %d\n' % net_id)
                    try:
                        network = Network.objects.get(id=net_id)
                        backend_mod.delete_network(network,
                                                   backend=back_end)
                    except Network.DoesNotExist:
                        write("Not entry for network %s in DB !!\n" % net_id)


def get_network_pool(gnet):
    """Return available and reserved IP maps.

    Extract the available and reserved IP map from the info return from Ganeti
    for a network.

    """
    converter = IPPool(Foo(gnet['network']))
    a_map = bitarray_from_map(gnet['map'])
    a_map.invert()
    reserved = gnet['external_reservations']
    r_map = a_map.copy()
    r_map.setall(True)
    for address in reserved.split(','):
        index = converter.value_to_index(address)
        a_map[index] = True
        r_map[index] = False
    return a_map, r_map


def bitarray_from_map(bitmap):
    return bitarray.bitarray(bitmap.replace("X", "1").replace(".", "0"))


class Foo():
    def __init__(self, subnet):
        self.available_map = ''
        self.reserved_map = ''
        self.size = 0
        self.network = Foo.Foo1(subnet)

    class Foo1():
        def __init__(self, subnet):
            self.subnet = subnet
            self.gateway = None
