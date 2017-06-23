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

from mock import patch

from synnefo.logic.allocators.filter_default import DefaultFilter
from synnefo.logic.allocators.filter_base import FilterBase
from synnefo.db.models import Backend


class DefaultFilterTest(TestCase):
    def shortDescription(self):
        return None

    def setUp(self):
        self.filter = DefaultFilter()

    def test_default_filter_inherits_filter_base(self):
        """Every filter should inherit the FilterBase.

        """
        self.assertTrue(issubclass(DefaultFilter, FilterBase))

    def test_vm_fits_in_backend(self):
        """
        vm_fits_in_backend should check wether the
        backend has enough resources to satisfy the
        VM's needs.

        """
        backend = Backend()
        vm = {
            'disk': 10,
            'ram': 10,
        }

        # Not enough disk space
        backend.dfree = 5
        backend.mfree = 50
        backend.pinst_cnt = 1
        backend.ctotal = 100
        self.assertFalse(self.filter.vm_fits_in_backend(backend, vm))

        # Not enough memory
        backend.dfree = 50
        backend.mfree = 5
        self.assertFalse(self.filter.vm_fits_in_backend(backend, vm))

        # Not enough CPU
        backend.ctotal = 1
        backend.mfree = 50
        self.assertFalse(self.filter.vm_fits_in_backend(backend, vm))

        # The VM fits in the backend
        backend.ctotal = 100
        self.assertTrue(self.filter.vm_fits_in_backend(backend, vm))

    @patch('synnefo.logic.allocators.filter_default.DefaultFilter.vm_fits_in_backend')  # NOQA
    def test_filter_backends(self, vm_fits_mock):
        """The backends that the VM can fit into
        should not be filtered.

        """
        backends = [1, 2, 3]

        vm_fits_mock.return_value = True
        filtered_backends = self.filter.filter_backends(backends, {})
        self.assertEqual(backends, filtered_backends)

        # If the VM doesn't fit to any backend filter_backends should
        # return all of them
        vm_fits_mock.return_value = False
        filtered_backends = self.filter.filter_backends(backends, {})
        self.assertEqual(backends, filtered_backends)

        vm_fits_mock.side_effect = [True, False, False]
        filtered_backends = self.filter.filter_backends(backends, {})
        self.assertEqual([1], filtered_backends)
