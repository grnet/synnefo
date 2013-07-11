# vim: set fileencoding=utf-8 :
# Copyright 2012 GRNET S.A. All rights reserved.
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
import logging
from django.test import TestCase

from synnefo.db.models import VirtualMachine
from synnefo.db import models_factory as mfactory
from synnefo.logic import reconciliation
from datetime import timedelta
from mock import patch
from snf_django.utils.testing import mocked_quotaholder
from time import time
from synnefo import settings


@patch("synnefo.logic.rapi_pool.GanetiRapiClient")
class ReconciliationTest(TestCase):
    @patch("synnefo.logic.rapi_pool.GanetiRapiClient")
    def setUp(self, mrapi):
        self.backend = mfactory.BackendFactory()
        log = logging.getLogger()
        options = {"fix_unsynced": True,
                   "fix_stale": True,
                   "fix_orphans": True,
                   "fix_unsynced_nics": True,
                   "fix_unsynced_flavors": True}
        self.reconciler = reconciliation.BackendReconciler(self.backend,
                                                           options=options,
                                                           logger=log)

    def test_building_vm(self, mrapi):
        mrapi = self.reconciler.client
        vm1 = mfactory.VirtualMachineFactory(backend=self.backend,
                                             backendjobid=None,
                                             operstate="BUILD")
        self.reconciler.reconcile()
        # Assert not deleted
        vm1 = VirtualMachine.objects.get(id=vm1.id)
        self.assertFalse(vm1.deleted)
        self.assertEqual(vm1.operstate, "BUILD")

        vm1.created = vm1.created - timedelta(seconds=120)
        vm1.save()
        with mocked_quotaholder():
            self.reconciler.reconcile()
        vm1 = VirtualMachine.objects.get(id=vm1.id)
        self.assertEqual(vm1.operstate, "ERROR")

        vm1 = mfactory.VirtualMachineFactory(backend=self.backend,
                                             backendjobid=1,
                                             deleted=False,
                                             operstate="BUILD")
        vm1.backendtime = vm1.created - timedelta(seconds=120)
        vm1.backendjobid = 10
        vm1.save()
        for status in ["queued", "waiting", "running"]:
            mrapi.GetJobStatus.return_value = {"status": status}
            with mocked_quotaholder():
                self.reconciler.reconcile()
            vm1 = VirtualMachine.objects.get(id=vm1.id)
            self.assertFalse(vm1.deleted)
            self.assertEqual(vm1.operstate, "BUILD")

        mrapi.GetJobStatus.return_value = {"status": "error"}
        with mocked_quotaholder():
            self.reconciler.reconcile()
        vm1 = VirtualMachine.objects.get(id=vm1.id)
        self.assertFalse(vm1.deleted)
        self.assertEqual(vm1.operstate, "ERROR")

        for status in ["success", "cancelled"]:
            vm1.deleted = False
            vm1.save()
            mrapi.GetJobStatus.return_value = {"status": status}
            with mocked_quotaholder():
                self.reconciler.reconcile()
            vm1 = VirtualMachine.objects.get(id=vm1.id)
            self.assertTrue(vm1.deleted)
            self.assertEqual(vm1.operstate, "DESTROYED")

        vm1 = mfactory.VirtualMachineFactory(backend=self.backend,
                                             backendjobid=1,
                                             operstate="BUILD")
        vm1.backendtime = vm1.created - timedelta(seconds=120)
        vm1.backendjobid = 10
        vm1.save()
        cmrapi = self.reconciler.client
        cmrapi.GetInstances.return_value = \
            [{"name": vm1.backend_vm_id,
             "beparams": {"maxmem": 1024,
                          "minmem": 1024,
                          "vcpus": 4},
             "oper_state": False,
             "mtime": time(),
             "disk.sizes": [],
             "nic.ips": [],
             "nic.macs": [],
             "nic.networks": [],
             "tags": []}]
        mrapi.GetJobStatus.return_value = {"status": "running"}
        with mocked_quotaholder():
            self.reconciler.reconcile()
        vm1 = VirtualMachine.objects.get(id=vm1.id)
        self.assertEqual(vm1.operstate, "BUILD")
        mrapi.GetJobStatus.return_value = {"status": "error"}
        with mocked_quotaholder():
            self.reconciler.reconcile()
        vm1 = VirtualMachine.objects.get(id=vm1.id)
        self.assertEqual(vm1.operstate, "ERROR")

    def test_stale_server(self, mrapi):
        mrapi.GetInstances = []
        vm1 = mfactory.VirtualMachineFactory(backend=self.backend,
                                             deleted=False,
                                             operstate="ERROR")
        with mocked_quotaholder():
            self.reconciler.reconcile()
        vm1 = VirtualMachine.objects.get(id=vm1.id)
        self.assertTrue(vm1.deleted)

    def test_orphan_server(self, mrapi):
        cmrapi = self.reconciler.client
        mrapi().GetInstances.return_value =\
            [{"name": "%s22" % settings.BACKEND_PREFIX_ID,
             "beparams": {"maxmem": 1024,
                          "minmem": 1024,
                          "vcpus": 4},
             "oper_state": True,
             "mtime": time(),
             "disk.sizes": [],
             "nic.ips": [],
             "nic.macs": [],
             "nic.networks": [],
             "tags": []}]
        self.reconciler.reconcile()
        cmrapi.DeleteInstance\
              .assert_called_once_with("%s22" % settings.BACKEND_PREFIX_ID)

    def test_unsynced_operstate(self, mrapi):
        vm1 = mfactory.VirtualMachineFactory(backend=self.backend,
                                             deleted=False,
                                             operstate="STOPPED")
        mrapi().GetInstances.return_value =\
            [{"name": vm1.backend_vm_id,
             "beparams": {"maxmem": 1024,
                          "minmem": 1024,
                          "vcpus": 4},
             "oper_state": True,
             "mtime": time(),
             "disk.sizes": [],
             "nic.ips": [],
             "nic.macs": [],
             "nic.networks": [],
             "tags": []}]
        with mocked_quotaholder():
            self.reconciler.reconcile()
        vm1 = VirtualMachine.objects.get(id=vm1.id)
        self.assertEqual(vm1.operstate, "STARTED")

    def test_unsynced_flavor(self, mrapi):
        flavor1 = mfactory.FlavorFactory(cpu=2, ram=1024, disk=1,
                                         disk_template="drbd")
        flavor2 = mfactory.FlavorFactory(cpu=4, ram=2048, disk=1,
                                         disk_template="drbd")
        vm1 = mfactory.VirtualMachineFactory(backend=self.backend,
                                             deleted=False,
                                             flavor=flavor1,
                                             operstate="STARTED")
        mrapi().GetInstances.return_value =\
            [{"name": vm1.backend_vm_id,
             "beparams": {"maxmem": 2048,
                          "minmem": 2048,
                          "vcpus": 4},
             "oper_state": True,
             "mtime": time(),
             "disk.sizes": [],
             "nic.ips": [],
             "nic.macs": [],
             "nic.networks": [],
             "tags": []}]
        with mocked_quotaholder():
            self.reconciler.reconcile()
        vm1 = VirtualMachine.objects.get(id=vm1.id)
        self.assertEqual(vm1.flavor, flavor2)
        self.assertEqual(vm1.operstate, "STARTED")

    def test_unsynced_nics(self, mrapi):
        network1 = mfactory.NetworkFactory(subnet="10.0.0.0/24")
        network2 = mfactory.NetworkFactory(subnet="192.168.2.0/24")
        vm1 = mfactory.VirtualMachineFactory(backend=self.backend,
                                             deleted=False,
                                             operstate="STOPPED")
        mfactory.NetworkInterfaceFactory(machine=vm1, network=network1,
                                         ipv4="10.0.0.0")
        mrapi().GetInstances.return_value =\
            [{"name": vm1.backend_vm_id,
             "beparams": {"maxmem": 2048,
                          "minmem": 2048,
                          "vcpus": 4},
             "oper_state": True,
             "mtime": time(),
             "disk.sizes": [],
             "nic.ips": ["192.168.2.1"],
             "nic.macs": ["aa:00:bb:cc:dd:ee"],
             "nic.networks": [network2.backend_id],
             "tags": []}]
        with mocked_quotaholder():
            self.reconciler.reconcile()
        vm1 = VirtualMachine.objects.get(id=vm1.id)
        self.assertEqual(vm1.operstate, "STARTED")
        nic = vm1.nics.all()[0]
        self.assertEqual(nic.network, network2)
        self.assertEqual(nic.ipv4, "192.168.2.1")
        self.assertEqual(nic.mac, "aa:00:bb:cc:dd:ee")
