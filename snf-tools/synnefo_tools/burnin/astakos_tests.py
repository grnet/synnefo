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

"""
This is the burnin class that tests the Astakos functionality

"""

from kamaki.clients.compute import ComputeClient
from kamaki.clients import ClientError

from synnefo_tools.burnin.common import BurninTests, Proper


# pylint: disable=too-many-public-methods
class AstakosTestSuite(BurninTests):
    """Test Astakos functionality"""
    details = Proper(value=None)

    def test_001_unauthorized_access(self):
        """Test that access without a valid token fails"""
        false_token = "12345"
        self.info("Will use token %s", false_token)
        client = ComputeClient(self.clients.compute_url, false_token)
        client.CONNECTION_RETRY_LIMIT = self.clients.retry

        with self.assertRaises(ClientError) as cl_error:
            client.list_servers()
            self.assertEqual(cl_error.exception.status, 401)

    def test_002_name2uuid(self):
        """Test that usernames2uuids and uuids2usernames are complementary"""
        our_uuid = self._get_uuid()

        given_name = self.clients.astakos.get_usernames([our_uuid])
        self.info("uuids2usernames returned %s", given_name)
        self.assertIn(our_uuid, given_name)

        given_uuid = self.clients.astakos.get_uuids([given_name[our_uuid]])
        self.info("usernames2uuids returned %s", given_uuid)
        self.assertIn(given_name[our_uuid], given_uuid)

        self.assertEqual(given_uuid[given_name[our_uuid]], our_uuid)

    def test_005_authenticate(self):
        """Test astakos.authenticate"""
        astakos = self.clients.astakos
        self.details = astakos.authenticate()
        self.info('Check result integrity')
        self.assertIn('access', self.details)
        access = self.details['access']
        self.assertEqual(set(('user', 'token', 'serviceCatalog')), set(access))
        self.info('Top-level keys are correct')
        self.assertEqual(self.clients.token, access['token']['id'])
        self.info('Token is correct')
        self.assertEqual(
            set(['roles', 'name', 'id', 'roles_links', 'projects']),
            set(astakos.user_info))
        self.info('User section is correct')

    def test_010_get_service_endpoints(self):
        """Test endpoints integrity"""
        scat = self.details['access']['serviceCatalog']
        types = (
            'compute', 'object-store', 'identity', 'account',
            'image', 'volume', 'network', 'astakos_weblogin',
            'admin', 'vmapi', 'astakos_auth')
        self.assertEqual(set(types), set([s['type'] for s in scat]))
        self.info('All expected endpoint types (and only them) found')

        astakos = self.clients.astakos
        for etype in types:
            endpoint = [s for s in scat
                        if s['type'] == etype][0]['endpoints'][0]
            self.assertEqual(endpoint, astakos.get_service_endpoints(etype))
        self.info('Endpoint call results match original results')
