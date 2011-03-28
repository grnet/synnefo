#
# Unit Tests for logic
#
# Provides automated tests for logic module
#
# Copyright 2010 Greek Research and Technology Network
#

from db.models import *

from logic import credits

from django.test import TestCase

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
