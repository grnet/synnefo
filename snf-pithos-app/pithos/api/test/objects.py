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

from collections import defaultdict
from urllib import quote
import time as _time

from pithos.api.test import (PithosAPITest, pithos_settings,
                             AssertMappingInvariant, AssertUUidInvariant,
                             DATE_FORMATS)
from pithos.api.test.util import compute_md5_hash, strnextling, get_random_data
from pithos.api.test.util.hashmap import merkle

from synnefo.lib import join_urls

import django.utils.simplejson as json

import random
import re
import datetime


class ObjectGet(PithosAPITest):
    def setUp(self):
        PithosAPITest.setUp(self)
        self.containers = ['c1', 'c2']

        # create some containers
        for c in self.containers:
            self.create_container(c)

        # upload files
        self.objects = defaultdict(list)
        self.objects['c1'].append(self.upload_object('c1')[0])

    def test_versions(self):
        c = 'c1'
        o = self.objects[c][0]
        url = join_urls(self.pithos_path, self.user, c, o)

        meta = {'HTTP_X_OBJECT_META_QUALITY': 'AAA'}
        r = self.post(url, content_type='', **meta)
        self.assertEqual(r.status_code, 202)

        url = join_urls(self.pithos_path, self.user, c, o)
        r = self.get('%s?version=list&format=json' % url)
        self.assertEqual(r.status_code, 200)
        l1 = json.loads(r.content)['versions']
        self.assertEqual(len(l1), 2)

        # update meta
        meta = {'HTTP_X_OBJECT_META_QUALITY': 'AB',
                'HTTP_X_OBJECT_META_STOCK': 'True'}
        r = self.post(url, content_type='', **meta)
        self.assertEqual(r.status_code, 202)

        # assert a newly created version has been created
        r = self.get('%s?version=list&format=json' % url)
        self.assertEqual(r.status_code, 200)
        l2 = json.loads(r.content)['versions']
        self.assertEqual(len(l2), len(l1) + 1)
        self.assertEqual(l2[:-1], l1)

        vserial, _ = l2[-2]
        self.assertEqual(self.get_object_meta(c, o, version=vserial),
                         {'X-Object-Meta-Quality': 'AAA'})

        # update data
        self.append_object_data(c, o)

        # assert a newly created version has been created
        r = self.get('%s?version=list&format=json' % url)
        self.assertEqual(r.status_code, 200)
        l3 = json.loads(r.content)['versions']
        self.assertEqual(len(l3), len(l2) + 1)
        self.assertEqual(l3[:-1], l2)

    def test_objects_with_trailing_spaces(self):
        # create object
        oname = self.upload_object('c1')[0]
        url = join_urls(self.pithos_path, self.user, 'c1', oname)

        r = self.get(quote('%s ' % url))
        self.assertEqual(r.status_code, 404)

        # delete object
        self.delete(url)

        r = self.get(url)
        self.assertEqual(r.status_code, 404)

        # upload object with trailing space
        oname = self.upload_object('c1', quote('%s ' % get_random_data(8)))[0]

        url = join_urls(self.pithos_path, self.user, 'c1', oname)
        r = self.get(url)
        self.assertEqual(r.status_code, 200)

        url = join_urls(self.pithos_path, self.user, 'c1', oname[:-1])
        r = self.get(url)
        self.assertEqual(r.status_code, 404)

    def test_get_partial(self):
        cname = self.containers[0]
        oname, odata = self.upload_object(cname, length=512)[:-1]
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.get(url, HTTP_RANGE='bytes=0-499')
        self.assertEqual(r.status_code, 206)
        data = r.content
        self.assertEqual(data, odata[:500])
        self.assertTrue('Content-Range' in r)
        self.assertEqual(r['Content-Range'], 'bytes 0-499/%s' % len(odata))
        self.assertTrue('Content-Type' in r)
        self.assertTrue(r['Content-Type'], 'application/octet-stream')

    def test_get_final_500(self):
        cname = self.containers[0]
        oname, odata = self.upload_object(cname, length=512)[:-1]
        size = len(odata)
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.get(url, HTTP_RANGE='bytes=-500')
        self.assertEqual(r.status_code, 206)
        self.assertEqual(r.content, odata[-500:])
        self.assertTrue('Content-Range' in r)
        self.assertEqual(r['Content-Range'],
                         'bytes %s-%s/%s' % (size - 500, size - 1, size))
        self.assertTrue('Content-Type' in r)
        self.assertTrue(r['Content-Type'], 'application/octet-stream')

    def test_get_rest(self):
        cname = self.containers[0]
        oname, odata = self.upload_object(cname, length=512)[:-1]
        size = len(odata)
        url = join_urls(self.pithos_path, self.user, cname, oname)
        offset = len(odata) - random.randint(1, 512)
        r = self.get(url, HTTP_RANGE='bytes=%s-' % offset)
        self.assertEqual(r.status_code, 206)
        self.assertEqual(r.content, odata[offset:])
        self.assertTrue('Content-Range' in r)
        self.assertEqual(r['Content-Range'],
                         'bytes %s-%s/%s' % (offset, size - 1, size))
        self.assertTrue('Content-Type' in r)
        self.assertTrue(r['Content-Type'], 'application/octet-stream')

    def test_get_range_not_satisfiable(self):
        cname = self.containers[0]
        oname, odata = self.upload_object(cname, length=512)[:-1]
        url = join_urls(self.pithos_path, self.user, cname, oname)

        # TODO
        #r = self.get(url, HTTP_RANGE='bytes=50-10')
        #self.assertEqual(r.status_code, 416)

        offset = len(odata) + 1
        r = self.get(url, HTTP_RANGE='bytes=0-%s' % offset)
        self.assertEqual(r.status_code, 416)

    def test_multiple_range(self):
        cname = self.containers[0]
        oname, odata = self.upload_object(cname, length=1024)[:-1]
        url = join_urls(self.pithos_path, self.user, cname, oname)

        l = ['0-499', '-500', '1000-']
        ranges = 'bytes=%s' % ','.join(l)
        r = self.get(url, HTTP_RANGE=ranges)
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

    def test_multiple_range_not_satisfiable(self):
        # perform get with multiple range
        cname = self.containers[0]
        oname, odata = self.upload_object(cname, length=1024)[:-1]
        out_of_range = len(odata) + 1
        l = ['0-499', '-500', '%d-' % out_of_range]
        ranges = 'bytes=%s' % ','.join(l)
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.get(url, HTTP_RANGE=ranges)
        self.assertEqual(r.status_code, 416)

    def test_get_with_if_match_with_md5(self):
        cname = self.containers[0]
        oname, odata = self.upload_object(cname, length=1024)[:-1]

        # perform get with If-Match
        url = join_urls(self.pithos_path, self.user, cname, oname)

        if pithos_settings.UPDATE_MD5:
            etag = compute_md5_hash(odata)
        else:
            etag = merkle(odata)

        r = self.get(url, HTTP_IF_MATCH=etag)

        # assert get success
        self.assertEqual(r.status_code, 200)

        # assert response content
        self.assertEqual(r.content, odata)

    def test_get_with_if_match_star_with_md5(self):
        cname = self.containers[0]
        oname, odata = self.upload_object(cname, length=1024)[:-1]

        # perform get with If-Match *
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.get(url, HTTP_IF_MATCH='*')

        # assert get success
        self.assertEqual(r.status_code, 200)

        # assert response content
        self.assertEqual(r.content, odata)

    def test_get_with_multiple_if_match_without_md5(self):
        cname = self.containers[0]
        oname, odata = self.upload_object(cname, length=1024)[:-1]

        # perform get with If-Match
        url = join_urls(self.pithos_path, self.user, cname, oname)

        if pithos_settings.UPDATE_MD5:
            etag = compute_md5_hash(odata)
        else:
            etag = merkle(odata)

        r = self.get(url, HTTP_IF_MATCH=','.join([etag,
                                                  get_random_data(8)]))

        # assert get success
        self.assertEqual(r.status_code, 200)

        # assert response content
        self.assertEqual(r.content, odata)

    def test_if_match_precondition_failed(self):
        cname = self.containers[0]
        oname, odata = self.upload_object(cname, length=1024)[:-1]

        # perform get with If-Match
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.get(url, HTTP_IF_MATCH=get_random_data(8))
        self.assertEqual(r.status_code, 412)

    def test_if_none_match_without_md5(self):
        # upload object
        cname = self.containers[0]
        oname, odata = self.upload_object(cname, length=1024)[:-1]

        if pithos_settings.UPDATE_MD5:
            etag = compute_md5_hash(odata)
        else:
            etag = merkle(odata)

        # perform get with If-None-Match
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.get(url, HTTP_IF_NONE_MATCH=etag)

        # assert precondition_failed
        self.assertEqual(r.status_code, 304)

        # update object data
        r = self.append_object_data(cname, oname)[-1]
        self.assertTrue(etag != r['ETag'])

        # perform get with If-None-Match
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.get(url, HTTP_IF_NONE_MATCH=etag)

        # assert get success
        self.assertEqual(r.status_code, 200)

    def test_if_none_match_star_without_md5(self):
        # upload object
        cname = self.containers[0]
        oname, odata = self.upload_object(cname, length=1024)[:-1]

        # perform get with If-None-Match with star
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.get(url, HTTP_IF_NONE_MATCH='*')

        self.assertEqual(r.status_code, 304)

    def test_if_modified_since(self):
        # upload object
        cname = self.containers[0]
        oname, odata = self.upload_object(cname, length=1024)[:-1]
        object_info = self.get_object_info(cname, oname)
        last_modified = object_info['Last-Modified']
        t1 = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])
        t1_formats = map(t1.strftime, DATE_FORMATS)

        # Check not modified since
        url = join_urls(self.pithos_path, self.user, cname, oname)
        for t in t1_formats:
            r = self.get(url, HTTP_IF_MODIFIED_SINCE=t)
            self.assertEqual(r.status_code, 304)

        _time.sleep(1)

        # update object data
        appended_data = self.append_object_data(cname, oname)[1]

        # Check modified since
        url = join_urls(self.pithos_path, self.user, cname, oname)
        for t in t1_formats:
            r = self.get(url, HTTP_IF_MODIFIED_SINCE=t)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.content, odata + appended_data)

    def test_if_modified_since_invalid_date(self):
        cname = self.containers[0]
        oname, odata = self.upload_object(cname, length=1024)[:-1]
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.get(url, HTTP_IF_MODIFIED_SINCE='Monday')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, odata)

    def test_if_not_modified_since(self):
        cname = self.containers[0]
        oname, odata = self.upload_object(cname, length=1024)[:-1]
        url = join_urls(self.pithos_path, self.user, cname, oname)
        object_info = self.get_object_info(cname, oname)
        last_modified = object_info['Last-Modified']
        t = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])

        # Check unmodified
        t1 = t + datetime.timedelta(seconds=1)
        t1_formats = map(t1.strftime, DATE_FORMATS)
        for t in t1_formats:
            r = self.get(url, HTTP_IF_UNMODIFIED_SINCE=t)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(odata, odata)

        # modify object
        _time.sleep(2)
        self.append_object_data(cname, oname)

        object_info = self.get_object_info(cname, oname)
        last_modified = object_info['Last-Modified']
        t = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])
        t2 = t - datetime.timedelta(seconds=1)
        t2_formats = map(t2.strftime, DATE_FORMATS)

        # Check modified
        for t in t2_formats:
            r = self.get(url, HTTP_IF_UNMODIFIED_SINCE=t)
            self.assertEqual(r.status_code, 412)

        # modify account: update account meta
        _time.sleep(1)
        self.update_object_meta(cname, oname, {'foo': 'bar'})

        object_info = self.get_object_info(cname, oname)
        last_modified = object_info['Last-Modified']
        t = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])
        t3 = t - datetime.timedelta(seconds=1)
        t3_formats = map(t3.strftime, DATE_FORMATS)

        # Check modified
        for t in t3_formats:
            r = self.get(url, HTTP_IF_UNMODIFIED_SINCE=t)
            self.assertEqual(r.status_code, 412)

    def test_if_unmodified_since(self):
        cname = self.containers[0]
        oname, odata = self.upload_object(cname, length=1024)[:-1]
        url = join_urls(self.pithos_path, self.user, cname, oname)
        object_info = self.get_object_info(cname, oname)
        last_modified = object_info['Last-Modified']
        t = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])
        t = t + datetime.timedelta(seconds=1)
        t_formats = map(t.strftime, DATE_FORMATS)

        for tf in t_formats:
            r = self.get(url, HTTP_IF_UNMODIFIED_SINCE=tf)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.content, odata)

    def test_if_unmodified_since_precondition_failed(self):
        cname = self.containers[0]
        oname, odata = self.upload_object(cname, length=1024)[:-1]
        url = join_urls(self.pithos_path, self.user, cname, oname)
        object_info = self.get_object_info(cname, oname)
        last_modified = object_info['Last-Modified']
        t = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])
        t = t - datetime.timedelta(seconds=1)
        t_formats = map(t.strftime, DATE_FORMATS)

        for tf in t_formats:
            r = self.get(url, HTTP_IF_UNMODIFIED_SINCE=tf)
            self.assertEqual(r.status_code, 412)

    def test_hashes(self):
        l = random.randint(2, 5) * pithos_settings.BACKEND_BLOCK_SIZE
        cname = self.containers[0]
        oname, odata = self.upload_object(cname, length=l)[:-1]
        size = len(odata)

        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.get('%s?format=json&hashmap' % url)
        self.assertEqual(r.status_code, 200)
        body = json.loads(r.content)

        hashes = body['hashes']
        block_size = body['block_size']
        block_hash = body['block_hash']
        block_num = size / block_size if size / block_size == 0 else\
            size / block_size + 1
        self.assertTrue(len(hashes), block_num)
        i = 0
        for h in hashes:
            start = i * block_size
            end = (i + 1) * block_size
            hash = merkle(odata[start:end], int(block_size), block_hash)
            self.assertEqual(h, hash)
            i += 1


class ObjectPut(PithosAPITest):
    def setUp(self):
        PithosAPITest.setUp(self)
        self.container = get_random_data(8)
        self.create_container(self.container)

    def test_upload(self):
        cname = self.container
        oname = get_random_data(8)
        data = get_random_data(length=1024)
        meta = {'test': 'test1'}
        headers = dict(('HTTP_X_OBJECT_META_%s' % k.upper(), v)
                       for k, v in meta.iteritems())
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.put(url, data=data, content_type='application/pdf', **headers)
        self.assertEqual(r.status_code, 201)
        self.assertTrue('ETag' in r)
        self.assertTrue('X-Object-Version' in r)

        info = self.get_object_info(cname, oname)

        # assert object meta
        self.assertTrue('X-Object-Meta-Test' in info)
        self.assertEqual(info['X-Object-Meta-Test'], 'test1')

        # assert content-type
        self.assertEqual(info['content-type'], 'application/pdf')

        # assert uploaded content
        r = self.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, data)

    def test_maximum_upload_size_exceeds(self):
        cname = self.container
        oname = get_random_data(8)

#        info = self.get_account_info()
#        length = int(info['X-Account-Policy-Quota']) + 1
#        data = get_random_data(length)
#        url = join_urls(self.pithos_path, self.user, cname, oname)
#        r = self.put(url, data=data)
#        self.assertEqual(r.status_code, 413)

        # set container quota to 100
        url = join_urls(self.pithos_path, self.user, cname)
        r = self.post(url, HTTP_X_CONTAINER_POLICY_QUOTA='100')
        self.assertEqual(r.status_code, 202)

        info = self.get_container_info(cname)
        length = int(info['X-Container-Policy-Quota']) + 1

        data = get_random_data(length)
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.put(url, data=data)
        self.assertEqual(r.status_code, 413)

    def test_upload_with_name_containing_slash(self):
        cname = self.container
        oname = '/%s' % get_random_data(8)
        data = get_random_data(1024)
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.put(url, data=data)
        self.assertEqual(r.status_code, 201)
        self.assertTrue('ETag' in r)
        self.assertTrue('X-Object-Version' in r)

        r = self.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, data)

    def test_upload_unprocessable_entity(self):
        cname = self.container
        oname = get_random_data(8)
        data = get_random_data(1024)
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.put(url, data=data, HTTP_ETAG='123')
        self.assertEqual(r.status_code, 422)

#    def test_chunked_transfer(self):
#        cname = self.container
#        oname = '/%s' % get_random_data(8)
#        data = get_random_data(1024)
#        url = join_urls(self.pithos_path, self.user, cname, oname)
#        r = self.put(url, data=data, HTTP_TRANSFER_ENCODING='chunked')
#        self.assertEqual(r.status_code, 201)
#        self.assertTrue('ETag' in r)
#        self.assertTrue('X-Object-Version' in r)

    def test_manifestation(self):
        cname = self.container
        prefix = 'myobject/'
        data = ''
        for i in range(random.randint(2, 10)):
            part = '%s%d' % (prefix, i)
            data += self.upload_object(cname, oname=part)[1]

        manifest = '%s/%s' % (cname, prefix)
        oname = get_random_data(8)
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.put(url, data='', HTTP_X_OBJECT_MANIFEST=manifest)
        self.assertEqual(r.status_code, 201)

        # assert object exists
        r = self.get(url)
        self.assertEqual(r.status_code, 200)

        # assert its content
        self.assertEqual(r.content, data)

        # invalid manifestation
        invalid_manifestation = '%s/%s' % (cname, get_random_data(8))
        self.put(url, data='', HTTP_X_OBJECT_MANIFEST=invalid_manifestation)
        r = self.get(url)
        self.assertEqual(r.content, '')

    def test_create_zero_length_object(self):
        cname = self.container
        oname = get_random_data(8)
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.put(url, data='')
        self.assertEqual(r.status_code, 201)

        r = self.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(int(r['Content-Length']), 0)
        self.assertEqual(r.content, '')

        r = self.get('%s?hashmap=&format=json' % url)
        self.assertEqual(r.status_code, 200)
        body = json.loads(r.content)
        hashes = body['hashes']
        block_size = body['block_size']
        block_hash = body['block_hash']
        hash = merkle('', int(block_size), block_hash)
        self.assertEqual(hashes, [hash])

    def test_create_object_by_hashmap(self):
        cname = self.container
        block_size = pithos_settings.BACKEND_BLOCK_SIZE

        # upload an object
        oname, data = self.upload_object(cname, length=block_size + 1)[:-1]
        # get it hashmap
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.get('%s?hashmap=&format=json' % url)

        oname = get_random_data(8)
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.put('%s?hashmap=' % url, data=r.content)
        self.assertEqual(r.status_code, 201)

        r = self.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, data)


class ObjectCopy(PithosAPITest):
    def setUp(self):
        PithosAPITest.setUp(self)
        self.container = 'c1'
        self.create_container(self.container)
        self.object, self.data = self.upload_object(self.container)[:-1]

        url = join_urls(
            self.pithos_path, self.user, self.container, self.object)
        r = self.head(url)
        self.etag = r['X-Object-Hash']

    def test_copy(self):
        with AssertMappingInvariant(self.get_object_info, self.container,
                                    self.object):
            # copy object
            oname = get_random_data(8)
            url = join_urls(self.pithos_path, self.user, self.container, oname)
            r = self.put(url, data='', HTTP_X_OBJECT_META_TEST='testcopy',
                         HTTP_X_COPY_FROM='/%s/%s' % (
                             self.container, self.object))

            # assert copy success
            self.assertEqual(r.status_code, 201)

            # assert access the new object
            r = self.head(url)
            self.assertEqual(r.status_code, 200)
            self.assertTrue('X-Object-Meta-Test' in r)
            self.assertEqual(r['X-Object-Meta-Test'], 'testcopy')

            # assert etag is the same
            self.assertTrue('X-Object-Hash' in r)
            self.assertEqual(r['X-Object-Hash'], self.etag)

    def test_copy_from_different_container(self):
        cname = 'c2'
        self.create_container(cname)
        with AssertMappingInvariant(self.get_object_info, self.container,
                                    self.object):
            oname = get_random_data(8)
            url = join_urls(self.pithos_path, self.user, cname, oname)
            r = self.put(url, data='', HTTP_X_OBJECT_META_TEST='testcopy',
                         HTTP_X_COPY_FROM='/%s/%s' % (
                             self.container, self.object))

            # assert copy success
            self.assertEqual(r.status_code, 201)

            # assert access the new object
            r = self.head(url)
            self.assertEqual(r.status_code, 200)
            self.assertTrue('X-Object-Meta-Test' in r)
            self.assertEqual(r['X-Object-Meta-Test'], 'testcopy')

            # assert etag is the same
            self.assertTrue('X-Object-Hash' in r)
            self.assertEqual(r['X-Object-Hash'], self.etag)

    def test_copy_invalid(self):
        # copy from non-existent object
        oname = get_random_data(8)
        url = join_urls(self.pithos_path, self.user, self.container, oname)
        r = self.put(url, data='', HTTP_X_OBJECT_META_TEST='testcopy',
                     HTTP_X_COPY_FROM='/%s/%s' % (
                         self.container, get_random_data(8)))
        self.assertEqual(r.status_code, 404)

        # copy from non-existent container
        oname = get_random_data(8)
        url = join_urls(self.pithos_path, self.user, self.container, oname)
        r = self.put(url, data='', HTTP_X_OBJECT_META_TEST='testcopy',
                     HTTP_X_COPY_FROM='/%s/%s' % (
                         get_random_data(8), self.object))
        self.assertEqual(r.status_code, 404)

    def test_copy_dir(self):
        folder = self.create_folder(self.container)[0]
        subfolder = self.create_folder(
            self.container, oname='%s/%s' % (folder, get_random_data(8)))[0]
        objects = [subfolder]
        append = objects.append
        append(self.upload_object(self.container,
                                  '%s/%s' % (folder, get_random_data(8)),
                                  HTTP_X_OBJECT_META_DEPTH='1')[0])
        append(self.upload_object(self.container,
                                  '%s/%s' % (subfolder, get_random_data(8)),
                                  HTTP_X_OBJECT_META_DEPTH='2')[0])
        other = self.upload_object(self.container, strnextling(folder))[0]

        # copy dir
        copy_folder = self.create_folder(self.container)[0]
        url = join_urls(self.pithos_path, self.user, self.container,
                        copy_folder)
        r = self.put('%s?delimiter=/' % url, data='',
                     HTTP_X_COPY_FROM='/%s/%s' % (self.container, folder))
        self.assertEqual(r.status_code, 201)

        for obj in objects:
            # assert object exists
            url = join_urls(self.pithos_path, self.user, self.container,
                            obj.replace(folder, copy_folder))
            r = self.head(url)
            self.assertEqual(r.status_code, 200)

            # assert metadata
            meta = self.get_object_meta(self.container, obj)
            for k in meta.keys():
                self.assertTrue(k in r)
                self.assertEqual(r[k], meta[k])

        # assert other has not been created under copy folder
        url = join_urls(self.pithos_path, self.user, self.container,
                        '%s/%s' % (copy_folder,
                                   other.replace(folder, copy_folder)))
        r = self.head(url)
        self.assertEqual(r.status_code, 404)


class ObjectMove(PithosAPITest):
    def setUp(self):
        PithosAPITest.setUp(self)
        self.container = 'c1'
        self.create_container(self.container)
        self.object, self.data = self.upload_object(self.container)[:-1]

        url = join_urls(
            self.pithos_path, self.user, self.container, self.object)
        r = self.head(url)
        self.etag = r['X-Object-Hash']

    def test_move(self):
        # move object
        oname = get_random_data(8)
        url = join_urls(self.pithos_path, self.user, self.container, oname)
        r = self.put(url, data='', HTTP_X_OBJECT_META_TEST='testcopy',
                     HTTP_X_MOVE_FROM='/%s/%s' % (
                         self.container, self.object))

        # assert move success
        self.assertEqual(r.status_code, 201)

        # assert access the new object
        r = self.head(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue('X-Object-Meta-Test' in r)
        self.assertEqual(r['X-Object-Meta-Test'], 'testcopy')

        # assert etag is the same
        self.assertTrue('X-Object-Hash' in r)

        # assert the initial object has been deleted
        url = join_urls(self.pithos_path, self.user, self.container,
                        self.object)
        r = self.head(url)
        self.assertEqual(r.status_code, 404)

    def test_move_dir(self):
        folder = self.create_folder(self.container)[0]
        subfolder = self.create_folder(
            self.container, oname='%s/%s' % (folder, get_random_data(8)))[0]
        objects = [subfolder]
        append = objects.append
        meta = {}
        meta[objects[0]] = {}
        append(self.upload_object(self.container,
                                  '%s/%s' % (folder, get_random_data(8)),
                                  HTTP_X_OBJECT_META_DEPTH='1')[0])
        meta[objects[1]] = {'X-Object-Meta-Depth': '1'}
        append(self.upload_object(self.container,
                                  '%s/%s' % (subfolder, get_random_data(8)),
                                  HTTP_X_OBJECT_META_DEPTH='2')[0])
        meta[objects[1]] = {'X-Object-Meta-Depth': '2'}
        other = self.upload_object(self.container, strnextling(folder))[0]

        # move dir
        copy_folder = self.create_folder(self.container)[0]
        url = join_urls(self.pithos_path, self.user, self.container,
                        copy_folder)
        r = self.put('%s?delimiter=/' % url, data='',
                     HTTP_X_MOVE_FROM='/%s/%s' % (self.container, folder))
        self.assertEqual(r.status_code, 201)

        for obj in objects:
            # assert initial object does not exist
            url = join_urls(self.pithos_path, self.user, self.container, obj)
            r = self.head(url)
            self.assertEqual(r.status_code, 404)

            # assert new object was created
            url = join_urls(self.pithos_path, self.user, self.container,
                            obj.replace(folder, copy_folder))
            r = self.head(url)
            self.assertEqual(r.status_code, 200)

#            # assert metadata
#            for k in meta[obj].keys():
#                self.assertTrue(k in r)
#                self.assertEqual(r[k], meta[obj][k])

        # assert other has not been created under copy folder
        url = join_urls(self.pithos_path, self.user, self.container,
                        '%s/%s' % (copy_folder,
                                   other.replace(folder, copy_folder)))
        r = self.head(url)
        self.assertEqual(r.status_code, 404)


class ObjectPost(PithosAPITest):
    def setUp(self):
        PithosAPITest.setUp(self)
        self.container = 'c1'
        self.create_container(self.container)
        self.object, self.object_data = self.upload_object(self.container)[:2]

    def test_update_meta(self):
        with AssertUUidInvariant(self.get_object_info,
                                 self.container,
                                 self.object):
            # update metadata
            d = {'a' * 114: 'b' * 256}
            kwargs = dict(('HTTP_X_OBJECT_META_%s' % k, v) for
                          k, v in d.items())
            url = join_urls(self.pithos_path, self.user, self.container,
                            self.object)
            r = self.post(url, content_type='', **kwargs)
            self.assertEqual(r.status_code, 202)

            # assert metadata have been updated
            meta = self.get_object_meta(self.container, self.object)

            for k, v in d.items():
                key = 'X-Object-Meta-%s' % k.title()
                self.assertTrue(key in meta)
                self.assertTrue(meta[key], v)

            # Header key too large
            d = {'a' * 115: 'b' * 256}
            kwargs = dict(('HTTP_X_OBJECT_META_%s' % k, v) for
                          k, v in d.items())
            r = self.post(url, content_type='', **kwargs)
            self.assertEqual(r.status_code, 400)

            # Header value too large
            d = {'a' * 114: 'b' * 257}
            kwargs = dict(('HTTP_X_OBJECT_META_%s' % k, v) for
                          k, v in d.items())
            r = self.post(url, content_type='', **kwargs)
            self.assertEqual(r.status_code, 400)

#            # Check utf-8 meta
#            d = {'α' * (114 / 2): 'β' * (256 / 2)}
#            kwargs = dict(('HTTP_X_OBJECT_META_%s' % quote(k), quote(v)) for
#                          k, v in d.items())
#            url = join_urls(self.pithos_path, self.user, self.container,
#                            self.object)
#            r = self.post(url, content_type='', **kwargs)
#            self.assertEqual(r.status_code, 202)
#
#            # assert metadata have been updated
#            meta = self.get_object_meta(self.container, self.object)
#
#            for k, v in d.items():
#                key = 'X-Object-Meta-%s' % k.title()
#                self.assertTrue(key in meta)
#                self.assertTrue(meta[key], v)
#
#            # Header key too large
#            d = {'α' * 114: 'β' * (256 / 2)}
#            kwargs = dict(('HTTP_X_OBJECT_META_%s' % quote(k), quote(v)) for
#                          k, v in d.items())
#            r = self.post(url, content_type='', **kwargs)
#            self.assertEqual(r.status_code, 400)
#
#            # Header value too large
#            d = {'α' * 114: 'β' * 256}
#            kwargs = dict(('HTTP_X_OBJECT_META_%s' % quote(k), quote(v)) for
#                          k, v in d.items())
#            r = self.udpate(url, content_type='', **kwargs)
#            self.assertEqual(r.status_code, 400)

    def test_update_object(self):
        block_size = pithos_settings.BACKEND_BLOCK_SIZE
        oname, odata = self.upload_object(
            self.container, length=random.randint(
                block_size + 1, 2 * block_size))[:2]

        length = len(odata)
        first_byte_pos = random.randint(1, block_size)
        last_byte_pos = random.randint(block_size + 1, length - 1)
        range = 'bytes %s-%s/%s' % (first_byte_pos, last_byte_pos, length)
        kwargs = {'content_type': 'application/octet-stream',
                  'HTTP_CONTENT_RANGE': range}

        url = join_urls(self.pithos_path, self.user, self.container, oname)
        partial = last_byte_pos - first_byte_pos + 1
        data = get_random_data(partial)
        r = self.post(url, data=data, **kwargs)

        self.assertEqual(r.status_code, 204)
        self.assertTrue('ETag' in r)
        updated_data = odata.replace(odata[first_byte_pos: last_byte_pos + 1],
                                     data)
        if pithos_settings.UPDATE_MD5:
            etag = compute_md5_hash(updated_data)
        else:
            etag = merkle(updated_data)
        #self.assertEqual(r['ETag'], etag)

        # check modified object
        r = self.get(url)

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, updated_data)
        self.assertEqual(etag, r['ETag'])

    def test_update_object_divided_by_blocksize(self):
        block_size = pithos_settings.BACKEND_BLOCK_SIZE
        oname, odata = self.upload_object(self.container,
                                          length=2 * block_size)[:2]

        length = len(odata)
        first_byte_pos = block_size
        last_byte_pos = 2 * block_size - 1
        range = 'bytes %s-%s/%s' % (first_byte_pos, last_byte_pos, length)
        kwargs = {'content_type': 'application/octet-stream',
                  'HTTP_CONTENT_RANGE': range}

        url = join_urls(self.pithos_path, self.user, self.container, oname)
        partial = last_byte_pos - first_byte_pos + 1
        data = get_random_data(partial)
        r = self.post(url, data=data, **kwargs)

        self.assertEqual(r.status_code, 204)
        self.assertTrue('ETag' in r)
        updated_data = odata.replace(odata[first_byte_pos: last_byte_pos + 1],
                                     data)
        if pithos_settings.UPDATE_MD5:
            etag = compute_md5_hash(updated_data)
        else:
            etag = merkle(updated_data)
        #self.assertEqual(r['ETag'], etag)

        # check modified object
        r = self.get(url)

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, updated_data)
        self.assertEqual(etag, r['ETag'])

    def test_update_object_invalid_content_length(self):
        block_size = pithos_settings.BACKEND_BLOCK_SIZE
        oname, odata = self.upload_object(
            self.container, length=random.randint(
                block_size + 1, 2 * block_size))[:2]

        length = len(odata)
        first_byte_pos = random.randint(1, block_size)
        last_byte_pos = random.randint(block_size + 1, length - 1)
        partial = last_byte_pos - first_byte_pos + 1
        data = get_random_data(partial)
        range = 'bytes %s-%s/%s' % (first_byte_pos, last_byte_pos, length)
        kwargs = {'content_type': 'application/octet-stream',
                  'HTTP_CONTENT_RANGE': range,
                  'CONTENT_LENGTH': partial + 1}

        url = join_urls(self.pithos_path, self.user, self.container, oname)
        r = self.post(url, data=data, **kwargs)

        self.assertEqual(r.status_code, 400)

    def test_update_object_invalid_range(self):
        block_size = pithos_settings.BACKEND_BLOCK_SIZE
        oname, odata = self.upload_object(
            self.container, length=random.randint(block_size + 1,
                                                  2 * block_size))[:2]

        length = len(odata)
        first_byte_pos = random.randint(1, block_size)
        last_byte_pos = first_byte_pos - 1
        range = 'bytes %s-%s/%s' % (first_byte_pos, last_byte_pos, length)
        kwargs = {'content_type': 'application/octet-stream',
                  'HTTP_CONTENT_RANGE': range}

        url = join_urls(self.pithos_path, self.user, self.container, oname)
        r = self.post(url, data=get_random_data(1024), **kwargs)

        self.assertEqual(r.status_code, 416)

    def test_update_object_out_of_limits(self):
        block_size = pithos_settings.BACKEND_BLOCK_SIZE
        oname, odata = self.upload_object(
            self.container, length=random.randint(block_size + 1,
                                                  2 * block_size))[:2]

        length = len(odata)
        first_byte_pos = random.randint(1, block_size)
        last_byte_pos = length + 1
        range = 'bytes %s-%s/%s' % (first_byte_pos, last_byte_pos, length)
        kwargs = {'content_type': 'application/octet-stream',
                  'HTTP_CONTENT_RANGE': range}

        url = join_urls(self.pithos_path, self.user, self.container, oname)
        r = self.post(url, data=get_random_data(1024), **kwargs)

        self.assertEqual(r.status_code, 416)

    def test_append(self):
        length = random.randint(1, 1024)
        data = get_random_data(length)
        url = join_urls(self.pithos_path, self.user, self.container,
                        self.object)
        r = self.post(url, data=data, content_type='application/octet-stream',
                      HTTP_CONTENT_LENGTH=str(length),
                      HTTP_CONTENT_RANGE='bytes */*')
        self.assertEqual(r.status_code, 204)

        r = self.get(url)
        content = r.content
        self.assertEqual(len(content), len(self.object_data) + length)
        self.assertEqual(content, self.object_data + data)

    def test_update_with_chunked_transfer(self):
        length = random.randint(1, 1024)
        data = get_random_data(length)

        url = join_urls(self.pithos_path, self.user, self.container,
                        self.object)
        r = self.post(url, data=data, content_type='application/octet-stream',
                      HTTP_CONTENT_RANGE='bytes 0-/*',
                      HTTP_TRANSFER_ENCODING='chunked')
        self.assertEqual(r.status_code, 204)

        # check modified object
        r = self.get(url)
        content = r.content
        self.assertEqual(content[0:length], data)
        self.assertEqual(content[length:], self.object_data[length:])

    def test_update_from_other_object(self):
        src = self.object
        dest = get_random_data(8)

        url = join_urls(self.pithos_path, self.user, self.container, src)
        r = self.get(url)
        source_data = r.content
        source_meta = self.get_object_info(self.container, src)

        # update zero length object
        url = join_urls(self.pithos_path, self.user, self.container, dest)
        r = self.put(url, data='')
        self.assertEqual(r.status_code, 201)

        r = self.post(url,
                      HTTP_CONTENT_RANGE='bytes */*',
                      HTTP_X_SOURCE_OBJECT='/%s/%s' % (self.container, src))
        self.assertEqual(r.status_code, 204)

        r = self.get(url)
        dest_data = r.content
        dest_meta = self.get_object_info(self.container, dest)

        self.assertEqual(source_data, dest_data)
        #self.assertEqual(source_meta['ETag'], dest_meta['ETag'])
        self.assertEqual(source_meta['X-Object-Hash'],
                         dest_meta['X-Object-Hash'])
        self.assertTrue(
            source_meta['X-Object-UUID'] != dest_meta['X-Object-UUID'])

    def test_update_range_from_other_object(self):
        src = self.object
        dest = get_random_data(8)

        url = join_urls(self.pithos_path, self.user, self.container, src)
        r = self.get(url)
        source_data = r.content

        # update zero length object
        url = join_urls(self.pithos_path, self.user, self.container, dest)
        length = random.randint(1, 1024)
        r = self.put(url, data=get_random_data(length))
        self.assertEqual(r.status_code, 201)

        offset = random.randint(1, length - 2)
        upto = random.randint(offset, length - 1)
        r = self.post(url,
                      HTTP_CONTENT_RANGE='bytes %s-%s/*' % (offset, upto),
                      HTTP_X_SOURCE_OBJECT='/%s/%s' % (self.container, src))
        self.assertEqual(r.status_code, 204)

        r = self.get(url)
        content = r.content
        self.assertEqual(content[:offset], source_data[:offset])
        self.assertEqual(content[offset:upto + 1],
                         source_data[:upto - offset + 1])
        self.assertEqual(content[upto + 1:], source_data[upto + 1:])


class ObjectDelete(PithosAPITest):
    def setUp(self):
        PithosAPITest.setUp(self)
        self.container = 'c1'
        self.create_container(self.container)
        self.object, self.object_data = self.upload_object(self.container)[:2]

    def test_delete(self):
        url = join_urls(self.pithos_path, self.user, self.container,
                        self.object)
        r = self.delete(url)
        self.assertEqual(r.status_code, 204)

        r = self.head(url)
        self.assertEqual(r.status_code, 404)

    def test_delete_non_existent(self):
        url = join_urls(self.pithos_path, self.user, self.container,
                        get_random_data(8))
        r = self.delete(url)
        self.assertEqual(r.status_code, 404)

    def test_delete_dir(self):
        folder = self.create_folder(self.container)[0]
        subfolder = self.create_folder(
            self.container, oname='%s/%s' % (folder, get_random_data(8)))[0]
        objects = [subfolder]
        append = objects.append
        meta = {}
        meta[objects[0]] = {}
        append(self.upload_object(self.container,
                                  '%s/%s' % (folder, get_random_data(8)),
                                  HTTP_X_OBJECT_META_DEPTH='1')[0])
        meta[objects[1]] = {'X-Object-Meta-Depth': '1'}
        append(self.upload_object(self.container,
                                  '%s/%s' % (subfolder, get_random_data(8)),
                                  HTTP_X_OBJECT_META_DEPTH='2')[0])
        meta[objects[1]] = {'X-Object-Meta-Depth': '2'}
        other = self.upload_object(self.container, strnextling(folder))[0]

        # move dir
        url = join_urls(self.pithos_path, self.user, self.container, folder)
        r = self.delete('%s?delimiter=/' % url)
        self.assertEqual(r.status_code, 204)

        for obj in objects:
            # assert object does not exist
            url = join_urls(self.pithos_path, self.user, self.container, obj)
            r = self.head(url)
            self.assertEqual(r.status_code, 404)

        # assert other has not been deleted
        url = join_urls(self.pithos_path, self.user, self.container, other)
        r = self.head(url)
        self.assertEqual(r.status_code, 200)
