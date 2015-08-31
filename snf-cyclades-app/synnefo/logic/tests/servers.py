# vim: set fileencoding=utf-8 :
# Copyright (C) 2010-2015 GRNET S.A. and individual contributors
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

# Provides automated tests for logic module
from django.test import TransactionTestCase
#from snf_django.utils.testing import mocked_quotaholder
from synnefo.logic import servers
from synnefo.logic import backend
from synnefo import quotas
from synnefo.db import models_factory as mfactory, models
from mock import patch, Mock

from snf_django.lib.api import faults
from snf_django.utils.testing import mocked_quotaholder, override_settings
from django.conf import settings
from copy import deepcopy

fixed_image = Mock()
fixed_image.return_value = {'location': 'pithos://foo',
                            'mapfile': 'test_mapfile',
                            "id": 1,
                            "name": "test_image",
                            "version": 42,
                            "is_public": True,
                            "owner": "user2",
                            "status": "AVAILABLE",
                            "size": 1000,
                            "is_snapshot": False,
                            'disk_format': 'diskdump'}


@patch('synnefo.api.util.get_image', fixed_image)
@patch("synnefo.logic.rapi_pool.GanetiRapiClient")
class ServerCreationTest(TransactionTestCase):
    def test_create(self, mrapi):
        flavor = mfactory.FlavorFactory()
        kwargs = {
            "userid": "test",
            "name": "test_vm",
            "password": "1234",
            "flavor": flavor,
            "image_id": "safs",
            "networks": [],
            "metadata": {"foo": "bar"},
            "personality": [],
        }
        # no backend!
        mfactory.BackendFactory(offline=True)
        self.assertRaises(faults.ServiceUnavailable, servers.create, **kwargs)
        self.assertEqual(models.VirtualMachine.objects.count(), 0)

        mfactory.IPv4SubnetFactory(network__public=True)
        mfactory.IPv6SubnetFactory(network__public=True)
        backend = mfactory.BackendFactory()

        # error in nics
        req = deepcopy(kwargs)
        req["networks"] = [{"uuid": 42}]
        self.assertRaises(faults.ItemNotFound, servers.create, **req)
        self.assertEqual(models.VirtualMachine.objects.count(), 0)

        # error in enqueue. check the vm is deleted and resources released
        mrapi().CreateInstance.side_effect = Exception("ganeti is down")
        with mocked_quotaholder():
            servers.create(**kwargs)
        vm = models.VirtualMachine.objects.get()
        self.assertFalse(vm.deleted)
        self.assertEqual(vm.operstate, "ERROR")
        for nic in vm.nics.all():
            self.assertEqual(nic.state, "ERROR")

        # test ext settings:
        req = deepcopy(kwargs)
        ext_flavor = mfactory.FlavorFactory(
            volume_type__disk_template="ext_archipelago",
            disk=1)
        req["flavor"] = ext_flavor
        mrapi().CreateInstance.return_value = 42
        backend.disk_templates = ["ext"]
        backend.save()
        osettings = {
            "GANETI_DISK_PROVIDER_KWARGS": {
                "archipelago": {
                    "foo": "mpaz",
                    "lala": "lolo"
                }
            }
        }
        with mocked_quotaholder():
            with override_settings(settings, **osettings):
                vm = servers.create(**req)
        name, args, kwargs = mrapi().CreateInstance.mock_calls[-1]
        self.assertEqual(kwargs["disks"][0],
                         {"provider": "archipelago",
                          "origin": "test_mapfile",
                          "origin_size": 1000,
                          "name": vm.volumes.all()[0].backend_volume_uuid,
                          "foo": "mpaz",
                          "lala": "lolo",
                          "size": 1024})


@patch("synnefo.logic.rapi_pool.GanetiRapiClient")
class ServerTest(TransactionTestCase):
    def test_connect_network(self, mrapi):
        # Common connect
        for dhcp in [True, False]:
            subnet = mfactory.IPv4SubnetFactory(network__flavor="CUSTOM",
                                                cidr="192.168.2.0/24",
                                                gateway="192.168.2.1",
                                                dhcp=dhcp)
            net = subnet.network
            vm = mfactory.VirtualMachineFactory(operstate="STARTED")
            mfactory.BackendNetworkFactory(network=net, backend=vm.backend)
            mrapi().ModifyInstance.return_value = 42
            with override_settings(settings, GANETI_USE_HOTPLUG=True):
                servers.connect(vm, net)
            pool = net.get_ip_pools(locked=False)[0]
            self.assertFalse(pool.is_available("192.168.2.2"))
            args, kwargs = mrapi().ModifyInstance.call_args
            nics = kwargs["nics"][0]
            self.assertEqual(kwargs["instance"], vm.backend_vm_id)
            self.assertEqual(nics[0], "add")
            self.assertEqual(nics[1], "-1")
            self.assertEqual(nics[2]["ip"], "192.168.2.2")
            self.assertEqual(nics[2]["network"], net.backend_id)

        # Test connect to IPv6 only network
        vm = mfactory.VirtualMachineFactory(operstate="STARTED")
        subnet = mfactory.IPv6SubnetFactory(cidr="2000::/64",
                                            gateway="2000::1")
        net = subnet.network
        mfactory.BackendNetworkFactory(network=net, backend=vm.backend)
        with override_settings(settings, GANETI_USE_HOTPLUG=True):
            servers.connect(vm, net)
        args, kwargs = mrapi().ModifyInstance.call_args
        nics = kwargs["nics"][0]
        self.assertEqual(kwargs["instance"], vm.backend_vm_id)
        self.assertEqual(nics[0], "add")
        self.assertEqual(nics[1], "-1")
        self.assertEqual(nics[2]["ip"], None)
        self.assertEqual(nics[2]["network"], net.backend_id)

    def test_attach_wait_for_sync(self, mrapi):
        """Test wait_for_sync when attaching volume to instance.

        """
        volume = mfactory.VolumeFactory()
        vm = volume.machine
        # Test Started VM
        vm.operstate = "STARTED"
        vm.save()
        mrapi().ModifyInstance.return_value = 1
        for sync in [True, False]:
            with override_settings(settings, GANETI_DISKS_WAIT_FOR_SYNC=sync):
                jobid = backend.attach_volume(vm, volume)
                self.assertEqual(jobid, 1)
                name, args, kwargs = mrapi().ModifyInstance.mock_calls[-1]
                self.assertEqual(kwargs['wait_for_sync'], sync)

        # Test Stopped VM. We do not pass wait_for_sync.
        vm.operstate = "STOPPED"
        vm.save()
        mrapi().ModifyInstance.return_value = 1
        for sync in [True, False]:
            with override_settings(settings, GANETI_DISKS_WAIT_FOR_SYNC=sync):
                jobid = backend.attach_volume(vm, volume)
                self.assertEqual(jobid, 1)
                name, args, kwargs = mrapi().ModifyInstance.mock_calls[-1]
                self.assertFalse('wait_for_sync' in kwargs)


@patch("synnefo.logic.rapi_pool.GanetiRapiClient")
class ServerCommandTest(TransactionTestCase):
    def test_pending_task(self, mrapi):
        vm = mfactory.VirtualMachineFactory(task="REBOOT", task_job_id=1)
        self.assertRaises(faults.BadRequest, servers.start, vm)
        vm = mfactory.VirtualMachineFactory(task="BUILD", task_job_id=1)
        self.assertRaises(faults.BuildInProgress, servers.start, vm)
        # Assert always succeeds
        vm = mfactory.VirtualMachineFactory(task="BUILD", task_job_id=1)
        mrapi().DeleteInstance.return_value = 1
        with mocked_quotaholder():
            servers.destroy(vm)
        vm = mfactory.VirtualMachineFactory(task="REBOOT", task_job_id=1)
        with mocked_quotaholder():
            servers.destroy(vm)

    def test_deleted_vm(self, mrapi):
        vm = mfactory.VirtualMachineFactory(deleted=True)
        self.assertRaises(faults.BadRequest, servers.start, vm)

    def test_invalid_operstate_for_action(self, mrapi):
        vm = mfactory.VirtualMachineFactory(operstate="STARTED")
        self.assertRaises(faults.BadRequest, servers.start, vm)
        vm = mfactory.VirtualMachineFactory(operstate="STOPPED")
        self.assertRaises(faults.BadRequest, servers.stop, vm)
        vm = mfactory.VirtualMachineFactory(operstate="STARTED")
        flavor = mfactory.FlavorFactory()
        self.assertRaises(faults.BadRequest, servers.resize, vm, flavor)
        # Check that connect/disconnect is allowed only in STOPPED vms
        # if hotplug is disabled.
        vm = mfactory.VirtualMachineFactory(operstate="STARTED")
        network = mfactory.NetworkFactory(state="ACTIVE")
        with override_settings(settings, GANETI_USE_HOTPLUG=False):
            self.assertRaises(faults.BadRequest, servers.connect, vm, network)
            self.assertRaises(faults.BadRequest, servers.disconnect, vm,
                              network)
        #test valid
        vm = mfactory.VirtualMachineFactory(operstate="STOPPED")
        mrapi().StartupInstance.return_value = 1
        with mocked_quotaholder():
            servers.start(vm)
        vm.task = None
        vm.task_job_id = None
        vm.save()
        with mocked_quotaholder():
            quotas.accept_resource_serial(vm)
        mrapi().RebootInstance.return_value = 1
        with mocked_quotaholder():
            servers.reboot(vm, "HARD")

    def test_commission(self, mrapi):
        vm = mfactory.VirtualMachineFactory(operstate="STOPPED")
        # Still pending
        vm.serial = mfactory.QuotaHolderSerialFactory(serial=200,
                                                      resolved=False,
                                                      pending=True)
        serial = vm.serial
        mrapi().StartupInstance.return_value = 1
        with mocked_quotaholder() as m:
            with self.assertRaises(quotas.ResolveError):
                servers.start(vm)
        # Not pending, rejct
        vm.task = None
        vm.serial = mfactory.QuotaHolderSerialFactory(serial=400,
                                                      resolved=False,
                                                      pending=False,
                                                      accept=False)
        serial = vm.serial
        mrapi().StartupInstance.return_value = 1
        with mocked_quotaholder() as m:
            servers.start(vm)
            m.resolve_commissions.assert_called_once_with([],
                                                          [serial.serial])
            self.assertTrue(m.issue_one_commission.called)
        # Not pending, accept
        vm.task = None
        vm.serial = mfactory.QuotaHolderSerialFactory(serial=600,
                                                      resolved=False,
                                                      pending=False,
                                                      accept=True)
        serial = vm.serial
        mrapi().StartupInstance.return_value = 1
        with mocked_quotaholder() as m:
            servers.start(vm)
            m.resolve_commissions.assert_called_once_with([serial.serial],
                                                          [])
            self.assertTrue(m.issue_one_commission.called)

        mrapi().StartupInstance.side_effect = ValueError
        vm.task = None
        vm.serial = None
        # Test reject if Ganeti erro
        with mocked_quotaholder() as m:
            try:
                servers.start(vm)
            except Exception:
                (accept, reject), kwargs = m.resolve_commissions.call_args
                self.assertEqual(accept, [])
                self.assertEqual(len(reject), 1)
                self.assertEqual(kwargs, {})
            else:
                raise AssertionError("Starting a server should raise an"
                                     " exception.")

    def test_task_after(self, mrapi):
        return
        vm = mfactory.VirtualMachineFactory()
        mrapi().StartupInstance.return_value = 1
        mrapi().ShutdownInstance.return_value = 2
        mrapi().RebootInstance.return_value = 2
        with mocked_quotaholder():
            vm.task = None
            vm.operstate = "STOPPED"
            servers.start(vm)
            self.assertEqual(vm.task, "START")
            self.assertEqual(vm.task_job_id, 1)
        with mocked_quotaholder():
            vm.task = None
            vm.operstate = "STARTED"
            servers.stop(vm)
            self.assertEqual(vm.task, "STOP")
            self.assertEqual(vm.task_job_id, 2)
        with mocked_quotaholder():
            vm.task = None
            servers.reboot(vm)
            self.assertEqual(vm.task, "REBOOT")
            self.assertEqual(vm.task_job_id, 3)

    def test_reassign_vm(self, mrapi):
        volume = mfactory.VolumeFactory()
        vm = volume.machine
        another_project = "another_project"
        with mocked_quotaholder():
            servers.reassign(vm, another_project, False)
            self.assertEqual(vm.project, another_project)
            self.assertEqual(vm.shared_to_project, False)
            vol = vm.volumes.get(id=volume.id)
            self.assertNotEqual(vol.project, another_project)

        volume = mfactory.VolumeFactory()
        volume.index = 0
        volume.save()
        vm = volume.machine
        another_project = "another_project"
        with mocked_quotaholder():
            servers.reassign(vm, another_project, True)
            self.assertEqual(vm.project, another_project)
            self.assertEqual(vm.shared_to_project, True)
            vol = vm.volumes.get(id=volume.id)
            self.assertEqual(vol.project, another_project)
            self.assertEqual(vol.shared_to_project, True)
