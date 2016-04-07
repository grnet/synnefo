# -*- coding: utf-8 -*-
#
# Copyright (C) 2010-2014 GRNET S.A.
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
import simplejson as json
from datetime import datetime, timedelta

from synnefo.db import transaction
from synnefo.db.models import (Backend, VirtualMachine, Flavor,
                               pooled_rapi_client, Network,
                               BackendNetwork, BridgePoolTable,
                               MacPrefixPoolTable)
from synnefo.db import pools
from synnefo.logic import utils, rapi, backend as backend_mod
from synnefo.lib.utils import merge_time
from synnefo.plankton.backend import (PlanktonBackend, OBJECT_UNAVAILABLE,
                                      OBJECT_ERROR)

logger = logging.getLogger()
logging.basicConfig()

BUILDING_NIC_TIMEOUT = timedelta(seconds=120)


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

        self.event_time = datetime.now()

        self.db_servers = get_database_servers(backend)
        self.db_servers_keys = set(self.db_servers.keys())
        log.debug("Got servers info from database.")

        self.gnt_servers = get_ganeti_servers(backend)
        self.gnt_servers_keys = set(self.gnt_servers.keys())
        log.debug("Got servers info from Ganeti backend.")

        self.gnt_jobs = get_ganeti_jobs(backend)
        log.debug("Got jobs from Ganeti backend")

        self.stale_servers = self.reconcile_stale_servers()
        self.orphan_servers = self.reconcile_orphan_servers()
        self.unsynced_servers = self.reconcile_unsynced_servers()
        self.unsynced_snapshots = self.reconcile_unsynced_snapshots()
        self.close()

    def get_build_status(self, db_server):
        """Return the status of the build job.

        Return whether the job is RUNNING, FINALIZED or ERROR, together
        with the timestamp that the job finished (if any).

        """
        job_id = db_server.backendjobid
        if job_id in self.gnt_jobs:
            job = self.gnt_jobs[job_id]
            gnt_job_status = job["status"]
            end_timestamp = job["end_ts"]
            if end_timestamp is not None:
                end_timestamp = merge_time(end_timestamp)
            if gnt_job_status == rapi.JOB_STATUS_ERROR:
                return "ERROR", end_timestamp
            elif gnt_job_status not in rapi.JOB_STATUS_FINALIZED:
                return "RUNNING", None
            else:
                return "FINALIZED", end_timestamp
        else:
            return "ERROR", None

    def reconcile_stale_servers(self):
        # Detect stale servers
        stale = []
        stale_keys = self.db_servers_keys - self.gnt_servers_keys
        for server_id in stale_keys:
            db_server = self.db_servers[server_id]
            if db_server.operstate == "BUILD":
                build_status, end_timestamp = self.get_build_status(db_server)
                if build_status == "ERROR":
                    # Special handling of BUILD eerrors
                    self.reconcile_building_server(db_server)
                elif build_status != "RUNNING":
                    stale.append(server_id)
            elif (db_server.operstate == "ERROR" and
                  db_server.action != "DESTROY"):
                # Servers at building ERROR are stale only if the user has
                # asked to destroy them.
                pass
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
                vm = get_locked_server(server_id)
                backend_mod.process_op_status(
                    vm=vm,
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
        for server_id in self.db_servers_keys & self.gnt_servers_keys:
            db_server = self.db_servers[server_id]
            gnt_server = self.gnt_servers[server_id]
            if db_server.operstate == "BUILD":
                build_status, end_timestamp = self.get_build_status(db_server)
                if build_status == "RUNNING":
                    # Do not reconcile building VMs
                    continue
                elif build_status == "ERROR":
                    # Special handling of build errors
                    self.reconcile_building_server(db_server)
                    continue
                elif end_timestamp >= self.event_time:
                    # Do not continue reconciliation for building server that
                    # the build job completed after quering the state of
                    # Ganeti servers.
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
            vm = get_locked_server(db_server.id)
            backend_mod.process_op_status(
                vm=vm,
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
                vm = get_locked_server(server_id)
                # If server is in building state, you will have first to
                # reconcile it's creation, to avoid wrong quotas
                if db_server.operstate == "BUILD":
                    backend_mod.process_op_status(
                        vm=vm, etime=self.event_time, jobid=-0,
                        opcode="OP_INSTANCE_CREATE", status='success',
                        logmsg='Reconciliation: simulated Ganeti event')
                fix_opcode = "OP_INSTANCE_STARTUP"\
                    if gnt_server["state"] == "STARTED"\
                    else "OP_INSTANCE_SHUTDOWN"
                backend_mod.process_op_status(
                    vm=vm, etime=self.event_time, jobid=-0,
                    opcode=fix_opcode, status='success',
                    logmsg='Reconciliation: simulated Ganeti event')
                self.log.debug("Simulated Ganeti state event for server '%s'",
                               server_id)

    def reconcile_unsynced_flavor(self, server_id, db_server, gnt_server):
        db_flavor = db_server.flavor
        gnt_flavor = gnt_server["flavor"]
        if (db_flavor.ram != gnt_flavor["ram"] or
           db_flavor.cpu != gnt_flavor["vcpus"] or
           db_flavor.disk != gnt_flavor["disk"]):
            try:
                gnt_flavor = Flavor.objects.get(
                    ram=gnt_flavor["ram"],
                    cpu=gnt_flavor["vcpus"],
                    disk=gnt_flavor["disk"],
                    volume_type_id=db_flavor.volume_type_id)
            except Flavor.DoesNotExist:
                self.log.warning("Server '%s' has unknown flavor.", server_id)
                return

            self.log.info("Server '%s' has flavor '%s' in DB and '%s' in"
                          " Ganeti", server_id, db_flavor, gnt_flavor)
            if self.options["fix_unsynced_flavors"]:
                vm = get_locked_server(server_id)
                old_state = vm.operstate
                opcode = "OP_INSTANCE_SET_PARAMS"
                beparams = {"vcpus": gnt_flavor.cpu,
                            "minmem": gnt_flavor.ram,
                            "maxmem": gnt_flavor.ram}
                backend_mod.process_op_status(
                    vm=vm, etime=self.event_time, jobid=-0,
                    opcode=opcode, status='success',
                    job_fields={"beparams": beparams},
                    logmsg='Reconciliation: simulated Ganeti event')
                # process_op_status with beparams will set the vmstate to
                # shutdown. Fix this be returning it to old state
                vm = VirtualMachine.objects.get(pk=server_id)
                vm.operstate = old_state
                vm.save()
                self.log.debug("Simulated Ganeti flavor event for server '%s'",
                               server_id)

    def reconcile_unsynced_nics(self, server_id, db_server, gnt_server):
        building_time = self.event_time - BUILDING_NIC_TIMEOUT
        db_nics = db_server.nics.exclude(state="BUILD",
                                         created__lte=building_time) \
                                .order_by("id")
        gnt_nics = gnt_server["nics"]
        try:
            gnt_nics_parsed = backend_mod.parse_instance_nics(gnt_nics)
        except Network.InvalidBackendIdError as e:
            self.log.warning("Server %s is connected to unknown network %s"
                             " Cannot reconcile server." % (server_id, str(e)))
            return
        nics_changed = len(db_nics) != len(gnt_nics)
        for db_nic, gnt_nic in zip(db_nics, sorted(gnt_nics_parsed.items())):
            gnt_nic_id, gnt_nic = gnt_nic
            if (db_nic.id == gnt_nic_id) and\
               backend_mod.nics_are_equal(db_nic, gnt_nic):
                continue
            else:
                nics_changed = True
                break
        if nics_changed:
            msg = "Found unsynced NICs for server '%s'.\n"\
                  "\tDB:\n\t\t%s\n\tGaneti:\n\t\t%s"
            db_nics_str = "\n\t\t".join(map(format_db_nic, db_nics))
            gnt_nics_str = "\n\t\t".join(map(format_gnt_nic,
                                         sorted(gnt_nics_parsed.items())))
            self.log.info(msg, server_id, db_nics_str, gnt_nics_str)
            if self.options["fix_unsynced_nics"]:
                vm = get_locked_server(server_id)
                backend_mod.process_op_status(
                    vm=vm, etime=self.event_time, jobid=-0,
                    opcode="OP_INSTANCE_SET_PARAMS", status='success',
                    logmsg="Reconciliation: simulated Ganeti event",
                    nics=gnt_nics)

    def reconcile_unsynced_disks(self, server_id, db_server, gnt_server):
        building_time = self.event_time - BUILDING_NIC_TIMEOUT
        db_disks = db_server.volumes.exclude(status="CREATING",
                                             created__lte=building_time) \
                                    .filter(deleted=False)\
                                    .order_by("id")
        gnt_disks = gnt_server["disks"]
        gnt_disks_parsed = backend_mod.parse_instance_disks(gnt_disks)
        disks_changed = len(db_disks) != len(gnt_disks)
        for db_disk, gnt_disk in zip(db_disks,
                                     sorted(gnt_disks_parsed.items())):
            gnt_disk_id, gnt_disk = gnt_disk
            if (db_disk.id == gnt_disk_id) and\
               backend_mod.disks_are_equal(db_disk, gnt_disk):
                continue
            else:
                disks_changed = True
                break
        if disks_changed:
            msg = "Found unsynced disks for server '%s'.\n"\
                  "\tDB:\n\t\t%s\n\tGaneti:\n\t\t%s"
            db_disks_str = "\n\t\t".join(map(format_db_disk, db_disks))
            gnt_disks_str = "\n\t\t".join(map(format_gnt_disk,
                                          sorted(gnt_disks_parsed.items())))
            self.log.info(msg, server_id, db_disks_str, gnt_disks_str)
            if self.options["fix_unsynced_disks"]:
                vm = get_locked_server(server_id)
                backend_mod.process_op_status(
                    vm=vm, etime=self.event_time, jobid=-0,
                    opcode="OP_INSTANCE_SET_PARAMS", status='success',
                    logmsg="Reconciliation: simulated Ganeti event",
                    disks=gnt_disks)

    def reconcile_pending_task(self, server_id, db_server):
        job_id = db_server.task_job_id
        pending_task = False
        if job_id not in self.gnt_jobs:
            pending_task = True
        else:
            gnt_job_status = self.gnt_jobs[job_id]["status"]
            if gnt_job_status in rapi.JOB_STATUS_FINALIZED:
                pending_task = True

        if pending_task:
            db_server = get_locked_server(server_id)
            if db_server.task_job_id != job_id:
                # task has changed!
                return
            self.log.info("Found server '%s' with pending task: '%s'",
                          server_id, db_server.task)
            if self.options["fix_pending_tasks"]:
                db_server.task = None
                db_server.task_job_id = None
                db_server.save()
                self.log.info("Cleared pending task for server '%s", server_id)

    def reconcile_unsynced_snapshots(self):
        # Find the biggest ID of the retrieved Ganeti jobs. Reconciliation
        # will be performed for IDs that are smaller from this.
        max_job_id = max(self.gnt_jobs.keys()) if self.gnt_jobs.keys() else 0

        with PlanktonBackend(None) as b:
            snapshots = b.list_snapshots(check_permissions=False)
        unavail_snapshots = [s for s in snapshots
                             if s["status"] == OBJECT_UNAVAILABLE]

        for snapshot in unavail_snapshots:
            uuid = snapshot["id"]
            backend_info = snapshot["backend_info"]
            if backend_info is None:
                self.log.warning("Cannot perform reconciliation for"
                                 " snapshot '%s'. Not enough information.",
                                 uuid)
                continue
            job_info = json.loads(backend_info)
            backend_id = job_info["ganeti_backend_id"]
            job_id = job_info["ganeti_job_id"]

            if backend_id == self.backend.id and job_id <= max_job_id:
                if job_id in self.gnt_jobs:
                    job_status = self.gnt_jobs[job_id]["status"]
                    state = \
                        backend_mod.snapshot_state_from_job_status(job_status)
                    if state == OBJECT_UNAVAILABLE:
                        continue
                else:
                    # Snapshot in unavailable but no job exists
                    state = OBJECT_ERROR

                self.log.info("Snapshot '%s' is '%s' in Pithos DB but should"
                              " be '%s'", uuid, snapshot["status"], state)
                if self.options["fix_unsynced_snapshots"]:
                    backend_mod.update_snapshot(uuid, snapshot["owner"],
                                                job_id=-1,
                                                job_status=job_status,
                                                etime=self.event_time)
                    self.log.info("Fixed state of snapshot '%s'.", uuid)


NIC_MSG = ": %s\t".join(["ID", "State", "IP", "Network", "MAC", "Index",
                         "Firewall"]) + ": %s"


def format_db_nic(nic):
    return NIC_MSG % (nic.id, nic.state, nic.ipv4_address, nic.network_id,
                      nic.mac, nic.index, nic.firewall_profile)


def format_gnt_nic(nic):
    nic_name, nic = nic
    return NIC_MSG % (nic_name, nic["state"], nic["ipv4_address"],
                      nic["network"].id, nic["mac"], nic["index"],
                      nic["firewall_profile"])

DISK_MSG = ": %s\t".join(["ID", "State", "Size", "Index"]) + ": %s"


def format_db_disk(disk):
    return DISK_MSG % (disk.id, disk.status, disk.size, disk.index)


def format_gnt_disk(disk):
    disk_name, disk = disk
    return DISK_MSG % (disk_name, disk["status"], disk["size"], disk["index"])


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
        # Since ganeti 2.10 networks are connected to nodegroups
        # with mode and link AND vlan (ovs extra nicparam)
        for group_info in group_list:
            groups.add(group_info[0])
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
    servers = backend.virtual_machines.select_related("flavor")\
                                      .prefetch_related("nics__ips__subnet")\
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

    disks = disks_from_instance(instance)
    root_disk = [d for d in disks if d['index'] == 0]
    if root_disk:
        disk = (int(root_disk[0].get('size', 0)) >> 10)
    else:
        disk = 0

    flavor = {
        'vcpus': vcpus,
        'ram': ram,
        'disk': disk
    }

    return {
        "id": instance_id,
        "state": state,  # FIX
        "updated": datetime.fromtimestamp(instance["mtime"]),
        "disks": disks,
        "nics": nics_from_instance(instance),
        "flavor": flavor,
        "tags": instance["tags"]
    }


def nics_from_instance(i):
    ips = zip(itertools.repeat('ip'), i['nic.ips'])
    names = zip(itertools.repeat('name'), i['nic.names'])
    macs = zip(itertools.repeat('mac'), i['nic.macs'])
    networks = zip(itertools.repeat('network'), i['nic.networks.names'])
    indexes = zip(itertools.repeat('index'), range(0, len(ips)))
    # modes = zip(itertools.repeat('mode'), i['nic.modes'])
    # links = zip(itertools.repeat('link'), i['nic.links'])
    # nics = zip(ips,macs,modes,networks,links)
    nics = zip(ips, names, macs, networks, indexes)
    nics = map(lambda x: dict(x), nics)
    tags = i["tags"]
    for tag in tags:
        t = tag.split(":")
        if t[0:2] == ["synnefo", "network"]:
            if len(t) != 4:
                logger.error("Malformed synefo tag %s", tag)
                continue
            nic_name = t[2]
            firewall = t[3]
            [nic.setdefault("firewall", firewall)
             for nic in nics if nic["name"] == nic_name]
    return nics


def disks_from_instance(i):
    sizes = zip(itertools.repeat('size'), i['disk.sizes'])
    names = zip(itertools.repeat('name'), i['disk.names'])
    uuids = zip(itertools.repeat('uuid'), i['disk.uuids'])
    indexes = zip(itertools.repeat('index'), range(0, len(sizes)))
    disks = zip(sizes, names, uuids, indexes)
    disks = map(lambda x: dict(x), disks)
    return disks


def get_ganeti_jobs(backend):
    gnt_jobs = backend_mod.get_jobs(backend)
    return dict([(int(j["id"]), j) for j in gnt_jobs])


class NetworkReconciler(object):
    def __init__(self, logger, fix=False):
        self.log = logger
        self.fix = fix

    @transaction.commit_on_success
    def reconcile_networks(self):
        # Get models from DB
        self.backends = Backend.objects.exclude(offline=True)
        self.networks = Network.objects.filter(deleted=False)

        self.event_time = datetime.now()

        # Get info from all ganeti backends
        self.ganeti_networks = {}
        self.ganeti_hanging_networks = {}
        for b in self.backends:
            g_nets = get_networks_from_ganeti(b)
            self.ganeti_networks[b] = g_nets
            g_hanging_nets = hanging_networks(b, g_nets)
            self.ganeti_hanging_networks[b] = g_hanging_nets

        self._reconcile_orphan_networks()

        for network in self.networks:
            self._reconcile_network(network)

    @transaction.commit_on_success
    def _reconcile_network(self, network):
        """Reconcile a network with corresponging Ganeti networks.

        Reconcile a Network and the associated BackendNetworks with the
        corresponding Ganeti networks in all Ganeti backends.

        """
        if network.subnets.filter(ipversion=4, dhcp=True).exists():
            ip_pools = network.get_ip_pools()  # X-Lock on IP pools
        else:
            ip_pools = None
        for bend in self.backends:
            bnet = get_backend_network(network, bend)
            gnet = self.ganeti_networks[bend].get(network.id)
            if bnet is None and gnet is not None:
                # Network exists in backend but not in DB for this backend
                bnet = self.reconcile_parted_network(network, bend)

            if bnet is None:
                continue

            if gnet is None:
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
                hanging_groups = self.ganeti_hanging_networks[bend][network.id]
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

            # Check that externally reserved IPs of the network in Ganeti are
            # also externally reserved to the IP pool
            externally_reserved = gnet['external_reservations']
            if externally_reserved and ip_pools is not None:
                for ip in externally_reserved.split(","):
                    ip = ip.strip()
                    for ip_pool in ip_pools:
                        if ip_pool.contains(ip):
                            if not ip_pool.is_reserved(ip):
                                msg = ("D: IP '%s' is reserved for network"
                                       " '%s' in backend '%s' but not in DB.")
                                self.log.info(msg, ip, network, bend)
                                if self.fix:
                                    ip_pool.reserve(ip, external=True)
                                    ip_pool.save()
                                    self.log.info("F: Reserved IP '%s'", ip)
        if network.state != "ACTIVE":
            network = Network.objects.select_for_update().get(id=network.id)
            backend_mod.update_network_state(network)

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
            backend_network = BackendNetwork.objects.select_for_update()\
                                                    .get(id=backend_network.id)
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
            backend_network = BackendNetwork.objects.select_for_update()\
                                                    .get(id=backend_network.id)
            backend_mod.process_network_status(
                backend_network, self.event_time, 0,
                "OP_NETWORK_CONNECT",
                "success",
                "Reconciliation simulated eventd")

    def _reconcile_orphan_networks(self):
        db_networks = self.networks
        ganeti_networks = self.ganeti_networks
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


class PoolReconciler(object):
    def __init__(self, logger, fix=False):
        self.log = logger
        self.fix = fix

    def reconcile(self):
        self.reconcile_bridges()
        self.reconcile_mac_prefixes()

        networks = Network.objects.prefetch_related("subnets")\
                                  .filter(deleted=False)
        for network in networks:
            for subnet in network.subnets.all():
                if subnet.ipversion == 4 and subnet.dhcp:
                    self.reconcile_ip_pool(network)

    @transaction.commit_on_success
    def reconcile_bridges(self):
        networks = Network.objects.filter(deleted=False,
                                          flavor="PHYSICAL_VLAN")
        check_unique_values(objects=networks, field='link', logger=self.log)
        try:
            pool = BridgePoolTable.get_pool()
        except pools.EmptyPool:
            self.log.info("There is no available pool for bridges.")
            return

        # Since pool is locked, no new networks may be created
        used_bridges = set(networks.values_list('link', flat=True))
        check_pool_consistent(pool=pool, pool_class=pools.BridgePool,
                              used_values=used_bridges, fix=self.fix,
                              logger=self.log)

    @transaction.commit_on_success
    def reconcile_mac_prefixes(self):
        networks = Network.objects.filter(deleted=False, flavor="MAC_FILTERED")
        check_unique_values(objects=networks, field='mac_prefix',
                            logger=self.log)
        try:
            pool = MacPrefixPoolTable.get_pool()
        except pools.EmptyPool:
            self.log.info("There is no available pool for MAC prefixes.")
            return

        # Since pool is locked, no new network may be created
        used_mac_prefixes = set(networks.values_list('mac_prefix', flat=True))
        check_pool_consistent(pool=pool, pool_class=pools.MacPrefixPool,
                              used_values=used_mac_prefixes, fix=self.fix,
                              logger=self.log)

    @transaction.commit_on_success
    def reconcile_ip_pool(self, network):
        # Check that all NICs have unique IPv4 address
        nics = network.ips.exclude(address__isnull=True).all()
        check_unique_values(objects=nics, field="address", logger=self.log)

        for ip_pool in network.get_ip_pools():
            # IP pool is now locked, so no new IPs may be created
            used_ips = ip_pool.pool_table.subnet\
                              .ips.exclude(address__isnull=True)\
                              .exclude(deleted=True)\
                              .values_list("address", flat=True)
            used_ips = filter(lambda x: ip_pool.contains(x), used_ips)
            check_pool_consistent(pool=ip_pool,
                                  pool_class=pools.IPPool,
                                  used_values=used_ips,
                                  fix=self.fix, logger=self.log)


def check_unique_values(objects, field, logger):
    used_values = list(objects.values_list(field, flat=True))
    if len(used_values) != len(set(used_values)):
        duplicate_values = [v for v in used_values if used_values.count(v) > 1]
        for value in duplicate_values:
            filter_args = {field: value}
            using_objects = objects.filter(**filter_args)
            msg = "Value '%s' is used as %s for more than one objects: %s"
            logger.error(msg, value, field, ",".join(map(str, using_objects)))
        return False
    logger.debug("Values for field '%s' are unique.", field)
    return True


def check_pool_consistent(pool, pool_class, used_values, fix, logger):
    dummy_pool = create_empty_pool(pool, pool_class)
    [dummy_pool.reserve(value) for value in used_values]
    if dummy_pool.available != pool.available:
        msg = "'%s' is not consistent!\nPool: %s\nUsed: %s"
        pool_diff = dummy_pool.available ^ pool.available
        for index in pool_diff.itersearch(bitarray.bitarray("1")):
            value = pool.index_to_value(int(index))
            msg = "%s is incosistent! Value '%s' is %s but should be %s."
            value1 = pool.is_available(value) and "available" or "unavailable"
            value2 = dummy_pool.is_available(value) and "available"\
                or "unavailable"
            logger.error(msg, pool, value, value1, value2)
        if fix:
            pool.available = dummy_pool.available
            pool.save()
            logger.info("Fixed available map of pool '%s'", pool)


def create_empty_pool(pool, pool_class):
    pool_row = pool.pool_table
    pool_row.available_map = ""
    pool_row.reserved_map = ""
    return pool_class(pool_row)


def get_locked_server(server_id):
    return VirtualMachine.objects.select_for_update().get(id=server_id)
