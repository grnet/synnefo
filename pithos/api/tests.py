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

from pithos.lib.client import Client, Fault
import unittest
from django.utils import simplejson as json
from xml.dom import minidom
import types
import hashlib
import os
import mimetypes
import random
import datetime
import string
import re

#from pithos.backends import backend

DATE_FORMATS = ["%a %b %d %H:%M:%S %Y",
                "%A, %d-%b-%y %H:%M:%S GMT",
                "%a, %d %b %Y %H:%M:%S GMT"]

DEFAULT_HOST = 'pithos.dev.grnet.gr'
#DEFAULT_HOST = '127.0.0.1:8000'
DEFAULT_API = 'v1'
DEFAULT_USER = 'papagian'
DEFAULT_AUTH = '0004'

class BaseTestCase(unittest.TestCase):
    #TODO unauthorized request
    def setUp(self):
        self.client = Client(DEFAULT_HOST, DEFAULT_AUTH, DEFAULT_USER, DEFAULT_API)
        self.invalid_client = Client(DEFAULT_HOST, DEFAULT_AUTH, 'non-existing', DEFAULT_API)
        self.unauthorised_client = Client(DEFAULT_HOST, '', DEFAULT_USER, DEFAULT_API)
        self.headers = {
            'account': ('x-account-container-count',
                        'x-account-bytes-used',
                        'last-modified',
                        'content-length',
                        'date',
                        'content-type',
                        'server',),
            'object': ('etag',
                       'content-length',
                       'content-type',
                       'content-encoding',
                       'last-modified',
                       'date',
                       'x-object-manifest',
                       'content-range',
                       'x-object-modified-by',
                       'x-object-version',
                       'x-object-version-timestamp',
                       'server',),
            'container': ('x-container-object-count',
                          'x-container-bytes-used',
                          'content-type',
                          'last-modified',
                          'content-length',
                          'date',
                          'x-container-block-size',
                          'x-container-block-hash',
                          'x-container-policy-quota',
                          'x-container-policy-versioning',
                          'server',
                          'x-container-object-meta',
                          'x-container-policy-versioning',
                          'server',)}

        self.contentTypes = {'xml':'application/xml',
                             'json':'application/json',
                             '':'text/plain'}
        self.extended = {
            'container':(
                'name',
                'count',
                'bytes',
                'last_modified'),
            'object':(
                'name',
                'hash',
                'bytes',
                'content_type',
                'content_encoding',
                'last_modified',)}
        self.return_codes = (400, 401, 404, 503,)

    def assert_status(self, status, codes):
        l = [elem for elem in self.return_codes]
        if type(codes) == types.ListType:
            l.extend(codes)
        else:
            l.append(codes)
        self.assertTrue(status in l)
    
    def assert_list(self, path, entity, limit=10000, format='text', params=None, **headers):
        status, headers, data = self.client.get(path, format=format,
                                                headers=headers, params=params)
        
        self.assert_status(status, [200, 204, 304, 412])
        if format == 'text':
            data = data.strip().split('\n') if data else []
            self.assertTrue(len(data) <= limit)
        else:
            exp_content_type = self.contentTypes[format]
            self.assertEqual(headers['content-type'].find(exp_content_type), 0)
            #self.assert_extended(data, format, entity, limit)
            if format == 'json':
                data = json.loads(data) if data else []
            elif format == 'xml':
                data = minidom.parseString(data)
        return status, headers, data

    def list_containers(self, limit=10000, marker='', format='text', **headers):
        params = locals()
        params.pop('self')
        return self.assert_list('', 'account', limit, format, params, **headers)
    
    def list_objects(self, container, limit=10000, marker='',
                     prefix='', format='', path='', delimiter='', meta='',
                     **headers):
        params = locals()
        params.pop('self')
        params.pop('container')
        path = '/' + container
        format = 'text' if format == '' else format
        return self.assert_list(path, 'container', limit, format, params, **headers)
    
    def _assert_get_meta(self, path, entity, params=None, **exp_meta):
        status, headers, data = self.client.head(path, params)
        self.assert_status(status, 204)
        #self.assert_headers(headers, entity, **exp_meta)
        return status, headers, data
    
    def get_account_meta(self, params=None, **exp_meta):
        return self._assert_get_meta('', 'account', params, **exp_meta)

    def get_container_meta(self, container, params=None, **exp_meta):
        path = '/%s' % container
        return self._assert_get_meta(path, 'container', params, **exp_meta)

    def create_container(self, name, **meta):
        headers = {}
        for k,v in meta.items():
            headers['x-container-meta-%s' %k.strip().upper()] = v.strip()
        status, header, data = self.client.put('/' + name, headers=headers)
        self.assert_status(status, [201, 202])
        return status, header, data
    
    def get_object(self, container, name, format='', version=None, **headers):
        path = '/%s/%s' % (container, name)
        params = {'version':version} if version else None 
        status, headers, data = self.client.get(path, format, headers, params)
        self.assert_status(status, [200, 206, 304, 412, 416])
        #if status in [200, 206]:
        #    self.assert_headers(headers, 'object')
        return status, headers, data
    
    def update_object(self, container, name, data='', content_type='', **headers):
        if content_type != '':
            headers['content-type'] = content_type
        status, headers, data = self.client.update_object_data(container,
                                                               name,
                                                               data,
                                                               headers)
        self.assert_status(status, [202, 204, 416])
        return status, headers, data

    def assert_headers(self, headers, type, **exp_meta):
        prefix = 'x-%s-meta-' %type
        system_headers = [h for h in headers if not h.startswith(prefix)]
        for k,v in headers.items():
            if k in system_headers:
                self.assertTrue(k in headers[type])
            elif exp_meta:
                k = k.split(prefix)[-1]
                self.assertEqual(v, exp_meta[k])

    #def assert_extended(self, data, format, type, size):
    #    if format == 'xml':
    #        self._assert_xml(data, type, size)
    #    elif format == 'json':
    #        self._assert_json(data, type, size)
    #
    #def _assert_json(self, data, type, size):
    #    print '#', data
    #    convert = lambda s: s.lower()
    #    info = [convert(elem) for elem in self.extended[type]]
    #    data = json.loads(data)
    #    self.assertTrue(len(data) <= size)
    #    for item in info:
    #        for i in data:
    #            if 'subdir' in i.keys():
    #                continue
    #            self.assertTrue(item in i.keys())
    #
    #def _assert_xml(self, data, type, size):
    #    print '#', data
    #    convert = lambda s: s.lower()
    #    info = [convert(elem) for elem in self.extended[type]]
    #    try:
    #        info.remove('content_encoding')
    #    except ValueError:
    #        pass
    #    xml = minidom.parseString(data)
    #    entities = xml.getElementsByTagName(type)
    #    self.assertTrue(len(entities) <= size)
    #    for e in entities:
    #        for item in info:
    #            self.assertTrue(e.hasAttribute(item))
    
    def assert_raises_fault(self, status, callableObj, *args, **kwargs):
        """
        asserts that a Fault with a specific status is raised
        when callableObj is called with the specific arguments
        """
        try:
            callableObj(*args, **kwargs)
            self.fail('Should never reach here')
        except Fault, f:
            self.failUnless(f.status == status)
    
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
            
            headers = {}
            for k,v in meta.items():
                key = 'x-object-meta-%s' % k
                headers[key] = v
            headers['etag'] = etag if etag else obj['hash']
            guess = mimetypes.guess_type(name)
            type = type if type else guess[0]
            enc = enc if enc else guess[1]
            headers['content-type'] = type if type else 'plain/text'
            headers['content-encoding'] = enc if enc else None
            obj['meta'] = headers
            
            path = '/%s/%s' % (container, name)
            status, headers, data = self.client.put(path, obj['data'],
                                                    headers=headers)
            if status == 201:
                self.assertTrue('etag' in headers)
                self.assertEqual(obj['hash'], headers['etag'])
                return obj
        except IOError:
            return

class AccountHead(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.containers = ['apples', 'bananas', 'kiwis', 'oranges', 'pears']
        for item in self.containers:
            self.create_container(item)

    def tearDown(self):
        for c in  self.list_containers()[2]:
            self.client.delete_container(c)
        
    def test_get_account_meta(self):
        headers = self.get_account_meta()[1]
        
        containers = self.list_containers()[2]
        l = str(len(containers))
        self.assertEqual(headers['x-account-container-count'], l)
        size = 0
        for c in containers:
            h = self.get_container_meta(c)[1]
            size = size + int(h['x-container-bytes-used'])
        self.assertEqual(headers['x-account-bytes-used'], str(size))

    #def test_get_account_401(self):
    #    response = self.get_account_meta('non-existing-account')
    #    print response
    #    self.assertEqual(response.status_code, 401)

class AccountGet(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        #create some containers
        self.containers = ['apples', 'bananas', 'kiwis', 'oranges', 'pears']
        for item in self.containers:
            self.create_container(item)

    def tearDown(self):
        for c in self.list_containers()[2]:
            for o in self.list_objects(c)[2]:
                self.client.delete_object(c, o)
            self.client.delete_container(c)

    def test_list(self):
        #list containers
        containers = self.list_containers()[2]
        self.assertEquals(self.containers, containers)

    #def test_list_204(self):
    #    response = self.list_containers('non-existing-account')
    #    self.assertEqual(response.status_code, 204)

    def test_list_with_limit(self):
        limit = 2
        containers = self.list_containers(limit=limit)[2]
        self.assertEquals(len(containers), limit)
        self.assertEquals(self.containers[:2], containers)

    def test_list_with_marker(self):
        l = 2
        m = 'bananas'
        containers = self.list_containers(limit=l, marker=m)[2]
        i = self.containers.index(m) + 1
        self.assertEquals(self.containers[i:(i+l)], containers)
        
        m = 'oranges'
        containers = self.list_containers(limit=l, marker=m)[2]
        i = self.containers.index(m) + 1
        self.assertEquals(self.containers[i:(i+l)], containers)

    #def test_extended_list(self):
    #    self.list_containers(self.account, limit=3, format='xml')
    #    self.list_containers(self.account, limit=3, format='json')

    def test_list_json_with_marker(self):
        l = 2
        m = 'bananas'
        status, headers, containers = self.list_containers(limit=l, marker=m,
                                        format='json')
        self.assertEqual(containers[0]['name'], 'kiwis')
        self.assertEqual(containers[1]['name'], 'oranges')

    def test_list_xml_with_marker(self):
        l = 2
        m = 'oranges'
        status, headers, xml = self.list_containers(limit=l, marker=m,
                                        format='xml')
        nodes = xml.getElementsByTagName('name')
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].childNodes[0].data, 'pears')

    def test_if_modified_since(self):
        t = datetime.datetime.utcnow()
        t2 = t - datetime.timedelta(minutes=10)
        
        #add a new container
        self.create_container('dummy')

        for f in DATE_FORMATS:
            past = t2.strftime(f)
            
            headers = {'if-modified-since':'%s' %past}
            status, headers, data = self.list_containers(**headers)
            
            #assert get success
            self.assertEqual(status, 200)

    def test_if_modified_since_invalid_date(self):
        headers = {'if-modified-since':''}
        status, headers, data = self.list_containers(**headers)
            
        #assert get success
        self.assertEqual(status, 200)

    def test_if_not_modified_since(self):
        now = datetime.datetime.utcnow()
        since = now + datetime.timedelta(1)
        
        for f in DATE_FORMATS:
            headers = {'if-modified-since':'%s' %since.strftime(f)}
            #assert not modified
            self.assert_raises_fault(304, self.list_containers, **headers)

    def test_if_unmodified_since(self):
        now = datetime.datetime.utcnow()
        since = now + datetime.timedelta(1)
        
        for f in DATE_FORMATS:
            headers = {'if-unmodified-since':'%s' %since.strftime(f)}
            status, headers, data = self.list_containers(**headers)
            
            #assert success
            self.assertEqual(status, 200)
            self.assertEqual(self.containers, data)

    def test_if_unmodified_since_precondition_failed(self):
        t = datetime.datetime.utcnow()
        t2 = t - datetime.timedelta(minutes=10)
        
        #add a new container
        self.create_container('dummy')
        
        for f in DATE_FORMATS:
            past = t2.strftime(f)
            
            headers = {'if-unmodified-since':'%s' %past}
            #assert precondition failed
            self.assert_raises_fault(412, self.list_containers, **headers)

class AccountPost(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.containers = ['apples', 'bananas', 'kiwis', 'oranges', 'pears']
        for item in self.containers:
            self.create_container(item)

    def tearDown(self):
        containers = self.list_containers()[2]
        for c in  containers:
            self.client.delete_container(c)

    def test_update_meta(self):
        meta = {'test':'test', 'tost':'tost'}
        status, headers, data = self.get_account_meta(**meta)
    
    #def test_invalid_account_update_meta(self):
    #    with AssertMappingInvariant(self.get_account_meta, self.account):
    #        meta = {'HTTP_X_ACCOUNT_META_TEST':'test',
    #               'HTTP_X_ACCOUNT_META_TOST':'tost'}
    #        response = self.update_account_meta('non-existing-account', **meta)
    
class ContainerHead(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.container = 'apples'
        status = self.create_container(self.container)[0]

    def tearDown(self):
        for o in self.list_objects(self.container)[2]:
            self.client.delete_object(self.container, o)
        self.client.delete_container(self.container)

    def test_get_meta(self):
        meta = {'trash':'true'}
        t1 = datetime.datetime.utcnow()
        o = self.upload_random_data(self.container, o_names[0], **meta)
        if o:
            status, headers, data = self.get_container_meta(self.container)
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
        self.account = 'test'
        self.container = ['pears', 'apples']
        for c in self.container:
            self.create_container(c)
        self.obj = []
        for o in o_names[:8]:
            self.obj.append(self.upload_random_data(self.container[0], o))
        for o in o_names[8:]:
            self.obj.append(self.upload_random_data(self.container[1], o))

    def tearDown(self):
        for c in self.container:
            for obj in self.list_objects(c)[2]:
                self.client.delete_object(c, obj)
            self.client.delete_container(c)

    def test_list_objects(self):
        objects = self.list_objects(self.container[0])[2]
        l = [elem['name'] for elem in self.obj[:8]]
        l.sort()
        self.assertEqual(objects, l)

    def test_list_objects_with_limit_marker(self):
        objects = self.list_objects(self.container[0], limit=2)[2]
        l = [elem['name'] for elem in self.obj[:8]]
        l.sort()
        self.assertEqual(objects, l[:2])
        
        markers = ['How To Win Friends And Influence People.pdf',
                   'moms_birthday.jpg']
        limit = 4
        for m in markers:
            objects = self.list_objects(self.container[0], limit=limit,
                                        marker=m)[2]
            l = [elem['name'] for elem in self.obj[:8]]
            l.sort()
            start = l.index(m) + 1
            end = start + limit
            end = len(l) >= end and end or len(l)
            self.assertEqual(objects, l[start:end])

    def test_list_pseudo_hierarchical_folders(self):
        objects = self.list_objects(self.container[1], prefix='photos',
                                     delimiter='/')[2]
        self.assertEquals(['photos/animals/', 'photos/me.jpg',
                           'photos/plants/'], objects)
        
        objects = self.list_objects(self.container[1], prefix='photos/animals',
                                     delimiter='/')[2]
        l = ['photos/animals/cats/', 'photos/animals/dogs/']
        self.assertEquals(l, objects)
        
        objects = self.list_objects(self.container[1], path='photos')[2]
        self.assertEquals(['photos/me.jpg'], objects)

    def test_extended_list_json(self):
        objects = self.list_objects(self.container[1],
                                     format='json', limit=2,
                                     prefix='photos/animals',
                                     delimiter='/')[2]
        self.assertEqual(objects[0]['subdir'], 'photos/animals/cats/')
        self.assertEqual(objects[1]['subdir'], 'photos/animals/dogs/')

    def test_extended_list_xml(self):
        xml = self.list_objects(self.container[1], format='xml', limit=4,
                                prefix='photos', delimiter='/')[2]
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
        obj = self.list_objects(self.container[0], meta='Quality,Stock')[2]
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
        
        status, headers, data = self.list_objects(self.container[0],
                                                  meta='Quality')
        self.assertEqual(status, 200)
        self.assertEqual(len(data), 2)
        self.assertTrue(data, [o['name'] for o in self.obj[:2]])
        
        # test case insensitive
        status, headers, obj = self.list_objects(self.container[0],
                                                  meta='quality')
        self.assertEqual(status, 200)
        self.assertEqual(len(obj), 2)
        self.assertTrue(obj, [o['name'] for o in self.obj[:2]])
        
        # test multiple matches
        status, headers, obj = self.list_objects(self.container[0],
                                                  meta='Quality,Stock')
        self.assertEqual(status, 200)
        self.assertEqual(len(obj), 4)
        self.assertTrue(obj, [o['name'] for o in self.obj[:4]])
        
        # test non 1-1 multiple match
        status, headers, obj = self.list_objects(self.container[0],
                                                  meta='Quality,aaaa')
        self.assertEqual(status, 200)
        self.assertEqual(len(obj), 2)
        self.assertTrue(obj, [o['name'] for o in self.obj[:2]])

    def test_if_modified_since(self):
        t = datetime.datetime.utcnow()
        t2 = t - datetime.timedelta(minutes=10)
        
        #add a new object
        self.upload_random_data(self.container[0], o_names[0])

        for f in DATE_FORMATS:
            past = t2.strftime(f)
            
            headers = {'if-modified-since':'%s' %past}
            status, headers, data = self.list_objects(self.container[0],
                                                      **headers)
            
            #assert get success
            self.assertEqual(status, 200)

    def test_if_modified_since_invalid_date(self):
        headers = {'if-modified-since':''}
        status, headers, data = self.list_objects(self.container[0], **headers)
        
        #assert get success
        self.assertEqual(status, 200)

    def test_if_not_modified_since(self):
        now = datetime.datetime.utcnow()
        since = now + datetime.timedelta(1)
        
        for f in DATE_FORMATS:
            headers = {'if-modified-since':'%s' %since.strftime(f)}
            #assert not modified
            self.assert_raises_fault(304, self.list_objects, self.container[0],
                                     **headers)
    
    def test_if_unmodified_since(self):
        now = datetime.datetime.utcnow()
        since = now + datetime.timedelta(1)
        
        for f in DATE_FORMATS:
            headers = {'if-unmodified-since':'%s' %since.strftime(f)}
            status, headers, data = self.list_objects(self.container[0], **headers)
            
            #assert success
            self.assertEqual(status, 200)
            objlist = self.list_objects(self.container[0])[2]
            self.assertEqual(data, objlist)

    def test_if_unmodified_since_precondition_failed(self):
        t = datetime.datetime.utcnow()
        t2 = t - datetime.timedelta(minutes=10)
        
        #add a new container
        self.create_container('dummy')

        for f in DATE_FORMATS:
            past = t2.strftime(f)
            
            headers = {'if-unmodified-since':'%s' %past}
            #assert precondition failed
            self.assert_raises_fault(412, self.list_objects, self.container[0],
                                     **headers)

class ContainerPut(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.containers = ['c1', 'c2']

    def tearDown(self):
        for c in self.list_containers()[2]:
            r = self.client.delete_container(c)

    def test_create(self):
        status = self.create_container(self.containers[0])[0]
        self.assertEqual(status, 201)
        
        containers = self.list_containers()[2]
        self.assertTrue(self.containers[0] in containers)
        status = self.get_container_meta(self.containers[0])[0]
        self.assertEqual(status, 204)

    def test_create_twice(self):
        status, header, data = self.create_container(self.containers[0])
        if status == 201:
            status, header, data = self.create_container(self.containers[0])
            self.assertTrue(status, 202)

class ContainerPost(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.container = 'apples'
        self.create_container(self.container)

    def tearDown(self):
        for o in self.list_objects(self.container)[2]:
            self.client.delete_object(self.account, self.container, o)
        self.client.delete_container(self.container)

    def test_update_meta(self):
        meta = {'test':'test33',
                'tost':'tost22'}
        self.client.update_container_metadata(self.container, **meta)
        headers = self.get_container_meta(self.container)[1]
        for k,v in meta.items():
            k = 'x-container-meta-%s' % k
            self.assertTrue(headers[k])
            self.assertEqual(headers[k], v)

class ContainerDelete(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.containers = ['c1', 'c2']
        for c in self.containers:
            self.create_container(c)
        self.upload_random_data(self.containers[1], o_names[0])

    def tearDown(self):
        for c in self.list_containers()[2]:
            for o in self.list_objects(c)[2]:
                self.client.delete_object(c, o)
            self.client.delete_container(c)

    def test_delete(self):
        status = self.client.delete_container(self.containers[0])[0]
        self.assertEqual(status, 204)

    def test_delete_non_empty(self):
        self.assert_raises_fault(409, self.client.delete_container,
                                 self.containers[1])

    def test_delete_invalid(self):
        self.assert_raises_fault(404, self.client.delete_container, 'c3')

class ObjectHead(BaseTestCase):
    pass

class ObjectGet(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.containers = ['c1', 'c2']
        #create some containers
        for c in self.containers:
            self.create_container(c)
        
        #upload a file
        names = ('obj1', 'obj2')
        self.objects = []
        for n in names:
            self.objects.append(self.upload_random_data(self.containers[1], n))

    def tearDown(self):
        for c in self.containers:
            for o in self.list_objects(c)[2]:
                self.client.delete_object(c, o)
            self.client.delete_container(c)

    def test_get(self):
        #perform get
        status, headers, data = self.get_object(self.containers[1],
                            self.objects[0]['name'],
                            self.objects[0]['meta'])
        #assert success
        self.assertEqual(status, 200)
        
        #assert content-type
        self.assertEqual(headers['content-type'],
                         self.objects[0]['meta']['content-type'])

    def test_get_invalid(self):
        self.assert_raises_fault(404, self.get_object, self.containers[0],
                                 self.objects[0]['name'])

    def test_get_partial(self):
        #perform get with range
        headers = {'range':'bytes=0-499'}
        status, headers, data = self.get_object(self.containers[1],
                                                self.objects[0]['name'],
                                                **headers)
        
        #assert successful partial content
        self.assertEqual(status, 206)
        
        #assert content-type
        self.assertEqual(headers['content-type'],
                         self.objects[0]['meta']['content-type'])
        
        #assert content length
        self.assertEqual(int(headers['content-length']), 500)
        
        #assert content
        self.assertEqual(self.objects[0]['data'][:500], data)

    def test_get_final_500(self):
        #perform get with range
        headers = {'range':'bytes=-500'}
        status, headers, data = self.get_object(self.containers[1],
                                                self.objects[0]['name'],
                                                **headers)
        
        #assert successful partial content
        self.assertEqual(status, 206)
        
        #assert content-type
        self.assertEqual(headers['content-type'],
                         self.objects[0]['meta']['content-type'])
        
        #assert content length
        self.assertEqual(int(headers['content-length']), 500)
        
        #assert content
        self.assertTrue(self.objects[0]['data'][-500:], data)

    def test_get_rest(self):
        #perform get with range
        offset = len(self.objects[0]['data']) - 500
        headers = {'range':'bytes=%s-' %offset}
        status, headers, data = self.get_object(self.containers[1],
                                                self.objects[0]['name'],
                                                **headers)
        
        #assert successful partial content
        self.assertEqual(status, 206)
        
        #assert content-type
        self.assertEqual(headers['content-type'],
                         self.objects[0]['meta']['content-type'])
        
        #assert content length
        self.assertEqual(int(headers['content-length']), 500)
        
        #assert content
        self.assertTrue(self.objects[0]['data'][-500:], data)

    def test_get_range_not_satisfiable(self):
        #perform get with range
        offset = len(self.objects[0]['data']) + 1
        headers = {'range':'bytes=0-%s' %offset}
        
        #assert range not satisfiable
        self.assert_raises_fault(416, self.get_object, self.containers[1],
                                 self.objects[0]['name'], **headers)

    def test_multiple_range(self):
        #perform get with multiple range
        ranges = ['0-499', '-500', '1000-']
        headers = {'range' : 'bytes=%s' % ','.join(ranges)}
        status, headers, data = self.get_object(self.containers[1],
                                                self.objects[0]['name'],
                                                **headers)
        
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
        headers = {'range' : 'bytes=%s' % ','.join(ranges)}
        
        # assert partial content
        self.assert_raises_fault(416, self.get_object, self.containers[1],
                            self.objects[0]['name'], **headers)


    def test_get_with_if_match(self):
        #perform get with If-Match
        headers = {'if-match':self.objects[0]['hash']}
        status, headers, data = self.get_object(self.containers[1],
                                                self.objects[0]['name'],
                                                **headers)
        #assert get success
        self.assertEqual(status, 200)
        
        #assert content-type
        self.assertEqual(headers['content-type'],
                         self.objects[0]['meta']['content-type'])
        
        #assert response content
        self.assertEqual(self.objects[0]['data'], data)

    def test_get_with_if_match_star(self):
        #perform get with If-Match *
        headers = {'if-match':'*'}
        status, headers, data = self.get_object(self.containers[1],
                                                self.objects[0]['name'],
                                                **headers)
        #assert get success
        self.assertEqual(status, 200)
        
        #assert content-type
        self.assertEqual(headers['content-type'],
                         self.objects[0]['meta']['content-type'])
        
        #assert response content
        self.assertEqual(self.objects[0]['data'], data)

    def test_get_with_multiple_if_match(self):
        #perform get with If-Match
        etags = [i['hash'] for i in self.objects if i]
        etags = ','.join('"%s"' % etag for etag in etags)
        headers = {'if-match':etags}
        status, headers, data = self.get_object(self.containers[1],
                                                self.objects[0]['name'],
                                                **headers)
        #assert get success
        self.assertEqual(status, 200)
        
        #assert content-type
        self.assertEqual(headers['content-type'],
                         self.objects[0]['meta']['content-type'])
        
        #assert content-type
        self.assertEqual(headers['content-type'],
                         self.objects[0]['meta']['content-type'])
        
        #assert response content
        self.assertEqual(self.objects[0]['data'], data)

    def test_if_match_precondition_failed(self):
        #perform get with If-Match
        headers = {'if-match':'123'}
        
        #assert precondition failed
        self.assert_raises_fault(412, self.get_object, self.containers[1],
                                 self.objects[0]['name'], **headers)
        

    def test_if_none_match(self):
        #perform get with If-None-Match
        headers = {'if-none-match':'123'}
        status, headers, data = self.get_object(self.containers[1],
                                                self.objects[0]['name'],
                                                **headers)
        
        #assert get success
        self.assertEqual(status, 200)
        
        #assert content-type
        self.assertEqual(headers['content-type'],
                         self.objects[0]['meta']['content-type'])

    def test_if_none_match(self):
        #perform get with If-None-Match *
        headers = {'if-none-match':'*'}
        
        #assert not modified
        self.assert_raises_fault(304, self.get_object, self.containers[1],
                            self.objects[0]['name'],
                            **headers)

    def test_if_none_match_not_modified(self):
        #perform get with If-None-Match
        headers = {'if-none-match':'%s' %self.objects[0]['hash']}
        
        #assert not modified
        self.assert_raises_fault(304, self.get_object, self.containers[1],
                            self.objects[0]['name'],
                            **headers)
        
        headers = self.get_object(self.containers[1],
                                  self.objects[0]['name'])[1]
        self.assertEqual(headers['etag'], self.objects[0]['hash'])

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
            status, headers, data = self.get_object(self.containers[1],
                                                    self.objects[0]['name'],
                                                    **headers)
            
            #assert get success
            self.assertEqual(status, 200)
            
            #assert content-type
            self.assertEqual(headers['content-type'],
                             self.objects[0]['meta']['content-type'])   

    def test_if_modified_since_invalid_date(self):
        headers = {'if-modified-since':''}
        status, headers, data = self.get_object(self.containers[1],
                                                self.objects[0]['name'],
                                                **headers)
        
        #assert get success
        self.assertEqual(status, 200)
        
        #assert content-type
        self.assertEqual(headers['content-type'],
                         self.objects[0]['meta']['content-type'])

    def test_if_not_modified_since(self):
        now = datetime.datetime.utcnow()
        since = now + datetime.timedelta(1)
        
        for f in DATE_FORMATS:
            headers = {'if-modified-since':'%s' %since.strftime(f)}
            
            #assert not modified
            self.assert_raises_fault(304, self.get_object, self.containers[1],
                            self.objects[0]['name'], **headers)


    def test_if_unmodified_since(self):
        now = datetime.datetime.utcnow()
        since = now + datetime.timedelta(1)
        
        for f in DATE_FORMATS:
            headers = {'if-unmodified-since':'%s' %since.strftime(f)}
            status, headers, data = self.get_object(self.containers[1],
                                                    self.objects[0]['name'],
                                                    **headers)
            #assert success
            self.assertEqual(status, 200)
            self.assertEqual(self.objects[0]['data'], data)
            
            #assert content-type
            self.assertEqual(headers['content-type'],
                             self.objects[0]['meta']['content-type'])

    def test_if_unmodified_since_precondition_failed(self):
        t = datetime.datetime.utcnow()
        t2 = t - datetime.timedelta(minutes=10)
        
        #modify the object
        self.upload_data(self.containers[1],
                           self.objects[0]['name'],
                           self.objects[0]['data'][:200])
        
        for f in DATE_FORMATS:
            past = t2.strftime(f)
            
            headers = {'if-unmodified-since':'%s' %past}
            
            #assert precondition failed
            self.assert_raises_fault(412, self.get_object, self.containers[1],
                            self.objects[0]['name'], **headers)


    def test_hashes(self):
        l = 8388609
        fname = 'largefile'
        o = self.upload_random_data(self.containers[1], fname, l)
        if o:
            data = self.get_object(self.containers[1],
                                fname,
                                'json')[2]
            body = json.loads(data)
            hashes = body['hashes']
            block_size = body['block_size']
            block_hash = body['block_hash']
            block_num = l/block_size == 0 and l/block_size or l/block_size + 1
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
        self.account = 'test'
        self.container = 'c1'
        self.create_container(self.container)
    
    def tearDown(self):
        objects = self.list_objects(self.container)[2]
        for o in objects:
            self.client.delete_object(self.container, o)
        self.client.delete_container(self.container)

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
        status, headers, content = self.get_object(self.container, name)
        self.assertEqual(len(o['data']), int(headers['content-length']))
        self.assertEqual(o['data'], content)

    def test_upload_unprocessable_entity(self):
        meta={'etag':'123', 'test':'test1'}
        
        #assert unprocessable entity
        self.assert_raises_fault(422, self.upload_random_data,self.container,
                                 o_names[0], **meta)

    def test_chucked_transfer(self):
        fname = './api/tests.py'
        objname = os.path.split(fname)[-1:][0]
        f = open(fname, 'r')
        status = self.client.create_object(self.container,
                                           objname,
                                           f,
                                           chunked=True)[0]
        self.assertEqual(status, 201)
        
        uploaded_data = self.get_object(self.container,
                                        objname)[2]
        f = open(fname, 'r')
        actual_data = f.read()
        self.assertEqual(actual_data, uploaded_data)

class ObjectCopy(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.containers = ['c1', 'c2']
        for c in self.containers:
            self.create_container(c)
        self.obj = self.upload_random_data(self.containers[0], o_names[0])

    def tearDown(self):
        for c in self.containers:
            for o in self.list_objects(c)[2]:
                self.client.delete_object(c, o)
            self.client.delete_container(c)

    def test_copy(self):
        with AssertMappingInvariant(self.client.retrieve_object_metadata,
                             self.containers[0], self.obj['name']):
            #perform copy
            meta = {'test':'testcopy'}
            status = self.client.copy_object(self.containers[0],
                                              self.obj['name'],
                                              self.containers[0],
                                              'testcopy',
                                              **meta)[0]
            
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
                                             **meta)[0]
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
                                 'test.py', self.containers[1], 'testcopy',
                                 **meta)
        
        #copy from invalid container
        meta = {'test':'testcopy'}
        self.assert_raises_fault(404, self.client.copy_object, self.containers[1],
                                 self.obj['name'], self.containers[1],
                                 'testcopy', **meta)
        

class ObjectMove(ObjectCopy):
    def test_move(self):
        #perform move
        meta = {'test':'testcopy'}
        src_path = os.path.join('/', self.containers[0], self.obj['name'])
        status = self.client.move_object(self.containers[0], self.obj['name'],
                                         self.containers[0], 'testcopy',
                                         **meta)[0]
        
        #assert successful move
        self.assertEqual(status, 201)
        
        #assert updated metadata
        meta = self.client.retrieve_object_metadata(self.containers[0],
                                                    'testcopy',
                                                    restricted=True)
        self.assertTrue('test' in meta.keys())
        self.assertTrue(meta['test'], 'testcopy')
        
        #assert src object no more exists
        self.assert_object_not_exists(self.containers[0], self.obj['name'])

class ObjectPost(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.containers = ['c1', 'c2']
        for c in self.containers:
            self.create_container(c)
        self.obj = self.upload_random_data(self.containers[0], o_names[0])

    def tearDown(self):
        for c in self.containers:
            for o in self.list_objects(c)[2]:
                self.client.delete_object(c, o)
            self.client.delete_container(c)

    def test_update_meta(self):
        #perform update metadata
        more = {'foo':'foo', 'bar':'bar'}
        status = self.client.update_object_metadata(self.containers[0],
                                                    self.obj['name'],
                                                    **more)[0]
        #assert request accepted
        self.assertEqual(status, 202)
        
        #assert old metadata are still there
        headers = self.client.retrieve_object_metadata(self.containers[0],
                                                       self.obj['name'],
                                                       restricted=True)
        #assert new metadata have been updated
        for k,v in more.items():
            self.assertTrue(k in headers.keys())
            self.assertTrue(headers[k], v)

    def test_update_object(self,
                           first_byte_pos=0,
                           last_byte_pos=499,
                           instance_length = True,
                           content_length = 500):
        l = len(self.obj['data'])
        length = l if instance_length else '*'
        range = 'bytes %d-%d/%s' %(first_byte_pos,
                                       last_byte_pos,
                                       length)
        partial = last_byte_pos - first_byte_pos + 1
        data = get_random_data(partial)
        headers = {'content-range':range,
                   'content-type':'application/octet-stream'}
        if content_length:
            headers.update({'content-length':'%s' % content_length})
        
        status = self.client.update_object_data(self.containers[0],
                                                self.obj['name'],
                                                data,
                                                headers)[0]
        
        
        if partial < 0 or (instance_length and l <= last_byte_pos):
            self.assertEqual(status, 202)    
        else:
            self.assertEqual(status, 204)
            
            #check modified object
            content = self.get_object(self.containers[0], self.obj['name'])[2]
            self.assertEqual(content[0:partial], data)
            self.assertEqual(content[partial:l], self.obj['data'][partial:l])

    def test_update_object_no_content_length(self):
        self.test_update_object(content_length = None)


    #fails if the server resets the content-legth
    #def test_update_object_invalid_content_length(self):
    #    with AssertContentInvariant(self.get_object, self.containers[0],
    #                                self.obj['name']):
    #        self.test_update_object(content_length = 1000)

    def test_update_object_with_unknown_instance_length(self):
        self.test_update_object(instance_length = False)

    def test_update_object_invalid_range(self):
        with AssertContentInvariant(self.get_object, self.containers[0],
                                    self.obj['name']):
            self.test_update_object(499, 0, True)
    
    #no use if the server resets the content-legth
    def test_update_object_invalid_range_and_length(self):
        with AssertContentInvariant(self.get_object, self.containers[0],
                                    self.obj['name']):
            self.test_update_object(499, 0, True, -1)
    
    #no use if the server resets the content-legth
    def test_update_object_invalid_range_with_no_content_length(self):
        with AssertContentInvariant(self.get_object, self.containers[0],
                                    self.obj['name']):
            self.test_update_object(499, 0, True, content_length = None)
    
    def test_update_object_out_of_limits(self):    
        with AssertContentInvariant(self.get_object, self.containers[0],
                                    self.obj['name']):
            l = len(self.obj['data'])
            self.assert_raises_fault(416, self.test_update_object, 0, l+1, True)

    def test_append(self):
        data = get_random_data(500)
        headers = {'content-type':'application/octet-stream',
                   'content-length':'500'}
        status = self.client.update_object_data(self.containers[0],
                                                self.obj['name'],
                                                data, headers)[0]
        
        self.assertEqual(status, 204)
        
        content = self.get_object(self.containers[0], self.obj['name'])[2]
        self.assertEqual(len(content), len(self.obj['data']) + 500)
        self.assertEqual(content[:-500], self.obj['data'])

    def test_update_with_chunked_transfer(self):
        data, pure = create_random_chunked_data()
        dl = len(pure)
        fl = len(self.obj['data'])
        meta = {'transfer-encoding':'chunked',
                'content-range':'bytes 0-/%d' %fl}
        self.update_object(self.containers[0], self.obj['name'], data,
                           'application/octet-stream', **meta)
        
        #check modified object
        content = self.get_object(self.containers[0], self.obj['name'])[2]
        self.assertEqual(content[0:dl], pure)
        self.assertEqual(content[dl:fl], self.obj['data'][dl:fl])

    def test_update_with_chunked_transfer_strict_range(self):
        data, pure = create_random_chunked_data()
        dl = len(pure) - 1
        fl = len(self.obj['data'])
        meta = {'transfer-encoding':'chunked',
                'content-range':'bytes 0-%d/%d' %(dl, fl)}
        self.update_object(self.containers[0], self.obj['name'], data,
                           'application/octet-stream', **meta)
        
        #check modified object
        content = self.get_object(self.containers[0], self.obj['name'])[2]
        self.assertEqual(content[0:dl+1], pure)
        self.assertEqual(content[dl+1:fl], self.obj['data'][dl+1:fl])

class ObjectDelete(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.containers = ['c1', 'c2']
        for c in self.containers:
            self.create_container(c)
        self.obj = self.upload_random_data(self.containers[0], o_names[0])

    def tearDown(self):
        for c in self.containers:
            for o in self.list_objects(c)[2]:
                self.client.delete_object(c, o)
            self.client.delete_container(c)

    def test_delete(self):
        #perform delete object
        self.client.delete_object(self.containers[0], self.obj['name'])[0]
        
    def test_delete_invalid(self):
        #assert item not found
        self.assert_raises_fault(404, self.client.delete_object, self.containers[1],
                                 self.obj['name'])

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
        for k in self.map.keys():
            if is_date(map[k]):
                continue
            assert map[k] == self.map[k]

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

def create_chunked_update_test_file(src, dest):
    fr = open(src, 'r')
    fw = open(dest, 'w')
    data = fr.readline()
    while data:
        fw.write(hex(len(data)))
        fw.write('\r\n')
        fw.write(data)
        data = fr.readline()
    fw.write(hex(0))
    fw.write('\r\n')

def create_random_chunked_data(rows=5):
    i = 0
    out = []
    pure= []
    while i < rows:
        data = get_random_data(random.randint(1, 100))
        out.append(hex(len(data)))
        out.append(data)
        pure.append(data)
        i+=1
    out.append(hex(0))
    out.append('\r\n')
    return '\r\n'.join(out), ''.join(pure)

def get_random_data(length=500):
    char_set = string.ascii_uppercase + string.digits
    return ''.join(random.choice(char_set) for x in range(length))

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

if __name__ == "__main__":
    unittest.main()
