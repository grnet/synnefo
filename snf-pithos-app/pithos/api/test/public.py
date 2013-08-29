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

import random
import datetime
import time as _time

from synnefo.lib import join_urls

import django.utils.simplejson as json

from pithos.api.test import PithosAPITest
from pithos.api.test.util import get_random_name
from pithos.api import settings as pithos_settings


class TestPublic(PithosAPITest):
    def _assert_not_public_object(self, cname, oname):
        info = self.get_object_info(cname, oname)
        self.assertTrue('X-Object-Public' not in info)

    def _assert_public_object(self, cname, oname, odata):
        info = self.get_object_info(cname, oname)
        self.assertTrue('X-Object-Public' in info)
        public = info['X-Object-Public']

        self.assertTrue(len(public) >= pithos_settings.PUBLIC_URL_SECURITY)
        (self.assertTrue(l in pithos_settings.PUBLIC_URL_ALPHABET) for
         l in public)

        r = self.get(public, user='user2')
        self.assertEqual(r.status_code, 200)
        self.assertTrue('X-Object-Public' not in r)

        self.assertEqual(r.content, odata)

        # assert other users cannot access the object using the priavate path
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.head(url, user='user2')
        self.assertEqual(r.status_code, 403)

        r = self.get(url, user='user2')
        self.assertEqual(r.status_code, 403)

        return public

    def test_set_object_public(self):
        cname = get_random_name()
        self.create_container(cname)
        oname, odata = self.upload_object(cname)[:-1]
        self._assert_not_public_object(cname, oname)

        # set public
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)

        self._assert_public_object(cname, oname, odata)

    def test_set_twice(self):
        cname = get_random_name()
        self.create_container(cname)
        oname, odata = self.upload_object(cname)[:-1]
        self._assert_not_public_object(cname, oname)

        # set public
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)

        public = self._assert_public_object(cname, oname, odata)

        # set public
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)

        public2 = self._assert_public_object(cname, oname, odata)

        self.assertEqual(public, public2)

    def test_set_unset_set(self):
        cname = get_random_name()
        self.create_container(cname)
        oname, odata = self.upload_object(cname)[:-1]
        self._assert_not_public_object(cname, oname)

        # set public
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)

        public = self._assert_public_object(cname, oname, odata)

        # unset public
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='false')
        self.assertEqual(r.status_code, 202)

        self._assert_not_public_object(cname, oname)

        # set public
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)

        public2 = self._assert_public_object(cname, oname, odata)

        self.assertTrue(public != public2)

        # unset public
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='false')
        self.assertEqual(r.status_code, 202)

        self._assert_not_public_object(cname, oname)

    def test_update_public_object(self):
        cname = get_random_name()
        self.create_container(cname)
        oname, odata = self.upload_object(cname)[:-1]
        self._assert_not_public_object(cname, oname)

        # set public
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)

        public = self._assert_public_object(cname, oname, odata)

        odata2 = self.append_object_data(cname, oname)[1]

        public2 = self._assert_public_object(cname, oname, odata + odata2)

        self.assertTrue(public == public2)

    def test_delete_public_object(self):
        cname = get_random_name()
        self.create_container(cname)
        oname, odata = self.upload_object(cname)[:-1]
        self._assert_not_public_object(cname, oname)

        # set public
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)
        public = self._assert_public_object(cname, oname, odata)

        # delete object
        r = self.delete(url)
        self.assertEqual(r.status_code, 204)
        r = self.get(url)
        self.assertEqual(r.status_code, 404)
        r = self.get(public)
        self.assertEqual(r.status_code, 404)

    def test_delete_public_object_history(self):
        cname = get_random_name()
        self.create_container(cname)
        oname, odata = self.upload_object(cname)[:-1]
        self._assert_not_public_object(cname, oname)

        # set public
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)
        public = self._assert_public_object(cname, oname, odata)

        for _ in range(random.randint(1, 10)):
            odata += self.append_object_data(cname, oname)[1]
            _time.sleep(1)

        # get object versions
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.get('%s?version=list&format=json' % url)
        version_list = json.loads(r.content)['versions']
        mtime = [int(float(t[1])) for t in version_list]

        # delete object history
        i = random.randrange(len(mtime))
        self.delete('%s?until=%d' % (url, mtime[i]))
        public2 = self._assert_public_object(cname, oname, odata)
        self.assertEqual(public, public2)

        # delete object histoy until now
        _time.sleep(1)
        t = datetime.datetime.utcnow()
        now = int(_time.mktime(t.timetuple()))
        r = self.delete('%s?intil=%d' % (url, now))
        self.assertEqual(r.status_code, 204)
        r = self.get(url)
        self.assertEqual(r.status_code, 404)
        r = self.get(public)
        self.assertEqual(r.status_code, 404)
