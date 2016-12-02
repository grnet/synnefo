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
from random import randint

from synnefo.logic.allocators.base import AllocatorBase
from synnefo.logic.allocators.filter_base import FilterBase
from synnefo.logic.allocators.filter_allocator import FilterAllocator
from synnefo.db.models import Backend


class DummyFilter(FilterBase):

    def filter_backends(self, backends, vm):
        return backends


class RemoveFirstBackendFilter(FilterBase):

    def filter_backends(self, backends, vm):
        if not backends:
            return backends

        return backends[1:]


class FilterAllocatorTest(TestCase):
    def setUp(self):
        self.allocator = FilterAllocator()

    def test_filter_allocator_inherits_allocator_base(self):
        """The filter allocator should inherit the AllocatorBase.

        """
        self.assertTrue(issubclass(FilterAllocator, AllocatorBase))

    @patch('synnefo.logic.allocators.filter_allocator.FilterAllocator.backend_score')  # NOQA
    def test_allocate(self, backend_score_mock):
        """
        The allocate function takes a list of backends
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
        """
        The backend_score function takes a backend as
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

    @patch('synnefo.logic.tests.allocators.DummyFilter.filter_backends')
    def test_filter_backends_without_filters(self, filter_mock):
        """
        When no filters are set, the filter allocator must be a no-op.

        """
        backends = [1, 2, 3]

        allocator = FilterAllocator(filter_modules=[])
        filtered_backends = allocator.filter_backends(backends, {})
        self.assertEqual(filtered_backends, backends)

    @patch('synnefo.logic.tests.allocators.DummyFilter.filter_backends')
    def test_filter_backends(self, filter_mock):
        """
        Filter allocator is responsible of running each registered filter,
        in order they were registered.

        """
        backends = [1, 2, 3]
        filters = [
            'synnefo.logic.tests.allocators.filter_allocator.DummyFilter',
            'synnefo.logic.tests.allocators.filter_allocator.DummyFilter'
        ]
        allocator = FilterAllocator(filter_modules=filters)
        allocator.filter_backends(backends, {})
        self.assertEqual(filter_mock.call_count, 2)

        filter_mock.reset_mock()
        filters = [
            'synnefo.logic.tests.allocators.filter_allocator.RemoveFirstBackendFilter',  # NOQA
            'synnefo.logic.tests.allocators.filter_allocator.DummyFilter'
        ]
        allocator = FilterAllocator(filter_modules=filters)
        allocator.filter_backends(backends, {})
        filter_mock.assert_called_once_with(backends[1:], {})
