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
import uuid
import random
import string
import os

from collections import defaultdict

from pithos.api.manage_accounts import ManageAccounts


def get_random_data(length=500):
    char_set = string.ascii_uppercase + string.digits
    return ''.join(random.choice(char_set) for x in xrange(length))


class ManageAccountsTests(unittest.TestCase):
    def setUp(self):
        self.utils = ManageAccounts()
        self.accounts = ('account1', 'Account1', 'account2', 'account3')
        for i in self.accounts:
            self.utils.create_account(i)

    def tearDown(self):
        for i in self.accounts:
            self.utils._delete_account(i)
        self.utils.cleanup()

    def _verify_object(self, account, container, object, expected=None,
                       strict=True):
        expected = expected or {}
        self._verify_object_metadata(account, container, object,
                                     expected.get('meta'))
        self._verify_object_history(account, container, object,
                                    expected.get('versions'),
                                    strict=strict)
        self._verify_object_permissions(account, container, object,
                                        expected.get('permissions'))

    def _verify_object_metadata(self, account, container, object, expected):
        object_meta = self.utils.backend.get_object_meta(
            account, account, container, object, 'pithos')
        for k in expected:
            self.assertTrue(k in object_meta)
            self.assertEquals(object_meta[k], expected[k])

    def _verify_object_history(self, account, container, object, expected,
                               strict=True):
        history = self.utils.list_past_versions(account, container, object)
        if strict:
            self.assertEquals(sorted(expected), history)
        else:
            self.assertTrue(set(expected) <= set(history))

    def _verify_object_permissions(self, account, container, object, expected):
        expected = expected or {}
        perms_tuple = self.utils.backend.get_object_permissions(
            account, account, container, object)

        self.assertEqual(len(perms_tuple), 3)

        object_perms = perms_tuple[2]

        for k in expected:
            self.assertTrue(set(expected.get(k)) <= set(object_perms.get(k)))

        for holder in expected.get('read', []):
            if holder == '*':
                continue
            try:
                # check first for a group permission
                owner, group = holder.split(':', 1)
            except ValueError:
                holders = [holder]
            else:
                holders = self.utils.backend.permissions.group_members(owner,
                                                                       group)

            for h in holders:
                try:
                    self.utils.backend.get_object_meta(
                        holder, account, container, object, 'pithos')
                except Exception, e:
                    self.fail(e)

    def test_existing_accounts(self):
        accounts = self.utils.existing_accounts()
        self.assertEquals(sorted(accounts), accounts)
        self.assertTrue(set(['account1', 'account2']) <= set(accounts))

    def test_duplicate_accounts(self):
        duplicates = self.utils.duplicate_accounts()
        self.assertTrue(['Account1', 'account1'] in duplicates)

    def test_list_all_containers(self):
        step = 10
        containers = []
        append = containers.append
        for i in range(3 * step + 1):
            while 1:
                cname = unicode(uuid.uuid4())
                if cname not in containers:
                    append(cname)
                    break
            self.utils.backend.put_container('account1', 'account1', cname)
        self.assertEquals(sorted(containers),
                          self.utils.list_all_containers('account1',
                                                         step=step))

    def test_list_all_container_objects(self):
        containers = ('container1', 'container2')
        objects = defaultdict(list)
        for c in containers:
            self.utils.backend.put_container('account1', 'account1', c)
            step = 10
            append = objects[c].append
            content_type = 'application/octet-stream'
            for i in range(3 * step + 1):
                while 1:
                    oname = unicode(uuid.uuid4())
                    if oname not in objects:
                        append(oname)
                        break
                data = get_random_data(int(random.random()))
                self.utils.create_update_object('account1', c, oname,
                                                content_type, data)

        (self.assertEquals(sorted(objects.get(c)),
                           self.utils.list_all_container_objects('account1', c)
                           ) for c in containers)

    def test_list_all_objects(self):
        containers = ('container1', 'container2')
        objects = []
        append = objects.append
        for c in containers:
            self.utils.backend.put_container('account1', 'account1', c)
            step = 10
            content_type = 'application/octet-stream'
            for i in range(3 * step + 1):
                while 1:
                    oname = unicode(uuid.uuid4())
                    if oname not in objects:
                        append(os.path.join(c, oname))
                        break
                data = get_random_data(int(random.random()))
                self.utils.create_update_object('account1', c, oname,
                                                content_type, data)

        self.assertEquals(len(objects),
                          len(self.utils.list_all_objects('account1')))
        self.assertEquals(sorted(objects),
                          self.utils.list_all_objects('account1'))

    def test_list_past_versions(self):
        self.utils.backend.put_container('account1', 'account1', 'container1')
        versions = []
        append = versions.append
        for i in range(5):
            data = get_random_data(int(random.random()))
            append(self.utils.create_update_object('account1', 'container1',
                                                   'object1',
                                                   'application/octet-stream',
                                                   data))
        self.assertEquals(sorted([i[0] for i in versions[:-1]]),
                          self.utils.list_past_versions('account1',
                                                        'container1',
                                                        'object1'))

    def test_move(self):
        # create containers
        self.utils.backend.put_container('account1', 'account1', 'container1')
        self.utils.backend.put_container('Account1', 'Account1', 'container1')

        # add group
        self.utils.backend.update_account_groups('Account1', 'Account1',
                                                 {'test': ['account3']})

        # upload object and update it several times
        versions = []
        append = versions.append
        meta = {'foo': 'bar'}
        permissions = {'read': ['account1', 'account2', 'Account1:test'],
                       'write': ['account2', 'Account1:test']}
        for i in range(5):
            data = get_random_data(int(random.random()))
            append(self.utils.create_update_object('Account1', 'container1',
                                                   'object1',
                                                   'application/octet-stream',
                                                   data, meta, permissions))

        self.utils.move_object('Account1', 'container1', 'object1', 'account1',
                               dry=False, silent=True)

        expected = {'meta': meta,
                    'versions': [i[0] for i in versions[:-1]],
                    'permissions': permissions}
        self._verify_object('account1', 'container1', 'object1', expected)

    def test_merge(self):
        # create container
        self.utils.backend.put_container('Account1', 'Account1', 'container0')
        self.utils.backend.put_container('Account1', 'Account1', 'container1')

        # add group
        self.utils.backend.update_account_groups('Account1', 'Account1',
                                                 {'test': ['account3']})

        # upload objects and update them several times
        versions = defaultdict(list)
        meta = {'foo': 'bar'}
        permissions = {'read': ['account2', 'Account1:test'],
                       'write': ['account2', 'Account1:test']}

        for i in range(2):
            container = 'container%s' % i
            versions[container] = {}
            for j in range(3):
                object = 'object%s' % j
                versions[container][object] = []
                append = versions[container][object].append
                for k in range(5):
                    data = get_random_data(int(random.random()))
                    append(self.utils.create_update_object(
                        'Account1', container, object,
                        'application/octet-stream', data, meta, permissions))

        self.utils.merge_account('Account1', 'account1', only_stats=False,
                                 dry=False, silent=True)

        self.assertTrue('Account1' in self.utils.existing_accounts())
        self.assertTrue('account1' in self.utils.existing_accounts())

        # assert container has been created
        try:
            self.utils.backend.get_container_meta('account1', 'account1',
                                                  'container1', 'pithos')
        except NameError, e:
            self.fail(e)

        expected = {'meta': meta,
                    'permissions': permissions}
        for c, o_dict in versions.iteritems():
            for o, versions in o_dict.iteritems():
                expected['versions'] = [i[0] for i in versions[:-1]]
                self._verify_object('account1', c, o, expected)

    def test_merge_existing_dest_container(self):
        # create container
        self.utils.backend.put_container('Account1', 'Account1', 'container1')
        self.utils.backend.put_container('account1', 'account1', 'container1')

        # add group
        self.utils.backend.update_account_groups('Account1', 'Account1',
                                                 {'test': ['account3']})

        # upload objects and update them several times
        versions = defaultdict(list)
        meta = {'foo': 'bar'}
        permissions = {'read': ['account2', 'Account1:test'],
                       'write': ['account2', 'Account1:test']}

        versions = []
        append = versions.append
        for k in range(5):
            data = get_random_data(int(random.random()))
            append(self.utils.create_update_object(
                'Account1', 'container1', 'object1',
                'application/octet-stream', data, meta, permissions))

        self.utils.merge_account('Account1', 'account1', only_stats=False,
                                 dry=False, silent=True)

        self.assertTrue('Account1' in self.utils.existing_accounts())
        self.assertTrue('account1' in self.utils.existing_accounts())

        try:
            self.utils.backend.get_container_meta('account1', 'account1',
                                                  'container1', 'pithos')
        except NameError, e:
            self.fail(e)

        expected = {'meta': meta,
                    'versions': [i[0] for i in versions[:-1]],
                    'permissions': permissions}
        self._verify_object('account1', 'container1', 'object1', expected)

    def test_merge_existing_dest_object(self):
        # create container
        self.utils.backend.put_container('Account1', 'Account1', 'container1')
        self.utils.backend.put_container('account1', 'account1', 'container1')

        # add group
        self.utils.backend.update_account_groups('Account1', 'Account1',
                                                 {'test': ['account3']})

        # upload objects and update them several times
        versions = defaultdict(list)
        meta = {'foo': 'bar'}
        permissions = {'read': ['account2', 'Account1:test'],
                       'write': ['account2', 'Account1:test']}

        container = 'container1'
        object = 'object1'
        versions = []
        append = versions.append
        for k in range(5):
            data = get_random_data(int(random.random()))
            append(self.utils.create_update_object(
                   'Account1', container, object,
                   'application/octet-stream', data, meta, permissions))
            data = get_random_data(int(random.random()))
            self.utils.create_update_object(
                   'account1', container, object,
                   'application/octet-stream', data, meta, permissions)

        self.utils.merge_account('Account1', 'account1', only_stats=False,
                                 dry=False, silent=True)

        self.assertTrue('Account1' in self.utils.existing_accounts())
        self.assertTrue('account1' in self.utils.existing_accounts())

        try:
            self.utils.backend.get_container_meta('account1', 'account1',
                                                  'container1', 'pithos')
        except NameError, e:
            self.fail(e)

        expected = {'meta': meta,
                    'permissions': permissions,
                    'versions': [i[0] for i in versions[:-1]]}
        self._verify_object('account1', container, object, expected,
                            strict=False)


if __name__ == '__main__':
    unittest.main()
