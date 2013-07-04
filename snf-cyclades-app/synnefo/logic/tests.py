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

# Provides automated tests for logic module

from random import randint

from django.test import TestCase

from snf_django.lib.api import faults
from synnefo.db.models import *
from synnefo.db import models_factory as mfactory
from synnefo.logic import reconciliation, servers
from synnefo.lib.utils import split_time
from datetime import datetime
from mock import patch
from synnefo.api.util import allocate_resource
from synnefo.logic.callbacks import (update_db, update_network,
                                     update_build_progress)
from snf_django.utils.testing import mocked_quotaholder

now = datetime.now
from time import time
import json


@patch("synnefo.logic.rapi_pool.GanetiRapiClient")
class ServerCommandTest(TestCase):
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
        vm = mfactory.VirtualMachineFactory(operstate="STOPPED")
        self.assertRaises(faults.BadRequest, servers.stop, vm)
        #test valid
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
                m.resolve_commissions.assert_called_once_with('', [],
                                                            [vm.serial.serial])

    def test_task_after(self, mrapi):
        return
        vm = mfactory.VirtualMachineFactory()
        mrapi().StartupInstance.return_value = 1
        mrapi().ShutdownInstance.return_value = 2
        mrapi().RebootInstance.return_value = 2
        with mocked_quotaholder() as m:
            vm.task = None
            vm.operstate = "STOPPED"
            servers.start(vm)
            self.assertEqual(vm.task, "START")
            self.assertEqual(vm.task_job_id, 1)
        with mocked_quotaholder() as m:
            vm.task = None
            vm.operstate = "STARTED"
            servers.stop(vm)
            self.assertEqual(vm.task, "STOP")
            self.assertEqual(vm.task_job_id, 2)
        with mocked_quotaholder() as m:
            vm.task = None
            servers.reboot(vm)
            self.assertEqual(vm.task, "REBOOT")
            self.assertEqual(vm.task_job_id, 3)



## Test Callbacks


@patch('synnefo.lib.amqp.AMQPClient')
class UpdateDBTest(TestCase):
    def create_msg(self, **kwargs):
        """Create snf-ganeti-eventd message"""
        msg = {'event_time': split_time(time())}
        msg['type'] = 'ganeti-op-status'
        msg['status'] = 'success'
        msg['jobId'] = 1
        msg['logmsg'] = 'Dummy Log'
        for key, val in kwargs.items():
            msg[key] = val
        message = {'body': json.dumps(msg)}
        return message

    def test_missing_attribute(self, client):
        update_db(client, json.dumps({'body': {}}))
        self.assertTrue(client.basic_reject.called)

    def test_unhandled_exception(self, client):
        update_db(client, {})
        client.basic_reject.assert_called_once()

    def test_missing_instance(self, client):
        msg = self.create_msg(operation='OP_INSTANCE_STARTUP',
                              instance='foo')
        update_db(client, msg)
        self.assertTrue(client.basic_ack.called)

    def test_wrong_type(self, client):
        msg = self.create_msg(type="WRONG_TYPE")
        update_db(client, msg)
        self.assertTrue(client.basic_nack.called)

    def test_old_msg(self, client):
        from time import sleep
        from datetime import datetime
        old_time = time()
        sleep(0.01)
        new_time = datetime.fromtimestamp(time())
        vm = mfactory.VirtualMachineFactory(backendtime=new_time)
        vm.operstate = 'STOPPED'
        vm.save()
        msg = self.create_msg(operation='OP_INSTANCE_STARTUP',
                              event_time=split_time(old_time),
                              instance=vm.backend_vm_id)
        update_db(client, msg)
        self.assertTrue(client.basic_ack.called)
        db_vm = VirtualMachine.objects.get(id=vm.id)
        self.assertEquals(db_vm.operstate, "STOPPED")
        self.assertEquals(db_vm.backendtime, new_time)

    def test_start(self, client):
        vm = mfactory.VirtualMachineFactory()
        msg = self.create_msg(operation='OP_INSTANCE_STARTUP',
                              instance=vm.backend_vm_id)
        with mocked_quotaholder():
            update_db(client, msg)
        self.assertTrue(client.basic_ack.called)
        db_vm = VirtualMachine.objects.get(id=vm.id)
        self.assertEqual(db_vm.operstate, 'STARTED')

    def test_stop(self, client):
        vm = mfactory.VirtualMachineFactory()
        msg = self.create_msg(operation='OP_INSTANCE_SHUTDOWN',
                              instance=vm.backend_vm_id)
        with mocked_quotaholder():
            update_db(client, msg)
        self.assertTrue(client.basic_ack.called)
        db_vm = VirtualMachine.objects.get(id=vm.id)
        self.assertEqual(db_vm.operstate, 'STOPPED')

    def test_reboot(self, client):
        vm = mfactory.VirtualMachineFactory()
        msg = self.create_msg(operation='OP_INSTANCE_REBOOT',
                              instance=vm.backend_vm_id)
        update_db(client, msg)
        self.assertTrue(client.basic_ack.called)
        db_vm = VirtualMachine.objects.get(id=vm.id)
        self.assertEqual(db_vm.operstate, 'STARTED')

    def test_remove(self, client):
        vm = mfactory.VirtualMachineFactory()
        # Also create a NIC
        nic = mfactory.NetworkInterfaceFactory(machine=vm)
        nic.network.get_pool().reserve(nic.ipv4)
        msg = self.create_msg(operation='OP_INSTANCE_REMOVE',
                              instance=vm.backend_vm_id)
        with mocked_quotaholder():
            update_db(client, msg)
        self.assertTrue(client.basic_ack.called)
        db_vm = VirtualMachine.objects.get(id=vm.id)
        self.assertEqual(db_vm.operstate, 'DESTROYED')
        self.assertTrue(db_vm.deleted)
        # Check that nics are deleted
        self.assertFalse(db_vm.nics.all())
        self.assertTrue(nic.network.get_pool().is_available(nic.ipv4))
        vm2 = mfactory.VirtualMachineFactory()
        network = mfactory.NetworkFactory(floating_ip_pool=True)
        fp1 = mfactory.FloatingIPFactory(machine=vm2, network=network)
        fp2 = mfactory.FloatingIPFactory(machine=vm2, network=network)
        mfactory.NetworkInterfaceFactory(machine=vm2, network=network,
                ipv4=fp1.ipv4)
        mfactory.NetworkInterfaceFactory(machine=vm2, network=network,
                ipv4=fp2.ipv4)
        pool = network.get_pool()
        pool.reserve(fp1.ipv4)
        pool.reserve(fp2.ipv4)
        pool.save()
        msg = self.create_msg(operation='OP_INSTANCE_REMOVE',
                              instance=vm2.backend_vm_id)
        with mocked_quotaholder():
            update_db(client, msg)
        client.basic_ack.assert_called_once()
        db_vm = VirtualMachine.objects.get(id=vm.id)
        self.assertEqual(db_vm.operstate, 'DESTROYED')
        self.assertTrue(db_vm.deleted)
        self.assertEqual(FloatingIP.objects.get(id=fp1.id).machine, None)
        self.assertEqual(FloatingIP.objects.get(id=fp2.id).machine, None)
        pool = network.get_pool()
        # Test that floating ips are not released
        self.assertFalse(pool.is_available(fp1.ipv4))
        self.assertFalse(pool.is_available(fp2.ipv4))

    def test_create(self, client):
        vm = mfactory.VirtualMachineFactory()
        msg = self.create_msg(operation='OP_INSTANCE_CREATE',
                              instance=vm.backend_vm_id)
        update_db(client, msg)
        self.assertTrue(client.basic_ack.called)
        db_vm = VirtualMachine.objects.get(id=vm.id)
        self.assertEqual(db_vm.operstate, 'STARTED')

    def test_create_error(self, client):
        """Test that error create sets vm to ERROR state"""
        vm = mfactory.VirtualMachineFactory()
        msg = self.create_msg(operation='OP_INSTANCE_CREATE',
                              instance=vm.backend_vm_id,
                              status='error')
        update_db(client, msg)
        self.assertTrue(client.basic_ack.called)
        db_vm = VirtualMachine.objects.get(id=vm.id)
        self.assertEqual(db_vm.operstate, 'ERROR')

    def test_remove_from_error(self, client):
        """Test that error removes delete error builds"""
        vm = mfactory.VirtualMachineFactory(operstate='ERROR')
        # Also create a NIC
        mfactory.NetworkInterfaceFactory(machine=vm)
        msg = self.create_msg(operation='OP_INSTANCE_REMOVE',
                              instance=vm.backend_vm_id)
        with mocked_quotaholder():
            update_db(client, msg)
        self.assertTrue(client.basic_ack.called)
        db_vm = VirtualMachine.objects.get(id=vm.id)
        self.assertEqual(db_vm.operstate, 'DESTROYED')
        self.assertTrue(db_vm.deleted)
        # Check that nics are deleted
        self.assertFalse(db_vm.nics.all())

    def test_other_error(self, client):
        """Test that other error messages do no affect the VM"""
        vm = mfactory.VirtualMachineFactory()
        msg = self.create_msg(operation='OP_INSTANCE_STARTUP',
                              instance=vm.backend_vm_id,
                              status='error')
        update_db(client, msg)
        self.assertTrue(client.basic_ack.called)
        db_vm = VirtualMachine.objects.get(id=vm.id)
        self.assertEqual(db_vm.operstate, vm.operstate)
        self.assertEqual(db_vm.backendtime, vm.backendtime)

    def test_resize_msg(self, client):
        vm = mfactory.VirtualMachineFactory()
        # Test empty beparams
        for status in ["success", "error"]:
            msg = self.create_msg(operation='OP_INSTANCE_SET_PARAMS',
                                  instance=vm.backend_vm_id,
                                  beparams={},
                                  status=status)
            client.reset_mock()
            with mocked_quotaholder():
                update_db(client, msg)
            self.assertTrue(client.basic_ack.called)
            db_vm = VirtualMachine.objects.get(id=vm.id)
            self.assertEqual(db_vm.operstate, vm.operstate)
        # Test intermediate states
        vm.operstate = "STOPPED"
        vm.save()
        for status in ["queued", "waiting", "running"]:
            msg = self.create_msg(operation='OP_INSTANCE_SET_PARAMS',
                                  instance=vm.backend_vm_id,
                                  beparams={"vcpus": 4, "minmem": 2048,
                                            "maxmem": 2048},
                                  status=status)
            client.reset_mock()
            update_db(client, msg)
            self.assertTrue(client.basic_ack.called)
            db_vm = VirtualMachine.objects.get(id=vm.id)
            self.assertEqual(db_vm.operstate, "STOPPED")
        # Test operstate after error
        msg = self.create_msg(operation='OP_INSTANCE_SET_PARAMS',
                              instance=vm.backend_vm_id,
                              beparams={"vcpus": 4},
                              status="error")
        client.reset_mock()
        with mocked_quotaholder():
            update_db(client, msg)
        self.assertTrue(client.basic_ack.called)
        db_vm = VirtualMachine.objects.get(id=vm.id)
        self.assertEqual(db_vm.operstate, "STOPPED")
        # Test success
        f1 = mfactory.FlavorFactory(cpu=4, ram=1024, disk_template="drbd",
                                    disk=1024)
        vm.flavor = f1
        vm.save()
        f2 = mfactory.FlavorFactory(cpu=8, ram=2048, disk_template="drbd",
                                    disk=1024)
        msg = self.create_msg(operation='OP_INSTANCE_SET_PARAMS',
                              instance=vm.backend_vm_id,
                              beparams={"vcpus": 8, "minmem": 2048,
                                        "maxmem": 2048},
                              status="success")
        client.reset_mock()
        with mocked_quotaholder():
            update_db(client, msg)
        self.assertTrue(client.basic_ack.called)
        db_vm = VirtualMachine.objects.get(id=vm.id)
        self.assertEqual(db_vm.operstate, "STOPPED")
        self.assertEqual(db_vm.flavor, f2)
        msg = self.create_msg(operation='OP_INSTANCE_SET_PARAMS',
                              instance=vm.backend_vm_id,
                              beparams={"vcpus": 100, "minmem": 2048,
                                        "maxmem": 2048},
                              status="success")
        client.reset_mock()
        with mocked_quotaholder():
            update_db(client, msg)
        self.assertTrue(client.basic_reject.called)


@patch('synnefo.lib.amqp.AMQPClient')
class UpdateNetTest(TestCase):
    def create_msg(self, **kwargs):
        """Create snf-ganeti-hook message"""
        msg = {'event_time': split_time(time())}
        msg['type'] = 'ganeti-op-status'
        msg['operation'] = 'OP_INSTANCE_SET_PARAMS'
        msg['status'] = 'success'
        msg['jobId'] = 1
        msg['logmsg'] = 'Dummy Log'
        for key, val in kwargs.items():
            msg[key] = val
        message = {'body': json.dumps(msg)}
        return message

    def test_missing_attribute(self, client):
        update_db(client, json.dumps({'body': {}}))
        self.assertTrue(client.basic_reject.called)

    def test_unhandled_exception(self, client):
        update_db(client, {})
        client.basic_reject.assert_called_once()

    def test_wrong_type(self, client):
        msg = self.create_msg(type="WRONG_TYPE")
        update_db(client, msg)
        self.assertTrue(client.basic_nack.called)

    def test_missing_instance(self, client):
        msg = self.create_msg(operation='OP_INSTANCE_STARTUP',
                              instance='foo')
        update_db(client, msg)
        self.assertTrue(client.basic_ack.called)

    def test_no_nics(self, client):
        vm = mfactory.VirtualMachineFactory(operstate='ERROR')
        mfactory.NetworkInterfaceFactory(machine=vm)
        mfactory.NetworkInterfaceFactory(machine=vm)
        mfactory.NetworkInterfaceFactory(machine=vm)
        self.assertEqual(len(vm.nics.all()), 3)
        msg = self.create_msg(nics=[],
                              instance=vm.backend_vm_id)
        update_db(client, msg)
        self.assertTrue(client.basic_ack.called)
        db_vm = VirtualMachine.objects.get(id=vm.id)
        self.assertEqual(len(db_vm.nics.all()), 0)

    def test_empty_nic(self, client):
        vm = mfactory.VirtualMachineFactory(operstate='ERROR')
        for public in [True, False]:
            net = mfactory.NetworkFactory(public=public)
            msg = self.create_msg(nics=[{'network': net.backend_id}],
                                  instance=vm.backend_vm_id)
            update_db(client, msg)
            self.assertTrue(client.basic_ack.called)
            db_vm = VirtualMachine.objects.get(id=vm.id)
            nics = db_vm.nics.all()
            self.assertEqual(len(nics), 1)
            self.assertEqual(nics[0].index, 0)
            self.assertEqual(nics[0].ipv4, '')
            self.assertEqual(nics[0].ipv6, '')
            self.assertEqual(nics[0].mac, '')
            if public:
                self.assertEqual(nics[0].firewall_profile,
                                 settings.DEFAULT_FIREWALL_PROFILE)
            else:
                self.assertEqual(nics[0].firewall_profile, '')

    def test_full_nic(self, client):
        vm = mfactory.VirtualMachineFactory(operstate='ERROR')
        net = mfactory.NetworkFactory(subnet='10.0.0.0/24')
        pool = net.get_pool()
        self.assertTrue(pool.is_available('10.0.0.22'))
        pool.save()
        msg = self.create_msg(nics=[{'network': net.backend_id,
                                     'ip': '10.0.0.22',
                                     'mac': 'aa:bb:cc:00:11:22'}],
                              instance=vm.backend_vm_id)
        update_db(client, msg)
        self.assertTrue(client.basic_ack.called)
        db_vm = VirtualMachine.objects.get(id=vm.id)
        nics = db_vm.nics.all()
        self.assertEqual(len(nics), 1)
        self.assertEqual(nics[0].index, 0)
        self.assertEqual(nics[0].ipv4, '10.0.0.22')
        self.assertEqual(nics[0].ipv6, '')
        self.assertEqual(nics[0].mac, 'aa:bb:cc:00:11:22')
        pool = net.get_pool()
        self.assertFalse(pool.is_available('10.0.0.22'))
        pool.save()


@patch('synnefo.lib.amqp.AMQPClient')
class UpdateNetworkTest(TestCase):
    def create_msg(self, **kwargs):
        """Create snf-ganeti-eventd message"""
        msg = {'event_time': split_time(time())}
        msg['type'] = 'ganeti-network-status'
        msg['status'] = 'success'
        msg['jobId'] = 1
        msg['logmsg'] = 'Dummy Log'
        for key, val in kwargs.items():
            msg[key] = val
        message = {'body': json.dumps(msg)}
        return message

    def test_missing_attribute(self, client):
        update_network(client, json.dumps({'body': {}}))
        self.assertTrue(client.basic_reject.called)

    def test_unhandled_exception(self, client):
        update_network(client, {})
        client.basic_reject.assert_called_once()

    def test_wrong_type(self, client):
        msg = self.create_msg(type="WRONG_TYPE")
        update_network(client, msg)
        self.assertTrue(client.basic_nack.called)

    def test_missing_network(self, client):
        msg = self.create_msg(operation='OP_NETWORK_CREATE',
                              network='foo')
        update_network(client, msg)
        self.assertTrue(client.basic_ack.called)

    def test_create(self, client):
        back_network = mfactory.BackendNetworkFactory(operstate='PENDING')
        net = back_network.network
        net.state = 'ACTIVE'
        net.save()
        back1 = back_network.backend

        back_network2 = mfactory.BackendNetworkFactory(operstate='PENDING',
                                                       network=net)
        back2 = back_network2.backend
        # Message from first backend network
        msg = self.create_msg(operation='OP_NETWORK_CONNECT',
                              network=net.backend_id,
                              cluster=back1.clustername)
        update_network(client, msg)
        self.assertTrue(client.basic_ack.called)

        back_net = BackendNetwork.objects.get(id=back_network.id)
        self.assertEqual(back_net.operstate, 'ACTIVE')
        db_net = Network.objects.get(id=net.id)
        self.assertEqual(db_net.state, 'ACTIVE')
        # msg from second backend network
        msg = self.create_msg(operation='OP_NETWORK_CONNECT',
                              network=net.backend_id,
                              cluster=back2.clustername)
        update_network(client, msg)
        self.assertTrue(client.basic_ack.called)

        db_net = Network.objects.get(id=net.id)
        self.assertEqual(db_net.state, 'ACTIVE')
        back_net = BackendNetwork.objects.get(id=back_network.id)
        self.assertEqual(back_net.operstate, 'ACTIVE')

    def test_create_offline_backend(self, client):
        """Test network creation when a backend is offline"""
        net = mfactory.NetworkFactory(state='ACTIVE')
        bn1 = mfactory.BackendNetworkFactory(network=net)
        bn2 = mfactory.BackendNetworkFactory(network=net,
                                             backend__offline=True)
        msg = self.create_msg(operation='OP_NETWORK_CONNECT',
                              network=net.backend_id,
                              cluster=bn1.backend.clustername)
        update_network(client, msg)
        self.assertTrue(client.basic_ack.called)
        new_net = Network.objects.get(id=net.id)
        self.assertEqual(new_net.state, 'ACTIVE')

    def test_disconnect(self, client):
        bn1 = mfactory.BackendNetworkFactory(operstate='ACTIVE')
        net1 = bn1.network
        net1.state = "ACTIVE"
        net1.state = 'ACTIVE'
        net1.save()
        bn2 = mfactory.BackendNetworkFactory(operstate='ACTIVE',
                                             network=net1)
        msg = self.create_msg(operation='OP_NETWORK_DISCONNECT',
                              network=net1.backend_id,
                              cluster=bn2.backend.clustername)
        update_network(client, msg)
        self.assertTrue(client.basic_ack.called)
        self.assertEqual(Network.objects.get(id=net1.id).state, 'ACTIVE')
        self.assertEqual(BackendNetwork.objects.get(id=bn2.id).operstate,
                         'PENDING')

    def test_remove(self, client):
        mfactory.MacPrefixPoolTableFactory()
        mfactory.BridgePoolTableFactory()
        bn = mfactory.BackendNetworkFactory(operstate='ACTIVE')
        for old_state in ['success', 'canceled', 'error']:
            for flavor in Network.FLAVORS.keys():
                bn.operstate = old_state
                bn.save()
                net = bn.network
                net.state = 'ACTIVE'
                net.flavor = flavor
                if flavor == 'PHYSICAL_VLAN':
                    net.link = allocate_resource('bridge')
                if flavor == 'MAC_FILTERED':
                    net.mac_prefix = allocate_resource('mac_prefix')
                net.save()
                msg = self.create_msg(operation='OP_NETWORK_REMOVE',
                                      network=net.backend_id,
                                      cluster=bn.backend.clustername)
                with mocked_quotaholder():
                    update_network(client, msg)
                self.assertTrue(client.basic_ack.called)
                db_bnet = BackendNetwork.objects.get(id=bn.id)
                self.assertEqual(db_bnet.operstate,
                                 'DELETED')
                db_net = Network.objects.get(id=net.id)
                self.assertEqual(db_net.state, 'DELETED', flavor)
                self.assertTrue(db_net.deleted)
                if flavor == 'PHYSICAL_VLAN':
                    pool = BridgePoolTable.get_pool()
                    self.assertTrue(pool.is_available(net.link))
                if flavor == 'MAC_FILTERED':
                    pool = MacPrefixPoolTable.get_pool()
                    self.assertTrue(pool.is_available(net.mac_prefix))

    def test_remove_offline_backend(self, client):
        """Test network removing when a backend is offline"""
        mfactory.BridgePoolTableFactory()
        net = mfactory.NetworkFactory(flavor='PHYSICAL_VLAN',
                                      state='ACTIVE',
                                      link='prv12')
        bn1 = mfactory.BackendNetworkFactory(network=net)
        mfactory.BackendNetworkFactory(network=net,
                                       operstate="ACTIVE",
                                       backend__offline=True)
        msg = self.create_msg(operation='OP_NETWORK_REMOVE',
                              network=net.backend_id,
                              cluster=bn1.backend.clustername)
        with mocked_quotaholder():
            update_network(client, msg)
        self.assertTrue(client.basic_ack.called)
        new_net = Network.objects.get(id=net.id)
        self.assertEqual(new_net.state, 'ACTIVE')
        self.assertFalse(new_net.deleted)

    def test_error_opcode(self, client):
        mfactory.MacPrefixPoolTableFactory()
        mfactory.BridgePoolTableFactory()
        for state, _ in Network.OPER_STATES:
            bn = mfactory.BackendNetworkFactory(operstate="ACTIVE")
            bn.operstate = state
            bn.save()
            network = bn.network
            network.state = state
            network.save()
            for opcode, _ in BackendNetwork.BACKEND_OPCODES:
                if opcode in ['OP_NETWORK_REMOVE', 'OP_NETWORK_ADD']:
                    continue
                msg = self.create_msg(operation=opcode,
                                      network=bn.network.backend_id,
                                      status='error',
                                      add_reserved_ips=[],
                                      remove_reserved_ips=[],
                                      cluster=bn.backend.clustername)
                with mocked_quotaholder():
                    update_network(client, msg)
                self.assertTrue(client.basic_ack.called)
                db_bnet = BackendNetwork.objects.get(id=bn.id)
                self.assertEqual(bn.operstate, db_bnet.operstate)
                self.assertEqual(bn.network.state, db_bnet.network.state)

    def test_ips(self, client):
        network = mfactory.NetworkFactory(subnet='10.0.0.0/24')
        bn = mfactory.BackendNetworkFactory(network=network)
        msg = self.create_msg(operation='OP_NETWORK_SET_PARAMS',
                              network=network.backend_id,
                              cluster=bn.backend.clustername,
                              status='success',
                              add_reserved_ips=['10.0.0.10', '10.0.0.20'],
                              remove_reserved_ips=[])
        update_network(client, msg)
        self.assertTrue(client.basic_ack.called)
        pool = network.get_pool()
        self.assertTrue(pool.is_reserved('10.0.0.10'))
        self.assertTrue(pool.is_reserved('10.0.0.20'))
        pool.save()
        # Release them
        msg = self.create_msg(operation='OP_NETWORK_SET_PARAMS',
                              network=network.backend_id,
                              cluster=bn.backend.clustername,
                              add_reserved_ips=[],
                              remove_reserved_ips=['10.0.0.10', '10.0.0.20'])
        update_network(client, msg)
        self.assertTrue(client.basic_ack.called)
        pool = network.get_pool()
        self.assertFalse(pool.is_reserved('10.0.0.10'))
        self.assertFalse(pool.is_reserved('10.0.0.20'))


@patch('synnefo.lib.amqp.AMQPClient')
class UpdateBuildProgressTest(TestCase):
    def setUp(self):
        self.vm = mfactory.VirtualMachineFactory()

    def get_db_vm(self):
        return VirtualMachine.objects.get(id=self.vm.id)

    def create_msg(self, **kwargs):
        """Create snf-progress-monitor message"""
        msg = {'event_time': split_time(time())}
        msg['type'] = 'image-copy-progress'
        msg['progress'] = 0
        for key, val in kwargs.items():
            msg[key] = val
        message = {'body': json.dumps(msg)}
        return message

    def test_missing_attribute(self, client):
        update_build_progress(client, json.dumps({'body': {}}))
        self.assertTrue(client.basic_reject.called)

    def test_unhandled_exception(self, client):
        update_build_progress(client, {})
        client.basic_reject.assert_called_once()

    def test_missing_instance(self, client):
        msg = self.create_msg(instance='foo')
        update_build_progress(client, msg)
        self.assertTrue(client.basic_ack.called)

    def test_wrong_type(self, client):
        msg = self.create_msg(type="WRONG_TYPE")
        update_build_progress(client, msg)
        self.assertTrue(client.basic_nack.called)

    def test_progress_update(self, client):
        rprogress = randint(10, 100)
        msg = self.create_msg(progress=rprogress,
                              instance=self.vm.backend_vm_id)
        update_build_progress(client, msg)
        self.assertTrue(client.basic_ack.called)
        vm = self.get_db_vm()
        self.assertEqual(vm.buildpercentage, rprogress)

    def test_invalid_value(self, client):
        old = self.vm.buildpercentage
        for rprogress in [0, -1, 'a']:
            msg = self.create_msg(progress=rprogress,
                                  instance=self.vm.backend_vm_id)
            update_build_progress(client, msg)
            self.assertTrue(client.basic_ack.called)
            vm = self.get_db_vm()
            self.assertEqual(vm.buildpercentage, old)


import logging
from datetime import timedelta


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
        cmrapi.DeleteInstance.assert_called_once_with(
                "%s22" % settings.BACKEND_PREFIX_ID)

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


from synnefo.logic.test.rapi_pool_tests import *
from synnefo.logic.test.utils_tests import *
