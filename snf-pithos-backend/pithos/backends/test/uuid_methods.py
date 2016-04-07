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

from pithos.backends.test.util import get_random_name

from pithos.backends.exceptions import NotAllowedError

import uuid as uuidlib


serial = 0


class TestUUIDMixin(object):
    def test_get_object_by_uuid(self):
        container = get_random_name()
        obj = get_random_name()
        t = self.account, self.account, container, obj
        self.b.put_container(*t[:-1])

        permissions = {'read': ['somebody']}
        self.upload_object(*t, permissions=permissions)
        self.b.update_object_meta(*t, domain='test1', meta={'domain': 'test1'})
        meta = self.b.get_object_meta(*t, include_user_defined=False)
        v1 = meta['version']

        self.b.update_object_meta(*t, domain='test2', meta={'domain': 'test2'})
        meta = self.b.get_object_meta(*t, include_user_defined=False)
        uuid = meta['uuid']
        v2 = meta['version']

        meta, permissions_, path = self.b.get_object_by_uuid(
            uuid, domain='test1', check_permissions=False)
        self.assertTrue('domain' in meta)
        self.assertEqual(meta['domain'], 'test1')
        self.assertEqual(permissions_, permissions)
        self.assertEqual(path, '/'.join(t[1:]))

        meta, permissions_, path = self.b.get_object_by_uuid(
            uuid, domain='test1', version=v2, check_permissions=False)
        self.assertTrue('domain' in meta)
        self.assertEqual(meta['domain'], 'test1')
        self.assertEqual(permissions_, permissions)
        self.assertEqual(path, '/'.join(t[1:]))

        meta, permissions_, path = self.b.get_object_by_uuid(
            uuid, domain='test2', version=v2, check_permissions=False)
        self.assertTrue('domain' in meta)
        self.assertEqual(meta['domain'], 'test2')
        self.assertEqual(permissions_, permissions)
        self.assertEqual(path, '/'.join(t[1:]))

        meta, permissions_, path = self.b.get_object_by_uuid(
            uuid, domain='test2', version=v1, check_permissions=False)
        self.assertTrue('domain' not in meta)
        self.assertEqual(permissions_, permissions)
        self.assertEqual(path, '/'.join(t[1:]))

        meta, permissions_, path = self.b.get_object_by_uuid(
            uuid, domain='test1', user='somebody', check_permissions=True)
        self.assertTrue('domain' in meta)
        self.assertEqual(meta['domain'], 'test1')
        self.assertEqual(permissions_, permissions)
        self.assertEqual(path, '/'.join(t[1:]))

        self.assertRaises(NotAllowedError,
                          self.b.get_object_by_uuid, uuid, user='not_allowed',
                          check_permissions=True)

        self.assertRaises(AssertionError, self.b.get_object_by_uuid, uuid,
                          domain='test1', user='somebody',
                          check_permissions=False)

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
