# Copyright 2011 GRNET S.A. All rights reserved.
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

import unittest
import random
import string
import datetime
import time as _time

import pithos.api.settings as settings

from pithos.api.swiss_army import SwissArmy

def get_random_data(length=500):
    char_set = string.ascii_uppercase + string.digits
    return ''.join(random.choice(char_set) for x in xrange(length))

class TestPublic(unittest.TestCase):
    def setUp(self):
        self.utils = SwissArmy()
        self.backend = self.utils.backend
        self.utils.create_account('account')

    def tearDown(self):
        self.utils._delete_account('account')
        self.utils.cleanup()

    def assert_not_public_object(self, account, container, object):
        public = self.backend.get_object_public(
            account, account, container, object
        )
        self.assertTrue(public == None)
        self.assertRaises(
            NameError,
            self.backend.get_public,
            '$$account$$',
            public
        )
        self.assertRaises(
            Exception, self.backend._can_read,
            '$$account$$', account, container, object
        )
        return public

    def assert_public_object(self, account, container, object):
        public = self.backend.get_object_public(
            account, account, container, object
        )
        self.assertTrue(public != None)
        self.assertTrue(len(public) >= settings.PUBLIC_URL_MIN_LENGTH)
        self.assertTrue(set(public) <= set(settings.PUBLIC_URL_ALPHABET))
        self.assertEqual(
            self.backend.get_public('$$account$$', public),
            (account, container, object)
        )
        try:
            self.backend._can_read('$$account$$', account, container, object)
        except Exception:
            self.fail('Public object should be readable.')
        return public

    def test_set_object_public(self):
        self.utils.backend.put_container('account', 'account', 'container')
        data = get_random_data(int(random.random()))
        self.utils.create_update_object(
            'account',
            'container',
            'object',
            'application/octet-stream',
            data
        )
        self.assert_not_public_object('account', 'container', 'object')

        self.backend.permissions.public_set(
            'account/container/object',
            self.backend.public_url_min_length,
            self.backend.public_url_alphabet
        )
        self.assert_public_object('account', 'container', 'object')

    def test_set_twice(self):
        self.utils.backend.put_container('account', 'account', 'container')
        data = get_random_data(int(random.random()))
        self.utils.create_update_object(
            'account',
            'container',
            'object',
            'application/octet-stream',
            data
        )
        self.backend.permissions.public_set(
            'account/container/object',
            self.backend.public_url_min_length,
            self.backend.public_url_alphabet
        )
        public = self.assert_public_object('account', 'container', 'object')

        self.backend.permissions.public_set(
            'account/container/object',
            self.backend.public_url_min_length,
            self.backend.public_url_alphabet
        )
        public2 = self.assert_public_object('account', 'container', 'object')

        self.assertEqual(public, public2)

    def test_set_unset_set(self):
        self.utils.backend.put_container('account', 'account', 'container')
        data = get_random_data(int(random.random()))
        self.utils.create_update_object(
            'account',
            'container',
            'object',
            'application/octet-stream',
            data
        )
        self.backend.permissions.public_set(
            'account/container/object',
            self.backend.public_url_min_length,
            self.backend.public_url_alphabet
        )
        public = self.assert_public_object('account', 'container', 'object')

        self.backend.permissions.public_unset('account/container/object')
        self.assert_not_public_object('account', 'container', 'object')

        self.backend.permissions.public_set(
            'account/container/object',
            self.backend.public_url_min_length,
            self.backend.public_url_alphabet
        )
        public3 = self.assert_public_object('account', 'container', 'object')

        self.assertTrue(public != public3)

    def test_update_object_public(self):
        self.utils.backend.put_container('account', 'account', 'container')
        data = get_random_data(int(random.random()))
        self.utils.create_update_object(
            'account',
            'container',
            'object',
            'application/octet-stream',
            data
        )

        self.backend.update_object_public(
            'account', 'account', 'container', 'object', public=False
        )
        self.assert_not_public_object('account', 'container', 'object')

        self.backend.update_object_public(
            'account', 'account', 'container', 'object', public=True
        )
        public = self.assert_public_object('account', 'container', 'object')

        self.backend.update_object_public(
            'account', 'account', 'container', 'object', public=False
        )
        self.assert_not_public_object('account', 'container', 'object')

        self.backend.update_object_public(
            'account', 'account', 'container', 'object', public=True
        )
        new_public = self.assert_public_object('account', 'container', 'object')
        self.assertTrue(public != new_public)

    def test_delete_not_public_object(self):
        self.utils.backend.put_container('account', 'account', 'container')
        data = get_random_data(int(random.random()))
        self.utils.create_update_object(
            'account',
            'container',
            'object',
            'application/octet-stream',
            data
        )
        self.assert_not_public_object('account', 'container', 'object')

        self.backend.delete_object('account', 'account', 'container', 'object')

        self.assert_not_public_object('account', 'container', 'object')

    def test_delete_public_object(self):
        self.utils.backend.put_container('account', 'account', 'container')
        data = get_random_data(int(random.random()))
        self.utils.create_update_object(
            'account',
            'container',
            'object',
            'application/octet-stream',
            data
        )
        self.assert_not_public_object('account', 'container', 'object')

        self.backend.permissions.public_set(
            'account/container/object',
            self.backend.public_url_min_length,
            self.backend.public_url_alphabet
        )
        self.assert_public_object('account', 'container', 'object')

        self.backend.delete_object('account', 'account', 'container', 'object')
        self.assert_not_public_object('account', 'container', 'object')

    def test_delete_public_object_history(self):
        self.utils.backend.put_container('account', 'account', 'container')
        for i in range(random.randint(1, 10)):
            data = get_random_data(int(random.random()))
            self.utils.create_update_object(
                'account',
                'container',
                'object',
                'application/octet-stream',
                data
            )
            _time.sleep(1)
        versions = self.backend.list_versions(
            'account', 'account', 'container', 'object'
        )
        mtime = [int(i[1]) for i in versions]
        self.assert_not_public_object('account', 'container', 'object')

        self.backend.permissions.public_set(
            'account/container/object',
            self.backend.public_url_min_length,
            self.backend.public_url_alphabet
        )
        public = self.assert_public_object('account', 'container', 'object')

        i = random.randrange(len(mtime))
        self.backend.delete_object(
            'account', 'account', 'container', 'object', until=mtime[i]
        )
        self.assert_public_object('account', 'container', 'object')
        public = self.assert_public_object('account', 'container', 'object')

        _time.sleep(1)
        t = datetime.datetime.utcnow()
        now = int(_time.mktime(t.timetuple()))
        self.backend.delete_object(
            'account', 'account', 'container', 'object', until=now
        )
        self.assertRaises(
            NameError,
            self.backend.get_public,
            '$$account$$',
            public
        )

if __name__ == '__main__':
    unittest.main()
