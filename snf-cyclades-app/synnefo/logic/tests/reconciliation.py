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

from synnefo.db.models import VirtualMachine, Network, BackendNetwork
from synnefo.db import models_factory as mfactory
from synnefo.logic import reconciliation
from mock import patch
from snf_django.utils.testing import mocked_quotaholder
from time import time
from synnefo import settings


@patch("synnefo.logic.rapi_pool.GanetiRapiClient")
class ServerReconciliationTest(TestCase):
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
        vm1 = mfactory.VirtualMachineFactory(backend=self.backend,
                                             backendjobid=1,
                                             operstate="BUILD")
        for status in ["queued", "waiting", "running"]:
            mrapi().GetJobs.return_value = [{"id": "1", "status": status}]
            with mocked_quotaholder():
                self.reconciler.reconcile()
            vm1 = VirtualMachine.objects.get(id=vm1.id)
            self.assertFalse(vm1.deleted)
            self.assertEqual(vm1.operstate, "BUILD")

        mrapi().GetJobs.return_value = [{"id": "1", "status": "error"}]
        with mocked_quotaholder():
            self.reconciler.reconcile()
        vm1 = VirtualMachine.objects.get(id=vm1.id)
        self.assertFalse(vm1.deleted)
        self.assertEqual(vm1.operstate, "ERROR")

        for status in ["success", "canceled"]:
            vm1.operstate = "BUILD"
            vm1.deleted = False
            vm1.save()
            mrapi().GetJobs.return_value = [{"id": "1", "status": status}]
            with mocked_quotaholder():
                self.reconciler.reconcile()
            vm1 = VirtualMachine.objects.get(id=vm1.id)
            self.assertFalse(vm1.deleted)
            self.assertEqual(vm1.operstate, "ERROR")

    def test_stale_server(self, mrapi):
        mrapi.GetInstances = []
        vm1 = mfactory.VirtualMachineFactory(backend=self.backend,
                                             deleted=False,
                                             operstate="ERROR")

        with mocked_quotaholder():
            self.reconciler.reconcile()
        vm1 = VirtualMachine.objects.get(id=vm1.id)
        self.assertFalse(vm1.deleted)
        vm2 = mfactory.VirtualMachineFactory(backend=self.backend,
                                             deleted=False,
                                             action="DESTROY",
                                             operstate="ERROR")
        with mocked_quotaholder():
            self.reconciler.reconcile()
        vm2 = VirtualMachine.objects.get(id=vm2.id)
        self.assertTrue(vm2.deleted)
        vm3 = mfactory.VirtualMachineFactory(backend=self.backend,
                                             deleted=False,
                                             action="DESTROY",
                                             operstate="ACTIVE")
        with mocked_quotaholder():
            self.reconciler.reconcile()
        vm3 = VirtualMachine.objects.get(id=vm3.id)
        self.assertTrue(vm3.deleted)

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


@patch("synnefo.logic.rapi_pool.GanetiRapiClient")
class NetworkReconciliationTest(TestCase):
    def setUp(self):
        self.backend = mfactory.BackendFactory()
        log = logging.getLogger()
        self.reconciler = reconciliation.NetworkReconciler(
            logger=log,
            fix=True)

    def test_parted_network(self, mrapi):
        net1 = mfactory.NetworkFactory(subnet="192.168.0.0/30", public=False)
        mrapi().GetNetworks.return_value = []
        # Test nothing if Ganeti returns nothing
        self.assertEqual(net1.backend_networks.count(), 0)
        self.reconciler.reconcile_networks()
        self.assertEqual(net1.backend_networks.count(), 0)

        # Test creation if exists in Ganeti
        self.assertEqual(net1.backend_networks.count(), 0)
        mrapi().GetNetworks.return_value = [{"name": net1.backend_id,
                                             "group_list": ["default"],
                                             "network": net1.subnet,
                                             "map": "....",
                                             "external_reservations": ""}]
        self.reconciler.reconcile_networks()
        self.assertTrue(net1.backend_networks
                            .filter(backend=self.backend).exists())
        # ..but not if it is destroying
        net1.backend_networks.all().delete()
        net1.action = "DESTROY"
        net1.save()
        self.reconciler.reconcile_networks()
        self.assertFalse(net1.backend_networks
                             .filter(backend=self.backend).exists())
        # or network is public!
        net1.action = "CREATE"
        net1.public = True
        net1.save()
        self.reconciler.reconcile_networks()
        self.assertFalse(net1.backend_networks
                             .filter(backend=self.backend).exists())
        # Test creation if network is a floating IP pool
        net2 = mfactory.NetworkFactory(subnet="192.168.0.0/30",
                                       floating_ip_pool=True)
        mrapi().GetNetworks.return_value = []
        self.assertEqual(net2.backend_networks.count(), 0)
        self.reconciler.reconcile_networks()
        self.assertTrue(net2.backend_networks
                            .filter(backend=self.backend).exists())

    def test_stale_network(self, mrapi):
        # Test that stale network will be deleted from DB, if network action is
        # destroy
        net1 = mfactory.NetworkFactory(subnet="192.168.0.0/30", public=False,
                                       flavor="IP_LESS_ROUTED",
                                       action="DESTROY", deleted=False)
        bn1 = mfactory.BackendNetworkFactory(network=net1,
                                             backend=self.backend,
                                             operstate="ACTIVE")
        mrapi().GetNetworks.return_value = []
        self.assertFalse(net1.deleted)
        with mocked_quotaholder():
            self.reconciler.reconcile_networks()
        bn1 = BackendNetwork.objects.get(id=bn1.id)
        net1 = Network.objects.get(id=net1.id)
        self.assertEqual(bn1.operstate, "DELETED")
        self.assertTrue(net1.deleted)
        # But not if action is not DESTROY
        net2 = mfactory.NetworkFactory(subnet="192.168.0.0/30", public=False,
                                       action="CREATE")
        mfactory.BackendNetworkFactory(network=net2, backend=self.backend)
        self.assertFalse(net2.deleted)
        self.reconciler.reconcile_networks()
        self.assertFalse(net2.deleted)

    def test_missing_network(self, mrapi):
        net2 = mfactory.NetworkFactory(subnet="192.168.0.0/30", public=False,
                                       action="CREATE")
        mfactory.BackendNetworkFactory(network=net2, backend=self.backend)
        mrapi().GetNetworks.return_value = []
        self.reconciler.reconcile_networks()
        self.assertEqual(len(mrapi().CreateNetwork.mock_calls), 1)

    #def test_hanging_networks(self, mrapi):
    #    pass

    def test_unsynced_networks(self, mrapi):
        net = mfactory.NetworkFactory(subnet="192.168.0.0/30", public=False,
                                      state="PENDING",
                                      action="CREATE", deleted=False)
        bn = mfactory.BackendNetworkFactory(network=net, backend=self.backend,
                                            operstate="PENDING")
        mrapi().GetNetworks.return_value = [{"name": net.backend_id,
                                             "group_list": [],
                                             "network": net.subnet,
                                             "map": "....",
                                             "external_reservations": ""}]
        self.assertEqual(bn.operstate, "PENDING")
        self.reconciler.reconcile_networks()
        bn = BackendNetwork.objects.get(id=bn.id)
        self.assertEqual(bn.operstate, "ACTIVE")

    def test_orphan_networks(self, mrapi):
        net = mfactory.NetworkFactory(subnet="192.168.0.0/30", public=False,
                                      action="CREATE", deleted=True)
        mrapi().GetNetworks.return_value = [{"name": net.backend_id,
                                             "group_list": [],
                                             "network": net.subnet,
                                             "map": "....",
                                             "external_reservations": ""}]
        self.reconciler.reconcile_networks()
        mrapi().DeleteNetwork.assert_called_once_with(net.backend_id, [])
