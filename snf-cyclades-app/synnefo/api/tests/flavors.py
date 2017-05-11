# Copyright (C) 2010-2017 GRNET S.A.
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
from synnefo.db.models_factory import (
    FlavorFactory,
    FlavorAccessFactory,
    VirtualMachineFactory,
)
from synnefo.lib.services import get_service_path
from synnefo.cyclades_settings import cyclades_services
from synnefo.lib import join_urls
from django.db.models import Q


class FlavorAPITest(BaseAPITest):

    def setUp(self):
        self.flavor1 = FlavorFactory()
        self.flavor2 = FlavorFactory(deleted=True)
        self.flavor3 = FlavorFactory()
        self.project1 = 'project1'
        self.project2 = 'project2'
        self.project3 = 'project3'
        self.projects = [self.project1, self.project2]
        self.flavor4 = FlavorFactory(public=False)
        self.flavor5 = FlavorFactory(public=False)
        self.flavor6 = FlavorFactory(public=False)
        self.flavor7 = FlavorFactory(public=False)
        self.flavor8 = FlavorFactory()
        self.flavoraccess1 = FlavorAccessFactory(project=self.project1,
                                                 flavor=self.flavor4)
        self.flavoraccess2 = FlavorAccessFactory(project=self.project1,
                                                 flavor=self.flavor5)
        self.flavoraccess3 = FlavorAccessFactory(project=self.project2,
                                                 flavor=self.flavor6)
        self.flavoraccess4 = FlavorAccessFactory(project=self.project3,
                                                 flavor=self.flavor7)
        self.flavoraccess5 = FlavorAccessFactory(project=self.project1,
                                                 flavor=self.flavor8)
        self.compute_path = get_service_path(cyclades_services, 'compute',
                                             version='v2.0')

    def myget(self, path, projects=None, *args, **kwargs):
        path = join_urls(self.compute_path, path)
        if projects is None:
            projects = self.projects
        return self.get(path, _projects=projects, *args, **kwargs)

    def test_flavor_list(self):
        """Test if the expected list of flavors is returned."""
        response = self.myget('flavors')
        self.assertSuccess(response)

        api_flavors = json.loads(response.content)['flavors']
        db_flavors = Flavor.objects.filter(deleted=False)\
                                   .filter(Q(access__project__in=self.projects)
                                           | Q(public=True))
        self.assertEqual(len(api_flavors), len(db_flavors))
        for api_flavor in api_flavors:
            db_flavor = Flavor.objects.get(id=api_flavor['id'])
            self.assertEqual(api_flavor['id'], db_flavor.id)
            self.assertEqual(api_flavor['name'], db_flavor.name)
            # Test that the user has access to the returned projects
            access_projects = [a.project for a in db_flavor.access.all()]
            access_projects = set(self.projects).intersection(access_projects)
            self.assertTrue(db_flavor.public or len(access_projects) > 0)

    def test_flavors_details(self):
        """Test if the flavors details are returned."""
        response = self.myget('flavors/detail')
        self.assertSuccess(response)

        db_flavors = Flavor.objects.filter(deleted=False)\
                                   .filter(Q(access__project__in=self.projects)
                                           | Q(public=True))
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
            self.assertEqual(api_flavor['os-flavor-access:is_public'],
                             db_flavor.public)

            access_projects = [a.project for a in db_flavor.access.all()]
            access_projects = set(self.projects).intersection(access_projects)
            self.assertEqual(len(api_flavor['SNF:flavor-access']),
                             len(access_projects))
            for access in api_flavor['SNF:flavor-access']:
                self.assertTrue(access in access_projects)
                self.assertTrue(access in [a.project
                                           for a in db_flavor.access.all()])
                # The flavor-access returned must belong to the user's projects
                self.assertTrue(access in self.projects)

    def test_flavor_list_filter_public(self):
        """Test listing only public flavors"""
        response = self.myget('flavors/detail', data={'is_public': 'true'})
        self.assertSuccess(response)

        api_flavors = json.loads(response.content)['flavors']
        self.assertEqual(len(api_flavors), 3)
        for api_flavor in api_flavors:
            self.assertTrue(api_flavor['os-flavor-access:is_public'])

    def test_flavor_list_filter_non_public(self):
        """Test listing only non-public flavors"""
        response = self.myget('flavors/detail', data={'is_public': 'false'})
        self.assertSuccess(response)

        api_flavors = json.loads(response.content)['flavors']
        self.assertEqual(len(api_flavors), 3)
        for api_flavor in api_flavors:
            self.assertFalse(api_flavor['os-flavor-access:is_public'])
            self.assertTrue(len(api_flavor['SNF:flavor-access']) > 0)
            for access in api_flavor['SNF:flavor-access']:
                self.assertTrue(access in self.projects)

    def test_flavor_list_filter_project(self):
        """Test listing only flavors accesed by a specific project"""
        response = self.myget('flavors/detail',
                              data={'SNF:flavor-access': self.project1})
        self.assertSuccess(response)

        api_flavors = json.loads(response.content)['flavors']
        self.assertEqual(len(api_flavors), 3)
        for api_flavor in api_flavors:
            self.assertTrue(len(api_flavor['SNF:flavor-access']) > 0)
            self.assertTrue(self.project1 in api_flavor['SNF:flavor-access'])
            for access in api_flavor['SNF:flavor-access']:
                self.assertTrue(access in self.projects)

    def test_flavor_list_filter_public_and_project(self):
        """Test listing based public flag and project access"""
        response = self.myget('flavors/detail',
                              data={'is_public': True,
                                    'SNF:flavor-access': self.project1})
        self.assertSuccess(response)

        api_flavors = json.loads(response.content)['flavors']
        self.assertEqual(len(api_flavors), 1)
        for api_flavor in api_flavors:
            self.assertTrue(len(api_flavor['SNF:flavor-access']) > 0)
            self.assertTrue(self.project1 in api_flavor['SNF:flavor-access'])
            for access in api_flavor['SNF:flavor-access']:
                self.assertTrue(access in self.projects)

        response = self.myget('flavors/detail',
                              data={'is_public': False,
                                    'SNF:flavor-access': self.project1})
        self.assertSuccess(response)

        api_flavors = json.loads(response.content)['flavors']
        self.assertEqual(len(api_flavors), 2)
        for api_flavor in api_flavors:
            self.assertTrue(len(api_flavor['SNF:flavor-access']) > 0)
            self.assertTrue(self.project1 in api_flavor['SNF:flavor-access'])
            for access in api_flavor['SNF:flavor-access']:
                self.assertTrue(access in self.projects)

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
        self.assertEqual(api_flavor['os-flavor-access:is_public'],
                         db_flavor.public)
        self.assertEqual(api_flavor['SNF:flavor-access'], [])

    def test_flavor_access(self):
        """Test that API returns information only for flavors the user has
        access."""
        # try to get details of a private flavor with access
        response = self.myget('flavors/%d' % self.flavor4.id)
        self.assertSuccess(response)
        api_flavor = json.loads(response.content)['flavor']
        self.assertEquals(api_flavor['name'], self.flavor4.name)

        # try to get details of a public flavor
        response = self.myget('flavors/%d' % self.flavor8.id)
        self.assertSuccess(response)
        api_flavor = json.loads(response.content)['flavor']
        self.assertEquals(api_flavor['name'], self.flavor8.name)

        # try to get details of a non-public flavor with no access
        response = self.myget('flavors/%d' % self.flavor7.id)
        self.assertForbidden(response)

        # try to get details of a flavor with no access, but with spawned VM
        vm = VirtualMachineFactory(flavor=self.flavor7)
        response = self.myget('flavors/%d' % self.flavor7.id, user=vm.userid)
        self.assertSuccess(response)
        api_flavor = json.loads(response.content)['flavor']
        self.assertEquals(api_flavor['name'], self.flavor7.name)

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
        self.assertEqual(len(api_flavors), 6)

    def test_deleted_flavors_details(self):
        """Test that deleted flavors do not appear to flavors detail list"""
        FlavorFactory(deleted=True)
        response = self.myget('flavors/detail')
        self.assertSuccess(response)
        api_flavors = json.loads(response.content)['flavors']
        self.assertEqual(len(api_flavors), 6)

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
