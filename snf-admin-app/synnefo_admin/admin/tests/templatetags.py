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
from .common import AdminTestCase


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
        last_app_data = {
            'owner': self.user,
            'project_id': project.id,
            'request_user': self.user,
            "resources": {u"σέρβις1.ρίσορς11": {
                "project_capacity": 1025,
                "member_capacity": 511}}
        }
        app =submit_application(**last_app_data)
        output = {
            'resources': [{
                'label': u"ρίσορς11",
                'new_member': 511,
                'old_member': 512,
                'diff_member': -1,
                'new_project': 1025,
                'old_project': 1024,
                'diff_project': 1,
            }]
        }
        self.assertEqual(admin_tags.get_project_modifications(project), output)
