# -*- coding: utf-8 -*-
# Copyright (C) 2010-2016 GRNET S.A.
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
from synnefo_admin.admin.templatetags import admin_tags
from astakos.im.functions import submit_application
from astakos.im.models import Project
from .common import AdminTestCase
from datetime import datetime
from datetime import timedelta


class TemplateTagsTest(AdminTestCase):
    def test_flatten_dict_to_dl(self):
        input1 = {
            'foo': 'bar'
        }
        output1 = '<dt>foo</dt><dd>bar</dd>'
        self.assertEqual(admin_tags.flatten_dict_to_dl(input1), output1)

        input2 = {
            'foo': 'bar',
            'foo0': {
                'foo1': 'bar1'
            }
        }
        output2 = '<dt>foo</dt><dd>bar</dd><dt>foo1</dt><dd>bar1</dd>'
        self.assertEqual(admin_tags.flatten_dict_to_dl(input2), output2)

        input3 = [1, 2, 3]
        output3 = ''
        self.assertEqual(admin_tags.flatten_dict_to_dl(input3), output3)

        input4 = {
            'foo': ''
        }
        output4 = '<dt>foo</dt><dd>-</dd>'
        self.assertEqual(admin_tags.flatten_dict_to_dl(input4), output4)

        input5 = input4
        output5 = '<dt>foo</dt><dd>boo</dd>'
        self.assertEqual(admin_tags.flatten_dict_to_dl(input5, 'boo'), output5)

    def test_diff_cls(self):
        self.assertEqual(admin_tags.diff_cls(213231), 'diff-positive')
        self.assertEqual(admin_tags.diff_cls('foo'), 'diff-positive')
        self.assertEqual(admin_tags.diff_cls(-20), 'diff-negative')
        self.assertEqual(admin_tags.diff_cls(None), '')
        self.assertEqual(admin_tags.diff_cls(0), '')
        self.assertEqual(admin_tags.diff_cls('-'), 'diff-zero')

    def test_get_project_modifications(self):
        project = self.project
        t2 = project.end_date + timedelta(days=12)
        common_output = {
            'resources': [],
            'policies': [],
            'details': []
        }
        common_app_data = {
            'owner': self.user,
            'project_id': project.id,
            'request_user': self.user,
            'resources': {}
        }

        # test output for change in project details
        last_app_data1 = common_app_data.copy()
        last_app_data1.update({
            'name': 'test-new.gr',
            'description': u'δεσκρίπτιον2',
            'end_date': t2,
        })
        last_app1 = submit_application(**last_app_data1)
        project = Project.objects.get(id=project.id)
        output_details = common_output.copy()
        output_details.update({
            'details': [{
                'label': 'name',
                'new': 'test-new.gr',
                'old': 'test.pr',
            }, {
                'label': 'description',
                'new': u'δεσκρίπτιον2',
                'old': u'δεσκρίπτιον',
            }, {
                'label': 'end date',
                'new': t2,
                'old': project.end_date,
                'diff': timedelta(days=12)
            }],
        })
        input_details = admin_tags.get_project_modifications(project)
        self.assertEqual(input_details, output_details)

        # test output for change in project policies
        last_app_data2 = common_app_data.copy()
        last_app_data2.update({
            'limit_on_members_number': 42
        })
        last_app2 = submit_application(**last_app_data2)
        project = Project.objects.get(id=project.id)
        output_policies = common_output.copy()
        output_policies.update({
            'policies': [{
                'label': 'max members',
                'new': 42,
                'old': 5,
                'diff': 37,
            }],
        })
        input_policies = admin_tags.get_project_modifications(project)
        self.assertEqual(input_policies, output_policies)

        # test output for change in project resources
        last_app_data3 = common_app_data.copy()
        last_app_data3.update({
            'resources': {u"σέρβις1.ρίσορς11": {
                'project_capacity': 1025,
                'member_capacity': 511}}
        })
        last_app3 = submit_application(**last_app_data3)
        project = Project.objects.get(id=project.id)
        output_resources = common_output.copy()
        output_resources.update({
            'resources': [{
                'label': u"σέρβις1.ρίσορς11s",
                'new_member': '511',
                'old_member': '512',
                'diff_member': '-1',
                'new_project': '1025',
                'old_project': '1024',
                'diff_project': '+1'
            }],
        })
        input_resources = admin_tags.get_project_modifications(project)
        self.assertEqual(input_resources, output_resources)
