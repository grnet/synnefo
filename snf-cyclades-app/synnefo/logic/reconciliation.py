# -*- coding: utf-8 -*-
#
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
#
"""Business logic for reconciliation

Reconcile the contents of the DB with the actual state of the
Ganeti backend.

Let D be the set of VMs in the DB, G the set of VMs in Ganeti.
RULES:
    R1. Stale servers in DB:
            For any v in D but not in G:
            Set deleted=True.
    R2. Orphan instances in Ganet:
            For any v in G with deleted=True in D:
            Issue OP_INSTANCE_DESTROY.
    R3. Unsynced operstate:
            For any v whose operating state differs between G and V:
            Set the operating state in D based on the state in G.
In the code, D, G are Python dicts mapping instance ids to operating state.
For D, the operating state is chosen from VirtualMachine.OPER_STATES.
For G, the operating state is True if the machine is up, False otherwise.

"""


from django.conf import settings

import logging
import itertools
import bitarray
from datetime import datetime

from django.db import transaction
from synnefo.db.models import (Backend, VirtualMachine, Flavor,
                               pooled_rapi_client, Network,
                               BackendNetwork)
from synnefo.db.pools import IPPool
from synnefo.logic import utils, backend as backend_mod

logger = logging.getLogger()
logging.basicConfig()

try:
    CHECK_INTERVAL = settings.RECONCILIATION_CHECK_INTERVAL
except AttributeError:
    CHECK_INTERVAL = 60

GANETI_JOB_ERROR = "error"
GANETI_JOBS_PENDING = ["queued", "waiting", "running", "canceling"]
GANETI_JOBS_FINALIZED = ["success", "error", "canceled"]


class BackendReconciler(object):
    def __init__(self, backend, logger, options=None):
        self.backend = backend
        self.log = logger
        self.client = backend.get_client()
        if options is None:
            self.options = {}
        else:
            self.options = options

    def close(self):
        self.backend.put_client(self.client)

    @transaction.commit_on_success
    def reconcile(self):
        log = self.log
        backend = self.backend
        log.debug("Reconciling backend %s", backend)

        self.db_servers = get_database_servers(backend)
        self.db_servers_keys = set(self.db_servers.keys())
        log.debug("Got servers info from database.")

        self.gnt_servers = get_ganeti_servers(backend)
        self.gnt_servers_keys = set(self.gnt_servers.keys())
        log.debug("Got servers info from Ganeti backend.")

        self.gnt_jobs = get_ganeti_jobs(backend)
        log.debug("Got jobs from Ganeti backend")

        self.event_time = datetime.now()

        self.stale_servers = self.reconcile_stale_servers()
        self.orphan_servers = self.reconcile_orphan_servers()
        self.unsynced_servers = self.reconcile_unsynced_servers()
        self.close()

    def get_build_status(self, db_server):
        job_id = db_server.backendjobid
        if job_id in self.gnt_jobs:
            gnt_job_status = self.gnt_jobs[job_id]["status"]
            if gnt_job_status == GANETI_JOB_ERROR:
                return "ERROR"
            elif gnt_job_status not in GANETI_JOBS_FINALIZED:
                return "RUNNING"
            else:
                return "FINALIZED"
        else:
            return "ERROR"

    def reconcile_stale_servers(self):
        # Detect stale servers
        stale = []
        stale_keys = self.db_servers_keys - self.gnt_servers_keys
        for server_id in stale_keys:
            db_server = self.db_servers[server_id]
            if db_server.operstate == "BUILD":
                build_status = self.get_build_status(db_server)
                if build_status == "ERROR":
                    # Special handling of BUILD eerrors
                    self.reconcile_building_server(db_server)
                elif build_status != "RUNNING":
                    stale.append(server_id)
            else:
                stale.append(server_id)

        # Report them
        if stale:
            self.log.info("Found stale servers %s at backend %s",
                          ", ".join(map(str, stale)), self.backend)
        else:
            self.log.debug("No stale servers at backend %s", self.backend)

        # Fix them
        if stale and self.options["fix_stale"]:
            for server_id in stale:
                db_server = self.db_servers[server_id]
                backend_mod.process_op_status(
                    vm=db_server,
                    etime=self.event_time,
                    jobid=-0,
                    opcode='OP_INSTANCE_REMOVE', status='success',
                    logmsg='Reconciliation: simulated Ganeti event')
            self.log.debug("Simulated Ganeti removal for stale servers.")

    def reconcile_orphan_servers(self):
        orphans = self.gnt_servers_keys - self.db_servers_keys
        if orphans:
            self.log.info("Found orphan servers %s at backend %s",
                          ", ".join(map(str, orphans)), self.backend)
        else:
            self.log.debug("No orphan servers at backend %s", self.backend)

        if orphans and self.options["fix_orphans"]:
            for server_id in orphans:
                server_name = utils.id_to_instance_name(server_id)
                self.client.DeleteInstance(server_name)
            self.log.debug("Issued OP_INSTANCE_REMOVE for orphan servers.")

    def reconcile_unsynced_servers(self):
        #log = self.log
        for server_id in self.db_servers_keys & self.gnt_servers_keys:
            db_server = self.db_servers[server_id]
            gnt_server = self.gnt_servers[server_id]
            if db_server.operstate == "BUILD":
                build_status = self.get_build_status(db_server)
                if build_status == "RUNNING":
                    # Do not reconcile building VMs
                    continue
                elif build_status == "ERROR":
                    # Special handling of build errors
                    self.reconcile_building_server(db_server)
                    continue

            self.reconcile_unsynced_operstate(server_id, db_server,
                                              gnt_server)
            self.reconcile_unsynced_flavor(server_id, db_server,
                                           gnt_server)
            self.reconcile_unsynced_nics(server_id, db_server, gnt_server)
            self.reconcile_unsynced_disks(server_id, db_server, gnt_server)
            if db_server.task is not None:
                self.reconcile_pending_task(server_id, db_server)

    def reconcile_building_server(self, db_server):
        self.log.info("Server '%s' is BUILD in DB, but 'ERROR' in Ganeti.",
                      db_server.id)
        if self.options["fix_unsynced"]:
            fix_opcode = "OP_INSTANCE_CREATE"
            backend_mod.process_op_status(
                vm=db_server,
                etime=self.event_time,
                jobid=-0,
                opcode=fix_opcode, status='error',
                logmsg='Reconciliation: simulated Ganeti event')
            self.log.debug("Simulated Ganeti error build event for"
                           " server '%s'", db_server.id)

    def reconcile_unsynced_operstate(self, server_id, db_server, gnt_server):
        if db_server.operstate != gnt_server["state"]:
            self.log.info("Server '%s' is '%s' in DB and '%s' in Ganeti.",
                          server_id, db_server.operstate, gnt_server["state"])
            if self.options["fix_unsynced"]:
                # If server is in building state, you will have first to
                # reconcile it's creation, to avoid wrong quotas
                if db_server.operstate == "BUILD":
                    backend_mod.process_op_status(
                        vm=db_server, etime=self.event_time, jobid=-0,
                        opcode="OP_INSTANCE_CREATE", status='success',
                        logmsg='Reconciliation: simulated Ganeti event')
                fix_opcode = "OP_INSTANCE_STARTUP"\
                    if gnt_server["state"] == "STARTED"\
                    else "OP_INSTANCE_SHUTDOWN"
                backend_mod.process_op_status(
                    vm=db_server, etime=self.event_time, jobid=-0,
                    opcode=fix_opcode, status='success',
                    logmsg='Reconciliation: simulated Ganeti event')
                self.log.debug("Simulated Ganeti state event for server '%s'",
                               server_id)

    def reconcile_unsynced_flavor(self, server_id, db_server, gnt_server):
        db_flavor = db_server.flavor
        gnt_flavor = gnt_server["flavor"]
        if (db_flavor.ram != gnt_flavor["ram"] or
           db_flavor.cpu != gnt_flavor["vcpus"]):
            try:
                gnt_flavor = Flavor.objects.get(
                    ram=gnt_flavor["ram"],
                    cpu=gnt_flavor["vcpus"],
                    disk=db_flavor.disk,
                    disk_template=db_flavor.disk_template)
            except Flavor.DoesNotExist:
                self.log.warning("Server '%s' has unknown flavor.", server_id)
                return

            self.log.info("Server '%s' has flavor '%s' in DB and '%s' in"
                          " Ganeti", server_id, db_flavor, gnt_flavor)
            if self.options["fix_unsynced_flavors"]:
                old_state = db_server.operstate
                opcode = "OP_INSTANCE_SET_PARAMS"
                beparams = {"vcpus": gnt_flavor.cpu,
                            "minmem": gnt_flavor.ram,
                            "maxmem": gnt_flavor.ram}
                backend_mod.process_op_status(
                    vm=db_server, etime=self.event_time, jobid=-0,
                    opcode=opcode, status='success',
                    beparams=beparams,
                    logmsg='Reconciliation: simulated Ganeti event')
                # process_op_status with beparams will set the vmstate to
                # shutdown. Fix this be returning it to old state
                vm = VirtualMachine.objects.get(pk=server_id)
                vm.operstate = old_state
                vm.save()
                self.log.debug("Simulated Ganeti flavor event for server '%s'",
                               server_id)

    def reconcile_unsynced_nics(self, server_id, db_server, gnt_server):
        db_nics = db_server.nics.order_by("index")
        gnt_nics = gnt_server["nics"]
        gnt_nics_parsed = backend_mod.process_ganeti_nics(gnt_nics)
        if backend_mod.nics_changed(db_nics, gnt_nics_parsed):
            msg = "Found unsynced NICs for server '%s'.\n\t"\
                  "DB: %s\n\tGaneti: %s"
            db_nics_str = ", ".join(map(format_db_nic, db_nics))
            gnt_nics_str = ", ".join(map(format_gnt_nic, gnt_nics_parsed))
            self.log.info(msg, server_id, db_nics_str, gnt_nics_str)
            if self.options["fix_unsynced_nics"]:
                backend_mod.process_net_status(vm=db_server,
                                               etime=self.event_time,
                                               nics=gnt_nics)

    def reconcile_unsynced_disks(self, server_id, db_server, gnt_server):
        pass

    def reconcile_pending_task(self, server_id, db_server):
        job_id = db_server.task_job_id
        pending_task = False
        if job_id not in self.gnt_jobs:
            pending_task = True
        else:
            gnt_job_status = self.gnt_jobs[job_id]["status"]
            if gnt_job_status in GANETI_JOBS_FINALIZED:
                pending_task = True

        if pending_task:
            self.log.info("Found server '%s' with pending task: '%s'",
                          server_id, db_server.task)
            if self.options["fix_pending_tasks"]:
                db_server.task = None
                db_server.task_job_id = None
                db_server.save()
                self.log.info("Cleared pending task for server '%s", server_id)


def format_db_nic(nic):
    return "Index: %s, IP: %s Network: %s MAC: %s Firewall: %s" % (nic.index,
           nic.ipv4, nic.network_id, nic.mac, nic.firewall_profile)


def format_gnt_nic(nic):
    return "Index: %s IP: %s Network: %s MAC: %s Firewall: %s" %\
           (nic["index"], nic["ipv4"], nic["network"], nic["mac"],
            nic["firewall_profile"])


#
# Networks
#


def get_networks_from_ganeti(backend):
    prefix = settings.BACKEND_PREFIX_ID + 'net-'

    networks = {}
    with pooled_rapi_client(backend) as c:
        for net in c.GetNetworks(bulk=True):
            if net['name'].startswith(prefix):
                id = utils.id_from_network_name(net['name'])
                networks[id] = net

    return networks


def hanging_networks(backend, GNets):
    """Get networks that are not connected to all Nodegroups.

    """
    def get_network_groups(group_list):
        groups = set()
        for g in group_list:
            g_name = g.split('(')[0]
            groups.add(g_name)
        return groups

    with pooled_rapi_client(backend) as c:
        groups = set(c.GetGroups())

    hanging = {}
    for id, info in GNets.items():
        group_list = get_network_groups(info['group_list'])
        if group_list != groups:
            hanging[id] = groups - group_list
    return hanging


def get_online_backends():
    return Backend.objects.filter(offline=False)


def get_database_servers(backend):
    servers = backend.virtual_machines.select_related("nics", "flavor")\
                                      .filter(deleted=False)
    return dict([(s.id, s) for s in servers])


def get_ganeti_servers(backend):
    gnt_instances = backend_mod.get_instances(backend)
    # Filter out non-synnefo instances
    snf_backend_prefix = settings.BACKEND_PREFIX_ID
    gnt_instances = filter(lambda i: i["name"].startswith(snf_backend_prefix),
                           gnt_instances)
    gnt_instances = map(parse_gnt_instance, gnt_instances)
    return dict([(i["id"], i) for i in gnt_instances if i["id"] is not None])


def parse_gnt_instance(instance):
    try:
        instance_id = utils.id_from_instance_name(instance['name'])
    except Exception:
        logger.error("Ignoring instance with malformed name %s",
                     instance['name'])
        return (None, None)

    beparams = instance["beparams"]

    vcpus = beparams["vcpus"]
    ram = beparams["maxmem"]
    state = instance["oper_state"] and "STARTED" or "STOPPED"

    return {
        "id": instance_id,
        "state": state,  # FIX
        "updated": datetime.fromtimestamp(instance["mtime"]),
        "disks": disks_from_instance(instance),
        "nics": nics_from_instance(instance),
        "flavor": {"vcpus": vcpus,
                   "ram": ram},
        "tags": instance["tags"]
    }


def nics_from_instance(i):
    ips = zip(itertools.repeat('ip'), i['nic.ips'])
    macs = zip(itertools.repeat('mac'), i['nic.macs'])
    networks = zip(itertools.repeat('network'), i['nic.networks'])
    # modes = zip(itertools.repeat('mode'), i['nic.modes'])
    # links = zip(itertools.repeat('link'), i['nic.links'])
    # nics = zip(ips,macs,modes,networks,links)
    nics = zip(ips, macs, networks)
    nics = map(lambda x: dict(x), nics)
    #nics = dict(enumerate(nics))
    tags = i["tags"]
    for tag in tags:
        t = tag.split(":")
        if t[0:2] == ["synnefo", "network"]:
            if len(t) != 4:
                logger.error("Malformed synefo tag %s", tag)
                continue
            try:
                index = int(t[2])
                nics[index]['firewall'] = t[3]
            except ValueError:
                logger.error("Malformed synnefo tag %s", tag)
            except IndexError:
                logger.error("Found tag %s for non-existent NIC %d",
                             tag, index)
    return nics


def get_ganeti_jobs(backend):
    gnt_jobs = backend_mod.get_jobs(backend)
    return dict([(int(j["id"]), j) for j in gnt_jobs])


def disks_from_instance(i):
    return dict([(index, {"size": size})
                 for index, size in enumerate(i["disk.sizes"])])


class NetworkReconciler(object):
    def __init__(self, logger, fix=False, conflicting_ips=False):
        self.log = logger
        self.conflicting_ips = conflicting_ips
        self.fix = fix

    @transaction.commit_on_success
    def reconcile_networks(self):
        # Get models from DB
        backends = Backend.objects.exclude(offline=True)
        networks = Network.objects.filter(deleted=False)

        self.event_time = datetime.now()

        # Get info from all ganeti backends
        ganeti_networks = {}
        ganeti_hanging_networks = {}
        for b in backends:
            g_nets = get_networks_from_ganeti(b)
            ganeti_networks[b] = g_nets
            g_hanging_nets = hanging_networks(b, g_nets)
            ganeti_hanging_networks[b] = g_hanging_nets

        # Perform reconciliation for each network
        for network in networks:
            ip_available_maps = []
            ip_reserved_maps = []
            for bend in backends:
                bnet = get_backend_network(network, bend)
                gnet = ganeti_networks[bend].get(network.id)
                if not bnet:
                    if network.floating_ip_pool:
                        # Network is a floating IP pool and does not exist in
                        # backend. We need to create it
                        bnet = self.reconcile_parted_network(network, bend)
                    elif not gnet:
                        # Network does not exist either in Ganeti nor in BD.
                        continue
                    else:
                        # Network exists in Ganeti and not in DB.
                        if network.action != "DESTROY" and not network.public:
                            bnet = self.reconcile_parted_network(network, bend)
                        else:
                            continue

                if not gnet:
                    # Network does not exist in Ganeti. If the network action
                    # is DESTROY, we have to mark as deleted in DB, else we
                    # have to create it in Ganeti.
                    if network.action == "DESTROY":
                        if bnet.operstate != "DELETED":
                            self.reconcile_stale_network(bnet)
                    else:
                        self.reconcile_missing_network(network, bend)
                    # Skip rest reconciliation!
                    continue

                try:
                    hanging_groups = ganeti_hanging_networks[bend][network.id]
                except KeyError:
                    # Network is connected to all nodegroups
                    hanging_groups = []

                if hanging_groups:
                    # CASE-3: Ganeti networks not connected to all nodegroups
                    self.reconcile_hanging_groups(network, bend,
                                                  hanging_groups)
                    continue

                if bnet.operstate != 'ACTIVE':
                    # CASE-4: Unsynced network state. At this point the network
                    # exists and is connected to all nodes so is must be
                    # active!
                    self.reconcile_unsynced_network(network, bend, bnet)

                # Get ganeti IP Pools
                available_map, reserved_map = get_network_pool(gnet)
                ip_available_maps.append(available_map)
                ip_reserved_maps.append(reserved_map)

            if ip_available_maps or ip_reserved_maps:
                # CASE-5: Unsynced IP Pools
                self.reconcile_ip_pools(network, ip_available_maps,
                                        ip_reserved_maps)

            if self.conflicting_ips:
                self.detect_conflicting_ips()

        # CASE-6: Orphan networks
        self.reconcile_orphan_networks(networks, ganeti_networks)

    def reconcile_parted_network(self, network, backend):
        self.log.info("D: Missing DB entry for network %s in backend %s",
                      network, backend)
        if self.fix:
            network.create_backend_network(backend)
            self.log.info("F: Created DB entry")
            bnet = get_backend_network(network, backend)
            return bnet

    def reconcile_stale_network(self, backend_network):
        self.log.info("D: Stale DB entry for network %s in backend %s",
                      backend_network.network, backend_network.backend)
        if self.fix:
            backend_mod.process_network_status(
                backend_network, self.event_time, 0,
                "OP_NETWORK_REMOVE",
                "success",
                "Reconciliation simulated event")
            self.log.info("F: Reconciled event: OP_NETWORK_REMOVE")

    def reconcile_missing_network(self, network, backend):
        self.log.info("D: Missing Ganeti network %s in backend %s",
                      network, backend)
        if self.fix:
            backend_mod.create_network(network, backend)
            self.log.info("F: Issued OP_NETWORK_CONNECT")

    def reconcile_hanging_groups(self, network, backend, hanging_groups):
        self.log.info('D: Network %s in backend %s is not connected to '
                      'the following groups:', network, backend)
        self.log.info('-  ' + '\n-  '.join(hanging_groups))
        if self.fix:
            for group in hanging_groups:
                self.log.info('F: Connecting network %s to nodegroup %s',
                              network, group)
                backend_mod.connect_network(network, backend, depends=[],
                                            group=group)

    def reconcile_unsynced_network(self, network, backend, backend_network):
        self.log.info("D: Unsynced network %s in backend %s", network, backend)
        if self.fix:
            self.log.info("F: Issuing OP_NETWORK_CONNECT")
            backend_mod.process_network_status(
                backend_network, self.event_time, 0,
                "OP_NETWORK_CONNECT",
                "success",
                "Reconciliation simulated eventd")

    def reconcile_ip_pools(self, network, available_maps, reserved_maps):
        available_map = reduce(lambda x, y: x & y, available_maps)
        reserved_map = reduce(lambda x, y: x & y, reserved_maps)

        pool = network.get_pool()
        # Temporary release unused floating IPs
        temp_pool = network.get_pool()
        used_ips = network.nics.values_list("ipv4", flat=True)
        unused_static_ips = network.floating_ips.exclude(ipv4__in=used_ips)
        map(lambda ip: temp_pool.put(ip.ipv4), unused_static_ips)
        if temp_pool.available != available_map:
            self.log.info("D: Unsynced available map of network %s:\n"
                          "\tDB: %r\n\tGB: %r", network,
                          temp_pool.available.to01(),
                          available_map.to01())
            if self.fix:
                pool.available = available_map
                # Release unsued floating IPs, as they are not included in the
                # available map
                map(lambda ip: pool.reserve(ip.ipv4), unused_static_ips)
                pool.save()
        if pool.reserved != reserved_map:
            self.log.info("D: Unsynced reserved map of network %s:\n"
                          "\tDB: %r\n\tGB: %r", network, pool.reserved.to01(),
                          reserved_map.to01())
            if self.fix:
                pool.reserved = reserved_map
                pool.save()

    def detect_conflicting_ips(self, network):
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
                self.log.info('D: Conflicting IP:%s Machines: %s',
                              i, ', '.join(machines))

    def reconcile_orphan_networks(self, db_networks, ganeti_networks):
        # Detect Orphan Networks in Ganeti
        db_network_ids = set([net.id for net in db_networks])
        for back_end, ganeti_networks in ganeti_networks.items():
            ganeti_network_ids = set(ganeti_networks.keys())
            orphans = ganeti_network_ids - db_network_ids

            if len(orphans) > 0:
                self.log.info('D: Orphan Networks in backend %s:',
                              back_end.clustername)
                self.log.info('-  ' + '\n-  '.join([str(o) for o in orphans]))
                if self.fix:
                    for net_id in orphans:
                        self.log.info('Disconnecting and deleting network %d',
                                      net_id)
                        try:
                            network = Network.objects.get(id=net_id)
                            backend_mod.delete_network(network,
                                                       backend=back_end)
                        except Network.DoesNotExist:
                            self.log.info("Not entry for network %s in DB !!",
                                          net_id)


def get_backend_network(network, backend):
    try:
        return BackendNetwork.objects.get(network=network, backend=backend)
    except BackendNetwork.DoesNotExist:
        return None


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
    if reserved:
        for address in reserved.split(','):
            index = converter.value_to_index(address.strip())
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
