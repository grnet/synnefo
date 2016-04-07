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
from random import randint

from synnefo.logic.allocators import default_allocator, base
from synnefo.db.models import Backend

class DefaultAllocatorTest(TestCase):
    def setUp(self):
        self.allocator = default_allocator.DefaultAllocator()

    def test_default_allocator_inherits_allocator_base(self):
        """The default allocator should inherit the AllocatorBase.

        """
        self.assertTrue(issubclass(default_allocator.DefaultAllocator, base.AllocatorBase))

    def test_vm_fits_in_backend(self):
        """vm_fits_in_backend should check wether the
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
        self.assertFalse(self.allocator.vm_fits_in_backend(backend, vm))

        # Not enough memory
        backend.dfree = 50
        backend.mfree = 5
        self.assertFalse(self.allocator.vm_fits_in_backend(backend, vm))

        # Not enough CPU
        backend.ctotal = 1
        backend.mfree = 50
        self.assertFalse(self.allocator.vm_fits_in_backend(backend, vm))

        # The VM fits in the backend
        backend.ctotal = 100
        self.assertTrue(self.allocator.vm_fits_in_backend(backend, vm))

    @patch('synnefo.logic.allocators.default_allocator.DefaultAllocator.backend_score')
    def test_allocate(self, backend_score_mock):
        """The allocate function takes a list of backends
        and a map containing the VM's requirements.
        It's expected to score the backends using the
        backend_score function, and return the backend
        with the minimum score.

        """
        # the allocate function doesn't care if the backends
        # array actually contains Backend model instances
        # so for simplicity an integer array will be used

        # array with multiple backends
        backends = [1, 2, 3, 4]
        # So the third backend will have the minimum score
        backend_score_mock.side_effect = [10, 2, 1, 32]

        # our implementation doesn't use the VM provided
        self.assertEqual(backends[2], self.allocator.allocate(backends, []))

        # array with only one backend
        backends = [1]
        self.assertEqual(backends[0], self.allocator.allocate(backends, []))

    def test_backend_score(self):
        """The backend_score function takes a backend as
        an arguement and returns a score according to the following
        expression:
        score = 0.5 * (mem_ratio + disk_ratio + cpu_ratio)

        """
        backend = Backend()

        # mtotal and dtotal and ctotal not 0
        backend.mfree = mfree = randint(0, 10)
        backend.mtotal = mtotal = randint(11, 100)
        backend.dfree = dfree = randint(0, 10)
        backend.dtotal = dtotal = randint(11, 100)
        backend.pinst_cnt = pinst_cnt = randint(0, 10)
        backend.ctotal = ctotal = randint(11, 100)

        mem_ratio = 1 - (float(mfree) / mtotal)
        disk_ratio = 1 - (float(dfree) / dtotal)
        cpu_ratio = ((pinst_cnt + 1) * 4) / (float(ctotal) * 3)
        score = 0.5 * cpu_ratio + 0.5 * (mem_ratio + disk_ratio)

        self.assertEqual(score, self.allocator.backend_score(backend))

        # mtotal dtotal and ctotal are 0
        backend.mtotal = backend.dtotal = backend.ctotal = 0

        # when ctotal = 0 then we make cpu_ratio = 1
        self.assertEqual(0.5 * 1, self.allocator.backend_score(backend))

    @patch('synnefo.logic.allocators.default_allocator.DefaultAllocator.vm_fits_in_backend')
    def test_filter_backends(self, vm_fits_mock):
        """The backends that the VM can fit into
        should not be filtered.

        """
        backends = [1, 2, 3]

        vm_fits_mock.return_value = True
        filtered_backends = self.allocator.filter_backends(backends, {})
        self.assertEqual(backends, filtered_backends)

        # If the VM doesn't fit to any backend filter_backends should
        # return all of them
        vm_fits_mock.return_value = False
        filtered_backends = self.allocator.filter_backends(backends, {})
        self.assertEqual(backends, filtered_backends)

        vm_fits_mock.side_effect = [True, False, False]
        filtered_backends = self.allocator.filter_backends(backends, {})
        self.assertEqual([1], filtered_backends)
