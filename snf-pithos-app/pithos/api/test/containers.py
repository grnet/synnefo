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

from pithos.api.test import (PithosAPITest, DATE_FORMATS, o_names,
                             pithos_settings, pithos_test_settings)
from pithos.api.test.util import strnextling, get_random_data, get_random_name

from synnefo.lib import join_urls

import django.utils.simplejson as json
from django.http import urlencode

from xml.dom import minidom
from urllib import quote
import time as _time

import random
import datetime


class ContainerHead(PithosAPITest):
    def test_get_meta(self):
        self.create_container('apples')

        # populate with objects
        objects = {}
        for i in range(random.randint(1, 100)):

            # upload object
            meta = {'foo%s' % i: 'bar'}
            name, data, resp = self.upload_object('apples', **meta)
            objects[name] = data

        t1 = datetime.datetime.utcnow()
        url = join_urls(self.pithos_path, self.user, 'apples')
        r = self.head(url)
        self.assertEqual(int(r['X-Container-Object-Count']), len(objects))
        self.assertEqual(int(r['X-Container-Bytes-Used']),
                         sum([len(i) for i in objects.values()]))
        self.assertTrue('X-Container-Block-Size' in r)
        self.assertTrue('X-Container-Block-Hash' in r)
        self.assertTrue('X-Container-Until-Timestamp' not in r)
        self.assertEqual(r['X-Container-Policy-Versioning'], 'auto')
        self.assertEqual(int(r['X-Container-Policy-Quota']), 0)
        t2 = datetime.datetime.strptime(r['Last-Modified'], DATE_FORMATS[2])
        delta = (t2 - t1)
        threashold = datetime.timedelta(seconds=1)
        self.assertTrue(delta < threashold)
        self.assertTrue(r['X-Container-Object-Meta'])
        (self.assertTrue('foo%s' % i in r['X-Container-Object-Meta'])
            for i in range(len(objects)))

    def test_get_container_meta_until(self):
        self.create_container('apples')

        # populate with objects
        objects = {}
        metalist = []
        for i in range(random.randint(1, 100)):
            # upload object
            metakey = 'Foo%s' % i
            meta = {metakey: 'bar'}
            name, data, resp = self.upload_object('apples', **meta)
            objects[name] = data
            metalist.append(metakey) 

        self.update_container_meta('apples', {'foo': 'bar'})

        container_info = self.get_container_info('apples')
        t = datetime.datetime.strptime(container_info['Last-Modified'],
                                       DATE_FORMATS[2])
        t1 = t + datetime.timedelta(seconds=1)
        until = int(_time.mktime(t1.timetuple()))

        _time.sleep(2)

        for i in range(random.randint(1, 100)):
            # upload object
            meta = {'foo%s' % i: 'bar'}
            self.upload_object('apples', **meta)

        self.update_container_meta('apples', {'quality': 'AAA'})

        container_info = self.get_container_info('apples')
        self.assertTrue('X-Container-Meta-Quality' in container_info)
        self.assertTrue('X-Container-Meta-Foo' in container_info)
        self.assertTrue('X-Container-Object-Count' in container_info)
        self.assertTrue(int(container_info['X-Container-Object-Count']) > len(objects))
        self.assertTrue('X-Container-Bytes-Used' in container_info)

        t = datetime.datetime.strptime(container_info['Last-Modified'],
                                       DATE_FORMATS[-1])
        last_modified = int(_time.mktime(t.timetuple()))
        assert until < last_modified

        container_info = self.get_container_info('apples', until=until)
        self.assertTrue('X-Container-Meta-Quality' not in container_info)
        self.assertTrue('X-Container-Meta-Foo' in container_info)
        self.assertTrue('X-Container-Until-Timestamp' in container_info)
        t = datetime.datetime.strptime(
            container_info['X-Container-Until-Timestamp'], DATE_FORMATS[2])
        self.assertTrue(int(_time.mktime(t1.timetuple())) <= until)
        self.assertTrue('X-Container-Object-Count' in container_info)
        self.assertEqual(int(container_info['X-Container-Object-Count']), len(objects))
        self.assertTrue('X-Container-Bytes-Used' in container_info)
        self.assertEqual(int(container_info['X-Container-Bytes-Used']),
                         sum([len(data) for data in objects.values()]))
        self.assertTrue('X-Container-Object-Meta' in container_info)
        self.assertEqual(container_info['X-Container-Object-Meta'],
                         ','.join(sorted(metalist))) 


class ContainerGet(PithosAPITest):
    def setUp(self):
        PithosAPITest.setUp(self)

        self.cnames = ['pears', 'apples']
        self.objects = {}
        for c in self.cnames:
            self.create_container(c)

        self.objects['pears'] = {}
        for o in o_names[:8]:
            name, data, resp = self.upload_object('pears', o)
            self.objects['pears'][name] = data
        self.objects['apples'] = {}
        for o in o_names[8:]:
            name, data, resp = self.upload_object('apples', o)
            self.objects['apples'][name] = data

    def test_list_until(self):
        account_info = self.get_account_info()
        t = datetime.datetime.strptime(account_info['Last-Modified'],
                                       DATE_FORMATS[2])
        t1 = t + datetime.timedelta(seconds=1)
        until = int(_time.mktime(t1.timetuple()))

        _time.sleep(2)

        cname = self.cnames[0]
        self.upload_object(cname)

        url = join_urls(self.pithos_path, self.user, cname)
        r = self.get('%s?until=%s' % (url, until))
        self.assertTrue(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertEqual(objects,
                         sorted(self.objects[cname].keys()))

        r = self.get('%s?until=%s&format=json' % (url, until))
        self.assertTrue(r.status_code, 200)
        try:
            objects = json.loads(r.content)
        except:
            self.fail('json format expected')
        self.assertEqual([o['name'] for o in objects],
                         sorted(self.objects[cname].keys()))

    def test_list_shared(self):
        # share an object
        cname = self.cnames[0]
        onames = self.objects[cname].keys()
        oname = onames.pop()
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_SHARING='read=*')
        self.assertEqual(r.status_code, 202)

        # publish another object
        other = onames.pop()
        url = join_urls(self.pithos_path, self.user, cname, other)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)

        # list shared and assert only the shared object is returned
        url = join_urls(self.pithos_path, self.user, cname)
        r = self.get('%s?shared=' % url)
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertEqual([oname], objects)

        # list detailed shared and assert only the shared object is returned
        url = join_urls(self.pithos_path, self.user, cname)
        r = self.get('%s?shared=&format=json' % url)
        self.assertEqual(r.status_code, 200)
        try:
            objects = json.loads(r.content)
        except:
            self.fail('json format expected')
        self.assertEqual([oname], [o['name'] for o in objects])
        self.assertTrue('x_object_sharing' in objects[0])
        self.assertTrue('x_object_public' not in objects[0])

        # publish the shared object and assert it is still listed in the
        # shared objects
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)
        url = join_urls(self.pithos_path, self.user, cname)
        r = self.get('%s?shared=&format=json' % url)
        self.assertEqual(r.status_code, 200)
        try:
            objects = json.loads(r.content)
        except:
            self.fail('json format expected')
        self.assertEqual([oname], [o['name'] for o in objects])
        self.assertTrue('x_object_sharing' in objects[0])
        self.assertTrue('x_object_public' in objects[0])

        # create child object
        descendant = strnextling(oname)
        self.upload_object(cname, descendant)
        # request shared and assert child obejct is not listed
        url = join_urls(self.pithos_path, self.user, cname)
        r = self.get('%s?shared=' % url)
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertTrue(oname in objects)
        self.assertTrue(descendant not in objects)

        # check folder inheritance
        oname, _ = self.create_folder(cname, HTTP_X_OBJECT_SHARING='read=*')
        # create child object
        descendant = '%s/%s' % (oname, get_random_name())
        self.upload_object(cname, descendant)
        # request shared
        url = join_urls(self.pithos_path, self.user, cname)
        r = self.get('%s?shared=' % url)
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertTrue(oname in objects)
        self.assertTrue(descendant in objects)

    def test_list_public(self):
        # publish an object
        cname = self.cnames[0]
        onames = self.objects[cname].keys()
        oname = onames.pop()
        other = onames.pop()

        # publish an object
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)

        # share another
        url = join_urls(self.pithos_path, self.user, cname, other)
        r = self.post(url, content_type='', HTTP_X_OBJECT_SHARING='read=alice')
        self.assertEqual(r.status_code, 202)

        # list public and assert only the public object is returned
        url = join_urls(self.pithos_path, self.user, cname)
        r = self.get('%s?public=' % url)
        objects = r.content.split('\n')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(oname in r.content.split('\n'))
        (self.assertTrue(object not in objects) for object in o_names[1:])

        # list detailed public and assert only the public object is returned
        url = join_urls(self.pithos_path, self.user, cname)
        r = self.get('%s?public=&format=json' % url)
        self.assertEqual(r.status_code, 200)
        try:
            objects = json.loads(r.content)
        except:
            self.fail('json format expected')
        self.assertEqual([oname], [obj['name'] for obj in objects])
        self.assertTrue('x_object_sharing' not in objects[0])
        self.assertTrue('x_object_public' in objects[0])

        # share the public object and assert it is still listed in the
        # public objects
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_SHARING='read=alice')
        self.assertEqual(r.status_code, 202)
        url = join_urls(self.pithos_path, self.user, cname)
        r = self.get('%s?public=&format=json' % url)
        self.assertEqual(r.status_code, 200)
        try:
            objects = json.loads(r.content)
        except:
            self.fail('json format expected')
        self.assertEqual([oname], [obj['name'] for obj in objects])
        self.assertTrue('x_object_sharing' in objects[0])
        self.assertTrue('x_object_public' in objects[0])

        url = join_urls(self.pithos_path, self.user, cname)

        # Assert listing the container public contents is forbidden to not
        # shared users
        r = self.get('%s?public=&format=json' % url, user='bob')
        self.assertEqual(r.status_code, 403)

        # Assert forbidden public object listing to shared users
        r = self.get('%s?public=&format=json' % url, user='alice')
        self.assertEqual(r.status_code, 403)

        # create child object
        descendant = strnextling(oname)
        self.upload_object(cname, descendant)
        # request public and assert child obejct is not listed
        r = self.get('%s?public=' % url)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(oname in objects)
        (self.assertTrue(o not in objects) for o in o_names[1:])

        # test folder inheritance
        oname, _ = self.create_folder(cname, HTTP_X_OBJECT_PUBLIC='true')
        # create child object
        descendant = '%s/%s' % (oname, get_random_name())
        self.upload_object(cname, descendant)
        # request public
        r = self.get('%s?public=' % url)
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        self.assertTrue(oname in objects)
        self.assertTrue(descendant not in objects)

    def test_list_shared_public(self):
        # publish an object
        cname = self.cnames[0]
        container_url = join_urls(self.pithos_path, self.user, cname)
        onames = self.objects[cname].keys()
        oname = onames.pop()
        url = join_urls(container_url, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)

        # share another
        other = onames.pop()
        url = join_urls(container_url, other)
        r = self.post(url, content_type='', HTTP_X_OBJECT_SHARING='read=alice')
        self.assertEqual(r.status_code, 202)

        # list shared and public objects and assert object is listed
        r = self.get('%s?shared=&public=&format=json' % container_url)
        self.assertEqual(r.status_code, 200)
        objects = json.loads(r.content)
        self.assertEqual([o['name'] for o in objects], sorted([oname, other]))
        for o in objects:
            if o['name'] == oname:
                self.assertTrue('x_object_public' in o.keys())
            elif o['name'] == other:
                self.assertTrue('x_object_sharing' in o.keys())

        # assert not listing shared and public to a not shared user
        r = self.get('%s?shared=&public=&format=json' % container_url,
                     user='bob')
        self.assertEqual(r.status_code, 403)

        # assert not listing public to a shared user
        r = self.get('%s?shared=&public=&format=json' % container_url,
                     user='alice')
        self.assertEqual(r.status_code, 403)

        # create child object
        descendant = strnextling(oname)
        self.upload_object(cname, descendant)
        # request public and assert child obejct is not listed
        r = self.get('%s?shared=&public=' % container_url)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(oname in objects)
        (self.assertTrue(o not in objects) for o in o_names[1:])

        # test folder inheritance
        oname, _ = self.create_folder(cname, HTTP_X_OBJECT_PUBLIC='true')
        # create child object
        descendant = '%s/%s' % (oname, get_random_name())
        self.upload_object(cname, descendant)
        # request public
        r = self.get('%s?shared=&public=' % container_url)
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertTrue(oname in objects)
        self.assertTrue(descendant not in objects)

    def test_list_objects(self):
        cname = self.cnames[0]
        url = join_urls(self.pithos_path, self.user, cname)
        r = self.get(url)
        self.assertTrue(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertEqual(objects, sorted(self.objects[cname].keys()))

    def test_list_objects_containing_slash(self):
        self.create_container('test')
        self.upload_object('test', quote('/objectname', ''))

        url = join_urls(self.pithos_path, self.user, 'test')

        r = self.get(url)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertEqual(objects, ['/objectname'])

        r = self.get('%s?format=json' % url)
        try:
            objects = json.loads(r.content)
        except:
            self.fail('json format expected')
        self.assertEqual([o['name'] for o in objects], ['/objectname'])

        r = self.get('%s?format=xml' % url)
        try:
            objects = minidom.parseString(r.content)
        except:
            self.fail('xml format expected')
        self.assertEqual(
            [n.firstChild.data for n in objects.getElementsByTagName('name')],
            ['/objectname'])

    def test_list_objects_with_limit_marker(self):
        cname = self.cnames[0]
        url = join_urls(self.pithos_path, self.user, cname)
        r = self.get('%s?limit=qwert' % url)
        self.assertTrue(r.status_code != 500)

        r = self.get('%s?limit=2' % url)
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')

        onames = sorted(self.objects[cname].keys())
        self.assertEqual(objects, onames[:2])

        markers = ['How To Win Friends And Influence People.pdf',
                   'moms_birthday.jpg']
        limit = 4
        for m in markers:
            r = self.get('%s?limit=%s&marker=%s' % (url, limit, m))
            objects = r.content.split('\n')
            if '' in objects:
                objects.remove('')
            start = onames.index(m) + 1
            end = start + limit
            end = end if len(onames) >= end else len(onames)
            self.assertEqual(objects, onames[start:end])

    @pithos_test_settings(API_LIST_LIMIT=10)
    def test_list_limit_exceeds(self):
        self.create_container('container')
        url = join_urls(self.pithos_path, self.user, 'container')

        for _ in range(pithos_settings.API_LIST_LIMIT + 1):
            self.upload_object('container')

        r = self.get('%s?format=json' % url)
        try:
            objects = json.loads(r.content)
        except:
            self.fail('json format expected')
        self.assertEqual(pithos_settings.API_LIST_LIMIT,
                         len(objects))

    def test_list_pseudo_hierarchical_folders(self):
        url = join_urls(self.pithos_path, self.user, 'apples')
        r = self.get('%s?prefix=photos&delimiter=/' % url)
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertEquals(
            ['photos/animals/', 'photos/me.jpg', 'photos/plants/'],
            objects)

        r = self.get('%s?prefix=photos/animals&delimiter=/' % url)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertEquals(
            ['photos/animals/cats/', 'photos/animals/dogs/'], objects)

        r = self.get('%s?path=photos' % url)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertEquals(['photos/me.jpg'], objects)

    def test_extended_list_json(self):
        url = join_urls(self.pithos_path, self.user, 'apples')
        params = {'format': 'json', 'limit': 2, 'prefix': 'photos/animals',
                  'delimiter': '/'}
        r = self.get('%s?%s' % (url, urlencode(params)))
        self.assertEqual(r.status_code, 200)
        try:
            objects = json.loads(r.content)
        except:
            self.fail('json format expected')
        self.assertEqual(objects[0]['subdir'], 'photos/animals/cats/')
        self.assertEqual(objects[1]['subdir'], 'photos/animals/dogs/')

    def test_extended_list_xml(self):
        url = join_urls(self.pithos_path, self.user, 'apples')
        params = {'format': 'xml', 'limit': 4, 'prefix': 'photos',
                  'delimiter': '/'}
        r = self.get('%s?%s' % (url, urlencode(params)))
        self.assertEqual(r.status_code, 200)
        try:
            xml = minidom.parseString(r.content)
        except:
            self.fail('xml format expected')
        self.assert_extended(xml, 'xml', 'object', size=4)
        dirs = xml.getElementsByTagName('subdir')
        self.assertEqual(len(dirs), 2)
        self.assertEqual(dirs[0].attributes['name'].value, 'photos/animals/')
        self.assertEqual(dirs[1].attributes['name'].value, 'photos/plants/')

        objects = xml.getElementsByTagName('name')
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0].childNodes[0].data, 'photos/me.jpg')

    def test_list_meta_double_matching(self):
        # update object meta
        cname = 'apples'
        container_url = join_urls(self.pithos_path, self.user, cname)
        oname = self.objects[cname].keys().pop()
        meta = {'quality': 'aaa', 'stock': 'true'}
        headers = dict(('HTTP_X_OBJECT_META_%s' % k.upper(), v)
                       for k, v in meta.iteritems())
        object_url = join_urls(container_url, oname)
        self.post(object_url, content_type='', **headers)

        # list objects that satisfy the criteria
        r = self.get('%s?meta=Quality,Stock' % container_url)
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertEqual(objects, [oname])

    def test_list_using_meta(self):
        # update object meta
        cname = 'apples'
        container_url = join_urls(self.pithos_path, self.user, cname)

        onames = self.objects[cname].keys()
        url = join_urls(container_url, onames[0])
        r = self.post(url, content_type='', HTTP_X_OBJECT_META_QUALITY='aaa')
        self.assertEqual(r.status_code, 202)

        url = join_urls(container_url, onames[1])
        r = self.post(url, content_type='', HTTP_X_OBJECT_META_QUALITY='ab')
        self.assertEqual(r.status_code, 202)

        url = join_urls(container_url, onames[2])
        r = self.post(url, content_type='', HTTP_X_OBJECT_META_STOCK='100')
        self.assertEqual(r.status_code, 202)

        url = join_urls(container_url, onames[3])
        r = self.post(url, content_type='', HTTP_X_OBJECT_META_STOCK='200')
        self.assertEqual(r.status_code, 202)

        # test multiple existence criteria matches
        r = self.get('%s?meta=Quality,Stock' % container_url)
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertTrue(objects, sorted(onames))

        # list objects that satisfy the existence criteria
        r = self.get('%s?meta=Stock' % container_url)
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertTrue(objects, sorted(onames[2:]))

        # test case insensitive existence criteria matching
        r = self.get('%s?meta=quality' % container_url)
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertTrue(objects, sorted(onames[:2]))

        # test do not all existencecriteria match
        r = self.get('%s?meta=Quality,Foo' % container_url)
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertTrue(objects, sorted(onames[:2]))

        # test equals criteria
        r = self.get('%s?meta=%s' % (container_url, quote('Quality=aaa')))
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertTrue(objects, [onames[0]])

        # test not equals criteria
        r = self.get('%s?meta=%s' % (container_url, quote('Quality!=aaa')))
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertTrue(objects, [onames[1]])

        # test lte criteria
        r = self.get('%s?meta=%s' % (container_url, quote('Stock<=120')))
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertTrue(objects, [onames[2]])

        # test gte criteria
        r = self.get('%s?meta=%s' % (container_url, quote('Stock>=200')))
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertTrue(objects, [onames[3]])

    def test_if_modified_since(self):
        cname = 'apples'
        container_info = self.get_container_info(cname)
        last_modified = container_info['Last-Modified']
        t1 = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])
        t1_formats = map(t1.strftime, DATE_FORMATS)

        # Check not modified
        url = join_urls(self.pithos_path, self.user, cname)
        for t in t1_formats:
            r = self.get(url, HTTP_IF_MODIFIED_SINCE=t)
            self.assertEqual(r.status_code, 304)

        # modify account: add container
        _time.sleep(1)
        oname = self.upload_object(cname)[0]

        # Check modified
        objects = self.objects[cname].keys()
        objects.append(oname)
        for t in t1_formats:
            r = self.get(url, HTTP_IF_MODIFIED_SINCE=t)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.content.split('\n')[:-1], sorted(objects))

        container_info = self.get_container_info(cname)
        last_modified = container_info['Last-Modified']
        t2 = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])
        t2_formats = map(t2.strftime, DATE_FORMATS)

        # modify account: update account meta
        _time.sleep(1)
        self.update_container_meta(cname, {'foo': 'bar'})

        # Check modified
        for t in t2_formats:
            r = self.get(url, HTTP_IF_MODIFIED_SINCE=t)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.content.split('\n')[:-1], sorted(objects))

    def test_if_modified_since_invalid_date(self):
        cname = 'apples'
        url = join_urls(self.pithos_path, self.user, cname)
        r = self.get(url, HTTP_IF_MODIFIED_SINCE='Monday')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content.split('\n')[:-1],
                         sorted(self.objects['apples'].keys()))

    def test_if_not_modified_since(self):
        cname = 'apples'
        url = join_urls(self.pithos_path, self.user, cname)
        container_info = self.get_container_info(cname)
        last_modified = container_info['Last-Modified']
        t = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])

        # Check unmodified
        t1 = t + datetime.timedelta(seconds=1)
        t1_formats = map(t1.strftime, DATE_FORMATS)
        for t in t1_formats:
            r = self.get(url, HTTP_IF_UNMODIFIED_SINCE=t)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(
                r.content.split('\n')[:-1],
                sorted(self.objects['apples']))

        # modify account: add container
        _time.sleep(2)
        self.upload_object(cname)

        container_info = self.get_container_info(cname)
        last_modified = container_info['Last-Modified']
        t = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])
        t2 = t - datetime.timedelta(seconds=1)
        t2_formats = map(t2.strftime, DATE_FORMATS)

        # Check modified
        for t in t2_formats:
            r = self.get(url, HTTP_IF_UNMODIFIED_SINCE=t)
            self.assertEqual(r.status_code, 412)

        # modify account: update account meta
        _time.sleep(1)
        self.update_container_meta(cname, {'foo': 'bar'})

        container_info = self.get_container_info(cname)
        last_modified = container_info['Last-Modified']
        t = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])
        t3 = t - datetime.timedelta(seconds=1)
        t3_formats = map(t3.strftime, DATE_FORMATS)

        # Check modified
        for t in t3_formats:
            r = self.get(url, HTTP_IF_UNMODIFIED_SINCE=t)
            self.assertEqual(r.status_code, 412)

    def test_if_unmodified_since(self):
        cname = 'apples'
        url = join_urls(self.pithos_path, self.user, cname)
        container_info = self.get_container_info(cname)
        last_modified = container_info['Last-Modified']
        t = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])
        t = t + datetime.timedelta(seconds=1)
        t_formats = map(t.strftime, DATE_FORMATS)

        for tf in t_formats:
            r = self.get(url, HTTP_IF_UNMODIFIED_SINCE=tf)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(
                r.content.split('\n')[:-1],
                sorted(self.objects['apples']))

    def test_if_unmodified_since_precondition_failed(self):
        cname = 'apples'
        url = join_urls(self.pithos_path, self.user, cname)
        container_info = self.get_container_info(cname)
        last_modified = container_info['Last-Modified']
        t = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])
        t = t - datetime.timedelta(seconds=1)
        t_formats = map(t.strftime, DATE_FORMATS)

        for tf in t_formats:
            r = self.get(url, HTTP_IF_UNMODIFIED_SINCE=tf)
            self.assertEqual(r.status_code, 412)


class ContainerPut(PithosAPITest):
    def test_create(self):
        self.create_container('c1')
        self.list_containers()
        self.assertTrue('c1' in self.list_containers(format=None))

    def test_create_twice(self):
        self.create_container('c1')
        self.assertTrue('c1' in self.list_containers(format=None))
        r = self.create_container('c1')[-1]
        self.assertEqual(r.status_code, 202)
        self.assertTrue('c1' in self.list_containers(format=None))


class ContainerPost(PithosAPITest):
    def test_update_meta(self):
        cname = 'apples'
        self.create_container(cname)
        meta = {'test': 'test33', 'tost': 'tost22'}
        self.update_container_meta(cname, meta)
        info = self.get_container_info(cname)
        for k, v in meta.items():
            k = 'x-container-meta-%s' % k
            self.assertTrue(k in info)
            self.assertEqual(info[k], v)

    def test_quota(self):
        self.create_container('c1')

        url = join_urls(self.pithos_path, self.user, 'c1')
        r = self.post(url, HTTP_X_CONTAINER_POLICY_QUOTA='100')
        self.assertEqual(r.status_code, 202)

        info = self.get_container_info('c1')
        self.assertTrue('x-container-policy-quota' in info)
        self.assertEqual(info['x-container-policy-quota'], '100')

        r = self.upload_object('c1', length=101, verify=False)[2]
        self.assertEqual(r.status_code, 413)

        url = join_urls(self.pithos_path, self.user, 'c1')
        r = self.post(url, HTTP_X_CONTAINER_POLICY_QUOTA='0')
        self.assertEqual(r.status_code, 202)

        r = self.upload_object('c1', length=1)


class ContainerDelete(PithosAPITest):
    def setUp(self):
        PithosAPITest.setUp(self)
        cnames = ['c1', 'c2']

        for c in cnames:
            self.create_container(c)

    def test_delete(self):
        url = join_urls(self.pithos_path, self.user, 'c1')
        r = self.delete(url)
        self.assertEqual(r.status_code, 204)
        self.assertTrue('c1' not in self.list_containers(format=None))

    def test_delete_non_empty(self):
        self.upload_object('c1')
        url = join_urls(self.pithos_path, self.user, 'c1')
        r = self.delete(url)
        self.assertEqual(r.status_code, 409)
        self.assertTrue('c1' in self.list_containers(format=None))

    def test_delete_invalid(self):
        url = join_urls(self.pithos_path, self.user, 'c3')
        r = self.delete(url)
        self.assertEqual(r.status_code, 404)

    def test_delete_contents(self):
        folder = self.create_folder('c1')[0]
        descendant = strnextling(folder)
        self.upload_object('c1', descendant)
        self.create_folder('c1', '%s/%s' % (folder, get_random_data(5)))[0]

        self.delete('%s?delimiter=/' % join_urls(
            self.pithos_path, self.user, 'c1'))
        self.assertEqual([], self.list_objects('c1'))
        self.assertTrue('c1' in self.list_containers(format=None))
