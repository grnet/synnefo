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

from synnefo.db.models import *
from synnefo.db import models_factory as mfactory
from synnefo.logic import backend
from synnefo.logic import reconciliation
from synnefo.logic.utils import get_rsapi_state
from synnefo.lib.utils import split_time
from datetime import datetime
from mock import patch
from synnefo.api.util import allocate_resource
from synnefo.logic.callbacks import update_db, update_net, update_network

now = datetime.now
from time import time
import json

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
        client.basic_nack.assert_called_once()

    def test_unhandled_exception(self, client):
        update_db(client, {})
        client.basic_reject.assert_called_once()

    def test_missing_instance(self, client):
        msg = self.create_msg(operation='OP_INSTANCE_STARTUP',
                              instance='foo')
        update_db(client, msg)
        client.basic_nack.assert_called_once()

    def test_wrong_type(self, client):
        msg = self.create_msg(type="WRONG_TYPE")
        update_db(client, msg)
        client.basic_ack.assert_called_once()

    def test_start(self, client):
        vm = mfactory.VirtualMachineFactory()
        msg = self.create_msg(operation='OP_INSTANCE_STARTUP',
                              instance=vm.backend_vm_id)
        update_db(client, msg)
        client.basic_ack.assert_called_once()
        db_vm = VirtualMachine.objects.get(id=vm.id)
        self.assertEqual(db_vm.operstate, 'STARTED')

    def test_stop(self, client):
        vm = mfactory.VirtualMachineFactory()
        msg = self.create_msg(operation='OP_INSTANCE_SHUTDOWN',
                              instance=vm.backend_vm_id)
        update_db(client, msg)
        client.basic_ack.assert_called_once()
        db_vm = VirtualMachine.objects.get(id=vm.id)
        self.assertEqual(db_vm.operstate, 'STOPPED')

    def test_reboot(self, client):
        vm = mfactory.VirtualMachineFactory()
        msg = self.create_msg(operation='OP_INSTANCE_REBOOT',
                              instance=vm.backend_vm_id)
        update_db(client, msg)
        client.basic_ack.assert_called_once()
        db_vm = VirtualMachine.objects.get(id=vm.id)
        self.assertEqual(db_vm.operstate, 'STARTED')

    def test_remove(self, client):
        vm = mfactory.VirtualMachineFactory()
        # Also create a NIC
        mfactory.NetworkInterfaceFactory(machine=vm)
        msg = self.create_msg(operation='OP_INSTANCE_REMOVE',
                              instance=vm.backend_vm_id)
        update_db(client, msg)
        client.basic_ack.assert_called_once()
        db_vm = VirtualMachine.objects.get(id=vm.id)
        self.assertEqual(db_vm.operstate, 'DESTROYED')
        self.assertTrue(db_vm.deleted)
        # Check that nics are deleted
        self.assertFalse(db_vm.nics.all())

    def test_create(self, client):
        vm = mfactory.VirtualMachineFactory()
        msg = self.create_msg(operation='OP_INSTANCE_CREATE',
                              instance=vm.backend_vm_id)
        update_db(client, msg)
        client.basic_ack.assert_called_once()
        db_vm = VirtualMachine.objects.get(id=vm.id)
        self.assertEqual(db_vm.operstate, 'STARTED')

    def test_create_error(self, client):
        """Test that error create sets vm to ERROR state"""
        vm = mfactory.VirtualMachineFactory()
        msg = self.create_msg(operation='OP_INSTANCE_CREATE',
                              instance=vm.backend_vm_id,
                              status='error')
        update_db(client, msg)
        client.basic_ack.assert_called_once()
        db_vm = VirtualMachine.objects.get(id=vm.id)
        self.assertEqual(db_vm.operstate, 'ERROR')

    def test_remove_from_error(self, client):
        """Test that error removes delete error builds"""
        vm = mfactory.VirtualMachineFactory(operstate='ERROR')
        # Also create a NIC
        mfactory.NetworkInterfaceFactory(machine=vm)
        msg = self.create_msg(operation='OP_INSTANCE_REMOVE',
                              instance=vm.backend_vm_id)
        update_db(client, msg)
        client.basic_ack.assert_called_once()
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
        client.basic_ack.assert_called_once()
        db_vm = VirtualMachine.objects.get(id=vm.id)
        self.assertEqual(db_vm.operstate, vm.operstate)
        self.assertEqual(db_vm.backendtime, vm.backendtime)


@patch('synnefo.lib.amqp.AMQPClient')
class UpdateNetTest(TestCase):
    def create_msg(self, **kwargs):
        """Create snf-ganeti-hook message"""
        msg = {'event_time': split_time(time())}
        msg['type'] = 'ganeti-net-status'
        msg['status'] = 'success'
        msg['jobId'] = 1
        msg['logmsg'] = 'Dummy Log'
        for key, val in kwargs.items():
            msg[key] = val
        message = {'body': json.dumps(msg)}
        return message

    def test_missing_attribute(self, client):
        update_net(client, json.dumps({'body': {}}))
        client.basic_nack.assert_called_once()

    def test_unhandled_exception(self, client):
        update_net(client, {})
        client.basic_reject.assert_called_once()

    def test_wrong_type(self, client):
        msg = self.create_msg(type="WRONG_TYPE")
        update_net(client, msg)
        client.basic_ack.assert_called_once()

    def test_missing_instance(self, client):
        msg = self.create_msg(operation='OP_INSTANCE_STARTUP',
                              instance='foo')
        update_net(client, msg)
        client.basic_nack.assert_called_once()

    def test_no_nics(self, client):
        vm = mfactory.VirtualMachineFactory(operstate='ERROR')
        mfactory.NetworkInterfaceFactory(machine=vm)
        mfactory.NetworkInterfaceFactory(machine=vm)
        mfactory.NetworkInterfaceFactory(machine=vm)
        self.assertEqual(len(vm.nics.all()), 3)
        msg = self.create_msg(nics=[],
                              instance=vm.backend_vm_id)
        update_net(client, msg)
        client.basic_ack.assert_called_once()
        db_vm = VirtualMachine.objects.get(id=vm.id)
        self.assertEqual(len(db_vm.nics.all()), 0)

    def test_empty_nic(self, client):
        vm = mfactory.VirtualMachineFactory(operstate='ERROR')
        for public in [True, False]:
            net = mfactory.NetworkFactory(public=public)
            msg = self.create_msg(nics=[{'network':net.backend_id}],
                                  instance=vm.backend_vm_id)
            update_net(client, msg)
            client.basic_ack.assert_called_once()
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
        msg = self.create_msg(nics=[{'network':net.backend_id,
                                     'ip': '10.0.0.22',
                                     'mac': 'aa:bb:cc:00:11:22'}],
                              instance=vm.backend_vm_id)
        update_net(client, msg)
        client.basic_ack.assert_called_once()
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
        client.basic_nack.assert_called_once()

    def test_unhandled_exception(self, client):
        update_network(client, {})
        client.basic_reject.assert_called_once()

    def test_wrong_type(self, client):
        msg = self.create_msg(type="WRONG_TYPE")
        update_network(client, msg)
        client.basic_ack.assert_called_once()

    def test_missing_network(self, client):
        msg = self.create_msg(operation='OP_NETWORK_CREATE',
                              network='foo')
        update_network(client, msg)
        client.basic_nack.assert_called_once()

    def test_create(self, client):
        back_network = mfactory.BackendNetworkFactory(operstate='PENDING')
        net = back_network.network
        back1 = back_network.backend

        back_network2 = mfactory.BackendNetworkFactory(operstate='PENDING',
                                                       network=net)
        back2 = back_network2.backend
        # Message from first backend network
        msg = self.create_msg(operation='OP_NETWORK_CONNECT',
                              network=net.backend_id,
                              cluster=back1.clustername)
        update_network(client, msg)
        client.basic_ack.assert_called_once()

        back_net = BackendNetwork.objects.get(id=back_network.id)
        self.assertEqual(back_net.operstate, 'ACTIVE')
        db_net = Network.objects.get(id=net.id)
        self.assertEqual(db_net.state, 'PENDING')
        # msg from second backend network
        msg = self.create_msg(operation='OP_NETWORK_CONNECT',
                              network=net.backend_id,
                              cluster=back2.clustername)
        update_network(client, msg)
        client.basic_ack.assert_called_once()

        db_net = Network.objects.get(id=net.id)
        self.assertEqual(db_net.state, 'ACTIVE')
        back_net = BackendNetwork.objects.get(id=back_network.id)
        self.assertEqual(back_net.operstate, 'ACTIVE')

    def test_disconnect(self, client):
        bn1 = mfactory.BackendNetworkFactory(operstate='ACTIVE')
        net1 = bn1.network
        net1.operstate = 'ACTIVE'
        net1.save()
        bn2 = mfactory.BackendNetworkFactory(operstate='ACTIVE',
                                             network=net1)
        msg = self.create_msg(operation='OP_NETWORK_DISCONNECT',
                              network=net1.backend_id,
                              cluster=bn2.backend.clustername)
        update_network(client, msg)
        client.basic_ack.assert_called_once()
        self.assertEqual(Network.objects.get(id=net1.id).state, 'PENDING')
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
                update_network(client, msg)
                client.basic_ack.assert_called_once()
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

    def test_error_opcode(self, client):
        for state, _ in Network.OPER_STATES:
            bn = mfactory.BackendNetworkFactory()
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
                                      cluster=bn.backend.clustername)
                update_network(client, msg)
                client.basic_ack.assert_called_once()
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
        client.basic_ack.assert_called_once()
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
        client.basic_ack.assert_called_once()
        pool = network.get_pool()
        self.assertFalse(pool.is_reserved('10.0.0.10'))
        self.assertFalse(pool.is_reserved('10.0.0.20'))


class ProcessOpStatusTestCase(TestCase):
    fixtures = ['db_test_data']
    msg_op = {
        'instance': 'instance-name',
        'type': 'ganeti-op-status',
        'operation': 'OP_INSTANCE_STARTUP',
        'jobId': 0,
        'status': 'success',
        'logmsg': 'unittest - simulated message'
    }

    def test_op_startup_success(self):
        """Test notification for successful OP_INSTANCE_START"""
        msg = self.msg_op
        msg['operation'] = 'OP_INSTANCE_STARTUP'
        msg['status'] = 'success'

        # This machine is initially in BUILD
        vm = VirtualMachine.objects.get(pk=30002)
        backend.process_op_status(vm, now(), msg["jobId"], msg["operation"],
                                  msg["status"], msg["logmsg"])
        self.assertEquals(get_rsapi_state(vm), 'ACTIVE')

    def test_op_shutdown_success(self):
        """Test notification for successful OP_INSTANCE_SHUTDOWN"""
        msg = self.msg_op
        msg['operation'] = 'OP_INSTANCE_SHUTDOWN'
        msg['status'] = 'success'

        # This machine is initially in BUILD
        vm = VirtualMachine.objects.get(pk=30002)
        backend.process_op_status(vm, now(), msg["jobId"], msg["operation"],
                                  msg["status"], msg["logmsg"])
        self.assertEquals(get_rsapi_state(vm), 'STOPPED')

    def test_op_reboot_success(self):
        """Test notification for successful OP_INSTANCE_REBOOT"""
        msg = self.msg_op
        msg['operation'] = 'OP_INSTANCE_REBOOT'
        msg['status'] = 'success'

        # This machine is initially in BUILD
        vm = VirtualMachine.objects.get(pk=30002)
        backend.process_op_status(vm, now(), msg["jobId"], msg["operation"],
                                  msg["status"], msg["logmsg"])
        self.assertEquals(get_rsapi_state(vm), 'ACTIVE')

    def test_op_create_success(self):
        """Test notification for successful OP_INSTANCE_CREATE"""
        msg = self.msg_op
        msg['operation'] = 'OP_INSTANCE_CREATE'
        msg['status'] = 'success'

        # This machine is initially in BUILD
        vm = VirtualMachine.objects.get(pk=30002)
        backend.process_op_status(vm, now(), msg["jobId"], msg["operation"],
                                  msg["status"], msg["logmsg"])
        self.assertEquals(get_rsapi_state(vm), 'ACTIVE')

    def test_op_remove_success(self):
        """Test notification for successful OP_INSTANCE_REMOVE"""
        msg = self.msg_op
        msg['operation'] = 'OP_INSTANCE_REMOVE'
        msg['status'] = 'success'

        # This machine is initially in BUILD
        vm = VirtualMachine.objects.get(pk=30002)
        backend.process_op_status(vm, now(), msg["jobId"], msg["operation"],
                                  msg["status"], msg["logmsg"])
        self.assertEquals(get_rsapi_state(vm), 'DELETED')
        self.assertTrue(vm.deleted)

    def test_op_create_error(self):
        """Test notification for failed OP_INSTANCE_CREATE"""
        msg = self.msg_op
        msg['operation'] = 'OP_INSTANCE_CREATE'
        msg['status'] = 'error'

        # This machine is initially in BUILD
        vm = VirtualMachine.objects.get(pk=30002)
        backend.process_op_status(vm, now(), msg["jobId"], msg["operation"],
                                  msg["status"], msg["logmsg"])
        self.assertEquals(get_rsapi_state(vm), 'ERROR')
        self.assertFalse(vm.deleted)

    def test_remove_machine_in_error(self):
        """Test notification for failed OP_INSTANCE_REMOVE, server in ERROR"""
        msg = self.msg_op
        msg['operation'] = 'OP_INSTANCE_REMOVE'
        msg['status'] = 'error'

        # This machine is initially in BUILD
        vm = VirtualMachine.objects.get(pk=30002)
        backend.process_op_status(vm, now(), 0, "OP_INSTANCE_CREATE", "error", "test")
        self.assertEquals(get_rsapi_state(vm), 'ERROR')

        backend.process_op_status(vm, now(), msg["jobId"], msg["operation"],
                                  msg["status"], msg["logmsg"])
        self.assertEquals(get_rsapi_state(vm), 'DELETED')
        self.assertTrue(vm.deleted)


class ProcessNetStatusTestCase(TestCase):
    fixtures = ['db_test_data']

    def test_set_ipv4(self):
        """Test reception of a net status notification"""
        msg = {'instance': 'instance-name',
               'type':     'ganeti-net-status',
               'nics': [
                   {'ip': '10.0.0.21',
                    'mac': 'aa:00:00:58:1e:b9',
                    'network':'snf-net-30000'}
               ]
        }
        vm = VirtualMachine.objects.get(pk=30000)
        backend.process_net_status(vm, now(), msg['nics'])
        self.assertEquals(vm.nics.all()[0].ipv4, '10.0.0.21')

    def test_set_empty_ipv4(self):
        """Test reception of a net status notification with no IPv4 assigned"""
        msg = {'instance': 'instance-name',
               'type':     'ganeti-net-status',
               'nics': [
                   {'ip': '',
                    'mac': 'aa:00:00:58:1e:b9',
                    'network':'snf-net-30000'}
               ]
        }
        vm = VirtualMachine.objects.get(pk=30000)
        backend.process_net_status(vm, now(), msg['nics'])
        self.assertEquals(vm.nics.all()[0].ipv4, '')


class ProcessProgressUpdateTestCase(TestCase):
    fixtures = ['db_test_data']

    def test_progress_update(self):
        """Test reception of a create progress notification"""

        # This machine is in BUILD
        vm = VirtualMachine.objects.get(pk=30002)
        rprogress = randint(10, 100)

        backend.process_create_progress(vm, now(), rprogress)
        self.assertEquals(vm.buildpercentage, rprogress)

        #self.assertRaises(ValueError, backend.process_create_progress,
        #                  vm, 9, 0)
        self.assertRaises(ValueError, backend.process_create_progress,
                          now(), vm, -1)
        self.assertRaises(ValueError, backend.process_create_progress,
                          now(), vm, 'a')

        # This machine is ACTIVE
        #vm = VirtualMachine.objects.get(pk=30000)
        #self.assertRaises(VirtualMachine.IllegalState,
        #                  backend.process_create_progress, vm, 1)


class ReconciliationTestCase(TestCase):
    SERVERS = 1000
    fixtures = ['db_test_data']

    def test_get_servers_from_db(self):
        """Test getting a dictionary from each server to its operstate"""
        reconciliation.get_servers_from_db()
        self.assertEquals(reconciliation.get_servers_from_db(),
                          {30000: 'STARTED', 30001: 'STOPPED', 30002: 'BUILD'})

    def test_stale_servers_in_db(self):
        """Test discovery of stale entries in DB"""

        D = {1: 'STARTED', 2: 'STOPPED', 3: 'STARTED', 30000: 'BUILD',
             30002: 'STOPPED'}
        G = {1: True, 3: True, 30000: True}
        self.assertEquals(reconciliation.stale_servers_in_db(D, G),
                          set([2, 30002]))

    def test_orphan_instances_in_ganeti(self):
        """Test discovery of orphan instances in Ganeti, without a DB entry"""

        G = {1: True, 2: False, 3: False, 4: True, 50: True}
        D = {1: True, 3: False}
        self.assertEquals(reconciliation.orphan_instances_in_ganeti(D, G),
                          set([2, 4, 50]))

    def test_unsynced_operstate(self):
        """Test discovery of unsynced operstate between the DB and Ganeti"""

        G = {1: True, 2: False, 3: True, 4: False, 50: True}
        D = {1: 'STARTED', 2: 'STARTED', 3: 'BUILD', 4: 'STARTED', 50: 'BUILD'}
        self.assertEquals(reconciliation.unsynced_operstate(D, G),
                          set([(2, 'STARTED', False),
                           (3, 'BUILD', True), (4, 'STARTED', False),
                           (50, 'BUILD', True)]))
