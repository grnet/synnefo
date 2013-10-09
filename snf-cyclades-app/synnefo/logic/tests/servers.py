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
from synnefo.db import models_factory as mfactory, models
from mock import patch

from snf_django.lib.api import faults
from snf_django.utils.testing import mocked_quotaholder, override_settings
from django.conf import settings
from copy import deepcopy


@patch("synnefo.logic.rapi_pool.GanetiRapiClient")
class ServerCreationTest(TransactionTestCase):
    def test_create(self, mrapi):
        flavor = mfactory.FlavorFactory()
        kwargs = {
            "userid": "test",
            "name": "test_vm",
            "password": "1234",
            "flavor": flavor,
            "image": {"id": "foo", "backend_id": "foo", "format": "diskdump",
                      "metadata": "{}"},
            "metadata": {"foo": "bar"},
            "personality": [],
        }
        # no backend!
        mfactory.BackendFactory(offline=True)
        self.assertRaises(faults.ServiceUnavailable, servers.create, **kwargs)
        self.assertEqual(models.VirtualMachine.objects.count(), 0)

        mfactory.BackendFactory(drained=False)
        mfactory.BackendNetworkFactory(network__public=True)

        # error in nics
        req = deepcopy(kwargs)
        req["private_networks"] = [42]
        self.assertRaises(faults.ItemNotFound, servers.create, **req)
        self.assertEqual(models.VirtualMachine.objects.count(), 0)

        # error in enqueue. check the vm is deleted and resources released
        mrapi().CreateInstance.side_effect = Exception("ganeti is down")
        with mocked_quotaholder():
            servers.create(**kwargs)
        vm = models.VirtualMachine.objects.get()
        self.assertFalse(vm.deleted)
        self.assertEqual(vm.operstate, "ERROR")
        self.assertEqual(len(vm.nics.all()), 1)
        for nic in vm.nics.all():
            self.assertEqual(nic.state, "ERROR")

        # success with no nics
        mrapi().CreateInstance.side_effect = None
        mrapi().CreateInstance.return_value = 42
        with override_settings(settings,
                               DEFAULT_INSTANCE_NETWORKS=[]):
            with mocked_quotaholder():
                vm = servers.create(**kwargs)
        vm = models.VirtualMachine.objects.get(id=vm.id)
        self.assertEqual(vm.nics.count(), 0)
        self.assertEqual(vm.backendjobid, 42)
        self.assertEqual(vm.task_job_id, 42)
        self.assertEqual(vm.task, "BUILD")

        # test connect in IPv6 only network
        net = mfactory.IPv6NetworkFactory(state="ACTIVE")
        mfactory.BackendNetworkFactory(network=net)
        with override_settings(settings,
                               DEFAULT_INSTANCE_NETWORKS=[str(net.id)]):
            with mocked_quotaholder():
                vm = servers.create(**kwargs)
        nics = vm.nics.all()
        self.assertEqual(len(nics), 1)
        self.assertEqual(nics[0].ipv4, None)
        args, kwargs = mrapi().CreateInstance.call_args
        ganeti_nic = kwargs["nics"][0]
        self.assertEqual(ganeti_nic["ip"], None)
        self.assertEqual(ganeti_nic["network"], net.backend_id)


@patch("synnefo.logic.rapi_pool.GanetiRapiClient")
class ServerTest(TransactionTestCase):
    def test_connect_network(self, mrapi):
        # Common connect
        net = mfactory.NetworkFactory(subnet="192.168.2.0/24",
                                      gateway="192.168.2.1",
                                      state="ACTIVE",
                                      dhcp=True,
                                      flavor="CUSTOM")
        vm = mfactory.VirtualMachineFactory(operstate="STARTED")
        mfactory.BackendNetworkFactory(network=net, backend=vm.backend)
        mrapi().ModifyInstance.return_value = 42
        servers.connect(vm, net)
        pool = net.get_pool(locked=False)
        self.assertFalse(pool.is_available("192.168.2.2"))
        args, kwargs = mrapi().ModifyInstance.call_args
        nics = kwargs["nics"][0]
        self.assertEqual(kwargs["instance"], vm.backend_vm_id)
        self.assertEqual(nics[0], "add")
        self.assertEqual(nics[1], "-1")
        self.assertEqual(nics[2]["ip"], "192.168.2.2")
        self.assertEqual(nics[2]["network"], net.backend_id)

        # No dhcp
        vm = mfactory.VirtualMachineFactory(operstate="STARTED")
        net = mfactory.NetworkFactory(subnet="192.168.2.0/24",
                                      gateway="192.168.2.1",
                                      state="ACTIVE",
                                      dhcp=False)
        mfactory.BackendNetworkFactory(network=net, backend=vm.backend)
        servers.connect(vm, net)
        pool = net.get_pool(locked=False)
        self.assertTrue(pool.is_available("192.168.2.2"))
        args, kwargs = mrapi().ModifyInstance.call_args
        nics = kwargs["nics"][0]
        self.assertEqual(kwargs["instance"], vm.backend_vm_id)
        self.assertEqual(nics[0], "add")
        self.assertEqual(nics[1], "-1")
        self.assertEqual(nics[2]["ip"], None)
        self.assertEqual(nics[2]["network"], net.backend_id)

        # Test connect to IPv6 only network
        vm = mfactory.VirtualMachineFactory(operstate="STARTED")
        net = mfactory.NetworkFactory(subnet6="2000::/64",
                                      state="ACTIVE",
                                      gateway="2000::1")
        mfactory.BackendNetworkFactory(network=net, backend=vm.backend)
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
        self.assertRaises(faults.BadRequest, servers.resize, vm)
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
            servers.start(vm)
            m.resolve_commissions.assert_called_once_with('', [],
                                                          [serial.serial])
            self.assertTrue(m.issue_one_commission.called)
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
            m.resolve_commissions.assert_called_once_with('', [],
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
            m.resolve_commissions.assert_called_once_with('', [serial.serial],
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
                 .assert_called_once_with('', [], [vm.serial.serial])

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
