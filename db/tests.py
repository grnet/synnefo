#
# Unit Tests for db
#
# Provides automated tests for db module
#
# Copyright 2010 Greek Research and Technology Network
#

import unittest
from datetime import datetime

from db.models import *

from db import CreditAllocator

class CreditAllocatorTestCase(unittest.TestCase):
    def setUp(self):
        """Setup the test"""
        user = OceanUser(id=1, name='Test User', credit=0, quota=100, monthly_rate=10)
        user.created = datetime.datetime.now()
        user.save()
    
    def tearDown(self):
        """Cleaning up the data"""
        user = OceanUser.objects.get(pk=1)
        user.delete()
    
    def test_credit_allocator(self):
        """Credit Allocator unit test method"""
        CreditAllocator.allocate_credit()        
        user = OceanUser.objects.get(pk=1)
        
        self.assertEquals(user.credit, 10, 'Allocation of credits failed, credit: %d (should be 10)' % ( user.credit, ) )
