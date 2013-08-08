#!/usr/bin/env python
#coding=utf8

# Copyright 2011-2013 GRNET S.A. All rights reserved.
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

from pithos.api import settings as pithos_settings
from pithos.api.test import PithosAPITest, DATE_FORMATS
from pithos.api.test.util import (md5_hash, get_random_data, get_random_name)
from pithos.api.test.objects import merkle

from synnefo.lib.services import get_service_path
from synnefo.lib import join_urls

from mock import patch
from urllib import quote
from urlparse import urlsplit, parse_qs

import django.utils.simplejson as json

import re
import datetime
import time as _time
import random


class ObjectGetView(PithosAPITest):
    def setUp(self):
        PithosAPITest.setUp(self)
        self.cname = self.create_container()[0]
        self.oname, self.odata = self.upload_object(self.cname)[:-1]

        self.view_path = join_urls(get_service_path(
            pithos_settings.pithos_services, 'pithos_ui'), 'view')
        self.view_url = join_urls(self.view_path, self.user, self.cname,
                                  self.oname)
        self.api_url = join_urls(self.pithos_path, self.user, self.cname,
                                 self.oname)

    def get(self, url, user='user', *args, **kwargs):
        with patch("pithos.api.util.get_token_from_cookie") as m:
            m.return_value = 'token'
            return super(ObjectGetView, self).get(url, user='user', *args,
                                                  **kwargs)

    def test_no_cookie_redirect(self):
        r = super(ObjectGetView, self).get(self.view_url)
        self.assertEqual(r.status_code, 302)
        self.assertTrue('Location' in r)
        parts = list(urlsplit(r['Location']))
        qs = parse_qs(parts[3])
        self.assertTrue('next' in qs)
        self.assertEqual(qs['next'][0], join_urls(pithos_settings.BASE_HOST,
                                                  self.view_url))

    def test_versions(self):
        c = self.cname
        o = self.oname

        meta = {'HTTP_X_OBJECT_META_QUALITY': 'AAA'}
        r = self.post(self.api_url, content_type='', **meta)
        self.assertEqual(r.status_code, 202)

        r = self.get('%s?version=list&format=json' % self.view_url)
        self.assertEqual(r.status_code, 200)
        l1 = json.loads(r.content)['versions']
        self.assertEqual(len(l1), 2)

        # update meta
        meta = {'HTTP_X_OBJECT_META_QUALITY': 'AB',
                'HTTP_X_OBJECT_META_STOCK': 'True'}
        r = self.post(self.api_url, content_type='', **meta)
        self.assertEqual(r.status_code, 202)

        # assert a newly created version has been created
        r = self.get('%s?version=list&format=json' % self.view_url)
        self.assertEqual(r.status_code, 200)
        l2 = json.loads(r.content)['versions']
        self.assertEqual(len(l2), len(l1) + 1)
        self.assertEqual(l2[:-1], l1)

        vserial, _ = l2[-2]
        self.assertEqual(self.get_object_meta(c, o, version=vserial),
                         {'Quality': 'AAA'})

        # update data
        self.append_object_data(c, o)

        # assert a newly created version has been created
        r = self.get('%s?version=list&format=json' % self.view_url)
        self.assertEqual(r.status_code, 200)
        l3 = json.loads(r.content)['versions']
        self.assertEqual(len(l3), len(l2) + 1)
        self.assertEqual(l3[:-1], l2)

    def test_objects_with_trailing_spaces(self):
        cname = self.cname

        r = self.get(quote('%s ' % self.view_url))
        self.assertEqual(r.status_code, 404)

        # delete object
        self.delete(self.api_url)

        r = self.get(self.view_url)
        self.assertEqual(r.status_code, 404)

        # upload object with trailing space
        oname = self.upload_object(cname, quote('%s ' % get_random_name()))[0]

        view_url = join_urls(self.view_path, self.user, cname, oname)
        r = self.get(view_url)
        self.assertEqual(r.status_code, 200)

        view_url = join_urls(self.view_path, self.user, cname, oname[:-1])
        r = self.get(view_url)
        self.assertEqual(r.status_code, 404)

    def test_get_partial(self):
        limit = pithos_settings.BACKEND_BLOCK_SIZE + 1
        r = self.get(self.view_url, HTTP_RANGE='bytes=0-%d' % limit)
        self.assertEqual(r.status_code, 206)
        self.assertEqual(r.content, self.odata[:limit + 1])
        self.assertTrue('Content-Range' in r)
        self.assertEqual(r['Content-Range'], 'bytes 0-%d/%d' % (
            limit, len(self.odata)))
        self.assertTrue('Content-Type' in r)
        self.assertTrue(r['Content-Type'], 'application/octet-stream')

    def test_get_range_not_satisfiable(self):
        # TODO
        #r = self.get(self.view_url, HTTP_RANGE='bytes=50-10')
        #self.assertEqual(r.status_code, 416)

        offset = len(self.odata) + 1
        r = self.get(self.view_url, HTTP_RANGE='bytes=0-%s' % offset)
        self.assertEqual(r.status_code, 416)

    def test_multiple_range(self):
        l = ['0-499', '-500', '1000-']
        ranges = 'bytes=%s' % ','.join(l)
        r = self.get(self.view_url, HTTP_RANGE=ranges)
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
                start = len(self.odata) - int(r[1])
                end = len(self.odata)
            elif not r[1]:
                start = int(r[0])
                end = len(self.odata)
            else:
                start = int(r[0])
                end = int(r[1]) + 1
            fdata = self.odata[start:end]
            sdata = '\r\n'.join(content[4:-1])
            self.assertEqual(len(fdata), len(sdata))
            self.assertEquals(fdata, sdata)
            i += 1

    def test_multiple_range_not_satisfiable(self):
        # perform get with multiple range
        out_of_range = len(self.odata) + 1
        l = ['0-499', '-500', '%d-' % out_of_range]
        ranges = 'bytes=%s' % ','.join(l)
        r = self.get(self.view_url, HTTP_RANGE=ranges)
        self.assertEqual(r.status_code, 416)

    def test_get_if_match(self):
        if pithos_settings.UPDATE_MD5:
            etag = md5_hash(self.odata)
        else:
            etag = merkle(self.odata)

        r = self.get(self.view_url, HTTP_IF_MATCH=etag)

        # assert get success
        self.assertEqual(r.status_code, 200)

        # assert response content
        self.assertEqual(r.content, self.odata)

    def test_get_if_match_star(self):
        r = self.get(self.view_url, HTTP_IF_MATCH='*')

        # assert get success
        self.assertEqual(r.status_code, 200)

        # assert response content
        self.assertEqual(r.content, self.odata)

    def test_get_multiple_if_match(self):
        if pithos_settings.UPDATE_MD5:
            etag = md5_hash(self.odata)
        else:
            etag = merkle(self.odata)

        quoted = lambda s: '"%s"' % s
        r = self.get(self.view_url, HTTP_IF_MATCH=','.join(
            [quoted(etag), quoted(get_random_data(64))]))

        # assert get success
        self.assertEqual(r.status_code, 200)

        # assert response content
        self.assertEqual(r.content, self.odata)

    def test_if_match_precondition_failed(self):
        r = self.get(self.view_url, HTTP_IF_MATCH=get_random_name())
        self.assertEqual(r.status_code, 412)

    def test_if_none_match(self):
        if pithos_settings.UPDATE_MD5:
            etag = md5_hash(self.odata)
        else:
            etag = merkle(self.odata)

        # perform get with If-None-Match
        r = self.get(self.view_url, HTTP_IF_NONE_MATCH=etag)

        # assert precondition_failed
        self.assertEqual(r.status_code, 304)

        # update object data
        r = self.append_object_data(self.cname, self.oname)[-1]
        self.assertTrue(etag != r['ETag'])

        # perform get with If-None-Match
        r = self.get(self.view_url, HTTP_IF_NONE_MATCH=etag)

        # assert get success
        self.assertEqual(r.status_code, 200)

    def test_if_none_match_star(self):
        # perform get with If-None-Match with star
        r = self.get(self.view_url, HTTP_IF_NONE_MATCH='*')
        self.assertEqual(r.status_code, 304)

    def test_if_modified_since(self):
        # upload object
        object_info = self.get_object_info(self.cname, self.oname)
        last_modified = object_info['Last-Modified']
        t1 = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])
        t1_formats = map(t1.strftime, DATE_FORMATS)

        # Check not modified since
        for t in t1_formats:
            r = self.get(self.view_url, HTTP_IF_MODIFIED_SINCE=t)
            self.assertEqual(r.status_code, 304)

        _time.sleep(1)

        # update object data
        appended_data = self.append_object_data(self.cname, self.oname)[1]

        # Check modified since
        for t in t1_formats:
            r = self.get(self.view_url, HTTP_IF_MODIFIED_SINCE=t)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.content, self.odata + appended_data)

    def test_if_modified_since_invalid_date(self):
        r = self.get(self.view_url, HTTP_IF_MODIFIED_SINCE='Monday')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, self.odata)

    def test_if_not_modified_since(self):
        object_info = self.get_object_info(self.cname, self.oname)
        last_modified = object_info['Last-Modified']
        t = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])

        # Check unmodified
        t1 = t + datetime.timedelta(seconds=1)
        t1_formats = map(t1.strftime, DATE_FORMATS)
        for t in t1_formats:
            r = self.get(self.view_url, HTTP_IF_UNMODIFIED_SINCE=t)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.content, self.odata)

        # modify object
        _time.sleep(2)
        self.append_object_data(self.cname, self.oname)

        object_info = self.get_object_info(self.cname, self.oname)
        last_modified = object_info['Last-Modified']
        t = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])
        t2 = t - datetime.timedelta(seconds=1)
        t2_formats = map(t2.strftime, DATE_FORMATS)

        # check modified
        for t in t2_formats:
            r = self.get(self.view_url, HTTP_IF_UNMODIFIED_SINCE=t)
            self.assertEqual(r.status_code, 412)

        # modify account: update object meta
        _time.sleep(1)
        self.update_object_meta(self.cname, self.oname, {'foo': 'bar'})

        object_info = self.get_object_info(self.cname, self.oname)
        last_modified = object_info['Last-Modified']
        t = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])
        t3 = t - datetime.timedelta(seconds=1)
        t3_formats = map(t3.strftime, DATE_FORMATS)

        # check modified
        for t in t3_formats:
            r = self.get(self.view_url, HTTP_IF_UNMODIFIED_SINCE=t)
            self.assertEqual(r.status_code, 412)

    def test_if_unmodified_since(self):
        object_info = self.get_object_info(self.cname, self.oname)
        last_modified = object_info['Last-Modified']
        t = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])
        t = t + datetime.timedelta(seconds=1)
        t_formats = map(t.strftime, DATE_FORMATS)

        for tf in t_formats:
            r = self.get(self.view_url, HTTP_IF_UNMODIFIED_SINCE=tf)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.content, self.odata)

    def test_if_unmodified_since_precondition_failed(self):
        object_info = self.get_object_info(self.cname, self.oname)
        last_modified = object_info['Last-Modified']
        t = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])
        t = t - datetime.timedelta(seconds=1)
        t_formats = map(t.strftime, DATE_FORMATS)

        for tf in t_formats:
            r = self.get(self.view_url, HTTP_IF_UNMODIFIED_SINCE=tf)
            self.assertEqual(r.status_code, 412)

    def test_hashes(self):
        l = random.randint(2, 5) * pithos_settings.BACKEND_BLOCK_SIZE
        oname, odata = self.upload_object(self.cname, length=l)[:-1]
        size = len(odata)

        view_url = join_urls(self.view_path, self.user, self.cname, oname)
        r = self.get('%s?format=json&hashmap' % view_url)
        self.assertEqual(r.status_code, 200)
        body = json.loads(r.content)

        hashes = body['hashes']
        block_size = body['block_size']
        block_num = size / block_size if size / block_size == 0 else\
            size / block_size + 1
        self.assertTrue(len(hashes), block_num)
        i = 0
        for h in hashes:
            start = i * block_size
            end = (i + 1) * block_size
            hash = merkle(odata[start:end])
            self.assertEqual(h, hash)
            i += 1
