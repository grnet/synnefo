# vim: set fileencoding=utf-8 :
# Copyright 2013 GRNET S.A. All rights reserved.
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

# Provides automated tests for logic module
from django.test import TransactionTestCase
#from snf_django.utils.testing import mocked_quotaholder
from synnefo.logic import servers
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
                            "status": "AVAILABLE",
                            "size": 1024,
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
        ext_flavor = mfactory.FlavorFactory(disk_template="ext_archipelago",
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
                          "origin": "pithos:test_mapfile",
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
            except:
                m.resolve_commissions\
                 .assert_called_once_with([], [vm.serial.serial])

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
