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

import json

from snf_django.utils.testing import BaseAPITest
from synnefo.lib.services import get_service_path
from synnefo.cyclades_settings import cyclades_services
from synnefo.lib import join_urls

COMPUTE_URL = get_service_path(cyclades_services, 'compute',
                               version='v2.0')
EXTENSIONS_URL = join_urls(COMPUTE_URL, "extensions/")


class ExtensionsAPITest(BaseAPITest):
    def test_list(self):
        response = self.get(EXTENSIONS_URL, "user")
        self.assertSuccess(response)
        extensions = json.loads(response.content)["extensions"]
        self.assertEqual(extensions, [])

    def test_get(self):
        response = self.get(join_urls(EXTENSIONS_URL, "SNF"), "user")
        self.assertEqual(response.status_code, 404)
        response = self.get(join_urls(EXTENSIONS_URL, "SNF_asfas_da"), "user")
        self.assertEqual(response.status_code, 404)
        response = self.get(join_urls(EXTENSIONS_URL, "SNF-AD"), "user")
        self.assertEqual(response.status_code, 404)
