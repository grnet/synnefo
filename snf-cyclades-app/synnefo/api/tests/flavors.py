# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
                             db_flavor.volume_type.disk_template)

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
                         db_flavor.volume_type.disk_template)

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

        flavor_id = max(Flavor.objects.values_list('id', flat=True)) + 1
        response = self.myget('flavors/%d' % flavor_id)
        self.assertItemNotFound(response)

    def test_catch_wrong_api_paths(self, *args):
        response = self.myget('nonexistent')
        self.assertEqual(response.status_code, 400)
        try:
            json.loads(response.content)
        except ValueError:
            self.assertTrue(False)
