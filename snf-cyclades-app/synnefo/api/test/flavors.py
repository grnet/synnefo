# Copyright 2012 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

import json

from snf_django.utils.testing import BaseAPITest
from synnefo.db.models import Flavor
from synnefo.db.models_factory import FlavorFactory
from synnefo.lib.services import get_service_path
from synnefo.cyclades_settings import cyclades_services
from synnefo.lib import join_urls


class FlavorAPITest(BaseAPITest):

    def setUp(self):
        self.flavor1 = FlavorFactory()
        self.flavor2 = FlavorFactory(deleted=True)
        self.flavor3 = FlavorFactory()
        self.compute_path = get_service_path(cyclades_services, 'compute',
                                             version='v2.0')


    def myget(self, path):
        path = join_urls(self.compute_path, path)
        return self.get(path)


    def test_flavor_list(self):
        """Test if the expected list of flavors is returned."""
        response = self.myget('flavors')
        self.assertSuccess(response)

        api_flavors = json.loads(response.content)['flavors']
        db_flavors = Flavor.objects.filter(deleted=False)
        self.assertEqual(len(api_flavors), len(db_flavors))
        for api_flavor in api_flavors:
            db_flavor = Flavor.objects.get(id=api_flavor['id'])
            self.assertEqual(api_flavor['id'], db_flavor.id)
            self.assertEqual(api_flavor['name'], db_flavor.name)

    def test_flavors_details(self):
        """Test if the flavors details are returned."""
        response = self.myget('flavors/detail')
        self.assertSuccess(response)

        db_flavors = Flavor.objects.filter(deleted=False)
        api_flavors = json.loads(response.content)['flavors']

        self.assertEqual(len(db_flavors), len(api_flavors))

        for i in range(0, len(db_flavors)):
            api_flavor = api_flavors[i]
            db_flavor = Flavor.objects.get(id=db_flavors[i].id)
            self.assertEqual(api_flavor['vcpus'], db_flavor.cpu)
            self.assertEqual(api_flavor['id'], db_flavor.id)
            self.assertEqual(api_flavor['disk'], db_flavor.disk)
            self.assertEqual(api_flavor['name'], db_flavor.name)
            self.assertEqual(api_flavor['ram'], db_flavor.ram)
            self.assertEqual(api_flavor['SNF:disk_template'],
                                        db_flavor.disk_template)

    def test_flavor_details(self):
        """Test if the expected flavor is returned."""
        flavor = self.flavor3

        response = self.myget('flavors/%d' % flavor.id)
        self.assertSuccess(response)

        api_flavor = json.loads(response.content)['flavor']
        db_flavor = Flavor.objects.get(id=flavor.id)
        self.assertEqual(api_flavor['vcpus'], db_flavor.cpu)
        self.assertEqual(api_flavor['id'], db_flavor.id)
        self.assertEqual(api_flavor['disk'], db_flavor.disk)
        self.assertEqual(api_flavor['name'], db_flavor.name)
        self.assertEqual(api_flavor['ram'], db_flavor.ram)
        self.assertEqual(api_flavor['SNF:disk_template'],
                         db_flavor.disk_template)

    def test_deleted_flavor_details(self):
        """Test that API returns details for deleted flavors"""
        flavor = self.flavor2
        response = self.myget('flavors/%d' % flavor.id)
        self.assertSuccess(response)
        api_flavor = json.loads(response.content)['flavor']
        self.assertEquals(api_flavor['name'], flavor.name)

    def test_deleted_flavors_list(self):
        """Test that deleted flavors do not appear to flavors list"""
        response = self.myget('flavors')
        self.assertSuccess(response)
        api_flavors = json.loads(response.content)['flavors']
        self.assertEqual(len(api_flavors), 2)

    def test_deleted_flavors_details(self):
        """Test that deleted flavors do not appear to flavors detail list"""
        FlavorFactory(deleted=True)
        response = self.myget('flavors/detail')
        self.assertSuccess(response)
        api_flavors = json.loads(response.content)['flavors']
        self.assertEqual(len(api_flavors), 2)

    def test_wrong_flavor(self):
        """Test 404 result when requesting a flavor that does not exist."""

        # XXX: flavors/22 below fails for no apparent reason
        response = self.myget('flavors/%d' % 23)
        self.assertItemNotFound(response)
