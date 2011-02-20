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

class CreditAllocatorTestCase(TestCase):
    fixtures = [ 'db_test_data' ]
        
    def test_credit_allocator(self):
        """Credit Allocator unit test method"""
        # test the allocator
        credit_allocator.allocate_credit()
        
        user = SynnefoUser.objects.get(pk=1)
        self.assertEquals(user.credit, 10, 'Allocation of credits failed, credit: (%d!=10)' % ( user.credit, ) )
        
        # get the quota from Limit model and check the answer
        limit_quota = Limit.get_limit_for_user('QUOTA_CREDIT', user)
        self.assertEquals(limit_quota, 100, 'User quota has not retrieved correctly (%d!=100)' % ( limit_quota, ))
        
        # test if the quota policy is endorced
        for i in range(1, 10):
            credit_allocator.allocate_credit()
                
        user = SynnefoUser.objects.get(pk=1)
        self.assertEquals(user.credit, limit_quota, 'User exceeded quota! (cr:%d, qu:%d)' % ( user.credit, limit_quota ) )


class FlavorCostHistoryTestCase(TestCase):
    fixtures = [ 'db_test_data' ]
    
    def test_flavor_cost_history(self):
        """Flavor Cost History unit test method"""
        flavor = Flavor.objects.get(pk=1)
        fch_list = flavor.get_price_list()
        
        self.assertEquals(len(fch_list), 2, 'Price list should have two objects! (%d!=2)' % ( len(fch_list), ))
        
        # 2010-10-10, active should be 2, inactive 1
        ex_date = date(year=2010, month=10, day=10)
        r = FlavorCostHistory.find_cost(fch_list, ex_date)
        
        self.assertEquals(r.cost_active, 2, 'Active cost for 2010-10-10 should be 2 (%d!=2)' % ( r.cost_active, ))
        self.assertEquals(r.cost_inactive, 1, 'Inactive cosr for 2010-10-10 should be 1 (%d!=1)' % ( r.cost_inactive, ))
        
        # 2011-11-11, active should be 10, inactive 5
        ex_date = date(year=2011, month=11, day=11)
        r = FlavorCostHistory.find_cost(fch_list, ex_date)
        self.assertEquals(r.cost_active, 10, 'Active cost for 2011-11-11 should be 10 (%d!=10)' % ( r.cost_active, ))
        self.assertEquals(r.cost_inactive, 5, 'Inactive cost for 2011-11-11 should be 5 (%d!=5)' % ( r.cost_inactive, ))


class FlavorTestCase(TestCase):
    def setUp(self):
        """Setup the test"""
        # Add the Flavor object
        flavor = Flavor(pk=1, cpu=10, ram=10, disk=10)
        flavor.save()
        
        # Add the FlavorCostHistory
        fch = FlavorCostHistory(pk=1, cost_active=10, cost_inactive=5)
        fch.effective_from = date(day=01, month=01, year=2011)
        fch.flavor = flavor
        fch.save()
        
        fch = FlavorCostHistory(pk=2, cost_active=2, cost_inactive=1)
        fch.effective_from = date(day=01, month=01, year=2010)
        fch.flavor = flavor
        fch.save()
    
    def tearDown(self):
        """Cleaning up the data"""
        flavor = Flavor.objects.get(pk=1)
        flavor.delete()
    
    def test_flavor(self):
        """Test a flavor object, its internal cost calculation and naming methods"""
        flavor = Flavor.objects.get(pk=1)
        
        self.assertEquals(flavor.cost_active, 10, 'Active cost is not calculated correctly! (%d!=10)' % ( flavor.cost_active, ) )
        self.assertEquals(flavor.cost_inactive, 5, 'Inactive cost is not calculated correctly! (%d!=5)' % ( flavor.cost_inactive, ) )
        self.assertEquals(flavor.name, u'C10R10D10', 'Invalid flavor name!')


class AccountingLogTestCase(TestCase):
    def setUp(self):
        """Setup the test"""
        userdj = User.objects.create_user('testuser','test','test2')
        userdj.save()
        
        # add a user
        user = SynnefoUser(pk=3, name='Test User', credit=100, monthly_rate=10)
        user.created = datetime.datetime.now()
        user.user = userdj
        user.violations = 0
        user.save()
        
        # add an Image
        si = Image(name='Test Name')
        si.updated = datetime.datetime.now()
        si.created = datetime.datetime.now()
        si.state = 'ACTIVE'
        si.owner = user
        si.description = 'testing 1.2.3'
        si.save()
        
        # add a Flavor
        flavor = Flavor(pk=11, cpu=10, ram=10, disk=10)
        flavor.save()
        
        # Now, add a VM
        vm = VirtualMachine(pk=10)
        vm.created = datetime.datetime.now()
        vm.charged = datetime.datetime.now() - datetime.timedelta(hours=1)
        vm.hostid = 'testhostid'
        vm.server_label = 'agreatserver'
        vm.image_version = '1.0.0'
        vm.ipfour = '127.0.0.1'
        vm.ipsix = '2001:0db8:85a3:0000:0000:8a2e:0370:7334'
        vm.flavor = flavor
        vm.sourceimage = si
        vm.save()
        
        # Now add the log entries
        alog = AccountingLog()
        alog.vm = vm
        alog.date = datetime.datetime(year=2010, month=01, day=01)
        alog.state = 'STARTED'
        alog.save()
        
        alog = AccountingLog()
        alog.vm = vm
        alog.date = datetime.datetime(year=2011, month=02, day=01)
        alog.state = 'STOPPED'
        alog.save()
        
    def tearDown(self):
        """Cleaning up the data"""
        user = User.objects.get(username='testuser')
        user.delete()
        
        flavor = Flavor.objects.get(pk=11)
        flavor.delete()
                
    def test_accounting_log(self):
        """Test the Accounting Log unit method"""
        vm = VirtualMachine.objects.get(pk=10)
        
        # get all entries, should be 2
        entries = AccountingLog.get_log_entries(vm, datetime.datetime(year=2009, month=01, day=01))
        self.assertEquals(len(entries), 2, 'Log entries should be 2 (%d!=2)' % ( len(entries), ))
        
        # get enrties only for 2011, should be 1
        entries = AccountingLog.get_log_entries(vm, datetime.datetime(year=2011, month=01, day=01))
        self.assertEquals(len(entries), 1, 'Log entries should be 1 (%d!=1)' % ( len(entries), ))


class ChargerTestCase(TestCase):
    def setUp(self):
        """Setup the test"""
        userdj = User.objects.create_user('testuser','test','test2')
        userdj.save()
        
        # add a user
        user = SynnefoUser(pk=1, name='Test User', credit=100, monthly_rate=10)
        user.created = datetime.datetime.now()
        user.user = userdj
        user.violations = 0
        user.max_violations = 5
        user.save()
        
        # add a Flavor
        flavor = Flavor(pk=1, cpu=10, ram=10, disk=10)
        flavor.save()
        
        # and fill the pricing list
        fch = FlavorCostHistory(pk=1, cost_active=10, cost_inactive=5)
        fch.effective_from = date(day=01, month=01, year=2010)
        fch.flavor = flavor
        fch.save()
        
        # add an Image
        si = Image(name='Test Name')
        si.updated = datetime.datetime.now()
        si.created = datetime.datetime.now()
        si.state = 'ACTIVE'
        si.owner = user
        si.description = 'testing 1.2.3'
        si.save()
        
        # Now, add a VM
        vm = VirtualMachine(pk=1)
        vm.created = datetime.datetime.now()
        vm.charged = datetime.datetime.now() - datetime.timedelta(hours=1)
        vm.hostid = 'testhostid'
        vm.server_label = 'agreatserver'
        vm.image_version = '1.0.0'
        vm.ipfour = '127.0.0.1'
        vm.ipsix = '2001:0db8:85a3:0000:0000:8a2e:0370:7334'
        vm.owner = user
        vm.flavor = flavor
        vm.sourceimage = si
        
        vm.save()
    
    def tearDown(self):
        """Cleaning up the data"""
        user = User.objects.get(username="testname")
        user.delete()
        
        flavor = Flavor.objects.get(pk=1)
    
    def test_charger(self):
        """Charger unit test method"""
        
        # charge when the vm is running
        charger.charge()
        
        user = SynnefoUser.objects.get(pk=1)
        self.assertEquals(user.credit, 90, 'Error in charging process (%d!=90, running)' % ( user.credit, ))
        
        # charge when the vm is stopped
        vm = VirtualMachine.objects.get(pk=1)
        vm.state = 'PE_VM_STOPPED'
        vm.charged = datetime.datetime.now() - datetime.timedelta(hours=1)
        vm.save()
        
        charger.charge()
        
        user = SynnefoUser.objects.get(pk=1)
        self.assertEquals(user.credit, 85, 'Error in charging process (%d!=85, stopped)' % ( user.credit, ))
        
        # try charge until the user spends all his credits, see if the charger
        vm = VirtualMachine.objects.get(pk=1)
        vm.state = 'PE_VM_RUNNING'
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
        

