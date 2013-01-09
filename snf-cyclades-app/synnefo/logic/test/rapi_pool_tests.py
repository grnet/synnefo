# Copyright 2011-2012 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

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
