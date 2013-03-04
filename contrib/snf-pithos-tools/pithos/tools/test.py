#!/usr/bin/env python
#coding=utf8

# Copyright 2011-2012 GRNET S.A. All rights reserved.
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

from pithos.tools.lib.client import Pithos_Client, Fault
from pithos.tools.lib.util import get_user, get_auth, get_url

from xml.dom import minidom
from StringIO import StringIO
from hashlib import new as newhasher
from binascii import hexlify
from httplib import HTTPConnection, HTTPSConnection
from urlparse import urlparse

import json
import unittest
import time as _time
import types
import hashlib
import mimetypes
import random
import datetime
import string
import re

DATE_FORMATS = ["%a %b %d %H:%M:%S %Y",
                "%A, %d-%b-%y %H:%M:%S GMT",
                "%a, %d %b %Y %H:%M:%S GMT"]

from pithos.api.settings import AUTHENTICATION_USERS
AUTHENTICATION_USERS = AUTHENTICATION_USERS or {}
OTHER_ACCOUNTS = AUTHENTICATION_USERS.copy()
try:
    OTHER_ACCOUNTS.pop(get_auth())
except:
    pass

class BaseTestCase(unittest.TestCase):
    #TODO unauthorized request
    def setUp(self):
        self.client = Pithos_Client(get_url(), get_auth(), get_user())

        #keep track of initial containers
        self.initial_containers = self.client.list_containers()
        if self.initial_containers == '':
            self.initial_containers = []

        self._clean_account()
        self.invalid_client = Pithos_Client(get_url(), get_auth(), 'invalid')

        #keep track of initial account groups
        self.initial_groups = self.client.retrieve_account_groups()

        #keep track of initial account meta
        self.initial_meta = self.client.retrieve_account_metadata(restricted=True)

        self.extended = {
            'container':(
                'name',
                'count',
                'bytes',
                'last_modified',
                'x_container_policy'),
            'object':(
                'name',
                'hash',
                'bytes',
                'content_type',
                'content_encoding',
                'last_modified',)}
        self.return_codes = (400, 401, 403, 404, 503,)

    def tearDown(self):
        #delete additionally created meta
        l = []
        for m in self.client.retrieve_account_metadata(restricted=True):
            if m not in self.initial_meta:
                l.append(m)
        self.client.delete_account_metadata(l)

        #delete additionally created groups
        l = []
        for g in self.client.retrieve_account_groups():
            if g not in self.initial_groups:
                l.append(g)
        self.client.unset_account_groups(l)
        self._clean_account()

    def _clean_account(self):
        for c in self.client.list_containers():
#             if c not in self.initial_containers:
                self.client.delete_container(c, delimiter='/')
                self.client.delete_container(c)

    def assert_status(self, status, codes):
        l = [elem for elem in self.return_codes]
        if type(codes) == types.ListType:
            l.extend(codes)
        else:
            l.append(codes)
        self.assertTrue(status in l)

    def assert_extended(self, data, format, type, size=10000):
        if format == 'xml':
            self._assert_xml(data, type, size)
        elif format == 'json':
            self._assert_json(data, type, size)

    def _assert_json(self, data, type, size):
        convert = lambda s: s.lower()
        info = [convert(elem) for elem in self.extended[type]]
        self.assertTrue(len(data) <= size)
        for item in info:
            for i in data:
                if 'subdir' in i.keys():
                    continue
                self.assertTrue(item in i.keys())

    def _assert_xml(self, data, type, size):
        convert = lambda s: s.lower()
        info = [convert(elem) for elem in self.extended[type]]
        try:
            info.remove('content_encoding')
        except ValueError:
            pass
        xml = data
        entities = xml.getElementsByTagName(type)
        self.assertTrue(len(entities) <= size)
        for e in entities:
            for item in info:
                self.assertTrue(e.getElementsByTagName(item))

    def assert_raises_fault(self, status, callableObj, *args, **kwargs):
        """
        asserts that a Fault with a specific status is raised
        when callableObj is called with the specific arguments
        """
        try:
            r = callableObj(*args, **kwargs)
            self.fail('Should never reach here')
        except Fault, f:
            if type(status) == types.ListType:
                self.failUnless(f.status in status)
            else:
                self.failUnless(f.status == status)

    def assert_not_raises_fault(self, status, callableObj, *args, **kwargs):
        """
        asserts that a Fault with a specific status is not raised
        when callableObj is called with the specific arguments
        """
        try:
            r = callableObj(*args, **kwargs)
        except Fault, f:
            self.failIfEqual(f.status, status)

    def assert_container_exists(self, container):
        """
        asserts the existence of a container
        """
        try:
            self.client.retrieve_container_metadata(container)
        except Fault, f:
            self.failIf(f.status == 404)

    def assert_container_not_exists(self, container):
        """
        asserts there is no such a container
        """
        self.assert_raises_fault(404, self.client.retrieve_container_metadata,
                                 container)

    def assert_object_exists(self, container, object):
        """
        asserts the existence of an object
        """
        try:
            self.client.retrieve_object_metadata(container, object)
        except Fault, f:
            self.failIf(f.status == 404)

    def assert_object_not_exists(self, container, object):
        """
        asserts there is no such an object
        """
        self.assert_raises_fault(404, self.client.retrieve_object_metadata,
                                 container, object)

    def assert_versionlist_structure(self, versionlist):
        self.assertTrue(type(versionlist) == types.ListType)
        for elem in versionlist:
            self.assertTrue(type(elem) == types.ListType)
            self.assertEqual(len(elem), 2)

    def upload_random_data(self, container, name, length=1024, type=None,
                           enc=None, **meta):
        data = get_random_data(length)
        return self.upload_data(container, name, data, type, enc, **meta)

    def upload_data(self, container, name, data, type=None, enc=None, etag=None,
                    **meta):
        obj = {}
        obj['name'] = name
        try:
            obj['data'] = data
            obj['hash'] = compute_md5_hash(obj['data'])

            args = {}
            args['etag'] = etag if etag else obj['hash']

            try:
                guess = mimetypes.guess_type(name)
                type = type if type else guess[0]
                enc = enc if enc else guess[1]
            except:
                pass
            args['content_type'] = type if type else 'plain/text'
            args['content_encoding'] = enc if enc else None

            obj['meta'] = args

            path = '/%s/%s' % (container, name)
            self.client.create_object(container, name, f=StringIO(obj['data']),
                                      meta=meta, **args)

            return obj
        except IOError:
            return

class AccountHead(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.containers = list(set(self.initial_containers + ['apples', 'bananas', 'kiwis', 'oranges', 'pears']))
        self.containers.sort()

        for item in self.containers:
            self.client.create_container(item)

        meta = {'foo':'bar'}
        self.client.update_account_metadata(**meta)
        #self.updated_meta = self.initial_meta.update(meta)

    def test_get_account_meta(self):
        meta = self.client.retrieve_account_metadata()

        containers = self.client.list_containers()
        l = str(len(containers))
        self.assertEqual(meta['x-account-container-count'], l)
        size1 = 0
        size2 = 0
        for c in containers:
            m = self.client.retrieve_container_metadata(c)
            csum = sum([o['bytes'] for o in self.client.list_objects(c, format='json')])
            self.assertEqual(int(m['x-container-bytes-used']), csum)
            size1 += int(m['x-container-bytes-used'])
            size2 += csum
        self.assertEqual(meta['x-account-bytes-used'], str(size1))
        self.assertEqual(meta['x-account-bytes-used'], str(size2))

    def test_get_account_403(self):
        self.assert_raises_fault(403,
                                 self.invalid_client.retrieve_account_metadata)

    def test_get_account_meta_until(self):
        t = datetime.datetime.utcnow()
        past = t - datetime.timedelta(minutes=15)
        past = int(_time.mktime(past.timetuple()))

        meta = {'premium':True}
        self.client.update_account_metadata(**meta)
        meta = self.client.retrieve_account_metadata(restricted=True,
                                                     until=past)
        self.assertTrue('premium' not in meta)

        meta = self.client.retrieve_account_metadata(restricted=True)
        self.assertTrue('premium' in meta)

    def test_get_account_meta_until_invalid_date(self):
        meta = {'premium':True}
        self.client.update_account_metadata(**meta)
        meta = self.client.retrieve_account_metadata(restricted=True,
                                                     until='kshfksfh')
        self.assertTrue('premium' in meta)

class AccountGet(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        #create some containers
        self.containers = list(set(self.initial_containers + ['apples', 'bananas', 'kiwis', 'oranges', 'pears']))
        self.containers.sort()

        for item in self.containers:
            self.client.create_container(item)

    def test_list(self):
        #list containers
        containers = self.client.list_containers()
        self.assertEquals(self.containers, containers)

    def test_list_403(self):
        self.assert_raises_fault(403, self.invalid_client.list_containers)

    def test_list_with_limit(self):
        limit = 2
        containers = self.client.list_containers(limit=limit)
        self.assertEquals(len(containers), limit)
        self.assertEquals(self.containers[:2], containers)

    def test_list_with_marker(self):
        l = 2
        m = 'bananas'
        containers = self.client.list_containers(limit=l, marker=m)
        i = self.containers.index(m) + 1
        self.assertEquals(self.containers[i:(i+l)], containers)

        m = 'oranges'
        containers = self.client.list_containers(limit=l, marker=m)
        i = self.containers.index(m) + 1
        self.assertEquals(self.containers[i:(i+l)], containers)

    def test_list_json_with_marker(self):
        l = 2
        m = 'bananas'
        containers = self.client.list_containers(limit=l, marker=m, format='json')
        self.assert_extended(containers, 'json', 'container', l)
        self.assertEqual(containers[0]['name'], 'kiwis')
        self.assertEqual(containers[1]['name'], 'oranges')

    def test_list_xml_with_marker(self):
        l = 2
        m = 'oranges'
        xml = self.client.list_containers(limit=l, marker=m, format='xml')
        self.assert_extended(xml, 'xml', 'container', l)
        nodes = xml.getElementsByTagName('name')
        self.assertTrue(len(nodes) <= l)
        names = [n.childNodes[0].data for n in nodes]
        self.assertTrue('pears' in names or 'pears' > name for name in names)

    def test_if_modified_since(self):
        t = datetime.datetime.utcnow()
        t2 = t - datetime.timedelta(minutes=10)

        #add a new container
        self.client.create_container('dummy')

        for f in DATE_FORMATS:
            past = t2.strftime(f)
            try:
                c = self.client.list_containers(if_modified_since=past)
                self.assertEqual(len(c), len(self.containers) + 1)
            except Fault, f:
                self.failIf(f.status == 304) #fail if not modified

    def test_if_modified_since_invalid_date(self):
        c = self.client.list_containers(if_modified_since='')
        self.assertEqual(len(c), len(self.containers))

    def test_if_not_modified_since(self):
        now = datetime.datetime.utcnow()
        since = now + datetime.timedelta(1)

        for f in DATE_FORMATS:
            args = {'if_modified_since':'%s' %since.strftime(f)}

            #assert not modified
            self.assert_raises_fault(304, self.client.list_containers, **args)

    def test_if_unmodified_since(self):
        now = datetime.datetime.utcnow()
        since = now + datetime.timedelta(1)

        for f in DATE_FORMATS:
            c = self.client.list_containers(if_unmodified_since=since.strftime(f))

            #assert success
            self.assertEqual(self.containers, c)

    def test_if_unmodified_since_precondition_failed(self):
        t = datetime.datetime.utcnow()
        t2 = t - datetime.timedelta(minutes=10)

        #add a new container
        self.client.create_container('dummy')

        for f in DATE_FORMATS:
            past = t2.strftime(f)

            args = {'if_unmodified_since':'%s' %past}

            #assert precondition failed
            self.assert_raises_fault(412, self.client.list_containers, **args)

class AccountPost(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.containers = list(set(self.initial_containers + ['apples', 'bananas', 'kiwis', 'oranges', 'pears']))
        self.containers.sort()

        for item in self.containers:
            self.client.create_container(item)

        meta = {'foo':'bar'}
        self.client.update_account_metadata(**meta)
        self.updated_meta = self.initial_meta.update(meta)

    def test_update_meta(self):
        with AssertMappingInvariant(self.client.retrieve_account_groups):
            meta = {'test':'test', 'tost':'tost'}
            self.client.update_account_metadata(**meta)

            meta.update(self.initial_meta)
            self.assertEqual(meta,
                             self.client.retrieve_account_metadata(
                                restricted=True))

    def test_invalid_account_update_meta(self):
        meta = {'test':'test', 'tost':'tost'}
        self.assert_raises_fault(403,
                                 self.invalid_client.update_account_metadata,
                                 **meta)

    def test_reset_meta(self):
        with AssertMappingInvariant(self.client.retrieve_account_groups):
            meta = {'test':'test', 'tost':'tost'}
            self.client.update_account_metadata(**meta)

            meta = {'test':'test33'}
            self.client.reset_account_metadata(**meta)

            self.assertEqual(meta, self.client.retrieve_account_metadata(restricted=True))

    def test_delete_meta(self):
        with AssertMappingInvariant(self.client.retrieve_account_groups):
            meta = {'test':'test', 'tost':'tost'}
            self.client.update_account_metadata(**meta)

            self.client.delete_account_metadata(meta.keys())

            account_meta = self.client.retrieve_account_metadata(restricted=True)
            for m in meta:
                self.assertTrue(m not in account_meta.keys())

    def test_set_account_groups(self):
        with AssertMappingInvariant(self.client.retrieve_account_metadata):
            groups = {'pithosdev':'verigak,gtsouk,chazapis'}
            self.client.set_account_groups(**groups)

            self.assertEqual(set(groups['pithosdev']),
                             set(self.client.retrieve_account_groups()['pithosdev']))

            more_groups = {'clientsdev':'pkanavos,mvasilak'}
            self.client.set_account_groups(**more_groups)

            groups.update(more_groups)
            self.assertEqual(set(groups['clientsdev']),
                             set(self.client.retrieve_account_groups()['clientsdev']))

    def test_reset_account_groups(self):
        with AssertMappingInvariant(self.client.retrieve_account_metadata):
            groups = {'pithosdev':'verigak,gtsouk,chazapis',
                      'clientsdev':'pkanavos,mvasilak'}
            self.client.set_account_groups(**groups)

            self.assertEqual(set(groups['pithosdev'].split(',')),
                             set(self.client.retrieve_account_groups()['pithosdev'].split(',')))
            self.assertEqual(set(groups['clientsdev'].split(',')),
                             set(self.client.retrieve_account_groups()['clientsdev'].split(',')))

            groups = {'pithosdev':'verigak,gtsouk,chazapis,papagian'}
            self.client.reset_account_groups(**groups)

            self.assertEqual(set(groups['pithosdev'].split(',')),
                             set(self.client.retrieve_account_groups()['pithosdev'].split(',')))

    def test_delete_account_groups(self):
        with AssertMappingInvariant(self.client.retrieve_account_metadata):
            groups = {'pithosdev':'verigak,gtsouk,chazapis',
                      'clientsdev':'pkanavos,mvasilak'}
            self.client.set_account_groups(**groups)

            self.client.unset_account_groups(groups.keys())

            self.assertEqual({}, self.client.retrieve_account_groups())

class ContainerHead(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.container = 'apples'
        self.client.create_container(self.container)

    def test_get_meta(self):
        meta = {'trash':'true'}
        t1 = datetime.datetime.utcnow()
        o = self.upload_random_data(self.container, o_names[0], **meta)
        if o:
            headers = self.client.retrieve_container_metadata(self.container)
            self.assertEqual(headers['x-container-object-count'], '1')
            self.assertEqual(headers['x-container-bytes-used'], str(len(o['data'])))
            t2 = datetime.datetime.strptime(headers['last-modified'], DATE_FORMATS[2])
            delta = (t2 - t1)
            threashold = datetime.timedelta(seconds=1)
            self.assertTrue(delta < threashold)
            self.assertTrue(headers['x-container-object-meta'])
            self.assertTrue('Trash' in headers['x-container-object-meta'])

class ContainerGet(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.container = ['pears', 'apples']
        for c in self.container:
            self.client.create_container(c)
        self.obj = []
        for o in o_names[:8]:
            self.obj.append(self.upload_random_data(self.container[0], o))
        for o in o_names[8:]:
            self.obj.append(self.upload_random_data(self.container[1], o))

    def test_list_shared(self):
        self.client.share_object(self.container[0], self.obj[0]['name'], ('*',))
        objs = self.client.list_objects(self.container[0], shared=True)
        self.assertEqual(objs, [self.obj[0]['name']])

        # create child object
        self.upload_random_data(self.container[0], strnextling(self.obj[0]['name']))
        objs = self.client.list_objects(self.container[0], shared=True)
        self.assertEqual(objs, [self.obj[0]['name']])

        # test inheritance
        self.client.create_folder(self.container[1], 'folder')
        self.client.share_object(self.container[1], 'folder', ('*',))
        self.upload_random_data(self.container[1], 'folder/object')
        objs = self.client.list_objects(self.container[1], shared=True)
        self.assertEqual(objs, ['folder', 'folder/object'])

    def test_list_public(self):
        self.client.publish_object(self.container[0], self.obj[0]['name'])
        objs = self.client.list_objects(self.container[0], public=True)
        self.assertEqual(objs, [self.obj[0]['name']])

        # create child object
        self.upload_random_data(self.container[0], strnextling(self.obj[0]['name']))
        objs = self.client.list_objects(self.container[0], public=True)
        self.assertEqual(objs, [self.obj[0]['name']])

        # test inheritance
        self.client.create_folder(self.container[1], 'folder')
        self.client.publish_object(self.container[1], 'folder')
        self.upload_random_data(self.container[1], 'folder/object')
        objs = self.client.list_objects(self.container[1], public=True)
        self.assertEqual(objs, ['folder'])

    def test_list_shared_public(self):
        self.client.share_object(self.container[0], self.obj[0]['name'], ('*',))
        self.client.publish_object(self.container[0], self.obj[1]['name'])
        objs = self.client.list_objects(self.container[0], shared=True, public=True)
        self.assertEqual(objs, [self.obj[0]['name'], self.obj[1]['name']])

        # create child object
        self.upload_random_data(self.container[0], strnextling(self.obj[0]['name']))
        self.upload_random_data(self.container[0], strnextling(self.obj[1]['name']))
        objs = self.client.list_objects(self.container[0], shared=True, public=True)
        self.assertEqual(objs, [self.obj[0]['name'], self.obj[1]['name']])

        # test inheritance
        self.client.create_folder(self.container[1], 'folder1')
        self.client.share_object(self.container[1], 'folder1', ('*',))
        self.upload_random_data(self.container[1], 'folder1/object')
        self.client.create_folder(self.container[1], 'folder2')
        self.client.publish_object(self.container[1], 'folder2')
        o = self.upload_random_data(self.container[1], 'folder2/object')
        objs = self.client.list_objects(self.container[1], shared=True, public=True)
        self.assertEqual(objs, ['folder1', 'folder1/object', 'folder2'])

    def test_list_objects(self):
        objects = self.client.list_objects(self.container[0])
        l = [elem['name'] for elem in self.obj[:8]]
        l.sort()
        self.assertEqual(objects, l)

    def test_list_objects_containing_slash(self):
        self.client.create_container('test')
        self.upload_random_data('test', '/objectname')

        objects = self.client.list_objects('test')
        self.assertEqual(objects, ['/objectname'])

        objects = self.client.list_objects('test', format='json')
        self.assertEqual(objects[0]['name'], '/objectname')

        objects = self.client.list_objects('test', format='xml')
        self.assert_extended(objects, 'xml', 'object')
        node_name = objects.getElementsByTagName('name')[0]
        self.assertEqual(node_name.firstChild.data, '/objectname')

    def test_list_objects_with_limit_marker(self):
        objects = self.client.list_objects(self.container[0], limit=2)
        l = [elem['name'] for elem in self.obj[:8]]
        l.sort()
        self.assertEqual(objects, l[:2])

        markers = ['How To Win Friends And Influence People.pdf',
                   'moms_birthday.jpg']
        limit = 4
        for m in markers:
            objects = self.client.list_objects(self.container[0], limit=limit,
                                               marker=m)
            l = [elem['name'] for elem in self.obj[:8]]
            l.sort()
            start = l.index(m) + 1
            end = start + limit
            end = end if len(l) >= end else len(l)
            self.assertEqual(objects, l[start:end])

    #takes too long
    def _test_list_limit_exceeds(self):
        self.client.create_container('pithos')

        for i in range(10001):
            self.client.create_zero_length_object('pithos', i)

        self.assertEqual(10000, len(self.client.list_objects('pithos')))

    def test_list_empty_params(self):
        objects = self.client.get('/%s/%s' % (get_user(), self.container[0]))[2]
        if objects:
            objects = objects.strip().split('\n')
        self.assertEqual(objects,
                         self.client.list_objects(self.container[0]))

    def test_list_pseudo_hierarchical_folders(self):
        objects = self.client.list_objects(self.container[1], prefix='photos',
                                           delimiter='/')
        self.assertEquals(['photos/animals/', 'photos/me.jpg',
                           'photos/plants/'], objects)

        objects = self.client.list_objects(self.container[1],
                                           prefix='photos/animals',
                                           delimiter='/')
        l = ['photos/animals/cats/', 'photos/animals/dogs/']
        self.assertEquals(l, objects)

        objects = self.client.list_objects(self.container[1], path='photos')
        self.assertEquals(['photos/me.jpg'], objects)

    def test_extended_list_json(self):
        objects = self.client.list_objects(self.container[1], format='json',
                                           limit=2, prefix='photos/animals',
                                           delimiter='/')
        self.assertEqual(objects[0]['subdir'], 'photos/animals/cats/')
        self.assertEqual(objects[1]['subdir'], 'photos/animals/dogs/')

    def test_extended_list_xml(self):
        xml = self.client.list_objects(self.container[1], format='xml', limit=4,
                                       prefix='photos', delimiter='/')
        self.assert_extended(xml, 'xml', 'object', size=4)
        dirs = xml.getElementsByTagName('subdir')
        self.assertEqual(len(dirs), 2)
        self.assertEqual(dirs[0].attributes['name'].value, 'photos/animals/')
        self.assertEqual(dirs[1].attributes['name'].value, 'photos/plants/')

        objects = xml.getElementsByTagName('name')
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0].childNodes[0].data, 'photos/me.jpg')

    def test_list_meta_double_matching(self):
        meta = {'quality':'aaa', 'stock':'true'}
        self.client.update_object_metadata(self.container[0],
                                           self.obj[0]['name'], **meta)
        obj = self.client.list_objects(self.container[0], meta='Quality,Stock')
        self.assertEqual(len(obj), 1)
        self.assertTrue(obj, self.obj[0]['name'])

    def test_list_using_meta(self):
        meta = {'quality':'aaa'}
        for o in self.obj[:2]:
            self.client.update_object_metadata(self.container[0], o['name'],
                                               **meta)
        meta = {'stock':'true'}
        for o in self.obj[3:5]:
            self.client.update_object_metadata(self.container[0], o['name'],
                                               **meta)

        obj = self.client.list_objects(self.container[0], meta='Quality')
        self.assertEqual(len(obj), 2)
        self.assertTrue(obj, [o['name'] for o in self.obj[:2]])

        # test case insensitive
        obj = self.client.list_objects(self.container[0], meta='quality')
        self.assertEqual(len(obj), 2)
        self.assertTrue(obj, [o['name'] for o in self.obj[:2]])

        # test multiple matches
        obj = self.client.list_objects(self.container[0], meta='Quality,Stock')
        self.assertEqual(len(obj), 4)
        self.assertTrue(obj, [o['name'] for o in self.obj[:4]])

        # test non 1-1 multiple match
        obj = self.client.list_objects(self.container[0], meta='Quality,aaaa')
        self.assertEqual(len(obj), 2)
        self.assertTrue(obj, [o['name'] for o in self.obj[:2]])

    def test_if_modified_since(self):
        t = datetime.datetime.utcnow()
        t2 = t - datetime.timedelta(minutes=10)

        #add a new object
        self.upload_random_data(self.container[0], o_names[0])

        for f in DATE_FORMATS:
            past = t2.strftime(f)
            try:
                o = self.client.list_objects(self.container[0],
                                            if_modified_since=past)
                self.assertEqual(o,
                                 self.client.list_objects(self.container[0]))
            except Fault, f:
                self.failIf(f.status == 304) #fail if not modified

    def test_if_modified_since_invalid_date(self):
        headers = {'if-modified-since':''}
        o = self.client.list_objects(self.container[0], if_modified_since='')
        self.assertEqual(o, self.client.list_objects(self.container[0]))

    def test_if_not_modified_since(self):
        now = datetime.datetime.utcnow()
        since = now + datetime.timedelta(1)

        for f in DATE_FORMATS:
            args = {'if_modified_since':'%s' %since.strftime(f)}

            #assert not modified
            self.assert_raises_fault(304, self.client.list_objects,
                                     self.container[0], **args)

    def test_if_unmodified_since(self):
        now = datetime.datetime.utcnow()
        since = now + datetime.timedelta(1)

        for f in DATE_FORMATS:
            obj = self.client.list_objects(self.container[0],
                                           if_unmodified_since=since.strftime(f))

            #assert unmodified
            self.assertEqual(obj, self.client.list_objects(self.container[0]))

    def test_if_unmodified_since_precondition_failed(self):
        t = datetime.datetime.utcnow()
        t2 = t - datetime.timedelta(minutes=10)

        #add a new container
        self.client.create_container('dummy')

        for f in DATE_FORMATS:
            past = t2.strftime(f)

            args = {'if_unmodified_since':'%s' %past}

            #assert precondition failed
            self.assert_raises_fault(412, self.client.list_objects,
                                     self.container[0], **args)

class ContainerPut(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.containers = list(set(self.initial_containers + ['c1', 'c2']))
        self.containers.sort()

    def test_create(self):
        self.client.create_container(self.containers[0])
        containers = self.client.list_containers()
        self.assertTrue(self.containers[0] in containers)
        self.assert_container_exists(self.containers[0])

    def test_create_twice(self):
        self.client.create_container(self.containers[0])
        self.assertTrue(not self.client.create_container(self.containers[0]))

    def test_quota(self):
        self.client.create_container(self.containers[0])

        policy = {'quota':100}
        self.client.set_container_policies(self.containers[0], **policy)

        meta = self.client.retrieve_container_metadata(self.containers[0])
        self.assertTrue('x-container-policy-quota' in meta)
        self.assertEqual(meta['x-container-policy-quota'], '100')

        args = [self.containers[0], 'o1']
        kwargs = {'length':101}
        self.assert_raises_fault(413, self.upload_random_data, *args, **kwargs)

        #reset quota
        policy = {'quota':0}
        self.client.set_container_policies(self.containers[0], **policy)

class ContainerPost(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.container = 'apples'
        self.client.create_container(self.container)

    def test_update_meta(self):
        meta = {'test':'test33',
                'tost':'tost22'}
        self.client.update_container_metadata(self.container, **meta)
        headers = self.client.retrieve_container_metadata(self.container)
        for k,v in meta.items():
            k = 'x-container-meta-%s' % k
            self.assertTrue(headers[k])
            self.assertEqual(headers[k], v)

class ContainerDelete(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.containers = list(set(self.initial_containers + ['c1', 'c2']))
        self.containers.sort()

        for c in self.containers:
            self.client.create_container(c)

    def test_delete(self):
        status = self.client.delete_container(self.containers[0])[0]
        self.assertEqual(status, 204)

    def test_delete_non_empty(self):
        self.upload_random_data(self.containers[1], o_names[0])
        self.assert_raises_fault(409, self.client.delete_container,
                                 self.containers[1])

    def test_delete_invalid(self):
        self.assert_raises_fault(404, self.client.delete_container, 'c3')

    def test_delete_contents(self):
        self.client.create_folder(self.containers[0], 'folder-1')
        self.upload_random_data(self.containers[1], 'folder-1/%s' % o_names[0])
        self.client.create_folder(self.containers[0], 'folder-1/subfolder')
        self.client.create_folder(self.containers[0], 'folder-2/%s' % o_names[1])

        objects = self.client.list_objects(self.containers[0])
        self.client.delete_container(self.containers[0], delimiter='/')
        for o in objects:
            self.assert_object_not_exists(self.containers[0], o)
        self.assert_container_exists(self.containers[0])

class ObjectGet(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.containers = list(set(self.initial_containers + ['c1', 'c2']))
        self.containers.sort()

        #create some containers
        for c in self.containers:
            self.client.create_container(c)

        #upload a file
        names = ('obj1', 'obj2')
        self.objects = []
        for n in names:
            self.objects.append(self.upload_random_data(self.containers[1], n))

    def test_versions(self):
        c = self.containers[1]
        o = self.objects[0]
        b = self.client.retrieve_object_versionlist(c, o['name'])['versions']
        self.assert_versionlist_structure(b)

        #update meta
        meta = {'quality':'AAA', 'stock':True}
        self.client.update_object_metadata(c, o['name'], **meta)

        a = self.client.retrieve_object_versionlist(c, o['name'])['versions']
        self.assert_versionlist_structure(a)
        self.assertEqual(len(b)+1, len(a))
        self.assertEqual(b, a[:-1])

        #get exact previous version metadata
        v = a[-2][0]
        v_meta = self.client.retrieve_object_metadata(c, o['name'],
                                                      restricted=True,
                                                      version=v)
        (self.assertTrue(k not in v_meta) for k in meta.keys())

        #update obejct
        data = get_random_data()
        self.client.update_object(c, o['name'], StringIO(data))

        aa = self.client.retrieve_object_versionlist(c, o['name'])['versions']
        self.assert_versionlist_structure(aa)
        self.assertEqual(len(a)+1, len(aa))
        self.assertEqual(a, aa[:-1])

        #get exact previous version
        v = aa[-3][0]
        v_data = self.client.retrieve_object_version(c, o['name'], version=v)
        self.assertEqual(o['data'], v_data)
        self.assertEqual(self.client.retrieve_object(c, o['name']),
                         '%s%s' %(v_data, data))

    def test_get(self):
        #perform get
        o = self.client.retrieve_object(self.containers[1],
                                        self.objects[0]['name'],
                                        self.objects[0]['meta'])
        self.assertEqual(o, self.objects[0]['data'])

    def test_objects_with_trailing_spaces(self):
        self.client.create_container('test')
        #create 'a' object
        self.upload_random_data('test', 'a')
        #look for 'a ' object
        self.assert_raises_fault(404, self.client.retrieve_object,
                                 'test', 'a ')

        #delete 'a' object
        self.client.delete_object('test', 'a')
        self.assert_raises_fault(404, self.client.retrieve_object,
                                 'test', 'a')

        #create 'a ' object
        self.upload_random_data('test', 'a ')
        #look for 'a' object
        self.assert_raises_fault(404, self.client.retrieve_object,
                                 'test', 'a')

    def test_get_invalid(self):
        self.assert_raises_fault(404, self.client.retrieve_object,
                                 self.containers[0], self.objects[0]['name'])

    def test_get_partial(self):
        #perform get with range
        status, headers, data = self.client.request_object(self.containers[1],
                                                            self.objects[0]['name'],
                                                            range='bytes=0-499')

        #assert successful partial content
        self.assertEqual(status, 206)

        #assert content-type
        self.assertEqual(headers['content-type'],
                         self.objects[0]['meta']['content_type'])

        #assert content length
        self.assertEqual(int(headers['content-length']), 500)

        #assert content
        self.assertEqual(self.objects[0]['data'][:500], data)

    def test_get_final_500(self):
        #perform get with range
        headers = {'range':'bytes=-500'}
        status, headers, data = self.client.request_object(self.containers[1],
                                                            self.objects[0]['name'],
                                                            range='bytes=-500')

        #assert successful partial content
        self.assertEqual(status, 206)

        #assert content-type
        self.assertEqual(headers['content-type'],
                         self.objects[0]['meta']['content_type'])

        #assert content length
        self.assertEqual(int(headers['content-length']), 500)

        #assert content
        self.assertTrue(self.objects[0]['data'][-500:], data)

    def test_get_rest(self):
        #perform get with range
        offset = len(self.objects[0]['data']) - 500
        status, headers, data = self.client.request_object(self.containers[1],
                                                self.objects[0]['name'],
                                                range='bytes=%s-' %offset)

        #assert successful partial content
        self.assertEqual(status, 206)

        #assert content-type
        self.assertEqual(headers['content-type'],
                         self.objects[0]['meta']['content_type'])

        #assert content length
        self.assertEqual(int(headers['content-length']), 500)

        #assert content
        self.assertTrue(self.objects[0]['data'][-500:], data)

    def test_get_range_not_satisfiable(self):
        #perform get with range
        offset = len(self.objects[0]['data']) + 1

        #assert range not satisfiable
        self.assert_raises_fault(416, self.client.retrieve_object,
                                 self.containers[1], self.objects[0]['name'],
                                 range='bytes=0-%s' %offset)

    def test_multiple_range(self):
        #perform get with multiple range
        ranges = ['0-499', '-500', '1000-']
        bytes = 'bytes=%s' % ','.join(ranges)
        status, headers, data = self.client.request_object(self.containers[1],
                                                           self.objects[0]['name'],
                                                           range=bytes)

        # assert partial content
        self.assertEqual(status, 206)

        # assert Content-Type of the reply will be multipart/byteranges
        self.assertTrue(headers['content-type'])
        content_type_parts = headers['content-type'].split()
        self.assertEqual(content_type_parts[0], ('multipart/byteranges;'))

        boundary = '--%s' %content_type_parts[1].split('=')[-1:][0]
        cparts = data.split(boundary)[1:-1]

        # assert content parts are exactly 2
        self.assertEqual(len(cparts), len(ranges))

        # for each content part assert headers
        i = 0
        for cpart in cparts:
            content = cpart.split('\r\n')
            headers = content[1:3]
            content_range = headers[0].split(': ')
            self.assertEqual(content_range[0], 'Content-Range')

            r = ranges[i].split('-')
            if not r[0] and not r[1]:
                pass
            elif not r[0]:
                start = len(self.objects[0]['data']) - int(r[1])
                end = len(self.objects[0]['data'])
            elif not r[1]:
                start = int(r[0])
                end = len(self.objects[0]['data'])
            else:
                start = int(r[0])
                end = int(r[1]) + 1
            fdata = self.objects[0]['data'][start:end]
            sdata = '\r\n'.join(content[4:-1])
            self.assertEqual(len(fdata), len(sdata))
            self.assertEquals(fdata, sdata)
            i+=1

    def test_multiple_range_not_satisfiable(self):
        #perform get with multiple range
        out_of_range = len(self.objects[0]['data']) + 1
        ranges = ['0-499', '-500', '%d-' %out_of_range]
        bytes = 'bytes=%s' % ','.join(ranges)

        # assert partial content
        self.assert_raises_fault(416, self.client.retrieve_object,
                                 self.containers[1],
                                 self.objects[0]['name'], range=bytes)

    def test_get_with_if_match(self):
        #perform get with If-Match
        etag = self.objects[0]['hash']
        status, headers, data = self.client.request_object(self.containers[1],
                                                           self.objects[0]['name'],
                                                           if_match=etag)
        #assert get success
        self.assertEqual(status, 200)

        #assert content-type
        self.assertEqual(headers['content-type'],
                         self.objects[0]['meta']['content_type'])

        #assert response content
        self.assertEqual(self.objects[0]['data'], data)

    def test_get_with_if_match_star(self):
        #perform get with If-Match *
        headers = {'if-match':'*'}
        status, headers, data = self.client.request_object(self.containers[1],
                                                self.objects[0]['name'],
                                                **headers)
        #assert get success
        self.assertEqual(status, 200)

        #assert content-type
        self.assertEqual(headers['content-type'],
                         self.objects[0]['meta']['content_type'])

        #assert response content
        self.assertEqual(self.objects[0]['data'], data)

    def test_get_with_multiple_if_match(self):
        #perform get with If-Match
        etags = [i['hash'] for i in self.objects if i]
        etags = ','.join('"%s"' % etag for etag in etags)
        status, headers, data = self.client.request_object(self.containers[1],
                                                           self.objects[0]['name'],
                                                           if_match=etags)
        #assert get success
        self.assertEqual(status, 200)

        #assert content-type
        self.assertEqual(headers['content-type'],
                         self.objects[0]['meta']['content_type'])

        #assert content-type
        self.assertEqual(headers['content-type'],
                         self.objects[0]['meta']['content_type'])

        #assert response content
        self.assertEqual(self.objects[0]['data'], data)

    def test_if_match_precondition_failed(self):
        #assert precondition failed
        self.assert_raises_fault(412, self.client.retrieve_object,
                                 self.containers[1],
                                 self.objects[0]['name'], if_match='123')

    def test_if_none_match(self):
        #perform get with If-None-Match
        status, headers, data = self.client.request_object(self.containers[1],
                                                           self.objects[0]['name'],
                                                           if_none_match='123')

        #assert get success
        self.assertEqual(status, 200)

        #assert content-type
        self.assertEqual(headers['content_type'],
                         self.objects[0]['meta']['content_type'])

    def test_if_none_match(self):
        #perform get with If-None-Match * and assert not modified
        self.assert_raises_fault(304, self.client.retrieve_object,
                                 self.containers[1],
                                 self.objects[0]['name'],
                                 if_none_match='*')

    def test_if_none_match_not_modified(self):
        #perform get with If-None-Match and assert not modified
        self.assert_raises_fault(304, self.client.retrieve_object,
                                 self.containers[1],
                                 self.objects[0]['name'],
                                 if_none_match=self.objects[0]['hash'])

        meta = self.client.retrieve_object_metadata(self.containers[1],
                                                    self.objects[0]['name'])
        self.assertEqual(meta['etag'], self.objects[0]['hash'])

    def test_if_modified_since(self):
        t = datetime.datetime.utcnow()
        t2 = t - datetime.timedelta(minutes=10)

        #modify the object
        self.upload_data(self.containers[1],
                           self.objects[0]['name'],
                           self.objects[0]['data'][:200])

        for f in DATE_FORMATS:
            past = t2.strftime(f)

            headers = {'if-modified-since':'%s' %past}
            try:
                o = self.client.retrieve_object(self.containers[1],
                                                self.objects[0]['name'],
                                                if_modified_since=past)
                self.assertEqual(o,
                                 self.client.retrieve_object(self.containers[1],
                                                             self.objects[0]['name']))
            except Fault, f:
                self.failIf(f.status == 304)

    def test_if_modified_since_invalid_date(self):
        o = self.client.retrieve_object(self.containers[1],
                                        self.objects[0]['name'],
                                        if_modified_since='')
        self.assertEqual(o, self.client.retrieve_object(self.containers[1],
                                                        self.objects[0]['name']))

    def test_if_not_modified_since(self):
        now = datetime.datetime.utcnow()
        since = now + datetime.timedelta(1)

        for f in DATE_FORMATS:
            #assert not modified
            self.assert_raises_fault(304, self.client.retrieve_object,
                                     self.containers[1], self.objects[0]['name'],
                                     if_modified_since=since.strftime(f))

    def test_if_unmodified_since(self):
        now = datetime.datetime.utcnow()
        since = now + datetime.timedelta(1)

        for f in DATE_FORMATS:
            t = since.strftime(f)
            status, headers, data = self.client.request_object(self.containers[1],
                                                               self.objects[0]['name'],
                                                               if_unmodified_since=t)
            #assert success
            self.assertEqual(status, 200)
            self.assertEqual(self.objects[0]['data'], data)

            #assert content-type
            self.assertEqual(headers['content-type'],
                             self.objects[0]['meta']['content_type'])

    def test_if_unmodified_since_precondition_failed(self):
        t = datetime.datetime.utcnow()
        t2 = t - datetime.timedelta(minutes=10)

        #modify the object
        self.upload_data(self.containers[1],
                           self.objects[0]['name'],
                           self.objects[0]['data'][:200])

        for f in DATE_FORMATS:
            past = t2.strftime(f)
            #assert precondition failed
            self.assert_raises_fault(412, self.client.retrieve_object,
                                     self.containers[1], self.objects[0]['name'],
                                     if_unmodified_since=past)

    def test_hashes(self):
        l = 8388609
        fname = 'largefile'
        o = self.upload_random_data(self.containers[1], fname, l)
        if o:
            body = self.client.retrieve_object(self.containers[1], fname,
                                               format='json')
            hashes = body['hashes']
            block_size = body['block_size']
            block_hash = body['block_hash']
            block_num = l/block_size if l/block_size == 0 else l/block_size + 1
            self.assertTrue(len(hashes), block_num)
            i = 0
            for h in hashes:
                start = i * block_size
                end = (i + 1) * block_size
                hash = compute_block_hash(o['data'][start:end], block_hash)
                self.assertEqual(h, hash)
                i += 1

class ObjectPut(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.container = 'c1'
        self.client.create_container(self.container)

    def test_upload(self):
        name = o_names[0]
        meta = {'test':'test1'}
        o = self.upload_random_data(self.container, name, **meta)

        headers = self.client.retrieve_object_metadata(self.container,
                                                       name,
                                                       restricted=True)
        self.assertTrue('test' in headers.keys())
        self.assertEqual(headers['test'], meta['test'])

        #assert uploaded content
        status, h, data = self.client.request_object(self.container, name)
        self.assertEqual(len(o['data']), int(h['content-length']))
        self.assertEqual(o['data'], data)

        #assert content-type
        self.assertEqual(h['content-type'], o['meta']['content_type'])

    def _test_maximum_upload_size_exceeds(self):
        name = o_names[0]
        meta = {'test':'test1'}
        #upload 5GB
        length= 5 * (1024 * 1024 * 1024) + 1
        self.assert_raises_fault(400, self.upload_random_data, self.container,
                                 name, length, **meta)

    def test_upload_with_name_containing_slash(self):
        name = '/%s' % o_names[0]
        meta = {'test':'test1'}
        o = self.upload_random_data(self.container, name, **meta)

        self.assertEqual(o['data'],
                         self.client.retrieve_object(self.container, name))

        self.assertTrue(name in self.client.list_objects(self.container))

    def test_create_directory_marker(self):
        self.client.create_directory_marker(self.container, 'foo')
        meta = self.client.retrieve_object_metadata(self.container, 'foo')
        self.assertEqual(meta['content-length'], '0')
        self.assertEqual(meta['content-type'], 'application/directory')

    def test_upload_unprocessable_entity(self):
        meta={'etag':'123', 'test':'test1'}

        #assert unprocessable entity
        self.assert_raises_fault(422, self.upload_random_data, self.container,
                                 o_names[0], **meta)

    def test_chunked_transfer(self):
        data = get_random_data()
        objname = 'object'
        self.client.create_object_using_chunks(self.container, objname,
                                               StringIO(data))

        uploaded_data = self.client.retrieve_object(self.container, objname)
        self.assertEqual(data, uploaded_data)

    def test_manifestation(self):
        prefix = 'myobject/'
        data = ''
        for i in range(5):
            part = '%s%d' %(prefix, i)
            o = self.upload_random_data(self.container, part)
            data += o['data']

        manifest = '%s/%s' %(self.container, prefix)
        self.client.create_manifestation(self.container, 'large-object', manifest)

        self.assert_object_exists(self.container, 'large-object')
        self.assertEqual(data, self.client.retrieve_object(self.container,
                                                           'large-object'))

        r = self.client.retrieve_object_hashmap(self.container,'large-object')
        hashes = r['hashes']
        block_size = int(r['block_size'])
        block_hash = r['block_hash']
        l = len(data)
        block_num = l/block_size if l/block_size != 0 else l/block_size + 1
        self.assertEqual(block_num, len(hashes))

        #wrong manifestation
        self.client.create_manifestation(self.container, 'large-object',
                                         '%s/invalid' % self.container)
        self.assertEqual('', self.client.retrieve_object(self.container,
                                                         'large-object'))

    def test_create_zero_length_object(self):
        c = self.container
        o = 'object'
        zero = self.client.create_zero_length_object(c, o)
        zero_meta = self.client.retrieve_object_metadata(c, o)
        zero_hash = self.client.retrieve_object_hashmap(c, o)["hashes"]
        zero_data = self.client.retrieve_object(c, o)

        self.assertEqual(int(zero_meta['content-length']), 0)
        hasher = newhasher('sha256')
        hasher.update("")
        emptyhash = hasher.digest()
        self.assertEqual(zero_hash, [hexlify(emptyhash)])
        self.assertEqual(zero_data, '')

    def test_create_object_by_hashmap(self):
        c = self.container
        o = 'object'
        self.upload_random_data(c, o)
        hashmap = self.client.retrieve_object(c, o, format='json')
        o2 = 'object-copy'
        self.client.create_object_by_hashmap(c, o2, hashmap)
        self.assertEqual(self.client.retrieve_object(c, o),
                         self.client.retrieve_object(c, o))

class ObjectCopy(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.containers = list(set(self.initial_containers + ['c1', 'c2']))
        self.containers.sort()

        for c in self.containers:
            self.client.create_container(c)
        self.obj = self.upload_random_data(self.containers[0], o_names[0])

    def test_copy(self):
        with AssertMappingInvariant(self.client.retrieve_object_metadata,
                             self.containers[0], self.obj['name']):
            #perform copy
            meta = {'test':'testcopy'}
            status = self.client.copy_object(self.containers[0],
                                              self.obj['name'],
                                              self.containers[0],
                                              'testcopy',
                                              meta)[0]

            #assert copy success
            self.assertEqual(status, 201)

            #assert access the new object
            headers = self.client.retrieve_object_metadata(self.containers[0],
                                                           'testcopy')
            self.assertTrue('x-object-meta-test' in headers.keys())
            self.assertTrue(headers['x-object-meta-test'], 'testcopy')

            #assert etag is the same
            self.assertEqual(headers['etag'], self.obj['hash'])

            #assert src object still exists
            self.assert_object_exists(self.containers[0], self.obj['name'])

    def test_copy_from_different_container(self):
        with AssertMappingInvariant(self.client.retrieve_object_metadata,
                             self.containers[0], self.obj['name']):
            meta = {'test':'testcopy'}
            status = self.client.copy_object(self.containers[0],
                                             self.obj['name'],
                                             self.containers[1],
                                             'testcopy',
                                             meta)[0]
            self.assertEqual(status, 201)

            # assert updated metadata
            meta = self.client.retrieve_object_metadata(self.containers[1],
                                                           'testcopy',
                                                           restricted=True)
            self.assertTrue('test' in meta.keys())
            self.assertTrue(meta['test'], 'testcopy')

            #assert src object still exists
            self.assert_object_exists(self.containers[0], self.obj['name'])

    def test_copy_invalid(self):
        #copy from invalid object
        meta = {'test':'testcopy'}
        self.assert_raises_fault(404, self.client.copy_object, self.containers[0],
                                 'test.py', self.containers[1], 'testcopy', meta)

        #copy from invalid container
        meta = {'test':'testcopy'}
        self.assert_raises_fault(404, self.client.copy_object, self.containers[1],
                                 self.obj['name'], self.containers[1],
                                 'testcopy', meta)

    def test_copy_dir(self):
        self.client.create_folder(self.containers[0], 'dir')
        self.client.create_folder(self.containers[0], 'dir/subdir')
        self.upload_random_data(self.containers[0], 'dir/object1.jpg', length=1024)
        self.upload_random_data(self.containers[0], 'dir/subdir/object2.pdf', length=2*1024)
        self.client.create_folder(self.containers[0], 'dirs')

        objects = self.client.list_objects(self.containers[0], prefix='dir')
        self.client.copy_object(self.containers[0], 'dir', self.containers[1], 'dir-backup', delimiter='/')
        for object in objects[:-1]:
            self.assert_object_exists(self.containers[0], object)
            self.assert_object_exists(self.containers[1], object.replace('dir', 'dir-backup', 1))
            meta0 = self.client.retrieve_object_metadata(self.containers[0], object)
            meta1 = self.client.retrieve_object_metadata(self.containers[1], object.replace('dir', 'dir-backup', 1))
            t = ('content-length', 'x-object-hash', 'content-type')
            (self.assertEqual(meta0[elem], meta1[elem]) for elem in t)
        self.assert_object_not_exists(self.containers[1], objects[-1])

class ObjectMove(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.containers = list(set(self.initial_containers + ['c1', 'c2']))
        self.containers.sort()

        for c in self.containers:
            self.client.create_container(c)
        self.obj = self.upload_random_data(self.containers[0], o_names[0])

    def test_move(self):
        meta = self.client.retrieve_object_metadata(self.containers[0],
                                                    self.obj['name'])
        self.assertTrue('x-object-uuid' in meta)
        uuid = meta['x-object-uuid']

        #perform move
        meta = {'test':'testcopy'}
        src_path = '/'.join(('/', self.containers[0], self.obj['name']))
        status = self.client.move_object(self.containers[0], self.obj['name'],
                                         self.containers[0], 'testcopy',
                                         meta)[0]

        #assert successful move
        self.assertEqual(status, 201)

        #assert updated metadata
        meta = self.client.retrieve_object_metadata(self.containers[0],
                                                    'testcopy')
        self.assertTrue('x-object-meta-test' in meta.keys())
        self.assertTrue(meta['x-object-meta-test'], 'testcopy')

        #assert same uuid
        self.assertTrue(meta['x-object-uuid'], uuid)

        #assert src object no more exists
        self.assert_object_not_exists(self.containers[0], self.obj['name'])


    def test_move_dir(self):
        meta = {}
        self.client.create_folder(self.containers[0], 'dir')
        meta['dir'] = self.client.retrieve_object_metadata(self.containers[0], 'dir')
        self.client.create_folder(self.containers[0], 'dir/subdir')
        meta['dir/subdir'] = self.client.retrieve_object_metadata(self.containers[0], 'dir/subdir')
        self.upload_random_data(self.containers[0], 'dir/object1.jpg', length=1024)
        meta['dir/object1.jpg'] = self.client.retrieve_object_metadata(self.containers[0], 'dir/object1.jpg')
        self.upload_random_data(self.containers[0], 'dir/subdir/object2.pdf', length=2*1024)
        meta['dir/subdir/object2.pdf'] = self.client.retrieve_object_metadata(self.containers[0], 'dir/subdir/object2.pdf')
        self.client.create_folder(self.containers[0], 'dirs')
        meta['dirs'] = self.client.retrieve_object_metadata(self.containers[0], 'dirs')

        objects = self.client.list_objects(self.containers[0], prefix='dir')
        self.client.move_object(self.containers[0], 'dir', self.containers[1], 'dir-backup', delimiter='/')
        for object in objects[:-1]:
            self.assert_object_not_exists(self.containers[0], object)
            self.assert_object_exists(self.containers[1], object.replace('dir', 'dir-backup', 1))
            meta1 = self.client.retrieve_object_metadata(self.containers[1], object.replace('dir', 'dir-backup', 1))
            t = ('content-length', 'x-object-hash', 'content-type')
            (self.assertEqual(meta0[elem], meta1[elem]) for elem in t)
        self.assert_object_exists(self.containers[0], objects[-1])
        self.assert_object_not_exists(self.containers[1], objects[-1])

class ObjectPost(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.containers = list(set(self.initial_containers + ['c1', 'c2']))
        self.containers.sort()

        for c in self.containers:
            self.client.create_container(c)
        self.obj = []
        for i in range(2):
            self.obj.append(self.upload_random_data(self.containers[0], o_names[i]))

    def test_update_meta(self):
        with AssertUUidInvariant(self.client.retrieve_object_metadata,
                                 self.containers[0],
                                 self.obj[0]['name']):
            #perform update metadata
            more = {'foo': 'foo', 'bar': 'bar', 'f' * 114: 'b' * 256}
            status = self.client.update_object_metadata(self.containers[0],
                                                        self.obj[0]['name'],
                                                        **more)[0]
            #assert request accepted
            self.assertEqual(status, 202)

            #assert old metadata are still there
            headers = self.client.retrieve_object_metadata(self.containers[0],
                                                           self.obj[0]['name'],
                                                           restricted=True)
            #assert new metadata have been updated
            for k,v in more.items():
                self.assertTrue(k in headers.keys())
                self.assertTrue(headers[k], v)

            #out of limits
            more = {'f' * 114: 'b' * 257}
            self.assert_raises_fault(400, self.client.update_object_metadata,
                                                        self.containers[0],
                                                        self.obj[0]['name'],
                                                        **more)

            #perform update metadata
            more = {'α': 'β' * 256}
            status = self.client.update_object_metadata(self.containers[0],
                                                        self.obj[0]['name'],
                                                        **more)[0]
            #assert request accepted
            self.assertEqual(status, 202)

            #assert old metadata are still there
            headers = self.client.retrieve_object_metadata(self.containers[0],
                                                           self.obj[0]['name'],
                                                           restricted=True)
            #assert new metadata have been updated
            for k,v in more.items():
                self.assertTrue(k in headers.keys())
                self.assertTrue(headers[k], v)

            #out of limits
            more = {'α': 'β' * 257}
            self.assert_raises_fault(400, self.client.update_object_metadata,
                                                        self.containers[0],
                                                        self.obj[0]['name'],
                                                        **more)

    def test_update_object(self,
                           first_byte_pos=0,
                           last_byte_pos=499,
                           instance_length = True,
                           content_length = 500):
        with AssertUUidInvariant(self.client.retrieve_object_metadata,
                                 self.containers[0],
                                 self.obj[0]['name']):
            l = len(self.obj[0]['data'])
            range = 'bytes %d-%d/%s' %(first_byte_pos,
                                           last_byte_pos,
                                            l if instance_length else '*')
            partial = last_byte_pos - first_byte_pos + 1
            length = first_byte_pos + partial
            data = get_random_data(partial)
            args = {'content_type':'application/octet-stream',
                    'content_range':'%s' %range}
            if content_length:
                args['content_length'] = content_length

            r = self.client.update_object(self.containers[0], self.obj[0]['name'],
                                      StringIO(data), **args)
            status = r[0]
            etag = r[1]['etag']
            if partial < 0 or (instance_length and l <= last_byte_pos):
                self.assertEqual(status, 202)
            else:
                self.assertEqual(status, 204)
                #check modified object
                content = self.client.retrieve_object(self.containers[0],
                                                  self.obj[0]['name'])
                self.assertEqual(content[:first_byte_pos], self.obj[0]['data'][:first_byte_pos])
                self.assertEqual(content[first_byte_pos:last_byte_pos+1], data)
                self.assertEqual(content[last_byte_pos+1:], self.obj[0]['data'][last_byte_pos+1:])
                self.assertEqual(etag, compute_md5_hash(content))

    def test_update_object_lt_blocksize(self):
        self.test_update_object(10, 20, content_length=None)

    def test_update_object_gt_blocksize(self):
        o = self.upload_random_data(self.containers[0], o_names[1],
                                length=4*1024*1024+5)
        c = self.containers[0]
        o_name = o['name']
        o_data = o['data']
        first_byte_pos = 4*1024*1024+1
        last_byte_pos = 4*1024*1024+4
        l = last_byte_pos - first_byte_pos + 1
        data = get_random_data(l)
        range = 'bytes %d-%d/*' %(first_byte_pos, last_byte_pos)
        self.client.update_object(c, o_name, StringIO(data), content_range=range)
        content = self.client.retrieve_object(c, o_name)
        self.assertEqual(content[:first_byte_pos], o_data[:first_byte_pos])
        self.assertEqual(content[first_byte_pos:last_byte_pos+1], data)
        self.assertEqual(content[last_byte_pos+1:], o_data[last_byte_pos+1:])

    def test_update_object_divided_by_blocksize(self):
        o = self.upload_random_data(self.containers[0], o_names[1],
                                length=4*1024*1024+5)
        c = self.containers[0]
        o_name = o['name']
        o_data = o['data']
        first_byte_pos = 4*1024*1024
        last_byte_pos = 5*1024*1024
        l = last_byte_pos - first_byte_pos + 1
        data = get_random_data(l)
        range = 'bytes %d-%d/*' %(first_byte_pos, last_byte_pos)
        self.client.update_object(c, o_name, StringIO(data), content_range=range)
        content = self.client.retrieve_object(c, o_name)
        self.assertEqual(content[:first_byte_pos], o_data[:first_byte_pos])
        self.assertEqual(content[first_byte_pos:last_byte_pos+1], data)
        self.assertEqual(content[last_byte_pos+1:], o_data[last_byte_pos+1:])

    def test_update_object_no_content_length(self):
        self.test_update_object(content_length = None)

    def test_update_object_invalid_content_length(self):
        with AssertContentInvariant(self.client.retrieve_object,
                                    self.containers[0], self.obj[0]['name']):
            self.assert_raises_fault(400, self.test_update_object,
                                     content_length = 1000)

    def test_update_object_invalid_range(self):
        with AssertContentInvariant(self.client.retrieve_object,
                                    self.containers[0], self.obj[0]['name']):
            self.assert_raises_fault(416, self.test_update_object, 499, 0, True)

    def test_update_object_invalid_range_and_length(self):
        with AssertContentInvariant(self.client.retrieve_object,
                                    self.containers[0], self.obj[0]['name']):
            self.assert_raises_fault([400, 416], self.test_update_object, 499, 0, True,
                                     -1)

    def test_update_object_invalid_range_with_no_content_length(self):
        with AssertContentInvariant(self.client.retrieve_object,
                                    self.containers[0], self.obj[0]['name']):
            self.assert_raises_fault(416, self.test_update_object, 499, 0, True,
                                     content_length = None)

    def test_update_object_out_of_limits(self):
        with AssertContentInvariant(self.client.retrieve_object,
                                    self.containers[0], self.obj[0]['name']):
            l = len(self.obj[0]['data'])
            self.assert_raises_fault(416, self.test_update_object, 0, l+1, True)

    def test_append(self):
        data = get_random_data(500)
        headers = {}
        self.client.update_object(self.containers[0], self.obj[0]['name'],
                                  StringIO(data), content_length=500,
                                  content_type='application/octet-stream')

        content = self.client.retrieve_object(self.containers[0],
                                              self.obj[0]['name'])
        self.assertEqual(len(content), len(self.obj[0]['data']) + 500)
        self.assertEqual(content[:-500], self.obj[0]['data'])

    def test_update_with_chunked_transfer(self):
        data = get_random_data(500)
        dl = len(data)
        fl = len(self.obj[0]['data'])

        self.client.update_object_using_chunks(self.containers[0],
                                               self.obj[0]['name'],
                                               StringIO(data),
                                               offset=0,
                                               content_type='application/octet-stream')

        #check modified object
        content = self.client.retrieve_object(self.containers[0],
                                              self.obj[0]['name'])
        self.assertEqual(content[0:dl], data)
        self.assertEqual(content[dl:fl], self.obj[0]['data'][dl:fl])

    def test_update_from_other_object(self):
        c = self.containers[0]
        src = o_names[0]
        dest = 'object'

        source_data = self.client.retrieve_object(c, src)
        source_meta = self.client.retrieve_object_metadata(c, src)
        source_hash = self.client.retrieve_object_hashmap(c, src)["hashes"]

        #update zero length object
        self.client.create_zero_length_object(c, dest)
        source_object = '/%s/%s' % (c, src)
        self.client.update_from_other_source(c, dest, source_object)
        dest_data = self.client.retrieve_object(c, src)
        dest_meta = self.client.retrieve_object_metadata(c, dest)
        dest_hash = self.client.retrieve_object_hashmap(c, src)["hashes"]
        self.assertEqual(source_data, dest_data)
        self.assertEqual(source_hash, dest_hash)

        #test append
        self.client.update_from_other_source(c, dest, source_object)
        content = self.client.retrieve_object(c, dest)
        self.assertEqual(source_data * 2, content)

    def test_update_range_from_other_object(self):
        c = self.containers[0]
        dest = 'object'

        #test update range
        src = self.obj[1]['name']
        src_data = self.client.retrieve_object(c, src)

        #update zero length object
        prev_data = self.upload_random_data(c, dest, length=4*1024*1024+10)['data']
        source_object = '/%s/%s' % (c, src)
        first_byte_pos = 4*1024*1024+1
        last_byte_pos = 4*1024*1024+4
        range = 'bytes %d-%d/*' %(first_byte_pos, last_byte_pos)
        self.client.update_from_other_source(c, dest, source_object,
                                             content_range=range)
        content = self.client.retrieve_object(c, dest)
        self.assertEqual(content[:first_byte_pos], prev_data[:first_byte_pos])
        self.assertEqual(content[first_byte_pos:last_byte_pos+1], src_data[:last_byte_pos - first_byte_pos + 1])
        self.assertEqual(content[last_byte_pos+1:], prev_data[last_byte_pos+1:])

    def test_update_hashes_from_other_object(self):
        c = self.containers[0]
        dest = 'object'

        #test update range
        src_data = self.upload_random_data(c, o_names[0], length=1024*1024+10)['data']

        #update zero length object
        prev_data = self.upload_random_data(c, dest, length=5*1024*1024+10)['data']
        source_object = '/%s/%s' % (c, o_names[0])
        first_byte_pos = 4*1024*1024
        last_byte_pos = 5*1024*1024
        range = 'bytes %d-%d/*' %(first_byte_pos, last_byte_pos)
        self.client.update_from_other_source(c, dest, source_object,
                                             content_range=range)
        content = self.client.retrieve_object(c, dest)
        self.assertEqual(content[:first_byte_pos], prev_data[:first_byte_pos])
        self.assertEqual(content[first_byte_pos:last_byte_pos+1], src_data[:last_byte_pos - first_byte_pos + 1])
        self.assertEqual(content[last_byte_pos+1:], prev_data[last_byte_pos+1:])


    def test_update_zero_length_object(self):
        c = self.containers[0]
        o = 'object'
        other = 'other'
        zero = self.client.create_zero_length_object(c, o)

        data = get_random_data()
        self.client.update_object(c, o, StringIO(data))
        self.client.create_object(c, other, StringIO(data))

        self.assertEqual(self.client.retrieve_object(c, o),
                         self.client.retrieve_object(c, other))

        self.assertEqual(self.client.retrieve_object_hashmap(c, o)["hashes"],
                         self.client.retrieve_object_hashmap(c, other)["hashes"])

class ObjectDelete(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.containers = ['c1', 'c2']
        self.containers.extend(self.initial_containers)

        for c in self.containers:
            self.client.create_container(c)
        self.obj = self.upload_random_data(self.containers[0], o_names[0])

    def test_delete(self):
        #perform delete object
        self.client.delete_object(self.containers[0], self.obj['name'])[0]

    def test_delete_invalid(self):
        #assert item not found
        self.assert_raises_fault(404, self.client.delete_object, self.containers[1],
                                 self.obj['name'])

    def test_delete_dir(self):
        self.client.create_folder(self.containers[0], 'dir')
        self.client.create_folder(self.containers[0], 'dir/subdir')
        self.upload_random_data(self.containers[0], 'dir/object1.jpg', length=1024)
        self.upload_random_data(self.containers[0], 'dir/subdir/object2.pdf', length=2*1024)
        self.client.create_folder(self.containers[0], 'dirs')

        objects = self.client.list_objects(self.containers[0], prefix='dir')
        self.client.delete_object(self.containers[0], 'dir', delimiter='/')
        for object in objects[:-1]:
            self.assert_object_not_exists(self.containers[0], object)
        self.assert_object_exists(self.containers[0], objects[-1])

class ListSharing(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        for i in range(2):
            self.client.create_container('c%s' %i)
        self.client.create_container('c')
        for i in range(2):
            self.upload_random_data('c1', 'o%s' %i)
        if not OTHER_ACCOUNTS:
            raise Warning('No other accounts avalaible for running this test.')
        for token, account in OTHER_ACCOUNTS.items():
            self.o1_sharing = token, account
            self.client.share_object('c1', 'o1', (account,), read=True)
            break

    def test_list_other_shared(self):
        self.other = Pithos_Client(get_url(),
                              self.o1_sharing[0],
                              self.o1_sharing[1])
        self.assertTrue(get_user() in self.other.list_shared_with_me())

    def test_list_my_shared(self):
        my_shared_containers = self.client.list_containers(shared=True)
        self.assertTrue('c1' in my_shared_containers)
        self.assertTrue('c2' not in my_shared_containers)

        my_shared_objects = self.client.list_objects('c1', shared=True)
        self.assertTrue('o1' in my_shared_objects)
        self.assertTrue('o2' not in my_shared_objects)

class List(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        for i in range(1, 5):
            c = 'c%s' % i
            self.client.create_container(c)
            for j in range(1, 3):
                o = 'o%s' % j
                self.upload_random_data(c, o)
            if i < 3:
                self.client.share_object(c, 'o1', ['papagian'], read=True)
            if i%2 != 0:
                self.client.publish_object(c, 'o2')

    def test_shared_public(self):
        diff = lambda l: set(l) - set(self.initial_containers)

        func, kwargs = self.client.list_containers, {'shared':True}
        l = func(**kwargs)
        self.assertEqual(set(['c1', 'c2']), diff(l))
        self.assertEqual(l, [e['name'] for e in func(format='json', **kwargs)])

        func, kwargs = self.client.list_containers, {'public':True}
        l = func(**kwargs)
        self.assertEqual(set(['c1', 'c3']), diff(l))
        self.assertEqual(l, [e['name'] for e in func(format='json', **kwargs)])

        func, kwargs = self.client.list_containers, {'shared':True, 'public':True}
        l = func(**kwargs)
        self.assertEqual(set(['c1', 'c2', 'c3']), diff(l))
        self.assertEqual(l, [e['name'] for e in func(format='json', **kwargs)])

        func, args, kwargs = self.client.list_objects, ['c1'], {'shared':True}
        l = func(*args, **kwargs)
        self.assertEqual(l, ['o1'])
        self.assertEqual(l, [e['name'] for e in func(*args, format='json', **kwargs)])

        func, args, kwargs = self.client.list_objects, ['c1'], {'public':True}
        l = func(*args, **kwargs)
        self.assertEqual(l, ['o2'])
        self.assertEqual(l, [e['name'] for e in func(*args, format='json', **kwargs)])

        func, args, kwargs = self.client.list_objects, ['c1'], {'shared':True, 'public':True}
        l = func(*args, **kwargs)
        self.assertEqual(l, ['o1', 'o2'])
        self.assertEqual(l, [e['name'] for e in func(*args, format='json', **kwargs)])

        func, args, kwargs = self.client.list_objects, ['c2'], {'shared':True}
        l = func(*args, **kwargs)
        self.assertEqual(l, ['o1'])
        self.assertEqual(l, [e['name'] for e in func(*args, format='json', **kwargs)])

        func, args, kwargs = self.client.list_objects, ['c2'], {'public':True}
        l = func(*args, **kwargs)
        self.assertEqual(l, '')
        self.assertEqual([], func(*args, format='json', **kwargs))

        func, args, kwargs = self.client.list_objects, ['c2'], {'shared':True, 'public':True}
        l = func(*args, **kwargs)
        self.assertEqual(l, ['o1'])
        self.assertEqual(l, [e['name'] for e in func(*args, format='json', **kwargs)])

        func, args, kwargs = self.client.list_objects, ['c3'], {'shared':True}
        l = func(*args, **kwargs)
        self.assertEqual(l, '')
        self.assertEqual([], func(*args, format='json', **kwargs))

        func, args, kwargs = self.client.list_objects, ['c3'], {'public':True}
        l = func(*args, **kwargs)
        self.assertEqual(l, ['o2'])
        self.assertEqual(l, [e['name'] for e in func(*args, format='json', **kwargs)])

        func, args, kwargs = self.client.list_objects, ['c3'], {'shared':True, 'public':True}
        l = func(*args, **kwargs)
        self.assertEqual(l, ['o2'])
        self.assertEqual(l, [e['name'] for e in func(*args, format='json', **kwargs)])

        func, args, kwargs = self.client.list_objects, ['c4'], {'shared':True}
        l = func(*args, **kwargs)
        self.assertEqual(l, '')
        self.assertEqual([], func(*args, format='json', **kwargs))

        func, args, kwargs = self.client.list_objects, ['c4'], {'public':True}
        l = func(*args, **kwargs)
        self.assertEqual(l, '')
        self.assertEqual([], func(*args, format='json', **kwargs))

        func, args, kwargs = self.client.list_objects, ['c4'], {'shared':True, 'public':True}
        l = func(*args, **kwargs)
        self.assertEqual(l, '')
        self.assertEqual([], func(*args, format='json', **kwargs))

class TestUTF8(BaseTestCase):
    def test_create_container(self):
        self.client.create_container('φάκελος')
        self.assert_container_exists('φάκελος')

        self.assertTrue('φάκελος' in self.client.list_containers())

    def test_create_object(self):
        self.client.create_container('φάκελος')
        self.upload_random_data('φάκελος', 'αντικείμενο')

        self.assert_object_exists('φάκελος', 'αντικείμενο')
        self.assertTrue('αντικείμενο' in self.client.list_objects('φάκελος'))

    def test_copy_object(self):
        src_container = 'φάκελος'
        src_object = 'αντικείμενο'
        dest_container = 'αντίγραφα'
        dest_object = 'ασφαλές-αντίγραφο'

        self.client.create_container(src_container)
        self.upload_random_data(src_container, src_object)

        self.client.create_container(dest_container)
        self.client.copy_object(src_container, src_object, dest_container,
                                dest_object)

        self.assert_object_exists(src_container, src_object)
        self.assert_object_exists(dest_container, dest_object)
        self.assertTrue(dest_object in self.client.list_objects(dest_container))

    def test_move_object(self):
        src_container = 'φάκελος'
        src_object = 'αντικείμενο'
        dest_container = 'αντίγραφα'
        dest_object = 'ασφαλές-αντίγραφο'

        self.client.create_container(src_container)
        self.upload_random_data(src_container, src_object)

        self.client.create_container(dest_container)
        self.client.move_object(src_container, src_object, dest_container,
                                dest_object)

        self.assert_object_not_exists(src_container, src_object)
        self.assert_object_exists(dest_container, dest_object)
        self.assertTrue(dest_object in self.client.list_objects(dest_container))

    def test_delete_object(self):
        self.client.create_container('φάκελος')
        self.upload_random_data('φάκελος', 'αντικείμενο')
        self.assert_object_exists('φάκελος', 'αντικείμενο')

        self.client.delete_object('φάκελος', 'αντικείμενο')
        self.assert_object_not_exists('φάκελος', 'αντικείμενο')
        self.assertTrue('αντικείμενο' not in self.client.list_objects('φάκελος'))

    def test_delete_container(self):
        self.client.create_container('φάκελος')
        self.assert_container_exists('φάκελος')

        self.client.delete_container('φάκελος')
        self.assert_container_not_exists('φάκελος')
        self.assertTrue('φάκελος' not in self.client.list_containers())

    def test_account_meta(self):
        meta = {'ποιότητα':'ΑΑΑ'}
        self.client.update_account_metadata(**meta)
        meta = self.client.retrieve_account_metadata(restricted=True)
        self.assertTrue('ποιότητα' in meta.keys())
        self.assertEqual(meta['ποιότητα'], 'ΑΑΑ')

    def test_container_meta(self):
        meta = {'ποιότητα':'ΑΑΑ'}
        self.client.create_container('φάκελος', meta=meta)

        meta = self.client.retrieve_container_metadata('φάκελος', restricted=True)
        self.assertTrue('ποιότητα' in meta.keys())
        self.assertEqual(meta['ποιότητα'], 'ΑΑΑ')

    def test_object_meta(self):
        self.client.create_container('φάκελος')
        meta = {'ποιότητα':'ΑΑΑ'}
        self.upload_random_data('φάκελος', 'αντικείμενο', **meta)

        meta = self.client.retrieve_object_metadata('φάκελος', 'αντικείμενο',
                                                    restricted=True)
        self.assertTrue('ποιότητα' in meta.keys())
        self.assertEqual(meta['ποιότητα'], 'ΑΑΑ')

    def test_list_meta_filtering(self):
        self.client.create_container('φάκελος')
        meta = {'ποιότητα':'ΑΑΑ'}
        self.upload_random_data('φάκελος', 'ο1', **meta)
        self.upload_random_data('φάκελος', 'ο2')
        self.upload_random_data('φάκελος', 'ο3')

        meta = {'ποσότητα':'μεγάλη'}
        self.client.update_object_metadata('φάκελος', 'ο2', **meta)
        objects = self.client.list_objects('φάκελος', meta='ποιότητα, ποσότητα')
        self.assertEquals(objects, ['ο1', 'ο2'])

        objects = self.client.list_objects('φάκελος', meta='!ποιότητα')
        self.assertEquals(objects, ['ο2', 'ο3'])

        objects = self.client.list_objects('φάκελος', meta='!ποιότητα, !ποσότητα')
        self.assertEquals(objects, ['ο3'])

        meta = {'ποιότητα':'ΑΒ'}
        self.client.update_object_metadata('φάκελος', 'ο2', **meta)
        objects = self.client.list_objects('φάκελος', meta='ποιότητα=ΑΑΑ')
        self.assertEquals(objects, ['ο1'])
        objects = self.client.list_objects('φάκελος', meta='ποιότητα!=ΑΑΑ')
        self.assertEquals(objects, ['ο2'])

        meta = {'έτος':'2011'}
        self.client.update_object_metadata('φάκελος', 'ο3', **meta)
        meta = {'έτος':'2012'}
        self.client.update_object_metadata('φάκελος', 'ο2', **meta)
        objects = self.client.list_objects('φάκελος', meta='έτος<2012')
        self.assertEquals(objects, ['ο3'])
        objects = self.client.list_objects('φάκελος', meta='έτος<=2012')
        self.assertEquals(objects, ['ο2', 'ο3'])
        objects = self.client.list_objects('φάκελος', meta='έτος<2012,έτος!=2011')
        self.assertEquals(objects, '')

    def test_groups(self):
        #create a group
        groups = {'γκρουπ':'chazapis,διογένης'}
        self.client.set_account_groups(**groups)
        groups.update(self.initial_groups)
        self.assertEqual(groups['γκρουπ'],
                         self.client.retrieve_account_groups()['γκρουπ'])

        #check read access
        self.client.create_container('φάκελος')
        o = self.upload_random_data('φάκελος', 'ο1')
        self.client.share_object('φάκελος', 'ο1', ['%s:γκρουπ' % get_user()])
        if 'διογένης' not in OTHER_ACCOUNTS.values():
            raise Warning('No such an account exists for running this test.')
        chef = Pithos_Client(get_url(),
                            '0009',
                            'διογένης')
        self.assert_not_raises_fault(403, chef.retrieve_object_metadata,
                                     'φάκελος', 'ο1', account=get_user())

        #check write access
        self.client.share_object('φάκελος', 'ο1', ['διογένης'], read=False)
        new_data = get_random_data()
        self.assert_not_raises_fault(403, chef.update_object,
                                     'φάκελος', 'ο1', StringIO(new_data),
                                     account=get_user())

        server_data = self.client.retrieve_object('φάκελος', 'ο1')
        self.assertEqual(server_data[:len(o['data'])], o['data'])
        self.assertEqual(server_data[len(o['data']):], new_data)

    def test_manifestation(self):
        self.client.create_container('κουβάς')
        prefix = 'μέρη/'
        data = ''
        for i in range(5):
            part = '%s%d' %(prefix, i)
            o = self.upload_random_data('κουβάς', part)
            data += o['data']

        self.client.create_container('φάκελος')
        manifest = '%s/%s' %('κουβάς', prefix)
        self.client.create_manifestation('φάκελος', 'άπαντα', manifest)

        self.assert_object_exists('φάκελος', 'άπαντα')
        self.assertEqual(data, self.client.retrieve_object('φάκελος',
                                                           'άπαντα'))

        #wrong manifestation
        self.client.create_manifestation('φάκελος', 'άπαντα', 'κουβάς/άκυρο')
        self.assertEqual('', self.client.retrieve_object('φάκελος', 'άπαντα'))

    def test_update_from_another_object(self):
        self.client.create_container('κουβάς')
        src_data = self.upload_random_data('κουβάς', 'πηγή')['data']
        initial_data = self.upload_random_data('κουβάς', 'νέο')['data']
        source_object = '/%s/%s' % ('κουβάς', 'πηγή')
        self.client.update_from_other_source('κουβάς', 'νέο', source_object)

        self.assertEqual(
            self.client.retrieve_object('κουβάς', 'νέο'),
            '%s%s' % (initial_data, self.client.retrieve_object('κουβάς', 'πηγή')))

class TestPermissions(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)

        if not OTHER_ACCOUNTS:
            raise Warning('No other accounts avalaible for running this test.')

        #create a group
        self.authorized = ['chazapis', 'verigak', 'gtsouk']
        groups = {'pithosdev':','.join(self.authorized)}
        self.client.set_account_groups(**groups)

        self.container = 'c'
        self.object = 'o'
        self.client.create_container(self.container)
        self.upload_random_data(self.container, self.object)
        self.upload_random_data(self.container, self.object+'/')
        self.upload_random_data(self.container, self.object+'/a')
        self.upload_random_data(self.container, self.object+'a')
        self.upload_random_data(self.container, self.object+'a/')
        self.dir_content_types = ('application/directory', 'application/folder')

    def assert_read(self, authorized=[], any=False, depth=0):
        for token, account in OTHER_ACCOUNTS.items():
            cl = Pithos_Client(get_url(), token, account)
            if account in authorized or any:
                self.assert_not_raises_fault(403, cl.retrieve_object_metadata,
                                             self.container, self.object,
                                             account=get_user())
            else:
                self.assert_raises_fault(403, cl.retrieve_object_metadata,
                                         self.container, self.object,
                                         account=get_user())

        #check inheritance
        meta = self.client.retrieve_object_metadata(self.container, self.object)
        type = meta['content-type']
        derivatives = self.client.list_objects(self.container, prefix=self.object)
        #exclude the self.object
        del derivatives[derivatives.index(self.object)]
        for o in derivatives:
            for token, account in OTHER_ACCOUNTS.items():
                cl = Pithos_Client(get_url(), token, account)
                prefix = self.object if self.object.endswith('/') else self.object+'/'
                if (account in authorized or any) and \
                (type in self.dir_content_types) and \
                o.startswith(prefix):
                    self.assert_not_raises_fault(403, cl.retrieve_object_metadata,
                                             self.container, o, account=get_user())
                else:
                    self.assert_raises_fault(403, cl.retrieve_object_metadata,
                                         self.container, o, account=get_user())

    def assert_write(self, authorized=[], any=False):
        o_data = self.client.retrieve_object(self.container, self.object)
        for token, account in OTHER_ACCOUNTS.items():
            cl = Pithos_Client(get_url(), token, account)
            new_data = get_random_data()
            if account in authorized or any:
                # test write access
                self.assert_not_raises_fault(403, cl.update_object,
                                             self.container, self.object, StringIO(new_data),
                                             account=get_user())
                try:
                    # test read access
                    server_data = cl.retrieve_object(self.container, self.object, account=get_user())
                    self.assertEqual(o_data, server_data[:len(o_data)])
                    self.assertEqual(new_data, server_data[len(o_data):])
                    o_data = server_data
                except Fault, f:
                    self.failIf(f.status == 403)
            else:
                self.assert_raises_fault(403, cl.update_object,
                                             self.container, self.object, StringIO(new_data),
                                             account=get_user())
        #check inheritance
        meta = self.client.retrieve_object_metadata(self.container, self.object)
        type = meta['content-type']
        derivatives = self.client.list_objects(self.container, prefix=self.object)
        #exclude the object
        del derivatives[derivatives.index(self.object)]
        for o in derivatives:
            for token, account in OTHER_ACCOUNTS.items():
                prefix = self.object if self.object.endswith('/') else self.object+'/'
                cl = Pithos_Client(get_url(), token, account)
                new_data = get_random_data()
                if (account in authorized or any) and \
                (type in self.dir_content_types) and \
                o.startswith(prefix):
                    # test write access
                    self.assert_not_raises_fault(403, cl.update_object,
                                                 self.container, o,
                                                 StringIO(new_data),
                                                 account=get_user())
                    try:
                        server_data = cl.retrieve_object(self.container, o, account=get_user())
                        self.assertEqual(new_data, server_data[-len(new_data):])
                    except Fault, f:
                        self.failIf(f.status == 403)
                else:
                    self.assert_raises_fault(403, cl.update_object,
                                                 self.container, o,
                                                 StringIO(new_data),
                                                 account=get_user())

    def test_group_read(self):
        self.client.share_object(self.container, self.object, ['%s:pithosdev' % get_user()])
        self.assert_read(authorized=self.authorized)

    def test_read_many(self):
        self.client.share_object(self.container, self.object, self.authorized)
        self.assert_read(authorized=self.authorized)

    def test_read_by_everyone(self):
        self.client.share_object(self.container, self.object, ['*'])
        self.assert_read(any=True)

    def test_read_directory(self):
        for type in self.dir_content_types:
            #change content type
            self.client.move_object(self.container, self.object, self.container, self.object, content_type=type)
            self.client.share_object(self.container, self.object, ['*'])
            self.assert_read(any=True)
            self.client.share_object(self.container, self.object, self.authorized)
            self.assert_read(authorized=self.authorized)
            self.client.share_object(self.container, self.object, ['%s:pithosdev' % get_user()])
            self.assert_read(authorized=self.authorized)

    def test_group_write(self):
        self.client.share_object(self.container, self.object, ['%s:pithosdev' % get_user()], read=False)
        self.assert_write(authorized=self.authorized)

    def test_write_many(self):
        self.client.share_object(self.container, self.object, self.authorized, read=False)
        self.assert_write(authorized=self.authorized)

    def test_write_by_everyone(self):
        self.client.share_object(self.container, self.object, ['*'], read=False)
        self.assert_write(any=True)

    def test_write_directory(self):
        dir_content_types = ('application/directory', 'application/foler')
        for type in dir_content_types:
            #change content type
            self.client.move_object(self.container, self.object, self.container, self.object, content_type='application/folder')
            self.client.share_object(self.container, self.object, ['*'], read=False)
            self.assert_write(any=True)
            self.client.share_object(self.container, self.object, self.authorized, read=False)
            self.assert_write(authorized=self.authorized)
            self.client.share_object(self.container, self.object, ['%s:pithosdev' % get_user()], read=False)
            self.assert_write(authorized=self.authorized)

    def test_shared_listing(self):
        self.client.share_object(self.container, self.object, self.authorized)

        my_shared_containers = self.client.list_containers(shared=True)
        self.assertTrue('c' in my_shared_containers)
        my_shared_objects = self.client.list_objects('c', shared=True)
        self.assertEqual(['o'], my_shared_objects)

        dir_content_types = ('application/directory', 'application/foler')
        for type in dir_content_types:
            #change content type
            self.client.move_object(self.container, self.object, self.container, self.object, content_type='application/folder')
            my_shared_objects = self.client.list_objects('c', shared=True)
            self.assertEqual(['o', 'o/', 'o/a'], my_shared_objects)

        for token, account in OTHER_ACCOUNTS.items():
            if account in self.authorized:
                self.other = Pithos_Client(get_url(), token, account)
                self.assertTrue(get_user() in self.other.list_shared_with_me())

class TestPublish(BaseTestCase):
    def test_publish(self):
        self.client.create_container('c')
        o_data = self.upload_random_data('c', 'o')['data']
        self.client.publish_object('c', 'o')
        meta = self.client.retrieve_object_metadata('c', 'o')
        self.assertTrue('x-object-public' in meta)
        url = meta['x-object-public']

        p = urlparse(get_url())
        if p.scheme == 'http':
            conn = HTTPConnection(p.netloc)
        elif p.scheme == 'https':
            conn = HTTPSConnection(p.netloc)
        else:
            raise Exception('Unknown URL scheme')

        conn.request('GET', url)
        resp = conn.getresponse()
        length = resp.getheader('content-length', None)
        data = resp.read(length)
        self.assertEqual(o_data, data)

class TestPolicies(BaseTestCase):
    def test_none_versioning(self):
        self.client.create_container('c', policies={'versioning':'none'})
        o = self.upload_random_data('c', 'o')
        meta = self.client.retrieve_object_metadata('c', 'o')
        v = meta['x-object-version']
        more_data = get_random_data()
        self.client.update_object('c', 'o', StringIO(more_data))
        vlist = self.client.retrieve_object_versionlist('c', 'o')
        self.assert_raises_fault(404, self.client.retrieve_object_version,
                                 'c', 'o', v)
        data = self.client.retrieve_object('c', 'o')
        end = len(o['data'])
        self.assertEqual(data[:end], o['data'])
        self.assertEqual(data[end:], more_data)

    def test_quota(self):
        self.client.create_container('c', policies={'quota':'1'})
        meta = self.client.retrieve_container_metadata('c')
        self.assertEqual(meta['x-container-policy-quota'], '1')
        self.assert_raises_fault(413, self.upload_random_data, 'c', 'o',
                                 length=1024*1024+1)

    def test_quota_none(self):
        self.client.create_container('c', policies={'quota':'0'})
        meta = self.client.retrieve_container_metadata('c')
        self.assertEqual(meta['x-container-policy-quota'], '0')
        self.assert_not_raises_fault(413, self.upload_random_data, 'c', 'o',
                                 length=1024*1024+1)

class AssertUUidInvariant(object):
    def __init__(self, callable, *args, **kwargs):
        self.callable = callable
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        self.map = self.callable(*self.args, **self.kwargs)
        assert('x-object-uuid' in self.map)
        self.uuid = self.map['x-object-uuid']
        return self.map

    def __exit__(self, type, value, tb):
        map = self.callable(*self.args, **self.kwargs)
        assert('x-object-uuid' in self.map)
        uuid = map['x-object-uuid']
        assert(uuid == self.uuid)

class AssertMappingInvariant(object):
    def __init__(self, callable, *args, **kwargs):
        self.callable = callable
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        self.map = self.callable(*self.args, **self.kwargs)
        return self.map

    def __exit__(self, type, value, tb):
        map = self.callable(*self.args, **self.kwargs)
        for k, v in self.map.items():
            if is_date(v):
                continue
            assert(k in map)
            assert v == map[k]

class AssertContentInvariant(object):
    def __init__(self, callable, *args, **kwargs):
        self.callable = callable
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        self.content = self.callable(*self.args, **self.kwargs)[2]
        return self.content

    def __exit__(self, type, value, tb):
        content = self.callable(*self.args, **self.kwargs)[2]
        assert self.content == content

def get_content_splitted(response):
    if response:
        return response.content.split('\n')

def compute_md5_hash(data):
    md5 = hashlib.md5()
    offset = 0
    md5.update(data)
    return md5.hexdigest().lower()

def compute_block_hash(data, algorithm):
    h = hashlib.new(algorithm)
    h.update(data.rstrip('\x00'))
    return h.hexdigest()

def get_random_data(length=500):
    char_set = string.ascii_uppercase + string.digits
    return ''.join(random.choice(char_set) for x in xrange(length))

def is_date(date):
    MONTHS = 'jan feb mar apr may jun jul aug sep oct nov dec'.split()
    __D = r'(?P<day>\d{2})'
    __D2 = r'(?P<day>[ \d]\d)'
    __M = r'(?P<mon>\w{3})'
    __Y = r'(?P<year>\d{4})'
    __Y2 = r'(?P<year>\d{2})'
    __T = r'(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})'
    RFC1123_DATE = re.compile(r'^\w{3}, %s %s %s %s GMT$' % (__D, __M, __Y, __T))
    RFC850_DATE = re.compile(r'^\w{6,9}, %s-%s-%s %s GMT$' % (__D, __M, __Y2, __T))
    ASCTIME_DATE = re.compile(r'^\w{3} %s %s %s %s$' % (__M, __D2, __T, __Y))
    for regex in RFC1123_DATE, RFC850_DATE, ASCTIME_DATE:
        m = regex.match(date)
        if m is not None:
            return True
    return False

def strnextling(prefix):
    """Return the first unicode string
       greater than but not starting with given prefix.
       strnextling('hello') -> 'hellp'
    """
    if not prefix:
        ## all strings start with the null string,
        ## therefore we have to approximate strnextling('')
        ## with the last unicode character supported by python
        ## 0x10ffff for wide (32-bit unicode) python builds
        ## 0x00ffff for narrow (16-bit unicode) python builds
        ## We will not autodetect. 0xffff is safe enough.
        return unichr(0xffff)
    s = prefix[:-1]
    c = ord(prefix[-1])
    if c >= 0xffff:
        raise RuntimeError
    s += unichr(c+1)
    return s

o_names = ['kate.jpg',
           'kate_beckinsale.jpg',
           'How To Win Friends And Influence People.pdf',
           'moms_birthday.jpg',
           'poodle_strut.mov',
           'Disturbed - Down With The Sickness.mp3',
           'army_of_darkness.avi',
           'the_mad.avi',
           'photos/animals/dogs/poodle.jpg',
           'photos/animals/dogs/terrier.jpg',
           'photos/animals/cats/persian.jpg',
           'photos/animals/cats/siamese.jpg',
           'photos/plants/fern.jpg',
           'photos/plants/rose.jpg',
           'photos/me.jpg']


def main():
    if get_user() == 'test':
        unittest.main(module='pithos.tools.test')
    else:
        print 'Will not run tests as any other user except \'test\' (current user: %s).' % get_user()


if __name__ == "__main__":
    main()

