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

from django.core.management import setup_environ
try:
    from synnefo import settings
except ImportError:
    raise Exception("Cannot import settings, make sure PYTHONPATH contains "
                    "the parent directory of the Synnefo Django project.")
setup_environ(settings)


from datetime import datetime, timedelta

from synnefo.db.models import VirtualMachine
from synnefo.util.dictconfig import dictConfig
from synnefo.util.rapi import GanetiApiError
from synnefo.logic.backend import get_ganeti_instances


log = logging.getLogger()


def stale_servers_in_db(D, G):
    idD = set(D.keys())
    idG = set(G.keys())

    stale = set()
    for i in idD - idG:
        if D[i] == 'BUILD':
            vm = VirtualMachine.objects.get(id=i)
            # Check time to avoid many rapi calls
            if datetime.now() > vm.backendtime + timedelta(seconds=5):
                try:
                    job_status = vm.client.GetJobStatus(vm.backendjobid)['status']
                    if job_status in ('queued', 'waiting', 'running'):
                        # Server is still building in Ganeti
                        continue
                    else:
                        new_vm = vm.client.GetInstance('%s%d' %
                                (settings.BACKEND_PREFIX_ID, i))
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
        if (G[i] and D[i] != 'STARTED' or
            not G[i] and D[i] not in ('BUILD', 'ERROR', 'STOPPED')):
            unsynced.add((i, D[i], G[i]))
        if not G[i] and D[i] == 'BUILD':
            vm = VirtualMachine.objects.get(id=i)
            # Check time to avoid many rapi calls
            if datetime.now() > vm.backendtime + timedelta(seconds=5):
                try:
                    job_info = vm.client.GetJobStatus(job_id = vm.backendjobid)
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
            # Check time to avoid many rapi calls
            if datetime.now() > vm.backendtime + timedelta(seconds=5):
                try:
                    job_info = vm.client.GetJobStatus(job_id = vm.backendjobid)
                    if job_info['status'] == 'error':
                        failed.add(i)
                except GanetiApiError:
                    failed.add(i)

    return failed



def get_servers_from_db():
    vms = VirtualMachine.objects.filter(deleted=False)
    return dict(map(lambda x: (x.id, x.operstate), vms))


def get_instances_from_ganeti():
    ganeti_instances = get_ganeti_instances(bulk=True)
    snf_instances = {}

    prefix = settings.BACKEND_PREFIX_ID
    for i in ganeti_instances:
        if i['name'].startswith(prefix):
            try:
                id = int(i['name'].split(prefix)[1])
            except Exception:
                log.error("Ignoring instance with malformed name %s",
                              i['name'])
                continue

            if id in snf_instances:
                log.error("Ignoring instance with duplicate Synnefo id %s",
                    i['name'])
                continue

            snf_instances[id] = i['oper_state']

    return snf_instances


# Only for testing this module individually
def main():
    print get_instances_from_ganeti()


if __name__ == "__main__":
    sys.exit(main())
