#
# Unit Tests for db
#
# Provides automated tests for db module
#
# Copyright 2010 Greek Research and Technology Network
#

import unittest
from datetime import datetime, date

from db.models import *

from db import CreditAllocator

class CreditAllocatorTestCase(unittest.TestCase):
    def setUp(self):
        """Setup the test"""
        user = OceanUser(pk=1, name='Test User', credit=0, quota=100, monthly_rate=10)
        user.created = datetime.datetime.now()
        user.save()
    
    def tearDown(self):
        """Cleaning up the data"""
        user = OceanUser.objects.get(pk=1)
        user.delete()
    
    def test_credit_allocator(self):
        """Credit Allocator unit test method"""
        # test the allocator
        CreditAllocator.allocate_credit()        
        user = OceanUser.objects.get(pk=1)
        
        self.assertEquals(user.credit, 10, 'Allocation of credits failed, credit: %d (should be 10)' % ( user.credit, ) )
        
        # test if the quota policy is endorced
        for i in range(1, 10):
            CreditAllocator.allocate_credit()
        
        user = OceanUser.objects.get(pk=1)
        
        self.assertEquals(user.credit, user.quota, 'User exceeded quota! (cr:%d, qu:%d)' % ( user.credit, user.quota) )


class FlavorTestCase(unittest.TestCase):
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


class ChargerTestcase(unittest.TestCase):
    def setUp(self):
        """Setup the test"""
        # add the user
        user = OceanUser(pk=1, name='Test User', credit=100, quota=100, monthly_rate=10)
        user.created = datetime.datetime.now()
        user.save() 
        
    def tearDown(self):
        """Cleaning up the data"""
        user = OceanUser.objects.get(pk=1)
        user.delete()
    
    def test_charger(self):
        """Charger unit test method"""
        
