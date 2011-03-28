#
# Unit Tests for db
#
# Provides automated tests for db module
#
# Copyright 2010 Greek Research and Technology Network
#

from db.models import *

from django.test import TestCase


class FlavorTestCase(TestCase):
    fixtures = [ 'db_test_data' ]

    def test_flavor(self):
        """Test a flavor object, its internal cost calculation and naming methods"""
        flavor = Flavor.objects.get(pk=30000)

        # test current active/inactive costs
        c_active = flavor.current_cost_active
        c_inactive = flavor.current_cost_inactive

        self.assertEqual(c_active, 10, 'flavor.cost_active should be 10! (%d)' % (c_active,))
        self.assertEqual(c_inactive, 5, 'flavor.cost_inactive should be 5! (%d)' % (c_inactive,))

        # test name property, should be C1R1024D10
        f_name = flavor.name

        self.assertEqual(f_name, 'C1R1024D10', 'flavor.name is not generated correctly, C1R1024D10! (%s)' % (f_name,))
