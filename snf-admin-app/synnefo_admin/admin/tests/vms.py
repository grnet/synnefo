# -*- coding: utf-8 -*-
# Copyright (C) 2015 GRNET S.A.
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

from .common import AdminTestCase

from django.conf import settings
from synnefo_admin.admin.queries_common import prefix_strip

class TestAdminFilterVMs(AdminTestCase):

    def test_prefix_strip(self):

        postfix = u'α'
        stripped, lookup_type = prefix_strip(postfix)
        self.assertEqual(stripped, None)
        self.assertEqual(lookup_type, None)

        postfix = "1234"
        query = settings.BACKEND_PREFIX_ID + postfix
        stripped, lookup_type = prefix_strip(query)
        self.assertEqual(stripped, int(postfix))
        self.assertEqual(lookup_type, "startswith")

        stripped, lookup_type = prefix_strip(postfix)
        self.assertEqual(stripped, int(postfix))
        self.assertEqual(lookup_type, "contains")
