# Copyright (C) 2010-2016 GRNET S.A. and individual contributors
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

from django.test import TestCase

from synnefo.logic.allocators import *
from synnefo.db import models_factory
from synnefo.db.models import Backend

class GeneralAllocatorTests(TestCase):
    def setUp(self):
        self.allocators = [cls() for cls in AllocatorBase.__subclasses__()]
        self.backend = models_factory.BackendFactory()

        flavor = models_factory.FlavorFactory()
        disk = flavor.disk * 1024
        ram = flavor.ram
        cpu = flavor.cpu

        self.vm = {'ram': ram, 'disk': disk, 'cpu': cpu, 'project': 'no_project'}


    def test_each_allocator_has_required_methods(self):
        """Each allocator has 2 required methods:
        - filter_backends which takes 2 arguements
        - allocate which takes 2 arguements

        """

        for allocator in self.allocators:
            try:
                allocator.filter_backends([self.backend], self.vm)
            except NotImplementedError:
                self.fail('The allocator ' + allocator.__name__ +
                    ' has not defined the `filter_backends` function.')

            try:
                allocator.allocate([self.backend], self.vm)
            except NotImplementedError:
                self.fail('The allocator ' + allocator.__name__ +
                    ' has not defined the `allocate` function.')

    def test_filter_backends_does_not_change_database(self):
        """Each allocator's `filter_backends` function should
        not change the backends in the database.

        """
        for allocator in self.allocators:
            allocator.filter_backends([self.backend], self.vm)
            backend = Backend.objects.get(pk=self.backend.pk)
            self.assertEqual(backend, self.backend)
