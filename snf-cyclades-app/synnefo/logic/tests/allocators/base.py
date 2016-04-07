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

from synnefo.logic.allocators.base import AllocatorBase

class AllocatorBaseTest(TestCase):
    def test_allocator_base_has_required_methods(self):
        """The AllocatorBase implements two methods:
        - allocate
        - filter_backends

        """
        allocate = getattr(AllocatorBase, "allocate", None)
        filter_backends = getattr(AllocatorBase, "filter_backends", None)
        self.assertTrue(callable(allocate))
        self.assertTrue(callable(filter_backends))

    def test_allocator_base_methods_throw_not_imlemented_error(self):
        """Since the AllocatorBase is acting as an interface,
        if the allocator class hasn't implemented any of the required
        functions a NotImplementedError exception should be raised.

        """
        instance = AllocatorBase()
        self.assertRaises(NotImplementedError, instance.allocate, None, None)
        self.assertRaises(NotImplementedError, instance.filter_backends, None, None)
