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
import unittest

from astakos.im.models import Project, Resource
from astakos.im.tests.projects import ProjectAPITest
from astakos.im.functions import approve_application

from synnefo_admin.admin.projects.utils import get_project_quota_category


class TestAdminProjects(ProjectAPITest):

    # Override the test_projects function of ProjectAPITest class so that it
    # doesn't get called.
    @unittest.skip("Skipping test of child class")
    def test_projects(self):
        pass

    def test_quota(self):
        # Do necessary initializations before carrying on with the actual test.

        # Create a simple project.
        h_owner = {"HTTP_X_AUTH_TOKEN": self.user1.auth_token}

        app1 = {"name": "test.pr",
                "description": u"δεσκρίπτιον",
                "end_date": "2013-5-5T20:20:20Z",
                "join_policy": "auto",
                "max_members": 5,
                "resources": {u"σέρβις1.ρίσορς11": {
                    "project_capacity": 1024,
                    "member_capacity": 512}}
                }
        status, body = self.create(app1, h_owner)

        # Ensure that the project application has been created.
        self.assertEqual(status, 201)
        project_id = body["id"]
        app_id = body["application"]

        # Approve the application.
        project = approve_application(app_id, project_id)
        self.assertIsNotNone(project)

        # The actual test begins here

        # Get the reported description of the resource.
        resource = Resource.objects.get(name=u"σέρβις1.ρίσορς11")
        desc = resource.report_desc

        # Get the member and project quota.
        member_quota = get_project_quota_category(project, "member")
        project_quota = get_project_quota_category(project, "limit")

        # Compare them to the ones in the application.
        self.assertEqual(member_quota, [(desc, '512')])
        self.assertEqual(project_quota, [(desc, '1024')])
