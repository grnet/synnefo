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

# Unit Tests for db
#
# Provides automated tests for db module

from synnefo.db.models import *
from django.test import TestCase

# Import pool tests
from synnefo.db.pools.tests import *


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
