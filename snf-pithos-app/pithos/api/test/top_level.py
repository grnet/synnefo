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

from synnefo.lib import join_urls

class TopLevel(PithosAPITest):
    def test_not_allowed_method(self):
        url = join_urls(self.pithos_path, '/')
        r = self.head(url)
        self.assertEqual(r.status_code, 405)
        self.assertTrue('Allow' in r)
        self.assertEqual(r['Allow'], 'GET')
        r = self.put(url, data='')
        self.assertEqual(r.status_code, 405)
        self.assertTrue('Allow' in r)
        self.assertEqual(r['Allow'], 'GET')
        r = self.post(url, data='')
        self.assertEqual(r.status_code, 405)
        self.assertTrue('Allow' in r)
        self.assertEqual(r['Allow'], 'GET')
        r = self.delete(url)
        self.assertEqual(r.status_code, 405)
        self.assertTrue('Allow' in r)
        self.assertEqual(r['Allow'], 'GET')


    def test_authenticate(self):
        url = join_urls(self.pithos_path, '/')
        r = self.get(url, token=None)
        self.assertEqual(r.status_code, 400)

        r = self.get(url, token=None, HTTP_X_AUTH_USER=self.user)
        self.assertEqual(r.status_code, 400)

        r = self.get(url, token=None, HTTP_X_AUTH_USER=self.user,
                     HTTP_X_AUTH_KEY='DummyToken')
        self.assertEqual(r.status_code, 204)
        self.assertTrue('X-Auth-Token' in r)
        self.assertTrue(r['X-Auth-Token'], 'DummyToken')
