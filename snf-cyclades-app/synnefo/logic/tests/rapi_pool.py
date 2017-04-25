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

from django.test import TestCase

from synnefo.logic import rapi_pool

from mock import patch


@patch('synnefo.logic.rapi_pool.GanetiRapiClient', spec=True)
class GanetiRapiPoolTest(TestCase):
    def test_new_client(self, rclient):
        cl = rapi_pool.get_rapi_client(1, 'amxixa', 'cluster0', '5080', 'user',
                                       'pass')
        rclient.assert_called_once_with("cluster0", "5080", "user", "pass")
        self.assertTrue('amxixa' in rapi_pool._pools)
        self.assertTrue(cl._pool is rapi_pool._pools[rapi_pool._hashes[1]])

    def test_invalid_get(self, rclient):
        self.assertRaises(ValueError, rapi_pool.get_rapi_client, 1, 'amxixa',
                          None, '5080', 'user', 'pass')
        self.assertRaises(ValueError, rapi_pool.get_rapi_client, 1, 'amxixa',
                          'Foo', None, 'user', 'pass')

    def test_get_from_pool(self, rclient):
        cl = rapi_pool.get_rapi_client(1, 'dummyhash', 'cluster1', '5080',
                                       'user', 'pass')
        rclient.assert_called_once_with("cluster1", "5080", "user", "pass")
        rapi_pool.put_rapi_client(cl)
        rclient.reset_mock()
        cl2 = rapi_pool.get_rapi_client(1, 'dummyhash', 'cluster1', '5080',
                                        'user', 'pass')
        self.assertTrue(cl is cl2)
        self.assertFalse(rclient.mock_calls)

    def test_changed_credentials(self, rclient):
        cl = rapi_pool.get_rapi_client(1, 'dummyhash2', 'cluster2', '5080',
                                       'user', 'pass')
        rclient.assert_called_once_with("cluster2", "5080", "user", "pass")
        rapi_pool.put_rapi_client(cl)
        rclient.reset_mock()
        rapi_pool.get_rapi_client(1, 'dummyhash3', 'cluster2', '5080',
                                  'user', 'new_pass')
        rclient.assert_called_once_with("cluster2", "5080", "user", "new_pass")
        self.assertFalse('dummyhash2' in rapi_pool._pools)

    def test_no_pool(self, rclient):
        cl = rapi_pool.get_rapi_client(1, 'dummyhash2', 'cluster2', '5080',
                                       'user', 'pass')
        cl._pool = None
        rapi_pool.put_rapi_client(cl)
        self.assertTrue(cl not in rapi_pool._pools.values())
