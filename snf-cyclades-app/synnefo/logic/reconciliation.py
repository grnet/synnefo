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


from django.core.management import setup_environ
try:
    from synnefo import settings
except ImportError:
    raise Exception("Cannot import settings, make sure PYTHONPATH contains "
                    "the parent directory of the Synnefo Django project.")
setup_environ(settings)


import logging
import itertools
from datetime import datetime, timedelta

from django.db import transaction
from synnefo.db.models import (Backend, VirtualMachine, Flavor,
                               pooled_rapi_client)
from synnefo.logic import utils, backend as backend_mod
from synnefo.logic.rapi import GanetiApiError

logger = logging.getLogger()
logging.basicConfig()

try:
    CHECK_INTERVAL = settings.RECONCILIATION_CHECK_INTERVAL
except AttributeError:
    CHECK_INTERVAL = 60


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

        self.event_time = datetime.now()

        self.stale_servers = self.reconcile_stale_servers()
        self.orphan_servers = self.reconcile_orphan_servers()
        self.unsynced_servers = self.reconcile_unsynced_servers()
        self.close()

    def get_build_status(self, db_server):
        job = db_server.backendjobid
        if job is None:
            created = db_server.created
            # Job has not yet been enqueued.
            if self.event_time < created + timedelta(seconds=60):
                return "RUNNING"
            else:
                return "ERROR"
        else:
            updated = db_server.backendtime
            if self.event_time >= updated + timedelta(seconds=60):
                try:
                    job_info = self.client.GetJobStatus(job_id=job)
                    finalized = ["success", "error", "cancelled"]
                    if job_info["status"] == "error":
                        return "ERROR"
                    elif job_info["status"] not in finalized:
                        return "RUNNING"
                    else:
                        return "FINALIZED"
                except GanetiApiError:
                    return "ERROR"
            else:
                self.log.debug("Pending build for server '%s'", db_server.id)
                return "RUNNING"

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
                fix_opcode = \
                    "OP_INSTANCE_STARTUP" if gnt_server["state"] == "STARTED"\
                    else "OP_INSTANCE_SHUTDOWN"
                backend_mod.process_op_status(
                    vm=db_server,
                    etime=self.event_time,
                    jobid=-0,
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

            self.log.info("Server '%s' has flavor '%' in DB and '%s' in"
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


def format_db_nic(nic):
    return "Index: %s IP: %s Network: %s MAC: %s Firewall: %s" % (nic.index,
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


def disks_from_instance(i):
    return dict([(index, {"size": size})
                 for index, size in enumerate(i["disk.sizes"])])
