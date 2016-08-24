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
from django.http import HttpRequest
import json
from django.core.urlresolvers import resolve

from synnefo.admin import views

from mock import patch

class CycladesAdminViewsTest(TestCase):
    @patch('synnefo.admin.stats.get_public_stats_from_cache')
    def test_get_public_stats(self, get_stats_mock):
        """get_public_stats should call get_public_stats_from_cache,
        convert it's output to json and return it.

        """
        data = {
            'a': 1,
            'b': 2,
            'c': 3
        }
        json_data = json.dumps(data)

        get_stats_mock.return_value = data

        request = HttpRequest()
        request.method = 'GET'
        response = views.get_public_stats_from_cache(request)

        self.assertEqual(200, response.status_code)
        self.assertEqual(json_data, response.content)

    def test_get_public_stats_has_valid_url(self):
        from synnefo.cyclades_settings import BASE_PATH, ADMIN_PREFIX
        prefix = '/%s/%s/' % (BASE_PATH, ADMIN_PREFIX)
        resolved = resolve(prefix + 'stats/simple')

        self.assertEqual(resolved.view_name, 'synnefo.admin.views.get_public_stats_from_cache')
