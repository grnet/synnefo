# vim: set fileencoding=utf-8 :
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
                   "fix_unsynced_disks": True,
                   "fix_unsynced_flavors": True}
        self.reconciler = reconciliation.BackendReconciler(self.backend,
                                                           options=options,
                                                           logger=log)

    def test_building_vm(self, mrapi):
        vm1 = mfactory.VirtualMachineFactory(backend=self.backend,
                                             backendjobid=1,
                                             operstate="BUILD")
        for status in ["queued", "waiting", "running"]:
            mrapi().GetJobs.return_value = [{"id": "1", "status": status,
                                             "end_ts": None}]
            with mocked_quotaholder():
                self.reconciler.reconcile()
            vm1 = VirtualMachine.objects.get(id=vm1.id)
            self.assertFalse(vm1.deleted)
            self.assertEqual(vm1.operstate, "BUILD")

        mrapi().GetJobs.return_value = [{"id": "1", "status": "error",
                                         "end_ts": [44123, 1]}]
        with mocked_quotaholder():
            self.reconciler.reconcile()
        vm1 = VirtualMachine.objects.get(id=vm1.id)
        self.assertFalse(vm1.deleted)
        self.assertEqual(vm1.operstate, "ERROR")

        for status in ["success", "canceled"]:
            vm1.operstate = "BUILD"
            vm1.deleted = False
            vm1.save()
            mrapi().GetJobs.return_value = [{"id": "1", "status": status,
                                            "end_ts": [44123, 1]}]
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
             "disk.names": [],
             "disk.uuids": [],
             "nic.ips": [],
             "nic.names": [],
             "nic.macs": [],
             "nic.networks.names": [],
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
             "disk.names": [],
             "disk.uuids": [],
             "nic.ips": [],
             "nic.names": [],
             "nic.macs": [],
             "nic.networks.names": [],
             "tags": []}]
        with mocked_quotaholder():
            self.reconciler.reconcile()
        vm1 = VirtualMachine.objects.get(id=vm1.id)
        self.assertEqual(vm1.operstate, "STARTED")

    def test_unsynced_flavor(self, mrapi):
        flavor1 = mfactory.FlavorFactory(cpu=2, ram=1024, disk=1,
                                         volume_type__disk_template="drbd")
        flavor2 = mfactory.FlavorFactory(cpu=4, ram=2048, disk=1,
                                         volume_type__disk_template="drbd")
        vm1 = mfactory.VirtualMachineFactory(backend=self.backend,
                                             deleted=False,
                                             flavor=flavor1,
                                             operstate="STARTED")
        v1 = mfactory.VolumeFactory(machine=vm1, size=flavor1.disk,
                volume_type=flavor1.volume_type)
        mrapi().GetInstances.return_value =\
            [{"name": vm1.backend_vm_id,
             "beparams": {"maxmem": 2048,
                          "minmem": 2048,
                          "vcpus": 4},
             "oper_state": True,
             "mtime": time(),
             "disk.sizes": [1024],
             "disk.names": [v1.backend_volume_uuid],
             "disk.uuids": [v1.backend_disk_uuid],
             "nic.ips": [],
             "nic.names": [],
             "nic.macs": [],
             "nic.networks.names": [],
             "tags": []}]
        with mocked_quotaholder():
            self.reconciler.reconcile()
        vm1 = VirtualMachine.objects.get(id=vm1.id)
        self.assertEqual(vm1.flavor, flavor2)
        self.assertEqual(vm1.operstate, "STARTED")

    def test_unsynced_nics(self, mrapi):
        network1 = mfactory.NetworkWithSubnetFactory(
            subnet__cidr="10.0.0.0/24", subnet__gateway="10.0.0.2")
        network2 = mfactory.NetworkWithSubnetFactory(
            subnet__cidr="192.168.2.0/24", subnet__gateway="192.168.2.2")
        vm1 = mfactory.VirtualMachineFactory(backend=self.backend,
                                             deleted=False,
                                             operstate="STOPPED")
        subnet = network1.subnets.get(ipversion=4)
        ip = mfactory.IPv4AddressFactory(nic__machine=vm1, network=network1,
                                         subnet=subnet,
                                         address="10.0.0.3")
        nic = ip.nic
        mrapi().GetInstances.return_value =\
            [{"name": vm1.backend_vm_id,
             "beparams": {"maxmem": 2048,
                          "minmem": 2048,
                          "vcpus": 4},
             "oper_state": True,
             "mtime": time(),
             "disk.sizes": [],
             "disk.names": [],
             "disk.uuids": [],
             "nic.names": [nic.backend_uuid],
             "nic.ips": ["192.168.2.5"],
             "nic.macs": ["aa:00:bb:cc:dd:ee"],
             "nic.networks.names": [network2.backend_id],
             "tags": []}]
        with mocked_quotaholder():
            self.reconciler.reconcile()
        vm1 = VirtualMachine.objects.get(id=vm1.id)
        self.assertEqual(vm1.operstate, "STARTED")
        nic = vm1.nics.all()[0]
        self.assertEqual(nic.network, network2)
        self.assertEqual(nic.ipv4_address, "192.168.2.5")
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
        net1 = mfactory.NetworkWithSubnetFactory(public=False)
        mrapi().GetNetworks.return_value = []
        # Test nothing if Ganeti returns nothing
        self.assertEqual(net1.backend_networks.count(), 0)
        self.reconciler.reconcile_networks()
        self.assertEqual(net1.backend_networks.count(), 0)

        # Test creation if exists in Ganeti
        self.assertEqual(net1.backend_networks.count(), 0)
        mrapi().GetNetworks.return_value = [{"name": net1.backend_id,
                                             "group_list": [["default",
                                                             "bridged",
                                                             "prv0",
                                                             "1"]],
                                             "network": net1.subnet4.cidr,
                                             "map": "....",
                                             "external_reservations": ""}]
        self.reconciler.reconcile_networks()
        self.assertTrue(net1.backend_networks
                        .filter(backend=self.backend).exists())

    def test_stale_network(self, mrapi):
        # Test that stale network will be deleted from DB, if network action is
        # destroy
        net1 = mfactory.NetworkWithSubnetFactory(public=False,
                                                 flavor="IP_LESS_ROUTED",
                                                 action="DESTROY",
                                                 deleted=False)
        bn1 = mfactory.BackendNetworkFactory(network=net1,
                                             backend=self.backend,
                                             operstate="ACTIVE")
        mrapi().GetNetworks.return_value = []
        self.assertFalse(net1.deleted)
        with mocked_quotaholder():
            self.reconciler.reconcile_networks()
        net1 = Network.objects.get(id=net1.id)
        self.assertTrue(net1.deleted)
        self.assertFalse(net1.backend_networks.filter(id=bn1.id).exists())
        # But not if action is not DESTROY
        net2 = mfactory.NetworkWithSubnetFactory(public=False, action="CREATE")
        mfactory.BackendNetworkFactory(network=net2, backend=self.backend)
        self.assertFalse(net2.deleted)
        self.reconciler.reconcile_networks()
        self.assertFalse(net2.deleted)

    def test_missing_network(self, mrapi):
        net2 = mfactory.NetworkWithSubnetFactory(public=False, action="CREATE")
        mfactory.BackendNetworkFactory(network=net2, backend=self.backend)
        mrapi().GetNetworks.return_value = []
        self.reconciler.reconcile_networks()
        self.assertEqual(len(mrapi().CreateNetwork.mock_calls), 1)

    #def test_hanging_networks(self, mrapi):
    #    pass

    def test_unsynced_networks(self, mrapi):
        net = mfactory.NetworkWithSubnetFactory(public=False, state="PENDING",
                                                action="CREATE", deleted=False)
        bn = mfactory.BackendNetworkFactory(network=net, backend=self.backend,
                                            operstate="PENDING")
        mrapi().GetNetworks.return_value = [{"name": net.backend_id,
                                             "group_list": [],
                                             "network": net.subnet4.cidr,
                                             "map": "....",
                                             "external_reservations": ""}]
        self.assertEqual(bn.operstate, "PENDING")
        self.reconciler.reconcile_networks()
        bn = BackendNetwork.objects.get(id=bn.id)
        self.assertEqual(bn.operstate, "ACTIVE")

    def test_orphan_networks(self, mrapi):
        net = mfactory.NetworkWithSubnetFactory(public=False, action="CREATE",
                                                deleted=True)
        mrapi().GetNetworks.return_value = [{"name": net.backend_id,
                                             "group_list": [],
                                             "network": net.subnet4.cidr,
                                             "map": "....",
                                             "external_reservations": ""}]
        self.reconciler.reconcile_networks()
        mrapi().DeleteNetwork.assert_called_once_with(net.backend_id, [])
