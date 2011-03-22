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


class SynnefoUserTestCase(TestCase):
    fixtures = [ 'db_test_data' ]

    def test_synnefo_user(self):
        """Test a SynnefoUser object"""
        s_user = SynnefoUser.objects.get(pk=30000)
        v_machine = VirtualMachine.objects.get(pk=30000)

        # charge the user
        credits.debit_account(s_user, 10, v_machine, "This should be a structured debit message!")

        # should have only one debit object
        d_list = Debit.objects.all()

        self.assertEqual(len(d_list), 1, 'SynnefoUser.debit_account() writes more than one or zero (%d) debit entries!' % ( len(d_list), ))

        # retrieve the user, now he/she should have zero credits
        s_user = SynnefoUser.objects.get(pk=30000)

        self.assertEqual(0, s_user.credit, 'SynnefoUser (pk=30000) should have zero credits (%d)' % ( s_user.credit, ))
