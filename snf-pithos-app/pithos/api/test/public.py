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

import random
import datetime
import time as _time
import re

from functools import partial
from urllib import unquote

from synnefo.lib import join_urls

import django.utils.simplejson as json

from pithos.api.test import (PithosAPITest, DATE_FORMATS, TEST_BLOCK_SIZE,
                             TEST_HASH_ALGORITHM)

from pithos.api.test.util import (get_random_name, get_random_data, md5_hash,
                                  merkle)
from pithos.api import settings as pithos_settings

merkle = partial(merkle,
                 blocksize=TEST_BLOCK_SIZE,
                 blockhash=TEST_HASH_ALGORITHM)


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

        p = re.compile('(attachment|inline); filename="(.+)"')

        r = self.delete(public)
        self.assertEqual(r.status_code, 405)
        self.assertEqual(sorted(r['Allow'].split(',')),  ['GET', 'HEAD'])

        r = self.post(public)
        self.assertEqual(r.status_code, 405)
        self.assertEqual(sorted(r['Allow'].split(',')),  ['GET', 'HEAD'])

        r = self.put(public)
        self.assertEqual(r.status_code, 405)
        self.assertEqual(sorted(r['Allow'].split(',')),  ['GET', 'HEAD'])

        r = self.copy(public)
        self.assertEqual(r.status_code, 405)
        self.assertEqual(sorted(r['Allow'].split(',')),  ['GET', 'HEAD'])

        r = self.move(public)
        self.assertEqual(r.status_code, 405)
        self.assertEqual(sorted(r['Allow'].split(',')),  ['GET', 'HEAD'])

        r = self.get(public, user='user2', token=None)
        self.assertEqual(r.status_code, 200)
        self.assertTrue('X-Object-Public' not in r)
        self.assertEqual(r.content, odata)
        content_disposition = unquote(r['Content-Disposition'])
        m = p.match(content_disposition)
        self.assertTrue(m is not None)
        disposition_type = m.group(1)
        self.assertEqual(disposition_type, 'inline')
        filename = m.group(2)
        self.assertEqual(oname, filename)

        r = self.get('%s?disposition-type=inline' % public, user='user2',
                     token=None)
        self.assertEqual(r.status_code, 200)
        self.assertTrue('X-Object-Public' not in r)
        content_disposition = unquote(r['Content-Disposition'])
        m = p.match(content_disposition)
        self.assertTrue(m is not None)
        disposition_type = m.group(1)
        self.assertEqual(disposition_type, 'inline')
        filename = m.group(2)
        self.assertEqual(oname, filename)

        r = self.get('%s?disposition-type=attachment' % public, user='user2',
                     token=None)
        self.assertEqual(r.status_code, 200)
        self.assertTrue('X-Object-Public' not in r)
        content_disposition = unquote(r['Content-Disposition'])
        m = p.match(content_disposition)
        self.assertTrue(m is not None)
        disposition_type = m.group(1)
        self.assertEqual(disposition_type, 'attachment')
        filename = m.group(2)
        self.assertEqual(oname, filename)

        r = self.get('%s?disposition-type=jsdljladj' % public, user='user2',
                     token=None)
        self.assertEqual(r.status_code, 200)
        self.assertTrue('X-Object-Public' not in r)
        content_disposition = unquote(r['Content-Disposition'])
        m = p.match(content_disposition)
        self.assertTrue(m is not None)
        disposition_type = m.group(1)
        self.assertEqual(disposition_type, 'inline')
        filename = m.group(2)
        self.assertEqual(oname, filename)

        # override Content-Disposition
        user_defined_disposition = content_disposition.replace(
            'attachment', 'extension-token')
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='',
                      HTTP_CONTENT_DISPOSITION=user_defined_disposition)
        self.assertEqual(r.status_code, 202)

        r = self.get(public, user='user2', token=None)
        self.assertEqual(r.status_code, 200)
        self.assertTrue('X-Object-Public' not in r)
        self.assertEqual(r.content, odata)
        content_disposition = unquote(r['Content-Disposition'])
        self.assertEqual(content_disposition, user_defined_disposition)

        r = self.get('%s?disposition-type=inline' % public, user='user2',
                     token=None)
        self.assertEqual(r.status_code, 200)
        self.assertTrue('X-Object-Public' not in r)
        content_disposition = unquote(r['Content-Disposition'])
        m = p.match(content_disposition)
        self.assertTrue(m is not None)
        disposition_type = m.group(1)
        self.assertEqual(disposition_type, 'inline')
        filename = m.group(2)
        self.assertEqual(oname, filename)

        r = self.get('%s?disposition-type=attachment' % public, user='user2',
                     token=None)
        self.assertEqual(r.status_code, 200)
        self.assertTrue('X-Object-Public' not in r)
        content_disposition = unquote(r['Content-Disposition'])
        m = p.match(content_disposition)
        self.assertTrue(m is not None)
        disposition_type = m.group(1)
        self.assertEqual(disposition_type, 'attachment')
        filename = m.group(2)
        self.assertEqual(oname, filename)

        r = self.get('%s?disposition-type=jsdljladj' % public, user='user2',
                     token=None)
        self.assertEqual(r.status_code, 200)
        self.assertTrue('X-Object-Public' not in r)
        content_disposition = unquote(r['Content-Disposition'])
        self.assertEqual(content_disposition, user_defined_disposition)

        # assert other users cannot access the object using the priavate path
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

        # delete object history until now
        _time.sleep(1)
        t = datetime.datetime.utcnow()
        now = int(_time.mktime(t.timetuple()))
        r = self.delete('%s?intil=%d' % (url, now))
        self.assertEqual(r.status_code, 204)
        r = self.get(url)
        self.assertEqual(r.status_code, 404)
        r = self.get(public)
        self.assertEqual(r.status_code, 404)

    def test_public_manifest(self):
        cname = self.create_container()[0]
        prefix = 'myobject/'
        data = ''
        for i in range(random.randint(2, 10)):
            part = '%s%d' % (prefix, i)
            data += self.upload_object(cname, oname=part)[1]

        manifest = '%s/%s' % (cname, prefix)
        oname = get_random_name()
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.put(url, data='', HTTP_X_OBJECT_MANIFEST=manifest,
                     HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 201)

        r = self.head(url)
        self.assertTrue('X-Object-Manifest' in r)
        self.assertEqual(r['X-Object-Manifest'], manifest)

        self.assertTrue('X-Object-Public' in r)
        public = r['X-Object-Public']

        r = self.get(public)
        self.assertTrue(r.content, data)
        #self.assertTrue('X-Object-Manifest' in r)
        #self.assertEqual(r['X-Object-Manifest'], manifest)

    def test_public_get_partial(self):
        cname = self.create_container()[0]
        oname, odata = self.upload_object(cname, length=512)[:-1]

        # set public
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)

        info = self.get_object_info(cname, oname)
        public_url = info['X-Object-Public']

        r = self.get(public_url, HTTP_RANGE='bytes=0-499')
        self.assertEqual(r.status_code, 206)
        data = r.content
        self.assertEqual(data, odata[:500])
        self.assertTrue('Content-Range' in r)
        self.assertEqual(r['Content-Range'], 'bytes 0-499/%s' % len(odata))
        self.assertTrue('Content-Type' in r)
        self.assertTrue(r['Content-Type'], 'application/octet-stream')

    def test_public_get_final_500(self):
        cname = self.create_container()[0]
        oname, odata = self.upload_object(cname, length=512)[:-1]
        size = len(odata)

        # set public
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)

        info = self.get_object_info(cname, oname)
        public_url = info['X-Object-Public']

        r = self.get(public_url, HTTP_RANGE='bytes=-500')
        self.assertEqual(r.status_code, 206)
        self.assertEqual(r.content, odata[-500:])
        self.assertTrue('Content-Range' in r)
        self.assertEqual(r['Content-Range'],
                         'bytes %s-%s/%s' % (size - 500, size - 1, size))
        self.assertTrue('Content-Type' in r)
        self.assertTrue(r['Content-Type'], 'application/octet-stream')

    def test_public_get_rest(self):
        cname = self.create_container()[0]
        oname, odata = self.upload_object(cname, length=512)[:-1]
        size = len(odata)
        offset = len(odata) - random.randint(1, 512)

        # set public
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)

        info = self.get_object_info(cname, oname)
        public_url = info['X-Object-Public']

        r = self.get(public_url, HTTP_RANGE='bytes=%s-' % offset)
        self.assertEqual(r.status_code, 206)
        self.assertEqual(r.content, odata[offset:])
        self.assertTrue('Content-Range' in r)
        self.assertEqual(r['Content-Range'],
                         'bytes %s-%s/%s' % (offset, size - 1, size))
        self.assertTrue('Content-Type' in r)
        self.assertTrue(r['Content-Type'], 'application/octet-stream')

    def test_public_get_range_not_satisfiable(self):
        cname = self.create_container()[0]
        oname, odata = self.upload_object(cname, length=512)[:-1]
        url = join_urls(self.pithos_path, self.user, cname, oname)

        offset = len(odata) + 1

        # set public
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)

        info = self.get_object_info(cname, oname)
        public_url = info['X-Object-Public']

        r = self.get(public_url, HTTP_RANGE='bytes=0-%s' % offset)
        self.assertEqual(r.status_code, 416)

    def test_public_multiple_range(self):
        cname = self.create_container()[0]
        oname, odata = self.upload_object(cname)[:-1]
        url = join_urls(self.pithos_path, self.user, cname, oname)

        # set public
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)

        info = self.get_object_info(cname, oname)
        public_url = info['X-Object-Public']

        l = ['0-499', '-500', '1000-']
        ranges = 'bytes=%s' % ','.join(l)
        r = self.get(public_url, HTTP_RANGE=ranges)
        self.assertEqual(r.status_code, 206)
        self.assertTrue('content-type' in r)
        p = re.compile(
            'multipart/byteranges; boundary=(?P<boundary>[0-9a-f]{32}\Z)',
            re.I)
        m = p.match(r['content-type'])
        if m is None:
            self.fail('Invalid multiple range content type')
        boundary = m.groupdict()['boundary']
        cparts = r.content.split('--%s' % boundary)[1:-1]

        # assert content parts length
        self.assertEqual(len(cparts), len(l))

        # for each content part assert headers
        i = 0
        for cpart in cparts:
            content = cpart.split('\r\n')
            headers = content[1:3]
            content_range = headers[0].split(': ')
            self.assertEqual(content_range[0], 'Content-Range')

            r = l[i].split('-')
            if not r[0] and not r[1]:
                pass
            elif not r[0]:
                start = len(odata) - int(r[1])
                end = len(odata)
            elif not r[1]:
                start = int(r[0])
                end = len(odata)
            else:
                start = int(r[0])
                end = int(r[1]) + 1
            fdata = odata[start:end]
            sdata = '\r\n'.join(content[4:-1])
            self.assertEqual(len(fdata), len(sdata))
            self.assertEquals(fdata, sdata)
            i += 1

    def test_public_multiple_range_not_satisfiable(self):
        # perform get with multiple range
        cname = self.create_container()[0]
        oname, odata = self.upload_object(cname)[:-1]

        # set public
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)

        info = self.get_object_info(cname, oname)
        public_url = info['X-Object-Public']

        out_of_range = len(odata) + 1
        l = ['0-499', '-500', '%d-' % out_of_range]
        ranges = 'bytes=%s' % ','.join(l)
        r = self.get(public_url, HTTP_RANGE=ranges)
        self.assertEqual(r.status_code, 416)

    def test_public_get_if_match(self):
        cname = self.create_container()[0]
        oname, odata = self.upload_object(cname)[:-1]

        # set public
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)

        info = self.get_object_info(cname, oname)
        public_url = info['X-Object-Public']

        def assert_matches(etag):
            r = self.get(public_url, HTTP_IF_MATCH=etag)

            # assert get success
            self.assertEqual(r.status_code, 200)

            # assert response content
            self.assertEqual(r.content, odata)

        # perform get with If-Match
        if pithos_settings.UPDATE_MD5:
            assert_matches(md5_hash(odata))
        else:
            assert_matches(merkle(odata))

    def test_public_get_if_match_star(self):
        cname = self.create_container()[0]
        oname, odata = self.upload_object(cname)[:-1]

        # set public
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)

        info = self.get_object_info(cname, oname)
        public_url = info['X-Object-Public']

        # perform get with If-Match *
        r = self.get(public_url, HTTP_IF_MATCH='*')

        # assert get success
        self.assertEqual(r.status_code, 200)

        # assert response content
        self.assertEqual(r.content, odata)

    def test_public_get_multiple_if_match(self):
        cname = self.create_container()[0]
        oname, odata = self.upload_object(cname)[:-1]

        # set public
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)

        info = self.get_object_info(cname, oname)
        public_url = info['X-Object-Public']

        def assert_multiple_match(etag):
            quoted = lambda s: '"%s"' % s
            r = self.get(public_url, HTTP_IF_MATCH=','.join(
                [quoted(etag), quoted(get_random_data(64))]))

            # assert get success
            self.assertEqual(r.status_code, 200)

            # assert response content
            self.assertEqual(r.content, odata)

        # perform get with If-Match
        if pithos_settings.UPDATE_MD5:
            assert_multiple_match(md5_hash(odata))
        else:
            assert_multiple_match(merkle(odata))

    def test_public_if_match_precondition_failed(self):
        cname = self.create_container()[0]
        oname, odata = self.upload_object(cname)[:-1]

        # set public
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)

        info = self.get_object_info(cname, oname)
        public_url = info['X-Object-Public']

        # perform get with If-Match
        r = self.get(public_url, HTTP_IF_MATCH=get_random_name())
        self.assertEqual(r.status_code, 412)

    def test_public_if_none_match(self):
        # upload object
        cname = self.create_container()[0]
        oname, odata = self.upload_object(cname)[:-1]

        # set public
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)

        info = self.get_object_info(cname, oname)
        public_url = info['X-Object-Public']

        def assert_non_match(etag):
            # perform get with If-None-Match
            r = self.get(public_url, HTTP_IF_NONE_MATCH=etag)

            # assert precondition_failed
            self.assertEqual(r.status_code, 304)

            # update object data
            r = self.append_object_data(cname, oname)[-1]
            self.assertTrue(etag != r['ETag'])

            # perform get with If-None-Match
            r = self.get(public_url, HTTP_IF_NONE_MATCH=etag)

            # assert get success
            self.assertEqual(r.status_code, 200)

        if pithos_settings.UPDATE_MD5:
            assert_non_match(md5_hash(odata))
        else:
            assert_non_match(merkle(odata))

    def test_public_if_none_match_star(self):
        # upload object
        cname = self.create_container()[0]
        oname, odata = self.upload_object(cname)[:-1]

        # set public
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)

        info = self.get_object_info(cname, oname)
        public_url = info['X-Object-Public']

        # perform get with If-None-Match with star
        r = self.get(public_url, HTTP_IF_NONE_MATCH='*')

        self.assertEqual(r.status_code, 304)

    def test_public_if_modified_sinse(self):
        cname = get_random_name()
        self.create_container(cname)
        oname, odata = self.upload_object(cname)[:-1]
        self._assert_not_public_object(cname, oname)

        # set public
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)

        info = self.get_object_info(cname, oname)
        public = info['X-Object-Public']

        object_info = self.get_object_info(cname, oname)
        last_modified = object_info['Last-Modified']
        t1 = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])
        t1_formats = map(t1.strftime, DATE_FORMATS)

        for t in t1_formats:
            r = self.get(public, user='user2', HTTP_IF_MODIFIED_SINCE=t,
                         token=None)
            self.assertEqual(r.status_code, 304)

        _time.sleep(1)

        # update object data
        appended_data = self.append_object_data(cname, oname)[1]

        # Check modified since
        for t in t1_formats:
            r = self.get(public, user='user2', HTTP_IF_MODIFIED_SINCE=t,
                         token=None)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.content, odata + appended_data)

    def test_public_if_modified_since_invalid_date(self):
        cname = self.create_container()[0]
        oname, odata = self.upload_object(cname)[:-1]

        # set public
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)

        info = self.get_object_info(cname, oname)
        public_url = info['X-Object-Public']

        r = self.get(public_url, HTTP_IF_MODIFIED_SINCE='Monday')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, odata)

    def test_public_if_public_not_modified_since(self):
        cname = self.create_container()[0]
        oname, odata = self.upload_object(cname)[:-1]

        # set public
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)

        info = self.get_object_info(cname, oname)
        public_url = info['X-Object-Public']
        last_modified = info['Last-Modified']
        t = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])

        # Check unmodified
        t1 = t + datetime.timedelta(seconds=1)
        t1_formats = map(t1.strftime, DATE_FORMATS)
        for t in t1_formats:
            r = self.get(public_url, HTTP_IF_UNMODIFIED_SINCE=t)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.content, odata)

        # modify object
        _time.sleep(2)
        self.append_object_data(cname, oname)

        info = self.get_object_info(cname, oname)
        last_modified = info['Last-Modified']
        t = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])
        t2 = t - datetime.timedelta(seconds=1)
        t2_formats = map(t2.strftime, DATE_FORMATS)

        # check modified
        for t in t2_formats:
            r = self.get(public_url, HTTP_IF_UNMODIFIED_SINCE=t)
            self.assertEqual(r.status_code, 412)

        # modify account: update object meta
        _time.sleep(1)
        self.update_object_meta(cname, oname, {'foo': 'bar'})

        info = self.get_object_info(cname, oname)
        last_modified = info['Last-Modified']
        t = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])
        t3 = t - datetime.timedelta(seconds=1)
        t3_formats = map(t3.strftime, DATE_FORMATS)

        # check modified
        for t in t3_formats:
            r = self.get(public_url, HTTP_IF_UNMODIFIED_SINCE=t)
            self.assertEqual(r.status_code, 412)

    def test_public_if_unmodified_since(self):
        cname = self.create_container()[0]
        oname, odata = self.upload_object(cname)[:-1]

        # set public
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)

        info = self.get_object_info(cname, oname)
        public_url = info['X-Object-Public']
        last_modified = info['Last-Modified']
        t = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])
        t = t + datetime.timedelta(seconds=1)
        t_formats = map(t.strftime, DATE_FORMATS)

        for tf in t_formats:
            r = self.get(public_url, HTTP_IF_UNMODIFIED_SINCE=tf)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.content, odata)

    def test_public_if_unmodified_since_precondition_failed(self):
        cname = self.create_container()[0]
        oname, odata = self.upload_object(cname)[:-1]

        # set public
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)

        info = self.get_object_info(cname, oname)
        public_url = info['X-Object-Public']
        last_modified = info['Last-Modified']
        t = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])
        t = t - datetime.timedelta(seconds=1)
        t_formats = map(t.strftime, DATE_FORMATS)

        for tf in t_formats:
            r = self.get(public_url, HTTP_IF_UNMODIFIED_SINCE=tf)
            self.assertEqual(r.status_code, 412)
