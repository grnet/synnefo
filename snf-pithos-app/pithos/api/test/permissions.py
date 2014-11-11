#!/usr/bin/env python
#coding=utf8

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

from pithos.api.test import PithosAPITest
from pithos.api.test.util import get_random_data, get_random_name

from synnefo.lib import join_urls


class TestPermissions(PithosAPITest):
    def setUp(self):
        PithosAPITest.setUp(self)

        # create a group
        self.users = ['alice', 'bob', 'chuck', 'dan', 'mallory', 'oscar']
        self.groups = {'group1': self.users[:2]}
        kwargs = dict(('HTTP_X_ACCOUNT_GROUP_%s' % k.upper(), ','.join(v)) for
                      k, v in self.groups.items())
        url = join_urls(self.pithos_path, self.user)
        r = self.post(url, **kwargs)
        self.assertEqual(r.status_code, 202)

        self.container = get_random_name()
        self.create_container(self.container)
        self.object = self.upload_object(self.container)[0]
        l = [self.object + '/', self.object + '/a', self.object + 'a',
             self.object + 'a/']
        for i in l:
            self.upload_object(self.container, i)

    def _assert_read(self, object, authorized=None):
        authorized = authorized or []
        for user in self.users:
            url = join_urls(
                self.pithos_path, self.user, self.container, object)
            r = self.head(url, user=user)
            if user in authorized:
                self.assertEqual(r.status_code, 200)
            else:
                self.assertEqual(r.status_code, 403)

            r = self.get(url, user=user)
            if user in authorized:
                self.assertEqual(r.status_code, 200)
            else:
                self.assertEqual(r.status_code, 403)

        # check inheritance
        info = self.get_object_info(self.container, object)
        is_directory = info['Content-Type'] in ('application/directory',
                                                'application/folder')
        prefix = object + '/'
        derivatives = [o['name'] for o in self.list_objects(
            self.container, prefix=object) if o['name'] != object]
        for o in derivatives:
            url = join_urls(self.pithos_path, self.user, self.container, o)
            for user in self.users:
                if (user in authorized and is_directory and
                        o.startswith(prefix)):
                    r = self.head(url, user=user)
                    self.assertEqual(r.status_code, 200)

                    r = self.get(url, user=user)
                    self.assertEqual(r.status_code, 200)
                else:
                    r = self.head(url, user=user)
                    self.assertEqual(r.status_code, 403)

                    r = self.get(url, user=user)
                    self.assertEqual(r.status_code, 403)

    def _assert_write(self, object, authorized=None):
        authorized = authorized or []

        url = join_urls(self.pithos_path, self.user, self.container, object)
        for user in self.users:
            if user in authorized:
                r = self.get(url)
                self.assertEqual(r.status_code, 200)
                initial_data = r.content

                # test write access
                data = get_random_data()
                r = self.post(url, user=user, data=data,
                              content_type='application/octet-stream',
                              HTTP_CONTENT_LENGTH=str(len(data)),
                              HTTP_CONTENT_RANGE='bytes */*')
                self.assertEqual(r.status_code, 204)

                # test read access
                r = self.get(url, user=user)
                self.assertEqual(r.status_code, 200)
                server_data = r.content
                self.assertEqual(server_data, initial_data + data)
            else:
                # test write access
                data = get_random_data()
                r = self.post(url, user=user, data=data,
                              content_type='application/octet-stream',
                              HTTP_CONTENT_LENGTH=str(len(data)),
                              HTTP_CONTENT_RANGE='bytes */*')
                self.assertEqual(r.status_code, 403)

        # check inheritance
        info = self.get_object_info(self.container, object)
        is_directory = info['Content-Type'] in ('application/directory',
                                                'application/folder')
        prefix = object + '/'

        derivatives = [o['name'] for o in self.list_objects(
            self.container, prefix=object) if o['name'] != object]

        for o in derivatives:
            url = join_urls(self.pithos_path, self.user, self.container, o)
            for user in self.users:
                if (user in authorized and is_directory and
                        o.startswith(prefix)):
                    # get initial data
                    r = self.get(url)
                    self.assertEqual(r.status_code, 200)
                    initial_data = r.content

                    # test write access
                    data = get_random_data()
                    r = self.post(url, user=user, data=data,
                                  content_type='application/octet-stream',
                                  HTTP_CONTENT_LENGTH=str(len(data)),
                                  HTTP_CONTENT_RANGE='bytes */*')
                    self.assertEqual(r.status_code, 204)

                    # test read access
                    r = self.get(url, user=user)
                    self.assertEqual(r.status_code, 200)
                    server_data = r.content
                    self.assertEqual(server_data, initial_data + data)
                    initial_data = server_data
                else:
                    # test write access
                    data = get_random_data()
                    r = self.post(url, user=user, data=data,
                                  content_type='application/octet-stream',
                                  HTTP_CONTENT_LENGTH=str(len(data)),
                                  HTTP_CONTENT_RANGE='bytes */*')
                    self.assertEqual(r.status_code, 403)

    def test_group_read(self):
        group = self.groups.keys()[0]
        members = self.groups[group]
        url = join_urls(
            self.pithos_path, self.user, self.container, self.object)
        r = self.post(
            url, content_type='', HTTP_CONTENT_RANGE='bytes */*',
            HTTP_X_OBJECT_SHARING='read=%s:%s' % (self.user, group))
        self.assertEqual(r.status_code, 202)
        self._assert_read(self.object, authorized=members)

    def test_read_many(self):
        l = self.users[:2]
        url = join_urls(
            self.pithos_path, self.user, self.container, self.object)
        r = self.post(
            url, content_type='', HTTP_CONTENT_RANGE='bytes */*',
            HTTP_X_OBJECT_SHARING='read=%s' % ','.join(l))
        self.assertEqual(r.status_code, 202)
        self._assert_read(self.object, authorized=l)

    def test_read_by_everyone(self):
        url = join_urls(
            self.pithos_path, self.user, self.container, self.object)
        r = self.post(
            url, content_type='', HTTP_CONTENT_RANGE='bytes */*',
            HTTP_X_OBJECT_SHARING='read=*')
        self.assertEqual(r.status_code, 202)
        self._assert_read(self.object, authorized=self.users)

    def test_read_directory(self):
        url = join_urls(
            self.pithos_path, self.user, self.container, self.object)
        for type in ('application/directory', 'application/folder'):
            # change content type
            r = self.put(url, data='', content_type=type,
                         HTTP_X_MOVE_FROM='/%s/%s' % (
                             self.container, self.object))
            self.assertEqual(r.status_code, 201)
            info = self.get_object_info(self.container, self.object)
            self.assertEqual(info['Content-Type'], type)

            url = join_urls(
                self.pithos_path, self.user, self.container, self.object)
            r = self.post(
                url, content_type='', HTTP_CONTENT_RANGE='bytes */*',
                HTTP_X_OBJECT_SHARING='read=*')
            self._assert_read(self.object, self.users)

            url = join_urls(
                self.pithos_path, self.user, self.container, self.object)
            r = self.post(
                url, content_type='', HTTP_CONTENT_RANGE='bytes */*',
                HTTP_X_OBJECT_SHARING='read=%s' % ','.join(
                    self.users[:2]))
            self._assert_read(self.object, self.users[:2])

            group = self.groups.keys()[0]
            members = self.groups[group]
            url = join_urls(
                self.pithos_path, self.user, self.container, self.object)
            r = self.post(
                url, content_type='', HTTP_CONTENT_RANGE='bytes */*',
                HTTP_X_OBJECT_SHARING='read=%s:%s' % (self.user, group))
            self._assert_read(self.object, members)

    def test_group_write(self):
        group = self.groups.keys()[0]
        members = self.groups[group]
        url = join_urls(
            self.pithos_path, self.user, self.container, self.object)
        r = self.post(
            url, content_type='', HTTP_CONTENT_RANGE='bytes */*',
            HTTP_X_OBJECT_SHARING='write=%s:%s' % (self.user, group))
        self.assertEqual(r.status_code, 202)
        self._assert_write(self.object, authorized=members)

    def test_write_many(self):
        l = self.users[:2]
        url = join_urls(
            self.pithos_path, self.user, self.container, self.object)
        r = self.post(
            url, content_type='', HTTP_CONTENT_RANGE='bytes */*',
            HTTP_X_OBJECT_SHARING='write=%s' % ','.join(l))
        self.assertEqual(r.status_code, 202)
        self._assert_write(self.object, authorized=l)

    def test_write_by_everyone(self):
        url = join_urls(
            self.pithos_path, self.user, self.container, self.object)
        r = self.post(
            url, content_type='', HTTP_CONTENT_RANGE='bytes */*',
            HTTP_X_OBJECT_SHARING='write=*')
        self.assertEqual(r.status_code, 202)
        self._assert_write(self.object, authorized=self.users)

    def test_write_directory(self):
        url = join_urls(
            self.pithos_path, self.user, self.container, self.object)
        for type in ('application/directory', 'application/folder'):
            # change content type
            r = self.put(url, data='', content_type=type,
                         HTTP_X_MOVE_FROM='/%s/%s' % (
                             self.container, self.object))
            self.assertEqual(r.status_code, 201)
            info = self.get_object_info(self.container, self.object)
            self.assertEqual(info['Content-Type'], type)

            url = join_urls(
                self.pithos_path, self.user, self.container, self.object)
            r = self.post(
                url, content_type='', HTTP_CONTENT_RANGE='bytes */*',
                HTTP_X_OBJECT_SHARING='write=*')
            self._assert_write(self.object, self.users)

            url = join_urls(
                self.pithos_path, self.user, self.container, self.object)
            r = self.post(
                url, content_type='', HTTP_CONTENT_RANGE='bytes */*',
                HTTP_X_OBJECT_SHARING='write=%s' % ','.join(
                    self.users[:2]))
            self._assert_write(self.object, self.users[:2])

            group = self.groups.keys()[0]
            members = self.groups[group]
            url = join_urls(
                self.pithos_path, self.user, self.container, self.object)
            r = self.post(
                url, content_type='', HTTP_CONTENT_RANGE='bytes */*',
                HTTP_X_OBJECT_SHARING='write=%s:%s' % (self.user, group))
            self._assert_write(self.object, members)

    def test_not_allowed(self):
        cname = self.create_container()[0]
        oname, odata = self.upload_object(cname)[:-1]

        url = join_urls(self.pithos_path, self.user)
        r = self.head(url, user='chuck')
        self.assertEqual(r.status_code, 403)
        r = self.get(url, user='chuck')
        self.assertEqual(r.status_code, 403)
        r = self.post(url, user='chuck', data=get_random_data())
        self.assertEqual(r.status_code, 403)

        url = join_urls(self.pithos_path, self.user, cname)
        r = self.head(url, user='chuck')
        self.assertEqual(r.status_code, 403)
        r = self.get(url, user='chuck')
        self.assertEqual(r.status_code, 403)
        r = self.put(url, user='chuck', data=get_random_data())
        self.assertEqual(r.status_code, 403)
        r = self.post(url, user='chuck', data=get_random_data())
        self.assertEqual(r.status_code, 403)
        r = self.delete(url, user='chuck')
        self.assertEqual(r.status_code, 403)

        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.head(url, user='chuck')
        self.assertEqual(r.status_code, 403)
        r = self.get(url, user='chuck')
        self.assertEqual(r.status_code, 403)
        r = self.put(url, user='chuck', data=get_random_data())
        self.assertEqual(r.status_code, 403)
        r = self.post(url, user='chuck', data=get_random_data())
        self.assertEqual(r.status_code, 403)
        r = self.delete(url, user='chuck')
        self.assertEqual(r.status_code, 403)

    def test_multiple_inheritance(self):
        cname = self.container
        folder = self.create_folder(cname, HTTP_X_OBJECT_SHARING='write=*')[0]
        subfolder = self.create_folder(cname, '%s/%s' % (folder,
                                                         get_random_name()))[0]
        self.upload_object(cname, '%s/%s' % (subfolder, get_random_name()))

        self._assert_read(subfolder, self.users)
        self._assert_write(subfolder, self.users)

        # share object for read only
        url = join_urls(self.pithos_path, self.user, cname, subfolder)
        self.post(url, content_type='', HTTP_CONTENT_RANGE='bytes */*',
                  HTTP_X_OBJECT_SHARING='read=*')

        self._assert_read(subfolder, self.users)
        self._assert_write(subfolder, [])
