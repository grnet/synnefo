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

from mock import call
from functools import wraps, partial

import uuid as uuidlib

from pithos.backends.random_word import get_random_word


serial = 0

get_random_data = lambda length: get_random_word(length)[:length]
get_random_name = partial(get_random_word, length=8)


def assert_issue_commission_calls(func):
    @wraps(func)
    def wrapper(tc):
        assert isinstance(tc, TestQuotaMixin)
        tc.expected_issue_commission_calls = []
        func(tc)
        tc.assertEqual(tc.b.astakosclient.issue_one_commission.mock_calls,
                       tc.expected_issue_commission_calls)
    return wrapper


class TestQuotaMixin(object):
    """Challenge quota accounting.

    Each test case records the expected quota commission calls resulting from
    the execution of the respective backend methods.

    Finally, it asserts that these calls have been actually made.
    """
    def _upload_object(self, user, account, container, obj, data=None,
                       length=None, type_='application/octet-stream',
                       permissions=None):
        data = self.upload_object(user, account, container, obj, data, length,
                                  type_, permissions)
        _, container_node = self.b._lookup_container(account, container)
        project = self.b._get_project(container_node)
        if len(data) != 0:
            self.expected_issue_commission_calls += [
                call.issue_one_commission(
                    holder=account,
                    provisions={(project, 'pithos.diskspace'): len(data)},
                    name='/'.join([account, container, obj]))]
        return data

    @assert_issue_commission_calls
    def test_upload_object(self):
        account = self.account
        container = get_random_name()
        obj = get_random_name()
        self.b.put_container(account, account, container)
        self._upload_object(account, account, container, obj)

    @assert_issue_commission_calls
    def test_copy_object(self):
        account = self.account
        container = get_random_name()
        obj = get_random_name()
        self.b.put_container(account, account, container)
        data = self._upload_object(account, account, container, obj)

        other_obj = get_random_name()
        self.b.copy_object(account, account, container, obj,
                           account, container, other_obj,
                           'application/octet-stream',
                           domain='pithos')
        self.expected_issue_commission_calls += [call.issue_one_commission(
            holder=account,
            provisions={(account, 'pithos.diskspace'): len(data)},
            name='/'.join([account, container, other_obj]))]

    @assert_issue_commission_calls
    def test_copy_object_to_other_container(self):
        account = self.account
        container = get_random_name()
        obj = get_random_name()
        self.b.put_container(account, account, container)
        data = self._upload_object(account, account, container, obj)

        other_container = get_random_name()
        self.b.put_container(account, account, other_container)
        other_obj = get_random_name()
        self.b.copy_object(account, account, container, obj,
                           account, other_container, other_obj,
                           'application/octet-stream',
                           domain='pithos')
        self.expected_issue_commission_calls += [
            call.issue_one_commission(
                holder=account,
                provisions={(account, 'pithos.diskspace'): len(data)},
                name='/'.join([account, other_container, other_obj]))]

    @assert_issue_commission_calls
    def test_copy_obj_to_other_project(self):
        account = self.account
        container = get_random_name()
        obj = get_random_name()
        self.b.put_container(account, account, container)
        data = self._upload_object(account, account, container, obj)

        other_container = get_random_name()
        project = unicode(uuidlib.uuid4())
        self.b.put_container(account, account, other_container,
                             policy={'project': project})
        self.b.copy_object(account, account, container, obj,
                           account, other_container, obj,
                           'application/octet-stream',
                           domain='pithos')
        self.expected_issue_commission_calls += [
            call.issue_one_commission(
                holder=account,
                provisions={(project, 'pithos.diskspace'): len(data)},
                name='/'.join([account, other_container, obj]))]

    @assert_issue_commission_calls
    def test_copy_object_to_other_account(self):
        account = self.account
        container = get_random_name()
        obj = get_random_name()
        self.b.put_container(account, account, container)

        other_account = get_random_name()
        self.b.put_container(other_account, other_account, container)

        data = self._upload_object(account, account, container, obj,
                                   permissions={'read': [other_account]})

        self.b.copy_object(other_account,
                           account, container, obj,
                           other_account, container, obj,
                           'application/octet-stream',
                           domain='pithos')

        self.expected_issue_commission_calls += [call.issue_one_commission(
            holder=other_account,
            provisions={(other_account, 'pithos.diskspace'): len(data)},
            name='/'.join([other_account, container, obj]))]

    @assert_issue_commission_calls
    def test_copy_to_existing_path(self):
        account = self.account
        container = get_random_name()
        obj = get_random_name()
        self.b.put_container(account, account, container)
        data = self._upload_object(account, account, container, obj)

        other = get_random_name()
        self._upload_object(account, account, container, other,
                            length=len(data) + 1)  # upload more data

        self.b.copy_object(account, account, container, obj,
                           account, container, other,
                           'application/octet-stream',
                           domain='pithos')

        self.expected_issue_commission_calls += [call.issue_one_commissions(
            holder=account,
            provisions={(account, 'pithos.diskspace'): -1},
            name='/'.join([account, container, other]))]

        other = get_random_name()
        self._upload_object(account, account, container, other,
                            length=len(data) - 1)  # upload less data

        self.b.copy_object(account, account, container, obj,
                           account, container, other,
                           'application/octet-stream',
                           domain='pithos')
        self.expected_issue_commission_calls += [call.issue_one_commissions(
            holder=account,
            provisions={(account, 'pithos.diskspace'): 1},
            name='/'.join([account, container, other]))]

    @assert_issue_commission_calls
    def test_copy_to_same_path(self):
        account = self.account
        container = get_random_name()
        obj = get_random_name()
        self.b.put_container(account, account, container)
        self._upload_object(account, account, container, obj)

        self.b.copy_object(account, account, container, obj,
                           account, container, obj,
                           'application/octet-stream',
                           domain='pithos')
        # No issued commissions

    @assert_issue_commission_calls
    def test_copy_dir(self):
        account = self.account
        container = get_random_name()
        self.b.put_container(account, account, container)

        folder = get_random_name()
        self.create_folder(account, account, container, folder)

        obj1 = '/'.join([folder, get_random_name()])
        data1 = self._upload_object(account, account, container, obj1)

        obj2 = '/'.join([folder, get_random_name()])
        data2 = self._upload_object(account, account, container, obj2)

        other_folder = get_random_name()
        self.b.copy_object(account, account, container, folder,
                           account, container, other_folder,
                           'application/directory',
                           domain='pithos',
                           delimiter='/')

        self.expected_issue_commission_calls += [
            call.issue_one_commissions(
                holder=account,
                provisions={(account, 'pithos.diskspace'): len(data1)},
                name='/'.join([account, container,
                               obj1.replace(folder, other_folder, 1)])),
            call.issue_one_commissions(
                holder=account,
                provisions={(account, 'pithos.diskspace'): len(data2)},
                name='/'.join([account, container,
                               obj2.replace(folder, other_folder, 1)]))]

    @assert_issue_commission_calls
    def test_copy_dir_to_other_container(self):
        account = self.account
        container = get_random_name()
        self.b.put_container(account, account, container)

        folder = get_random_name()
        self.create_folder(account, account, container, folder)

        container2 = get_random_name()
        self.b.put_container(account, account, container2)

        obj1 = '/'.join([folder, get_random_name()])
        data1 = self._upload_object(account, account, container, obj1)

        obj2 = '/'.join([folder, get_random_name()])
        data2 = self._upload_object(account, account, container, obj2)

        self.b.copy_object(account, account, container, folder,
                           account, container2, folder,
                           'application/directory',
                           domain='pithos',
                           delimiter='/')

        self.expected_issue_commission_calls += [
            call.issue_one_commissions(
                holder=account,
                provisions={(account, 'pithos.diskspace'): len(data1)},
                name='/'.join([account, container2, obj1])),
            call.issue_one_commissions(
                holder=account,
                provisions={(account, 'pithos.diskspace'): len(data2)},
                name='/'.join([account, container2, obj2]))]

    @assert_issue_commission_calls
    def test_copy_dir_to_other_account(self):
        account = self.account
        container = get_random_name()
        self.b.put_container(account, account, container)

        other_account = get_random_name()
        self.b.put_container(other_account, other_account, container)

        folder = get_random_name()
        self.create_folder(account, account, container, folder,
                           permissions={'read': [other_account]})

        obj1 = '/'.join([folder, get_random_name()])
        data1 = self._upload_object(account, account, container, obj1)

        obj2 = '/'.join([folder, get_random_name()])
        data2 = self._upload_object(account, account, container, obj2)

        self.b.copy_object(other_account, account, container, folder,
                           other_account, container, folder,
                           'application/directory',
                           domain='pithos',
                           delimiter='/')

        self.expected_issue_commission_calls += [
            call.issue_one_commissions(
                holder=other_account,
                provisions={(other_account, 'pithos.diskspace'): len(data1)},
                name='/'.join([other_account, container, obj1])),
            call.issue_one_commissions(
                holder=other_account,
                provisions={(other_account, 'pithos.diskspace'): len(data2)},
                name='/'.join([other_account, container, obj2]))]

    @assert_issue_commission_calls
    def test_copy_dir_to_existing_path(self):
        account = self.account
        container = get_random_name()
        self.b.put_container(account, account, container)

        folder = get_random_name()
        self.create_folder(account, account, container, folder)

        obj1 = '/'.join([folder, get_random_name()])
        data1 = self._upload_object(account, account, container, obj1)

        obj2 = '/'.join([folder, get_random_name()])
        data2 = self._upload_object(account, account, container, obj2)

        other_folder = get_random_name()
        self.create_folder(account, account, container, other_folder)
        # create object under the new folder
        # having the same name as an object in the initial folder
        obj3 = obj1.replace(folder, other_folder, 1)
        data3 = self._upload_object(account, account, container, obj3)

        obj4 = '/'.join([other_folder, get_random_name()])
        self._upload_object(account, account, container, obj4)

        self.b.copy_object(account, account, container, folder,
                           account, container, other_folder,
                           'application/directory',
                           domain='pithos',
                           delimiter='/')

        self.expected_issue_commission_calls += [
            call.issue_one_commissions(
                holder=account,
                provisions={(account, 'pithos.diskspace'):
                            len(data1) - len(data3)},
                name='/'.join([account, container, obj3])),
            call.issue_one_commissions(
                holder=account,
                provisions={(account, 'pithos.diskspace'): len(data2)},
                name='/'.join([account, container,
                               obj2.replace(folder, other_folder, 1)]))]

    @assert_issue_commission_calls
    def test_copy_dir_to_other_project(self):
        account = self.account
        container = get_random_name()
        self.b.put_container(account, account, container)

        folder = get_random_name()
        self.create_folder(account, account, container, folder)

        obj1 = '/'.join([folder, get_random_name()])
        data1 = self._upload_object(account, account, container, obj1)

        obj2 = '/'.join([folder, get_random_name()])
        data2 = self._upload_object(account, account, container, obj2)

        other_container = get_random_name()
        project = unicode(uuidlib.uuid4())
        self.b.put_container(account, account, other_container,
                             policy={'project': project})

        other_folder = get_random_name()
        self.create_folder(account, account, other_container, other_folder)
        # create object under the new folder
        # having the same name as an object in the initial folder
        obj3 = obj1.replace(folder, other_folder, 1)
        data3 = self._upload_object(account, account, other_container, obj3)

        obj4 = '/'.join([other_folder, get_random_name()])
        self._upload_object(account, account, other_container, obj4)
        self.b.copy_object(account, account, container, folder,
                           account, other_container, other_folder,
                           'application/directory',
                           domain='pithos',
                           delimiter='/')
        self.expected_issue_commission_calls += [
            call.issue_one_commissions(
                holder=account,
                provisions={(project, 'pithos.diskspace'):
                            len(data1) - len(data3)},
                name='/'.join([account, other_container, obj3])),
            call.issue_one_commissions(
                holder=account,
                provisions={(project, 'pithos.diskspace'): len(data2)},
                name='/'.join([account, other_container,
                               obj2.replace(folder, other_folder, 1)]))]

    @assert_issue_commission_calls
    def test_move_obj(self):
        account = self.account
        container = get_random_name()
        obj = get_random_name()
        self.b.put_container(account, account, container)
        self._upload_object(account, account, container, obj)

        other_obj = get_random_name()
        self.b.move_object(account, account, container, obj,
                           account, container, other_obj,
                           'application/octet-stream',
                           domain='pithos')

    @assert_issue_commission_calls
    def test_move_obj_to_other_container(self):
        account = self.account
        container = get_random_name()
        obj = get_random_name()
        self.b.put_container(account, account, container)
        self._upload_object(account, account, container, obj)

        other_container = get_random_name()
        self.b.put_container(account, account, other_container)
        other_obj = get_random_name()
        self.b.move_object(account, account, container, obj,
                           account, other_container, other_obj,
                           'application/octet-stream',
                           domain='pithos')

    @assert_issue_commission_calls
    def test_move_obj_to_other_project(self):
        account = self.account
        container = get_random_name()
        obj = get_random_name()
        self.b.put_container(account, account, container)
        data = self._upload_object(account, account, container, obj)

        other_container = get_random_name()
        project = unicode(uuidlib.uuid4())
        self.b.put_container(account, account, other_container,
                             policy={'project': project})
        self.b.move_object(account, account, container, obj,
                           account, other_container, obj,
                           'application/octet-stream',
                           domain='pithos')
        self.expected_issue_commission_calls += [
            call.issue_one_commission(
                holder=account,
                provisions={(project, 'pithos.diskspace'): len(data)},
                name='/'.join([account, other_container, obj])),
            call.issue_one_commission(
                holder=account,
                provisions={(account, 'pithos.diskspace'): -len(data)},
                name='/'.join([account, container, obj]))]

    @assert_issue_commission_calls
    def test_move_object_to_other_account(self):
        account = self.account
        container = get_random_name()
        obj = get_random_name()
        self.b.put_container(account, account, container)

        other_account = get_random_name()
        self.b.put_container(other_account, other_account, container)

        folder = 'shared'
        self.create_folder(other_account, other_account, container, folder,
                           permissions={'write': [account]})

        data = self._upload_object(account, account, container, obj)

        other_obj = '/'.join([folder, obj])
        self.b.move_object(account,
                           account, container, obj,
                           other_account, container, other_obj,
                           'application/octet-stream',
                           domain='pithos')

        self.expected_issue_commission_calls += [
            call.issue_one_commission(
                holder=other_account,
                provisions={(other_account, 'pithos.diskspace'): len(data)},
                name='/'.join([other_account, container, other_obj])),
            call.issue_one_commission(
                holder=account,
                provisions={(account, 'pithos.diskspace'): -len(data)},
                name='/'.join([account, container, obj]))]

    @assert_issue_commission_calls
    def test_move_to_existing_path(self):
        account = self.account
        container = get_random_name()
        obj = get_random_name()
        self.b.put_container(account, account, container)
        data = self._upload_object(account, account, container, obj)

        other = get_random_name()
        self._upload_object(account, account, container, other,
                            length=len(data) + 1)  # upload more data

        self.b.move_object(account, account, container, obj,
                           account, container, other,
                           'application/octet-stream',
                           domain='pithos')

        self.expected_issue_commission_calls += [call.issue_one_commissions(
            holder=account,
            provisions={(account, 'pithos.diskspace'): -1 - len(data)},
            name='/'.join([account, container, other]))]

        data = self._upload_object(account, account, container, obj)
        other = get_random_name()
        self._upload_object(account, account, container, other,
                            length=len(data) - 1)  # upload less data

        self.b.move_object(account, account, container, obj,
                           account, container, other,
                           'application/octet-stream',
                           domain='pithos')
        self.expected_issue_commission_calls += [call.issue_one_commissions(
            holder=account,
            provisions={(account, 'pithos.diskspace'): 1 - len(data)},
            name='/'.join([account, container, other]))]

    @assert_issue_commission_calls
    def test_move_to_same_path(self):
        account = self.account
        container = get_random_name()
        obj = get_random_name()
        self.b.put_container(account, account, container)
        self._upload_object(account, account, container, obj)

        self.b.move_object(account, account, container, obj,
                           account, container, obj,
                           'application/octet-stream',
                           domain='pithos')
        self.assertObjectExists(account, container, obj)
        # No issued commissions

    @assert_issue_commission_calls
    def test_move_dir(self):
        account = self.account
        container = get_random_name()
        self.b.put_container(account, account, container)

        folder = get_random_name()
        self.create_folder(account, account, container, folder)

        obj1 = '/'.join([folder, get_random_name()])
        self._upload_object(account, account, container, obj1)

        obj2 = '/'.join([folder, get_random_name()])
        self._upload_object(account, account, container, obj2)

        other_folder = get_random_name()
        self.b.move_object(account, account, container, folder,
                           account, container, other_folder,
                           'application/directory',
                           domain='pithos',
                           delimiter='/')

    @assert_issue_commission_calls
    def test_move_dir_to_other_container(self):
        account = self.account
        container = get_random_name()
        self.b.put_container(account, account, container)

        folder = get_random_name()
        self.create_folder(account, account, container, folder)

        container2 = get_random_name()
        self.b.put_container(account, account, container2)

        obj1 = '/'.join([folder, get_random_name()])
        self._upload_object(account, account, container, obj1)

        obj2 = '/'.join([folder, get_random_name()])
        self._upload_object(account, account, container, obj2)

        self.b.move_object(account, account, container, folder,
                           account, container2, folder,
                           'application/directory',
                           domain='pithos',
                           delimiter='/')

    @assert_issue_commission_calls
    def test_move_dir_to_existing_path(self):
        account = self.account
        container = get_random_name()
        self.b.put_container(account, account, container)

        folder = get_random_name()
        self.create_folder(account, account, container, folder)

        obj1 = '/'.join([folder, get_random_name()])
        self._upload_object(account, account, container, obj1)

        obj2 = '/'.join([folder, get_random_name()])
        self._upload_object(account, account, container, obj2)

        other_folder = get_random_name()
        self.create_folder(account, account, container, other_folder)
        # create object under the new folder
        # having the same name as an object in the initial folder
        obj3 = obj1.replace(folder, other_folder, 1)
        data3 = self._upload_object(account, account, container, obj3)

        obj4 = '/'.join([other_folder, get_random_name()])
        self._upload_object(account, account, container, obj4)

        self.b.move_object(account, account, container, folder,
                           account, container, other_folder,
                           'application/directory',
                           domain='pithos',
                           delimiter='/')
        self.expected_issue_commission_calls += [
            call.issue_one_commissions(
                holder=account,
                provisions={(account, 'pithos.diskspace'): - len(data3)},
                name='/'.join([account, container, other_folder]))]

    @assert_issue_commission_calls
    def test_move_dir_to_other_project(self):
        account = self.account
        container = get_random_name()
        self.b.put_container(account, account, container)

        folder = get_random_name()
        self.create_folder(account, account, container, folder)

        obj1 = '/'.join([folder, get_random_name()])
        data1 = self._upload_object(account, account, container, obj1)

        obj2 = '/'.join([folder, get_random_name()])
        data2 = self._upload_object(account, account, container, obj2)

        other_container = get_random_name()
        project = unicode(uuidlib.uuid4())
        self.b.put_container(account, account, other_container,
                             policy={'project': project})

        other_folder = get_random_name()
        self.create_folder(account, account, other_container, other_folder)
        # create object under the new folder
        # having the same name as an object in the initial folder
        obj3 = obj1.replace(folder, other_folder, 1)
        data3 = self._upload_object(account, account, other_container, obj3)

        obj4 = '/'.join([other_folder, get_random_name()])
        self._upload_object(account, account, other_container, obj4)

        self.b.move_object(account, account, container, folder,
                           account, other_container, other_folder,
                           'application/directory',
                           domain='pithos',
                           delimiter='/')
        self.expected_issue_commission_calls += [
            call.issue_one_commissions(
                holder=account,
                provisions={(project, 'pithos.diskspace'):
                            len(data1) - len(data3)},
                name='/'.join([account, other_container, obj3])),
            call.issue_one_commissions(
                holder=account,
                provisions={(account, 'pithos.diskspace'): -len(data1)},
                name='/'.join([account, container, obj1])),
            call.issue_one_commissions(
                holder=account,
                provisions={(project, 'pithos.diskspace'): len(data2)},
                name='/'.join([account, other_container,
                               obj2.replace(folder, other_folder, 1)])),
            call.issue_one_commissions(
                holder=account,
                provisions={(account, 'pithos.diskspace'): -len(data2)},
                name='/'.join([account, container, obj2]))]

    @assert_issue_commission_calls
    def test_move_dir_to_other_account(self):
        account = self.account
        container = get_random_name()
        self.b.put_container(account, account, container)

        other_account = get_random_name()
        self.b.put_container(other_account, other_account, container)

        folder = get_random_name()
        self.create_folder(account, account, container, folder)
        self.create_folder(other_account, other_account, container, folder,
                           permissions={'write': [account]})

        obj1 = '/'.join([folder, get_random_name()])
        data1 = self._upload_object(account, account, container, obj1)

        obj2 = '/'.join([folder, get_random_name()])
        data2 = self._upload_object(account, account, container, obj2)

        self.b.move_object(account, account, container, folder,
                           other_account, container, folder,
                           'application/directory',
                           domain='pithos',
                           delimiter='/')

        self.expected_issue_commission_calls += [
            call.issue_one_commissions(
                holder=other_account,
                provisions={(other_account, 'pithos.diskspace'): len(data1)},
                name='/'.join([other_account, container, obj1])),
            call.issue_one_commissions(
                holder=account,
                provisions={(account, 'pithos.diskspace'): -len(data1)},
                name='/'.join([account, container, obj1])),
            call.issue_one_commissions(
                holder=other_account,
                provisions={(other_account, 'pithos.diskspace'): len(data2)},
                name='/'.join([other_account, container, obj2])),
            call.issue_one_commissions(
                holder=account,
                provisions={(account, 'pithos.diskspace'): -len(data2)},
                name='/'.join([account, container, obj2]))]

    @assert_issue_commission_calls
    def test_delete_container_contents(self):
        account = self.account
        container = get_random_name()
        project = unicode(uuidlib.uuid4())
        self.b.put_container(account, account, container,
                             policy={'project': project})

        folder = get_random_name()
        self.create_folder(account, account, container, folder)

        obj1 = '/'.join([folder, get_random_name()])
        data = self._upload_object(account, account, container, obj1)

        obj2 = '/'.join([folder, get_random_name()])
        data += self._upload_object(account, account, container, obj2)

        self.b.delete_container(account, account, container, delimiter='/')

        self.expected_issue_commission_calls += [
            call.issue_one_commissions(
                holder=account,
                provisions={(project, 'pithos.diskspace'): -len(data)},
                name='/'.join([account, container, '']))]

    @assert_issue_commission_calls
    def test_delete_object(self):
        account = self.account
        container = get_random_name()
        project = unicode(uuidlib.uuid4())
        self.b.put_container(account, account, container,
                             policy={'project': project})

        obj = get_random_name()
        data = self._upload_object(account, account, container, obj)

        self.b.delete_object(account, account, container, obj)

        self.expected_issue_commission_calls += [
            call.issue_one_commissions(
                holder=account,
                provisions={(project, 'pithos.diskspace'): -len(data)},
                name='/'.join([account, container, obj]))]

    @assert_issue_commission_calls
    def test_delete_dir(self):
        account = self.account
        container = get_random_name()
        project = unicode(uuidlib.uuid4())
        self.b.put_container(account, account, container,
                             policy={'project': project})

        folder = get_random_name()
        self.create_folder(account, account, container, folder)

        obj1 = '/'.join([folder, get_random_name()])
        data = self._upload_object(account, account, container, obj1)

        obj2 = '/'.join([folder, get_random_name()])
        data += self._upload_object(account, account, container, obj2)

        self.b.delete_object(account, account, container, folder,
                             delimiter='/')

        self.expected_issue_commission_calls += [
            call.issue_one_commissions(
                holder=account,
                provisions={(project, 'pithos.diskspace'): -len(data)},
                name='/'.join([account, container, folder, '']))]
