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

from mock import MagicMock

from pithos.backends.test.util import get_random_data

from pithos.backends.exceptions import ItemNotExists
from pithos.backends.util import connect_backend

import random
import unittest


class CommonMixin(unittest.TestCase):
    block_size = 1024
    hash_algorithm = 'sha256'
    account = 'user'
    free_versioning = True

    @classmethod
    def setUpClass(cls):
        cls.create_db()

    @classmethod
    def tearDownClass(cls):
        cls.destroy_db()

    def setUp(self):
        self.b = connect_backend(db_connection=self.db_connection,
                                 db_module=self.db_module,
                                 block_size=self.block_size,
                                 hash_algorithm=self.hash_algorithm,
                                 free_versioning=self.free_versioning,
                                 mapfile_prefix=self.mapfile_prefix)
        self.b.astakosclient = MagicMock()
        self.b.astakosclient.issue_one_commission.return_value = 42
        self.b.commission_serials = MagicMock()

    def tearDown(self):
        account = self.account
        for c in self.b.list_containers(account, account):
            self.b.delete_container(account, account, c, delimiter='/')
            self.b.delete_container(account, account, c)
        self.b.close()

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

    def create_folder(self, user, account, container, folder,
                      permissions=None):
        return self._upload_object(user, account, container, folder,
                                   data='', length=0,
                                   type_='application/directory',
                                   permissions=permissions)

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
