# coding=utf-8
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
import urllib
from snf_django.utils.testing import BaseAPITest
from synnefo.userdata import models_factory as mfactory

from synnefo.cyclades_settings import cyclades_services
from synnefo.lib.services import get_service_path
from synnefo.lib import join_urls


COMPUTE_PATH = get_service_path(cyclades_services, "compute",
                                version="v2.0")
KEYPAIRS_PATH = join_urls(COMPUTE_PATH, 'os-keypairs')


class KeyPairAPITest(BaseAPITest):

    def setUp(self):
        self.user1 = 'user1'
        self.u1_key_name = 'test-keypair'
        self.keypair = mfactory.PublicKeyPairFactory(user=self.user1,
                                                     name=self.u1_key_name)

    def test_get_keypairs_list(self):
        """Test if the expected list of keypairs is returned"""
        response = self.get(KEYPAIRS_PATH)
        self.assertSuccess(response)
        keypairs = json.loads(response.content)['keypairs']
        self.assertEqual(keypairs, [])

    def test_get_keypairs_list_user1(self):
        """Test if the expected list of keypairs for a user is returned"""
        response = self.get(KEYPAIRS_PATH, self.user1)
        self.assertSuccess(response)
        keypairs = json.loads(response.content)['keypairs']
        self.assertTrue(isinstance(keypairs, list))
        self.assertEqual(len(keypairs), 1)
        keypair = keypairs[0]['keypair']
        self.assertTrue(isinstance(keypair, dict))
        self.assertEqual(keypair['name'], self.u1_key_name)

    def test_get_keypairs_detail(self):
        """Test if the details of a keypair are returned correctly"""
        new_keypair = mfactory.PublicKeyPairFactory(user=self.user1,
                                                    name='new-keypair')
        response = self.get(join_urls(KEYPAIRS_PATH, new_keypair.name),
                            self.user1)
        self.assertSuccess(response)
        keypair = json.loads(response.content)['keypair']
        self.assertEqual(keypair['name'], new_keypair.name)
        self.assertEqual(keypair['fingerprint'], new_keypair.fingerprint)
        self.assertIsNotNone(keypair['created_at'])
        self.assertIsNotNone(keypair['updated_at'])
        self.assertIsNone(keypair['deleted_at'])
        self.assertFalse(keypair['deleted'])

    def test_get_keypairs_detail_unicode_name(self):
        """Test if the details of a keypair with non-ASCII name are returned
        correctly
        """
        new_keypair = mfactory.PublicKeyPairFactory(user=self.user1,
                                                    name=u'το κλειδί μου!@#')
        response = self.get(join_urls(KEYPAIRS_PATH,
                            urllib.quote(new_keypair.name.encode('utf-8'))),
                            self.user1)
        self.assertSuccess(response)
        keypair = json.loads(response.content)['keypair']
        self.assertEqual(keypair['name'], new_keypair.name)
        self.assertEqual(keypair['fingerprint'], new_keypair.fingerprint)
        self.assertIsNotNone(keypair['created_at'])
        self.assertIsNotNone(keypair['updated_at'])
        self.assertIsNone(keypair['deleted_at'])
        self.assertFalse(keypair['deleted'])

    def test_get_invalid_keypair(self):
        """Test if an invalid key name is not present"""
        response = self.get(join_urls(KEYPAIRS_PATH, 'invalid-keypair'),
                            self.user1)
        self.assertItemNotFound(response)

    def test_get_key_with_control_chars_name(self):
        """Test keypair endpoint with name containing control characters"""
        response = self.get(join_urls(KEYPAIRS_PATH, u'\u0000'), self.user1)
        self.assertBadRequest(response)

    def test_get_key_with_separator_chars_name(self):
        """Test keypair endpoint with name containing separator characters"""
        response = self.get(join_urls(KEYPAIRS_PATH, u'\u2028'), self.user1)
        self.assertBadRequest(response)

    def test_create_keypair_empty_request(self):
        """Test if an empty creation request will fail"""
        empty_request = {}
        response = self.post(KEYPAIRS_PATH, self.user1,
                             json.dumps(empty_request))
        self.assertBadRequest(response)

    def test_create_key_with_control_chars_name(self):
        """Test keypair creation with name containing control characters"""
        keypair_wo_content = {'keypair': {'name': u'\u0000'}}
        response = self.post(KEYPAIRS_PATH, self.user1,
                             json.dumps(keypair_wo_content))
        self.assertBadRequest(response)

    def test_create_key_with_separator_chars_name(self):
        """Test keypair creation with name containing separator characters"""
        keypair_wo_content = {'keypair': {'name': u'\u2028'}}
        response = self.post(KEYPAIRS_PATH, self.user1,
                             json.dumps(keypair_wo_content))
        self.assertBadRequest(response)

    def test_create_key_with_unicode_chars_name(self):
        """Test keypair creation with non-ASCII name"""
        keypair_unicode = {'keypair': {'name': u' το κλειδί μου '}}
        response = self.post(KEYPAIRS_PATH, self.user1,
                             json.dumps(keypair_unicode))
        self.assertSuccess201(response)
        self.assertEqual(json.loads(response.content)['keypair']['name'],
                         keypair_unicode['keypair']['name'])

    def test_generate_new_keypair(self):
        """Test keypair generation"""
        keypair_wo_content = {'keypair': {'name': 'foo'}}
        response = self.post(KEYPAIRS_PATH, self.user1,
                             json.dumps(keypair_wo_content))
        self.assertSuccess201(response)
        new_keypair = json.loads(response.content)['keypair']
        priv_key = new_keypair.get('private_key')
        self.assertIsNotNone(priv_key)
        self.assertEqual(new_keypair['name'], 'foo')

    def test_create_new_keypair(self):
        """Test keypair creation with user provided key"""
        keypair_with_content = {
            'keypair': {'name': 'bar', 'public_key': self.keypair.content}}
        response = self.post(KEYPAIRS_PATH, self.user1,
                             json.dumps(keypair_with_content))
        self.assertSuccess201(response)
        new_keypair = json.loads(response.content)['keypair']
        priv_key = new_keypair.get('private_key')
        self.assertIsNone(priv_key)
        self.assertEqual(new_keypair['name'], 'bar')
        self.assertEqual(new_keypair['fingerprint'], self.keypair.fingerprint)

    def test_conflicting_keypair(self):
        """Test keypair creating with conflicting names"""
        conflicting_keypair = {'keypair':
                {'name': self.u1_key_name, 'public_key': self.keypair.content}}
        response = self.post(KEYPAIRS_PATH, self.user1,
                             json.dumps(conflicting_keypair))
        self.assertConflict(response)

    def test_delete_keypair(self):
        """Test keypair deletion"""
        keypair = mfactory.PublicKeyPairFactory(user=self.user1,
                                                name='to-delete')
        response = self.delete(join_urls(KEYPAIRS_PATH, keypair.name),
                               self.user1)
        self.assertSuccess204(response)

    def test_delete_invalid_keypair(self):
        """Test keypair with invalid name deletion"""
        response = self.delete(join_urls(KEYPAIRS_PATH, 'invalid-name'),
                               self.user1)
        self.assertItemNotFound(response)

    def test_delete_keypair_unicode_name(self):
        """Test keypair deletion for keypair with non-ASCII name"""
        keypair = mfactory.PublicKeyPairFactory(user=self.user1,
                                                name=u'για σβήσιμο!!!')
        response = self.delete(
            join_urls(KEYPAIRS_PATH,
                      urllib.quote(keypair.name.encode('utf-8'))),
                      self.user1)
        self.assertSuccess204(response)
