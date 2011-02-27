#
# Unit Tests for db
#
# Provides automated tests for db module
#
# Copyright 2010 Greek Research and Technology Network
#

import unittest

from datetime import datetime, date, timedelta

from db.models import *
from db import credit_allocator
from db import charger

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
import unittest

class CreditAllocatorTestCase(TestCase):
    fixtures = [ 'db_test_data' ]
        
    def test_credit_allocator(self):
        """Credit Allocator unit test method"""
        # test the allocator
        credit_allocator.allocate_credit()
        
        user = SynnefoUser.objects.get(pk=30000)
        self.assertEquals(user.credit, 10, 'Allocation of credits failed, credit: (%d!=10)' % ( user.credit, ) )
        
        # get the quota from Limit model and check the answer
        limit_quota = user.credit_quota
        self.assertEquals(limit_quota, 100, 'User quota has not retrieved correctly (%d!=100)' % ( limit_quota, ))
        
        # test if the quota policy is endorced
        for i in range(1, 10):
            credit_allocator.allocate_credit()
                
        user = SynnefoUser.objects.get(pk=30000)
        self.assertEquals(user.credit, limit_quota, 'User exceeded quota! (cr:%d, qu:%d)' % ( user.credit, limit_quota ) )


class FlavorTestCase(TestCase):
    fixtures = [ 'db_test_data' ]
    
    def test_flavor(self):
        """Test a flavor object, its internal cost calculation and naming methods"""
        flavor = Flavor.objects.get(pk=30000)
        
        flavor_name = u'C%dR%dD%d' % ( flavor.cpu, flavor.ram, flavor.disk )
        
        self.assertEquals(flavor.cost_active, 10, 'Active cost is not calculated correctly! (%d!=10)' % ( flavor.cost_active, ) )
        self.assertEquals(flavor.cost_inactive, 5, 'Inactive cost is not calculated correctly! (%d!=5)' % ( flavor.cost_inactive, ) )
        self.assertEquals(flavor.name, flavor_name, 'Invalid flavor name!')

    def test_flavor_cost_history(self):
        """Flavor unit test (find_cost method)"""
        flavor = Flavor.objects.get(pk=30000)
        fch_list = flavor.get_price_list()

        self.assertEquals(len(fch_list), 2, 'Price list should have two objects! (%d!=2)' % ( len(fch_list), ))

        # 2010-10-10, active should be 2, inactive 1
        ex_date = date(year=2010, month=10, day=10)
        r = flavor.find_cost(ex_date)

        self.assertEquals(r.cost_active, 2, 'Active cost for 2010-10-10 should be 2 (%d!=2)' % ( r.cost_active, ))
        self.assertEquals(r.cost_inactive, 1, 'Inactive cosr for 2010-10-10 should be 1 (%d!=1)' % ( r.cost_inactive, ))

        # 2011-11-11, active should be 10, inactive 5
        ex_date = date(year=2011, month=11, day=11)
        r = flavor.find_cost(ex_date)
        self.assertEquals(r.cost_active, 10, 'Active cost for 2011-11-11 should be 10 (%d!=10)' % ( r.cost_active, ))
        self.assertEquals(r.cost_inactive, 5, 'Inactive cost for 2011-11-11 should be 5 (%d!=5)' % ( r.cost_inactive, ))


class DebitTestCase(TestCase):
    fixtures = [ 'db_test_data' ]
                
    def test_accounting_log(self):
        """Test the Accounting Log unit method"""
        vm = VirtualMachine.objects.get(pk=30000)
        
        # get all entries, should be 2
        entries = Debit.get_log_entries(vm, datetime.datetime(year=2009, month=01, day=01))
        self.assertEquals(len(entries), 2, 'Log entries should be 2 (%d!=2)' % ( len(entries), ))
        
        # get enrties only for 2011, should be 1
        entries = Debit.get_log_entries(vm, datetime.datetime(year=2011, month=01, day=01))
        self.assertEquals(len(entries), 1, 'Log entries should be 1 (%d!=1)' % ( len(entries), ))


class VirtualMachineTestCase(TestCase):
    fixtures = [ 'db_test_data' ]
    
    def test_virtual_machine(self):
        """Virtual Machine (model) unit test method"""
        vm = VirtualMachine.objects.get(pk=30002)
        
        # should be three
        acc_logs = vm.get_accounting_logs()
        
        self.assertEquals(len(acc_logs), 3, 'Log Entries should be 3 (%d!=3)' % ( len(acc_logs), ))



class ChargerTestCase(TestCase):
    fixtures = [ 'db_test_data' ]

    def test_charger(self):
        """Charger unit test method"""
        
        # user with pk=1 should have 100 credits
        user = SynnefoUser.objects.get(pk=1)
        user.credit = 100
        user.save()
        
        # charge when the vm is running
        charger.charge()
        
        user = SynnefoUser.objects.get(pk=1)
        
        self.assertEquals(user.credit, 90, 'Error in charging process (%d!=90, running)' % ( user.credit, ))
        
        # charge when the vm is stopped
        vm = VirtualMachine.objects.get(pk=1)
        vm.charged = datetime.datetime.now() - datetime.timedelta(hours=1)
        vm.save()
        
        charger.charge()
        
        user = SynnefoUser.objects.get(pk=1)
        self.assertEquals(user.credit, 85, 'Error in charging process (%d!=85, stopped)' % ( user.credit, ))
        
        # try charge until the user spends all his credits, see if the charger
        vm = VirtualMachine.objects.get(pk=1)
        vm.charged = datetime.datetime.now() - datetime.timedelta(hours=1)
        vm.save()
        
        # the user now has 85, charge until his credits drop to zero
        for i in range(1, 10):
            vm = VirtualMachine.objects.get(pk=1)
            vm.charged = datetime.datetime.now() - datetime.timedelta(hours=1)
            vm.save()
            charger.charge()
        
        user = SynnefoUser.objects.get(pk=1)
        self.assertEquals(user.credit, 0, 'Error in charging process (%d!=0, running)' % ( user.credit, ))
        
