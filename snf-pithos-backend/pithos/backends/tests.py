# Copyright (C) 2014 GRNET S.A.
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

from functools import partial

from pithos.backends.base import ItemNotExists, NotAllowedError
from pithos.backends.random_word import get_random_word
from pithos.backends.util import connect_backend

import os
import random
import unittest
import uuid as uuidlib


serial = 0

get_random_data = lambda length: get_random_word(length)[:length]
get_random_name = partial(get_random_word, length=8)


class TestBackend(unittest.TestCase):
    block_size = 1024
    hash_algorithm = 'sha256'
    block_path = '/tmp/data'
    account = 'user'
    free_versioning = True

    def setUp(self):
        self.b = connect_backend(db_connection=self.db_connection,
                                 db_module=self.db_module,
                                 block_path=self.block_path,
                                 block_size=self.block_size,
                                 hash_algorithm=self.hash_algorithm,
                                 free_versioning=self.free_versioning)

    def tearDown(self):
        self.b.close()
        self.destroy_db()

    def upload_object(self, user, account, container, obj, data=None,
                      length=None, type_='application/octet-stream',
                      permissions=None):
        if data is None:
            if length is None:
                length = length or random.randint(1, self.block_size)
            data = get_random_data(length)
        assert len(data) == length
        hashmap = [self.b.put_block(data)]
        self.b.update_object_hashmap(user, account, container, obj,
                                     length, type_, hashmap, checksum='',
                                     domain='pithos',
                                     permissions=permissions)
        return data

    def assertObjectNotExist(self, account, container, obj):
        t = account, account, container, obj
        self.assertRaises(ItemNotExists, self.b.get_object_meta, *t,
                          include_user_defined=False)
        self.assertRaises(ItemNotExists, self.b.get_object_hashmap, *t)
        objects = [o[0] for o in self.b.list_objects(*t[:-1])]
        self.assertTrue(obj not in objects)

    def assertObjectExists(self, account, container, obj):
        t = account, account, container, obj
        try:
            self.b.get_object_meta(*t, include_user_defined=False)
            self.b.get_object_hashmap(*t)
        except ItemNotExists:
            self.fail('The object does not exist!')
        objects = self.b.list_objects(*t[:-1])
        objects = [o[0] for o in self.b.list_objects(*t[:-1])]
        self.assertTrue(obj in objects)

    def test_delete_by_uuid(self):
        self.assertRaises(ValueError, self.b.delete_by_uuid, self.account,
                          uuid=None)
        self.assertRaises(ValueError, self.b.delete_by_uuid, self.account,
                          uuid='None')
        random_UUID = uuidlib.uuid4()
        self.assertRaises(NameError, self.b.delete_by_uuid, self.account,
                          uuid=str(random_UUID))
        self.assertRaises(NameError, self.b.delete_by_uuid, self.account,
                          uuid='{%s}' % random_UUID)
        self.assertRaises(NameError, self.b.delete_by_uuid, self.account,
                          uuid='urn:uuid:%s' % random_UUID)

        container = get_random_name()
        obj = get_random_name()
        t = self.account, self.account, container, obj
        self.b.put_container(*t[:-1])

        self.upload_object(*t)
        meta = self.b.get_object_meta(*t, include_user_defined=False)
        uuid = meta['uuid']
        self.b.delete_by_uuid(self.account, unicode(uuid))
        self.assertObjectNotExist(*t[1:])

        self.upload_object(*t)
        meta = self.b.get_object_meta(*t, include_user_defined=False)
        self.assertTrue(meta['uuid'] != uuid)  # same path, new uuid
        uuid = meta['uuid']
        self.b.delete_by_uuid(self.account, str(uuid))
        self.assertObjectNotExist(*t[1:])

        self.upload_object(*t)
        meta = self.b.get_object_meta(*t, include_user_defined=False)
        self.assertTrue(meta['uuid'] != uuid)  # same path, new uuid
        uuid = meta['uuid']
        self.b.delete_by_uuid(self.account, uuid='{%s}' % uuid)
        self.assertObjectNotExist(*t[1:])

        self.upload_object(*t)
        meta = self.b.get_object_meta(*t, include_user_defined=False)
        self.assertTrue(meta['uuid'] != uuid)  # same path, new uuid
        uuid = meta['uuid']
        self.b.delete_by_uuid(self.account, uuid='urn:uuid:%s' % uuid)
        self.assertObjectNotExist(*t[1:])

        # check permissions
        self.upload_object(*t)
        meta = self.b.get_object_meta(*t, include_user_defined=False)
        uuid = meta['uuid']
        self.assertRaises(NotAllowedError, self.b.delete_by_uuid,
                          user='inexistent_account', uuid=uuid)
        self.assertObjectExists(*t[1:])

        other_account = get_random_name()
        self.b.put_account(other_account, other_account)
        # user has no access at all to the object
        self.assertRaises(NotAllowedError, self.b.delete_by_uuid,
                          user=other_account, uuid=uuid)
        self.assertObjectExists(*t[1:])

        # user has read access to the object
        self.b.update_object_permissions(*t,
                                         permissions={'read': [other_account]})
        try:
            self.b.get_object_meta(other_account, *t[1:],
                                   include_user_defined=False)
        except NotAllowedError:
            self.fail('User has read access to the object!')
        self.assertRaises(NotAllowedError, self.b.delete_by_uuid,
                          user=other_account, uuid=uuid)
        self.assertObjectExists(*t[1:])

        # user has write access to the object
        self.b.update_object_permissions(*t,
                                         permissions={'write':
                                                      [other_account]})
        try:
            self.b.update_object_meta(other_account, *t[1:],
                                      domain='test',
                                      meta={'foo': 'bar'})
        except NotAllowedError:
            self.fail('User has write access to the object!')
        self.assertRaises(NotAllowedError, self.b.delete_by_uuid,
                          user=other_account, uuid=uuid)
        self.assertObjectExists(*t[1:])


class TestSQLAlchemyBackend(TestBackend):
    db_file = '/tmp/test_pithos_backend.db'
    db_module = 'pithos.backends.lib.sqlalchemy'
    db_connection = 'sqlite:///%s' % db_file

    def destroy_db(self):
        os.remove(self.db_file)
