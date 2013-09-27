#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2011 GRNET S.A. All rights reserved.
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

import logging
import sys
import itertools
from datetime import datetime, timedelta

from synnefo.db.models import (VirtualMachine, pooled_rapi_client)
from synnefo.logic.rapi import GanetiApiError
from synnefo.logic.backend import get_ganeti_instances, get_backends
from synnefo.logic import utils
from django.conf import settings


log = logging.getLogger()

try:
    CHECK_INTERVAL = settings.RECONCILIATION_CHECK_INTERVAL
except AttributeError:
    CHECK_INTERVAL = 60


def needs_reconciliation(vm):
    now = datetime.now()
    return (now > vm.updated + timedelta(seconds=CHECK_INTERVAL)) or\
           (now > vm.backendtime + timedelta(seconds=2*CHECK_INTERVAL))


def stale_servers_in_db(D, G):
    idD = set(D.keys())
    idG = set(G.keys())

    stale = set()
    for i in idD - idG:
        if D[i] == 'BUILD':
            vm = VirtualMachine.objects.get(id=i)
            if needs_reconciliation(vm):
                with pooled_rapi_client(vm) as c:
                    try:
                        job_status = c.GetJobStatus(vm.backendjobid)['status']
                        if job_status in ('queued', 'waiting', 'running'):
                            # Server is still building in Ganeti
                            continue
                        else:
                            c.GetInstance(utils.id_to_instance_name(i))
                            # Server has just been created in Ganeti
                            continue
                    except GanetiApiError:
                        stale.add(i)
        else:
            stale.add(i)

    return stale


def orphan_instances_in_ganeti(D, G):
    idD = set(D.keys())
    idG = set(G.keys())

    return idG - idD


def unsynced_operstate(D, G):
    unsynced = set()
    idD = set(D.keys())
    idG = set(G.keys())

    for i in idD & idG:
        vm_unsynced = (G[i] and D[i] != "STARTED") or\
                      (not G[i] and D[i] not in ('BUILD', 'ERROR', 'STOPPED'))
        if vm_unsynced:
            unsynced.add((i, D[i], G[i]))
        if not G[i] and D[i] == 'BUILD':
            vm = VirtualMachine.objects.get(id=i)
            if needs_reconciliation(vm):
                with pooled_rapi_client(vm) as c:
                    try:
                        job_info = c.GetJobStatus(job_id=vm.backendjobid)
                        if job_info['status'] == 'success':
                            unsynced.add((i, D[i], G[i]))
                    except GanetiApiError:
                        pass

    return unsynced


def instances_with_build_errors(D, G):
    failed = set()
    idD = set(D.keys())
    idG = set(G.keys())

    for i in idD & idG:
        if not G[i] and D[i] == 'BUILD':
            vm = VirtualMachine.objects.get(id=i)
            if not vm.backendjobid:  # VM has not been enqueued in the backend
                if datetime.now() > vm.created + timedelta(seconds=120):
                    # If a job has not been enqueued after 2 minutues, then
                    # it must be a stale entry..
                    failed.add(i)
            elif needs_reconciliation(vm):
                # Check time to avoid many rapi calls
                with pooled_rapi_client(vm) as c:
                    try:
                        job_info = c.GetJobStatus(job_id=vm.backendjobid)
                        if job_info['status'] == 'error':
                            failed.add(i)
                    except GanetiApiError:
                        failed.add(i)

    return failed


def get_servers_from_db(backend=None):
    backends = get_backends(backend)
    vms = VirtualMachine.objects.filter(deleted=False, backend__in=backends)
    return dict(map(lambda x: (x.id, x.operstate), vms))


def get_instances_from_ganeti(backend=None):
    ganeti_instances = get_ganeti_instances(backend=backend, bulk=True)
    snf_instances = {}
    snf_nics = {}

    prefix = settings.BACKEND_PREFIX_ID
    for i in ganeti_instances:
        if i['name'].startswith(prefix):
            try:
                id = utils.id_from_instance_name(i['name'])
            except Exception:
                log.error("Ignoring instance with malformed name %s",
                          i['name'])
                continue

            if id in snf_instances:
                log.error("Ignoring instance with duplicate Synnefo id %s",
                          i['name'])
                continue

            snf_instances[id] = i['oper_state']
            snf_nics[id] = get_nics_from_instance(i)

    return snf_instances, snf_nics


#
# Nics
#
def get_nics_from_ganeti(backend=None):
    """Get network interfaces for each ganeti instance.

    """
    instances = get_ganeti_instances(backend=backend, bulk=True)
    prefix = settings.BACKEND_PREFIX_ID

    snf_instances_nics = {}
    for i in instances:
        if i['name'].startswith(prefix):
            try:
                id = utils.id_from_instance_name(i['name'])
            except Exception:
                log.error("Ignoring instance with malformed name %s",
                          i['name'])
                continue
            if id in snf_instances_nics:
                log.error("Ignoring instance with duplicate Synnefo id %s",
                          i['name'])
                continue

            snf_instances_nics[id] = get_nics_from_instance(i)

    return snf_instances_nics


def get_nics_from_instance(i):
    ips = zip(itertools.repeat('ipv4'), i['nic.ips'])
    macs = zip(itertools.repeat('mac'), i['nic.macs'])
    networks = zip(itertools.repeat('network'), i['nic.networks'])
    # modes = zip(itertools.repeat('mode'), i['nic.modes'])
    # links = zip(itertools.repeat('link'), i['nic.links'])
    # nics = zip(ips,macs,modes,networks,links)
    nics = zip(ips, macs, networks)
    nics = map(lambda x: dict(x), nics)
    nics = dict(enumerate(nics))
    return nics


def get_nics_from_db(backend=None):
    """Get network interfaces for each vm in DB.

    """
    backends = get_backends(backend)
    instances = VirtualMachine.objects.filter(deleted=False,
                                              backend__in=backends)
    instances_nics = {}
    for instance in instances:
        nics = {}
        for n in instance.nics.all():
            ipv4 = n.ipv4
            nic = {'mac':      n.mac,
                   'network':  n.network.backend_id,
                   'ipv4':     ipv4 if ipv4 != '' else None
                   }
            nics[n.index] = nic
        instances_nics[instance.id] = nics
    return instances_nics


def unsynced_nics(DBNics, GNics):
    """Find unsynced network interfaces between DB and Ganeti.

    @ rtype: dict; {instance_id: ganeti_nics}
    @ return Dictionary containing the instances ids that have unsynced network
    interfaces between DB and Ganeti and the network interfaces in Ganeti.

    """
    idD = set(DBNics.keys())
    idG = set(GNics.keys())

    unsynced = {}
    for i in idD & idG:
        nicsD = DBNics[i]
        nicsG = GNics[i]
        if len(nicsD) != len(nicsG):
            unsynced[i] = (nicsD, nicsG)
            continue
        for index in nicsG.keys():
            nicD = nicsD[index]
            nicG = nicsG[index]
            diff = (nicD['ipv4'] != nicG['ipv4'] or
                    nicD['mac'] != nicG['mac'] or
                    nicD['network'] != nicG['network'])
            if diff:
                    unsynced[i] = (nicsD, nicsG)
                    break

    return unsynced

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
