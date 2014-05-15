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

from django.utils import simplejson as json
from django.test import TestCase
from snf_django.utils.testing import astakos_user
from synnefo.cyclades_settings import cyclades_services
from synnefo.lib.services import get_service_path
from synnefo.lib import join_urls


class APITest(TestCase):
    def test_api_version(self):
        """Check API version."""
        path = get_service_path(cyclades_services,
                                'compute', version='v2.0')
        with astakos_user('user'):
            response = self.client.get(path.rstrip('/') + '/')
        self.assertEqual(response.status_code, 200)
        api_version = json.loads(response.content)['version']
        self.assertEqual(api_version['id'], 'v2.0')
        self.assertEqual(api_version['status'], 'CURRENT')

    def test_catch_wrong_api_paths(self, *args):
        path = get_service_path(cyclades_services,
                                'compute', version='v2.0')
        response = self.client.get(join_urls(path, 'nonexistent'))
        self.assertEqual(response.status_code, 400)
        try:
            error = json.loads(response.content)
        except ValueError:
            self.assertTrue(False)
