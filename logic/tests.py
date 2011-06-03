# vim: set fileencoding=utf-8 :
#
# Unit Tests for logic
#
# Provides automated tests for logic module
#
# Copyright 2010 Greek Research and Technology Network
#

from synnefo.db.models import *
from synnefo.logic import backend
from synnefo.logic import credits
from synnefo.logic import users
from django.test import TestCase
import time

import hashlib

class CostsTestCase(TestCase):
    fixtures = [ 'db_test_data' ]

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
    fixtures = [ 'db_test_data' ]

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
    fixtures = [ 'db_test_data' ]

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
    fixtures = [ 'db_test_data' ]

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

        self.assertRaises(SynnefoUser.DoesNotExist, SynnefoUser.objects.get, name = "jpage")


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
