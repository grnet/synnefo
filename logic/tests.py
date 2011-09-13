# vim: set fileencoding=utf-8 :
# Copyright 2011 GRNET S.A. All rights reserved.
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

import time
import hashlib
from random import randint

from django.test import TestCase
from django.conf import settings

from synnefo.db.models import *
from synnefo.logic import backend
from synnefo.logic import credits
from synnefo.logic import users
from synnefo.logic import reconciliation
from synnefo.logic.utils import get_rsapi_state


class CostsTestCase(TestCase):
    fixtures = ['db_test_data']

    def test_get_costs(self):
        """Test the Flavor cost-related methods method"""
        # first an easy test, a Flavor with only one FlavorCost entry
        flavor = Flavor.objects.get(pk=30001)

        start_date = datetime.datetime(year=2010, month=1, day=1)
        end_date = datetime.datetime(year=2010, month=1, day=2)

        # we now that the cost should be 5*24 (inactive) and 10*24 (active)
        r_active = credits.get_cost_active(flavor, start_date, end_date)
        r_inactive = credits.get_cost_inactive(flavor, start_date, end_date)

        self.assertEqual(len(r_active), 1, 'get_cost_active() should have returned 1 entry (%d)' %(len(r_active),))
        self.assertEqual(len(r_inactive), 1, 'get_cost_inactive() should have returned 1 entry (%d)'% (len(r_inactive),))

        self.assertEqual(10*24, r_active[0][1], 'get_cost_active() is not working properly (%d!=%d)' % (r_active[0][1], 10*24))
        self.assertEqual(5*24, r_inactive[0][1], 'get_cost_inactive() is not working properly (%d!=%d)' % (r_inactive[0][1], 5*24))

        # The second test, will involve a more complex cost example
        # The overall cost will be calculated by two FlavorCost entries

        flavor = Flavor.objects.get(pk=30000)

        start_date = datetime.datetime(year=2010, month=12, day=31)
        end_date = datetime.datetime(year=2011, month=01, day=2)

        # this is more complicated, active costs are 5*24 + 10*24 = 360
        # and inactive costs are 2*24 + 5*24 = 168

        r_active = credits.get_cost_active(flavor, start_date, end_date)
        r_inactive = credits.get_cost_inactive(flavor, start_date, end_date)

        self.assertEqual(len(r_active), 2, 'get_cost_active() should have returned 2 entries (%d)' %(len(r_active),))
        self.assertEqual(len(r_inactive), 2, 'get_cost_inactive() should have returned 2 entries (%d)'% (len(r_inactive),))

        ta_cost = sum([x[1] for x in r_active])
        tia_cost = sum([x[1] for x in r_inactive])

        self.assertEqual(360, ta_cost, 'get_cost_active() is not working properly (%d!=%d)' % (ta_cost, 360))
        self.assertEqual(168, tia_cost, 'get_cost_inactive() is not working properly (%d!=%d)' % (tia_cost, 168))

        
class ChargeTestCase(TestCase):
    fixtures = ['db_test_data']

    def test_charge_method(self):
        """Test VirtualMachine.charge() method"""

        # Since we have tested the costs, with this test
        # we must ensure the following:
        # 1. The vm.charged is updated
        # 2. Users credits are decreased

        vm_started = VirtualMachine.objects.get(pk=30000)

        initial_date = vm_started.charged
        initial_credits = vm_started.owner.credit

        credits.charge(vm_started)

        self.assertTrue(vm_started.charged > initial_date, 'Initial charged date should not be greater')
        self.assertTrue(initial_credits > vm_started.owner.credit, 'The user should have less credits now! (%d>%d)' % (initial_credits, vm_started.owner.credit))


class DebitAccountTestCase(TestCase):
    fixtures = ['db_test_data']

    def test_debit_account(self):
        """Test a SynnefoUser object"""
        s_user = SynnefoUser.objects.get(pk=30000)
        v_machine = VirtualMachine.objects.get(pk=30000)

        # charge the user
        credits.debit_account(s_user, 10, v_machine, "This should be a structured debit message!")

        # should have only one debit object
        d_list = Debit.objects.all()

        self.assertEqual(len(d_list), 1, 'debit_account() writes more than one or zero (%d) debit entries!' % ( len(d_list), ))

        # retrieve the user, now he/she should have zero credits
        s_user = SynnefoUser.objects.get(pk=30000)

        self.assertEqual(0, s_user.credit, 'SynnefoUser (pk=30000) should have zero credits (%d)' % ( s_user.credit, ))


class AuthTestCase(TestCase):
    fixtures = ['db_test_data']

    def _register_user(self):
        users.register_student ("Jimmy Page", "jpage", "jpage@zoso.com")
        self.user = SynnefoUser.objects.get(name = "jpage")

    def test_register(self):
        """ test user registration
        """
        self._register_user()
        self.assertNotEquals(self.user, None)

        #Check hash generation
        md5 = hashlib.md5()
        md5.update(self.user.uniq)
        md5.update(self.user.name)
        md5.update(time.asctime())

        self.assertEquals(self.user.auth_token, md5.hexdigest())

    def test_del_user(self):
        """ test user deletion
        """
        self._register_user()
        self.assertNotEquals(self.user, None)
        
        users.delete_user(self.user)

        self.assertRaises(SynnefoUser.DoesNotExist, SynnefoUser.objects.get,
                          name = "jpage")


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
        backend.process_op_status(vm, msg["jobId"], msg["operation"],
                                  msg["status"], msg["logmsg"])
        self.assertEquals(get_rsapi_state(vm), 'ACTIVE')

    def test_op_shutdown_success(self):
        """Test notification for successful OP_INSTANCE_SHUTDOWN"""
        msg = self.msg_op
        msg['operation'] = 'OP_INSTANCE_SHUTDOWN'
        msg['status'] = 'success'

        # This machine is initially in BUILD
        vm = VirtualMachine.objects.get(pk=30002)
        backend.process_op_status(vm, msg["jobId"], msg["operation"],
                                  msg["status"], msg["logmsg"])
        self.assertEquals(get_rsapi_state(vm), 'STOPPED')

    def test_op_reboot_success(self):
        """Test notification for successful OP_INSTANCE_REBOOT"""
        msg = self.msg_op
        msg['operation'] = 'OP_INSTANCE_REBOOT'
        msg['status'] = 'success'

        # This machine is initially in BUILD
        vm = VirtualMachine.objects.get(pk=30002)
        backend.process_op_status(vm, msg["jobId"], msg["operation"],
                                  msg["status"], msg["logmsg"])
        self.assertEquals(get_rsapi_state(vm), 'ACTIVE')

    def test_op_create_success(self):
        """Test notification for successful OP_INSTANCE_CREATE"""
        msg = self.msg_op
        msg['operation'] = 'OP_INSTANCE_CREATE'
        msg['status'] = 'success'

        # This machine is initially in BUILD
        vm = VirtualMachine.objects.get(pk=30002)
        backend.process_op_status(vm, msg["jobId"], msg["operation"],
                                  msg["status"], msg["logmsg"])
        self.assertEquals(get_rsapi_state(vm), 'ACTIVE')

    def test_op_remove_success(self):
        """Test notification for successful OP_INSTANCE_REMOVE"""
        msg = self.msg_op
        msg['operation'] = 'OP_INSTANCE_REMOVE'
        msg['status'] = 'success'

        # This machine is initially in BUILD
        vm = VirtualMachine.objects.get(pk=30002)
        backend.process_op_status(vm, msg["jobId"], msg["operation"],
                                  msg["status"], msg["logmsg"])
        self.assertEquals(get_rsapi_state(vm), 'DELETED')
        self.assertTrue(vm.deleted)

    def test_unknown_op(self):
        """Test notification for unknown Ganeti op raises exception"""
        msg = self.msg_op
        msg['operation'] = 'OP_INSTANCE_SOMETHING_ELSE'
        msg['status'] = 'success'

        # This machine is initially in BUILD
        vm = VirtualMachine.objects.get(pk=30002)
        self.assertRaises(VirtualMachine.InvalidBackendMsgError,
                          backend.process_op_status,
                          vm, msg["jobId"], msg["operation"],
                          msg["status"], msg["logmsg"])

    def test_op_create_error(self):
        """Test notification for failed OP_INSTANCE_CREATE"""
        msg = self.msg_op
        msg['operation'] = 'OP_INSTANCE_CREATE'
        msg['status'] = 'error'

        # This machine is initially in BUILD
        vm = VirtualMachine.objects.get(pk=30002)
        backend.process_op_status(vm, msg["jobId"], msg["operation"],
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
        backend.process_op_status(vm, 0, "OP_INSTANCE_CREATE", "error", "test")
        self.assertEquals(get_rsapi_state(vm), 'ERROR')

        backend.process_op_status(vm, msg["jobId"], msg["operation"],
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
                   {'ip': '192.168.33.1', 'mac': 'aa:00:00:58:1e:b9'}
               ]
        }
        vm = VirtualMachine.objects.get(pk=30000)
        backend.process_net_status(vm, msg['nics'])
        self.assertEquals(vm.nics.all()[0].ipv4, '192.168.33.1')

    def test_set_empty_ipv4(self):
        """Test reception of a net status notification with no IPv4 assigned"""
        msg = {'instance': 'instance-name',
               'type':     'ganeti-net-status',
               'nics': [
                   {'ip': '', 'mac': 'aa:00:00:58:1e:b9'}
               ]
        }
        vm = VirtualMachine.objects.get(pk=30000)
        backend.process_net_status(vm, msg['nics'])
        self.assertEquals(vm.nics.all()[0].ipv4, '')


class UsersTestCase(TestCase):
    def test_create_uname(self):
        username = users.create_uname("Donald Knuth")
        self.assertEquals(username, "knuthd")

        username = users.create_uname("Nemichandra Siddhanta Chakravati")
        self.assertEquals(username, "chakravn")

        username = users.create_uname(u'Γεώργιος Παπαγεωργίου')
        self.assertEquals(username, u'παπαγεωγ')


class ProcessProgressUpdateTestCase(TestCase):
    fixtures = ['db_test_data']

    def test_progress_update(self):
        """Test reception of a create progress notification"""

        # This machine is in BUILD
        vm = VirtualMachine.objects.get(pk=30002)
        rprogress = randint(10, 100)

        backend.process_create_progress(vm, rprogress, 0)
        self.assertEquals(vm.buildpercentage, rprogress)

        #self.assertRaises(ValueError, backend.process_create_progress,
        #                  vm, 9, 0)
        self.assertRaises(ValueError, backend.process_create_progress,
                          vm, -1, 0)
        self.assertRaises(ValueError, backend.process_create_progress,
                          vm, 'a', 0)

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

        D = {1: 'STARTED', 2: 'STOPPED', 3: 'STARTED', 4: 'BUILD', 5: 'BUILD'}
        G = {1: True, 3: True}
        self.assertEquals(reconciliation.stale_servers_in_db(D, G),
                          [2, 4, 5])

    def test_orphan_instances_in_ganeti(self):
        """Test discovery of orphan instances in Ganeti, without a DB entry"""

        G = {1: True, 2: False, 3: False, 4: True, 50: True}
        D = {1: True, 3: False}
        self.assertEquals(reconciliation.orphan_instances_in_ganeti(D, G),
                          [2, 4, 50])

    def test_unsynced_operstate(self):
        """Test discovery of unsynced operstate between the DB and Ganeti"""

        G = {1: True, 2: False, 3: True, 4: False, 50: True}
        D = {1: 'STARTED', 2: 'STARTED', 3: 'BUILD', 4: 'STARTED', 50: 'BUILD'}
        self.assertEquals(reconciliation.unsynced_operstate(D, G),
                          set((2, 'STARTED', False),
                           (3, 'BUILD', True), (4, 'STARTED', False),
                           (50, 'BUILD', True)))
