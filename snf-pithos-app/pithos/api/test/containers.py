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

from pithos.api.test import PithosAPITest, DATE_FORMATS, o_names,\
    strnextling, pithos_settings, pithos_test_settings
from pithos.backends.random_word import get_random_word

from synnefo.lib import join_urls

import django.utils.simplejson as json
from django.http import urlencode

from xml.dom import minidom
from urllib import quote

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
        # TODO
        #self.assertTrue('x_object_public' in objects[0])

        # create child object
        descendant = strnextling(oname)
        self.upload_object(cname, descendant)
        # request shared and assert child obejct is not listed
        url = join_urls(self.pithos_path, self.user, cname)
        r = self.get('%s?shared=' % url)
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        objects.remove('')
        self.assertTrue(oname in objects)
        self.assertTrue(descendant not in objects)

        # check folder inheritance
        oname, _ = self.create_folder(cname, HTTP_X_OBJECT_SHARING='read=*')
        # create child object
        descendant = '%s/%s' % (oname, get_random_word(8))
        self.upload_object(cname, descendant)
        # request shared
        url = join_urls(self.pithos_path, self.user, cname)
        r = self.get('%s?shared=' % url)
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        objects.remove('')
        self.assertTrue(oname in objects)
        self.assertTrue(descendant in objects)

    def test_list_public(self):
        # publish an object
        cname = self.cnames[0]
        onames = self.objects[cname].keys()
        oname = onames.pop()
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)

        # share another
        other = onames.pop()
        url = join_urls(self.pithos_path, self.user, cname, other)
        r = self.post(url, content_type='', HTTP_X_OBJECT_SHARING='read=alice')
        self.assertEqual(r.status_code, 202)

        # list public and assert only the public object is returned
        url = join_urls(self.pithos_path, self.user, cname)
        r = self.get('%s?public=' % url)
        objects = r.content.split('\n')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(oname in r.content.split('\n'))
        (self.assertTrue(o not in objects) for o in o_names[1:])

        # list detailed public and assert only the public object is returned
        url = join_urls(self.pithos_path, self.user, cname)
        r = self.get('%s?public=&format=json' % url)
        self.assertEqual(r.status_code, 200)
        try:
            objects = json.loads(r.content)
        except:
            self.fail('json format expected')
        self.assertEqual([oname], [o['name'] for o in objects])
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
        self.assertEqual([oname], [o['name'] for o in objects])
        self.assertTrue('x_object_sharing' in objects[0])
        self.assertTrue('x_object_public' in objects[0])

        url = join_urls(self.pithos_path, self.user, cname)

        # Assert listing the container public contents is forbidden to not
        # shared users
        r = self.get('%s?public=&format=json' % url, user='bob')
        self.assertEqual(r.status_code, 403)

        # Assert listing the container public contents to shared users
        r = self.get('%s?public=&format=json' % url, user='alice')
        self.assertEqual(r.status_code, 200)
        try:
            objects = json.loads(r.content)
        except:
            self.fail('json format expected')
        # TODO
        #self.assertEqual([oname], [o['name'] for o in objects])
        self.assertTrue('x_object_sharing' in objects[0])
        # assert public is not returned though
        self.assertTrue('x_object_public' not in objects[0])

        # create child object
        descendant = strnextling(oname)
        self.upload_object(cname, descendant)
        # request public and assert child obejct is not listed
        r = self.get('%s?public=' % url)
        objects = r.content.split('\n')
        objects.remove('')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(oname in objects)
        (self.assertTrue(o not in objects) for o in o_names[1:])

        # test folder inheritance
        oname, _ = self.create_folder(cname, HTTP_X_OBJECT_PUBLIC='true')
        # create child object
        descendant = '%s/%s' % (oname, get_random_word(8))
        self.upload_object(cname, descendant)
        # request public
        r = self.get('%s?public=' % url)
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        self.assertTrue(oname in objects)
        self.assertTrue(descendant not in objects)

#    def test_list_shared_public(self):
#        # publish an object
#        cname = self.cnames[0]
#        onames = self.objects[cname].keys()
#        oname = onames.pop()
#        r = self.post('/v1/%s/%s/%s' % (self.user, cname, oname),
#                      content_type='',
#                      HTTP_X_OBJECT_PUBLIC='true')
#        self.assertEqual(r.status_code, 202)
#
#        # share another
#        other = onames.pop()
#        r = self.post('/v1/%s/%s/%s' % (self.user, cname, other),
#                      content_type='',
#                      HTTP_X_OBJECT_SHARING='read=alice')
#        self.assertEqual(r.status_code, 202)
#
#        # list shared and public objects and assert object is listed
#        r = self.get('/v1/%s/%s?shared=&public=&format=json' % (
#            self.user, cname))
#        self.assertEqual(r.status_code, 200)
#        objects = json.loads(r.content)
#        self.assertEqual([o['name'] for o in objects], sorted([oname, other]))
#        for o in objects:
#            if o['name'] == oname:
#                self.assertTrue('x_object_public' in objects[0])
#            elif o['name'] == other:
#                self.assertTrue('x_object_sharing' in objects[1])
#
#        # assert not listing shared and public to a not shared user
#        r = self.get('/v1/%s/%s?shared=&public=&format=json' % (
#            self.user, cname), user='bob')
#        self.assertEqual(r.status_code, 403)
#
#        # assert listing shared and public to a shared user
#        r = self.get('/v1/%s/%s?shared=&public=&format=json' % (
#            self.user, cname), user='alice')
#        self.assertEqual(r.status_code, 200)
#        try:
#            objects = json.loads(r.content)
#        except:
#            self.fail('json format expected')
#        self.assertEqual([o['name'] for o in objects], sorted([oname, other]))
#
#        # create child object
#        descentant1 = strnextling(oname)
#        self.upload_object(cname, descendant1)
#        descentant2 = strnextling(other)
#        self.upload_object(cname, descendant2)
#        r = self.get('/v1/%s/%s?shared=&public=&format=json' % (
#            self.user, cname), user='alice')
#        self.assertEqual(r.status_code, 200)
#        try:
#            objects = json.loads(r.content)
#        except:
#            self.fail('json format expected')
#        self.assertEqual([o['name'] for o in objects], [oname])
#
#        # test inheritance
#        oname1, _ = self.create_folder(cname,
#                                       HTTP_X_OBJECT_SHARING='read=alice')
#        # create child object
#        descendant1 = '%s/%s' % (oname, get_random_word(8))
#        self.upload_object(cname, descendant1)
#
#        oname2, _ = self.create_folder(cname,
#                                       HTTP_X_OBJECT_PUBLIC='true')
#        # create child object
#        descendant2 = '%s/%s' % (oname, get_random_word(8))
#        self.upload_object(cname, descendant2)
#
#
#        o = self.upload_random_data(self.container[1], 'folder2/object')
#        objs = self.client.list_objects(
#            self.container[1], shared=True, public=True)
#        self.assertEqual(objs, ['folder1', 'folder1/object', 'folder2'])
#        objs = cl.list_objects(
#            self.container[1], shared=True, public=True, account=get_user()
#        )
#        self.assertEqual(objs, ['folder1', 'folder1/object'])
#
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
        self.upload_object('test', '/objectname')

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

        oname1 = self.objects[cname].keys().pop()
        url = join_urls(container_url, oname1)
        self.post(url, content_type='', HTTP_X_OBJECT_META_QUALITY='aaa')

        oname2 = self.objects[cname].keys().pop()
        url = join_urls(container_url, cname, oname2)
        self.post(url, content_type='', HTTP_X_OBJECT_META_QUALITY='ab')

        oname3 = self.objects[cname].keys().pop()
        url = join_urls(container_url, oname3)
        self.post(url, content_type='', HTTP_X_OBJECT_META_STOCK='100')

        oname4 = self.objects[cname].keys().pop()
        url = join_urls(container_url, oname4)
        self.post(url, content_type='', HTTP_X_OBJECT_META_STOCK='200')

        # test multiple existence criteria matches
        r = self.get('%s?meta=Quality,Stock' % container_url)
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertTrue(objects, sorted([oname1, oname2, oname3, oname4]))

        # list objects that satisfy the existence criteria
        r = self.get('%s?meta=Stock' % container_url)
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertTrue(objects, sorted([oname3, oname4]))

        # test case insensitive existence criteria matching
        r = self.get('%s?meta=quality' % container_url)
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertTrue(objects, sorted([oname1, oname2]))

        # test do not all existencecriteria match
        r = self.get('%s?meta=Quality,Foo' % container_url)
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertTrue(objects, sorted([oname1, oname2]))

        # test equals criteria
        r = self.get('%s?meta=%s' % (container_url, quote('Quality=aaa')))
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertTrue(objects, [oname1])

        # test not equals criteria
        r = self.get('%s?meta=%s' % (container_url, urlencode('Quality!=aaa')))
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove()
        self.assertTrue(objects, [oname2])

        # test lte criteria
        r = self.get('%s?meta=%s' % (container_url, urlencode('Stock<=120')))
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertTrue(objects, [oname3])

        # test gte criteria
        r = self.get('%s?meta=%s' % (container_url, urlencode('Stock>=200')))
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertTrue(objects, [oname4])

#
#    def test_if_modified_since(self):
#        t = datetime.datetime.utcnow()
#        t2 = t - datetime.timedelta(minutes=10)
#
#        #add a new object
#        self.upload_random_data(self.container[0], o_names[0])
#
#        for f in DATE_FORMATS:
#            past = t2.strftime(f)
#            try:
#                o = self.client.list_objects(self.container[0],
#                                            if_modified_since=past)
#                self.assertEqual(o,
#                                 self.client.list_objects(self.container[0]))
#            except Fault, f:
#                self.failIf(f.status == 304) #fail if not modified
#
#    def test_if_modified_since_invalid_date(self):
#        headers = {'if-modified-since':''}
#        o = self.client.list_objects(self.container[0], if_modified_since='')
#        self.assertEqual(o, self.client.list_objects(self.container[0]))
#
#    def test_if_not_modified_since(self):
#        now = datetime.datetime.utcnow()
#        since = now + datetime.timedelta(1)
#
#        for f in DATE_FORMATS:
#            args = {'if_modified_since':'%s' %since.strftime(f)}
#
#            #assert not modified
#            self.assert_raises_fault(304, self.client.list_objects,
#                                     self.container[0], **args)
#
#    def test_if_unmodified_since(self):
#        now = datetime.datetime.utcnow()
#        since = now + datetime.timedelta(1)
#
#        for f in DATE_FORMATS:
#            obj = self.client.list_objects(
#                self.container[0], if_unmodified_since=since.strftime(f))
#
#            #assert unmodified
#            self.assertEqual(obj, self.client.list_objects(self.container[0]))
#
#    def test_if_unmodified_since_precondition_failed(self):
#        t = datetime.datetime.utcnow()
#        t2 = t - datetime.timedelta(minutes=10)
#
#        #add a new container
#        self.client.create_container('dummy')
#
#        for f in DATE_FORMATS:
#            past = t2.strftime(f)
#
#            args = {'if_unmodified_since':'%s' %past}
#
#            #assert precondition failed
#            self.assert_raises_fault(412, self.client.list_objects,
#                                     self.container[0], **args)
#
#class ContainerPut(BaseTestCase):
#    def setUp(self):
#        BaseTestCase.setUp(self)
#        self.containers = list(set(self.initial_containers + ['c1', 'c2']))
#        self.containers.sort()
#
#    def test_create(self):
#        self.client.create_container(self.containers[0])
#        containers = self.client.list_containers()
#        self.assertTrue(self.containers[0] in containers)
#        self.assert_container_exists(self.containers[0])
#
#    def test_create_twice(self):
#        self.client.create_container(self.containers[0])
#        self.assertTrue(not self.client.create_container(self.containers[0]))
#
#    def test_quota(self):
#        self.client.create_container(self.containers[0])
#
#        policy = {'quota':100}
#        self.client.set_container_policies(self.containers[0], **policy)
#
#        meta = self.client.retrieve_container_metadata(self.containers[0])
#        self.assertTrue('x-container-policy-quota' in meta)
#        self.assertEqual(meta['x-container-policy-quota'], '100')
#
#        args = [self.containers[0], 'o1']
#        kwargs = {'length':101}
#        self.assert_raises_fault(
#            413, self.upload_random_data, *args, **kwargs)
#
#        #reset quota
#        policy = {'quota':0}
#        self.client.set_container_policies(self.containers[0], **policy)
