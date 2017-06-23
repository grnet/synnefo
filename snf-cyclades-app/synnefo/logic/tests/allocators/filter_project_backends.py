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

from synnefo.logic.allocators.filter_base import FilterBase
from synnefo.logic.allocators.filter_project_backends import (
    ProjectBackendsFilter
)
from synnefo.db.models_factory import BackendFactory, ProjectBackendFactory


class ProjectBackendsFilterTest(TestCase):
    def shortDescription(self):
        return None

    def setUp(self):
        self.filter = ProjectBackendsFilter()
        self.b1 = BackendFactory()
        self.b2 = BackendFactory()
        self.b3 = BackendFactory(public=False)
        self.available_backends = [self.b1, self.b2, self.b3]

    def test_filter_inherits_filter_base(self):
        """ Every filter should inherit the FilterBase. """
        self.assertTrue(issubclass(ProjectBackendsFilter, FilterBase))

    def test_filter_backends_no_project(self):
        """
        When no project is set, the public backends from the available
        backends should be returned.
        """
        vm = {'project': 'no_project'}
        backends = self.filter.filter_backends(self.available_backends, vm)
        self.assertItemsEqual(backends, [self.b1, self.b2])

    def test_filter_backends_projects(self):
        """
        When project are set for the backend, the intersection of the backends
        set and the available backends must be returned, irrespectively from
        the backend's public flag.
        """

        pb2 = ProjectBackendFactory(backend=self.b2)
        pb3 = ProjectBackendFactory(backend=self.b3)

        vm = {'project': pb2.project}
        backends = self.filter.filter_backends(self.available_backends, vm)
        self.assertItemsEqual(backends, [self.b2])

        vm = {'project': pb3.project}
        backends = self.filter.filter_backends(self.available_backends, vm)
        self.assertItemsEqual(backends, [self.b3])

        ProjectBackendFactory(project=pb3.project, backend=self.b2)
        backends = self.filter.filter_backends(self.available_backends, vm)
        self.assertItemsEqual(backends, [self.b2, self.b3])
