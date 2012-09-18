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
import datetime
import bitarray

from optparse import make_option

from synnefo.settings import PUBLIC_ROUTED_USE_POOL
from django.core.management.base import BaseCommand
from django.db import transaction

from synnefo.db.models import Backend, Network, BackendNetwork
from synnefo.db.pools import IPPool
from synnefo.logic import reconciliation, backend, utils


class Command(BaseCommand):
    help = 'Reconcile contents of Synnefo DB with state of Ganeti backend'
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
        self.verbosity = int(options['verbosity'])
        fix = options['fix']
        conflicting_ips = options['conflicting_ips']
        reconcile_networks(self.stdout, fix, conflicting_ips)


def reconcile_networks(out, fix, conflicting_ips):
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
        net_id = network.id
        destroying = network.action == 'DESTROY'
        uses_pool = not (network.type == 'PUBLIC_ROUTED' and (not
                        PUBLIC_ROUTED_USE_POOL))
        ip_available_maps = []
        ip_reserved_maps = []

        # Perform reconcilliation for each backend
        for b in backends:
            if network.public and not \
                BackendNetwork.objects.filter(network=network,
                                              backend=b).exists():
                    continue

            info = (net_id, b.clustername)
            back_network = None

            try:
                # Get the model describing the network to this backend
                back_network = BackendNetwork.objects.get(network=network,
                                                          backend=b)
            except BackendNetwork.DoesNotExist:
                out.write('D: No DB entry for network %d in backend %s\n' % info)
                if fix:
                    out.write('F: Created entry in DB\n')
                    back_network = \
                        BackendNetwork.objects.create(network=network,
                                                      backend=b)

            try:
                # Get the info from backend
                ganeti_networks[b][net_id]
            except KeyError:
                # Stale network does not exist in backend
                if destroying:
                    out.write('D: Stale network %d in backend %s\n' % info)
                    if fix:
                        out.write("F: Issued OP_NETWORK_REMOVE'\n")
                        etime = datetime.datetime.now()
                        backend.process_network_status(back_network, etime,
                                            0, 'OP_NETWORK_REMOVE', 'success',
                                            'Reconciliation simulated event.')
                    continue
                else:
                    # Pending network
                    out.write('D: Pending network %d in backend %s\n' % info)
                    if fix:
                        out.write('F: Creating network in backend.\n')
                        backend.create_network(network, [b])
                        # Skip rest reconciliation as the network is just
                        # being created
                    continue

            try:
                hanging_groups = ganeti_hanging_networks[b][net_id]
            except KeyError:
                # Network is connected to all nodegroups
                hanging_groups = []

            if hanging_groups and not destroying:
                # Hanging network = not connected to all nodegroups of backend
                out.write('D: Network %d in backend %s is not connected to '
                          'the following groups:\n' % info)
                out.write('-  ' + '\n-  '.join(hanging_groups) + '\n')
                if fix:
                    for group in hanging_groups:
                        out.write('F: Connecting network %d to nodegroup %s\n'
                                  % (net_id, group))
                        backend.connect_network_group(b, network, group)
            elif back_network and back_network.operstate != 'ACTIVE':
                # Network is active
                out.write('D: Unsynced network %d in backend %s\n' % info)
                if fix:
                    out.write("F: Issued OP_NETWORK_CONNECT\n")
                    etime = datetime.datetime.now()
                    backend.process_network_status(back_network, etime,
                                        0, 'OP_NETWORK_CONNECT', 'success',
                                        'Reconciliation simulated event.')

            if uses_pool:
                # Reconcile IP Pools
                gnet = ganeti_networks[b][net_id]
                converter = IPPool(Foo(gnet['network']))
                a_map = bitarray_from_map(gnet['map'])
                reserved = gnet['external_reservations']
                r_map = a_map.copy()
                r_map.setall(True)
                for address in reserved.split(','):
                    index = converter.value_to_index(address)
                    a_map[index] = True
                    r_map[index] = False
                ip_available_maps.append(a_map)
                ip_reserved_maps.append(r_map)

        if uses_pool and (ip_available_maps or ip_reserved_maps):
            available_map = reduce(lambda x, y: x | y, ip_available_maps)
            available_map.invert()
            reserved_map = reduce(lambda x, y: x | y, ip_reserved_maps)

            pool = network.get_pool()
            un_available = pool.available != available_map
            un_reserved = pool.reserved != reserved_map
            if un_available or un_reserved:
                out.write("Detected unsynchronized pool for network %r:\n" %
                          network.id)
                if un_available:
                    out.write("Available:\n\tDB: %r\n\tGB: %r\n" %
                             (pool.available.to01(), available_map.to01()))
                    if fix:
                        pool.available = available_map
                if un_reserved:
                    out.write("Reserved:\n\tDB: %r\n\tGB: %r\n" %
                             (pool.reserved.to01(), reserved_map.to01()))
                    if fix:
                        pool.reserved = reserved_map
                if fix:
                    out.write("Synchronized pools for network %r.\n" % network.id)
            pool.save()

        # Detect conflicting IPs: Detect NIC's that have the same IP
        # in the same network.
        if conflicting_ips:
            machine_ips = network.nics.all().values_list('ipv4', 'machine')
            ips = map(lambda x: x[0], machine_ips)
            distinct_ips = set(ips)
            if len(distinct_ips) < len(ips):
                out.write('D: Conflicting IP in network %s.\n' % net_id)
                conflicts = ips
                for i in distinct_ips:
                    conflicts.remove(i)
                for i in conflicts:
                    machines = [utils.id_to_instance_name(x[1]) \
                                for x in machine_ips if x[0] == i]
                    out.write('\tIP:%s Machines: %s\n' %
                              (i, ', '.join(machines)))
                if fix:
                    out.write('F: Can not fix it. Manually resolve the'
                              ' conflict.\n')

    # Detect Orphan Networks in Ganeti
    db_network_ids = set([net.id for net in networks])
    for back_end, ganeti_networks in ganeti_networks.items():
        ganeti_network_ids = set(ganeti_networks.keys())
        orphans = ganeti_network_ids - db_network_ids

        if len(orphans) > 0:
            out.write('D: Orphan Networks in backend %s:\n' % back_end.clustername)
            out.write('-  ' + '\n-  '.join([str(o) for o in orphans]) + '\n')
            if fix:
                for net_id in orphans:
                    out.write('Disconnecting and deleting network %d\n' % net_id)
                    network = Network.objects.get(id=net_id)
                    backend.delete_network(network, backends=[back_end])


def bitarray_from_map(bitmap):
    return bitarray.bitarray(bitmap.replace("X", "1").replace(".", "0"))


@transaction.commit_on_success
def update_network_reservations(network, reservations):
    network.pool.reservations = reservations
    network.pool.save()


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
