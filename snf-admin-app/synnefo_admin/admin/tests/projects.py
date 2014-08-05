# -*- coding: utf-8 -*-
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

#import logging
from astakos.im.models import Resource

from synnefo_admin.admin.projects.utils import get_project_quota_category
from .common import AdminTestCase


class TestAdminProjects(AdminTestCase):

    """Test suite for project-related tests."""

    def test_quota(self):
        """Test if project quota are measured properly."""
        # Get the reported description of the resource.
        resource = Resource.objects.get(name=u"σέρβις1.ρίσορς11")
        desc = resource.report_desc

        # Get the member and project quota.
        member_quota = get_project_quota_category(self.project, "member")
        project_quota = get_project_quota_category(self.project, "limit")

        # Compare them to the ones in the application.
        self.assertEqual(member_quota, [(desc, '512')])
        self.assertEqual(project_quota, [(desc, '1024')])
