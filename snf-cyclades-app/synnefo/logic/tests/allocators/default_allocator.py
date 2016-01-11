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
from mock import patch, Mock

from synnefo.logic.allocators import default_allocator as allocator

class DefaultAllocatorTest(TestCase):
    @patch('synnefo.logic.allocators.default_allocator.vm_fits_in_backend')
    def test_filter_backends(self, vm_fits_mock):
        """The backends that the VM can fit into
        should not be filtered.

        """
        backends = [1, 2, 3]

        vm_fits_mock.return_value = True
        filtered_backends = allocator.filter_backends(backends, {})
        self.assertEqual(backends, filtered_backends)

        # If the VM doesn't fit to any backend filter_backends should
        # return all of them
        vm_fits_mock.return_value = False
        filtered_backends = allocator.filter_backends(backends, {})
        self.assertEqual(backends, filtered_backends)

        vm_fits_mock.side_effect = [True, False, False]
        filtered_backends = allocator.filter_backends(backends, {})
        self.assertEqual([1], filtered_backends)
