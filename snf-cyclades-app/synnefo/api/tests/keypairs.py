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

import json
from django.conf import settings
from snf_django.utils.testing import BaseAPITest
from synnefo.userdata.models import PublicKeyPair
from synnefo.userdata import models_factory as mfactory

from synnefo.cyclades_settings import cyclades_services
from synnefo.lib.services import get_service_path
from synnefo.lib import join_urls

from mock import patch


COMPUTE_PATH = get_service_path(cyclades_services, "compute",
                                version="v2.0")
KEYPAIRS_PATH = join_urls(COMPUTE_PATH, 'os-keypairs')


class KeyPairAPITest(BaseAPITest):

    def get(self, endpoint, *args, **kwargs):
        url = join_urls(KEYPAIRS_PATH, endpoint)
        return super(KeyPairAPITest, self).get(url, *args, **kwargs)

    def post(self, endpoint, *args, **kwargs):
        url = join_urls(KEYPAIRS_PATH, endpoint)
        return super(KeyPairAPITest, self).post(url, *args, **kwargs)

    def delete(self, endpoint, *args, **kwargs):
        url = join_urls(KEYPAIRS_PATH, endpoint)
        return super(KeyPairAPITest, self).delete(url, *args, **kwargs)

    def setUp(self):

        self.user1 = 'user1'
        self.u1_key_name = 'test-keypair'
        self.keypair = mfactory.PublicKeyPairFactory(user=self.user1,
                                                     name=self.u1_key_name)

    def test_get_keypairs_list(self):
        response = self.get('')
        self.assertSuccess(response)
        keypairs = json.loads(response.content)['keypairs']
        self.assertEqual(keypairs, [])

    def test_get_keypairs_list_u1(self):
        response = self.get('', self.user1)
        self.assertSuccess(response)
        keypairs = json.loads(response.content)['keypairs']
        self.assertTrue(isinstance(keypairs, list))
        self.assertEqual(len(keypairs), 1)
        keypair = keypairs[0]['keypair']
        self.assertTrue(isinstance(keypair, dict))
        self.assertEqual(keypair['name'], self.u1_key_name)

    @patch('synnefo.api.util.get_keypair')
    def test_get_keypairs_detail(self, mkeypair):
        mkeypair.return_value = self.keypair
        response = self.get(self.u1_key_name, self.user1)
        self.assertSuccess(response)
        self.assertEqual(1, mkeypair.call_count)
        keypair = json.loads(response.content)['keypair']
        self.assertTrue(isinstance(keypair, dict))
        self.assertEqual(keypair['name'], self.u1_key_name)
