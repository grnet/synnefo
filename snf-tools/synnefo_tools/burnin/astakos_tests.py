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

from synnefo_tools.burnin import common


# pylint: disable=too-many-public-methods
class AstakosTestSuite(common.BurninTests):
    """Test Astakos functionality"""
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
