from django.test.client import Client
from django.test import TestCase
from django.utils import simplejson as json
from xml.dom import minidom
import types
import hashlib
import os


class AaiClient(Client):
    def request(self, **request):
        request['HTTP_X_AUTH_TOKEN'] = '46e427d657b20defe352804f0eb6f8a2'
        return super(AaiClient, self).request(**request)


class BaseTestCase(TestCase):
    #TODO unauthorized request
    def setUp(self):
        self.client = AaiClient()
        self.headers = {
            'account':(
                'X-Account-Container-Count',
                'X-Account-Bytes-Used',
                'Last-Modified',),
            'container':(
                'X-Container-Object-Count',
                'X-Container-Bytes-Used',
                'Last-Modified',),
            'object':(
                'ETag',
                'Content-Length',
                'Content-Type',
                'Content-Encoding',
                'Last-Modified',)}
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
    
    def assertFault(self, response, status_code, name):
        self.assertEqual(response.status_code, status_code)
    
    def assertBadRequest(self, response):
        self.assertFault(response, 400, 'badRequest')
    
    def assertItemNotFound(self, response):
        self.assertFault(response, 404, 'itemNotFound')

    def assertUnauthorized(self, response):
        self.assertFault(response, 401, 'unauthorized')

    def assertServiceUnavailable(self, response):
        self.assertFault(response, 503, 'serviceUnavailable')

    def assertNonEmpty(self, response):
        self.assertFault(response, 409, 'nonEmpty')

    def assert_status(self, response, codes):
        l = [elem for elem in self.return_codes]
        if type(codes) == types.ListType:
            l.extend(codes)
        else:
            l.append(codes)
        self.assertTrue(response.status_code in l)

    def get_account_meta(self, account):
        path = '/v1/%s' % account
        response = self.client.head(path)
        self.assert_status(response, 204)
        self.assert_headers(response, 'account')
        return response

    def list_containers(self, account, limit=10000, marker='', format=''):
        params = locals()
        params.pop('self')
        params.pop('account')
        path = '/v1/%s' % account
        response = self.client.get(path, params)
        self.assert_status(response, [200, 204])
        response.content = response.content.strip()
        if format:
            self.assert_extended(response, format, 'container', limit)
        else:
            names = get_content_splitted(response)
            self.assertTrue(len(names) <= limit)
        return response

    def update_account_meta(self, account, **metadata):
        path = '/v1/%s' % account
        response = self.client.post(path, **metadata)
        response.content = response.content.strip()
        self.assert_status(response, 202)
        return response

    def get_container_meta(self, account, container):
        params = locals()
        params.pop('self')
        params.pop('account')
        params.pop('container')
        path = '/v1/%s/%s' %(account, container)
        response = self.client.head(path, params)
        response.content = response.content.strip()
        self.assert_status(response, 204)
        if response.status_code == 204:
            self.assert_headers(response, 'container')
        return response

    def list_objects(self, account, container, limit=10000, marker='', prefix='', format='', path='', delimiter=''):
        params = locals()
        params.pop('self')
        params.pop('account')
        params.pop('container')
        path = '/v1/%s/%s' % (account, container)
        response = self.client.get(path, params)
        response.content = response.content.strip()
        if format:
            self.assert_extended(response, format, 'object', limit)
        self.assert_status(response, [200, 204])
        return response

    def create_container(self, account, name, **meta):
        path = '/v1/%s/%s' %(account, name)
        response = self.client.put(path, **meta)
        response.content = response.content.strip()
        self.assert_status(response, [201, 202])
        return response

    def update_container_meta(self, account, name, **meta):
        path = '/v1/%s/%s' %(account, name)
        response = self.client.post(path, data={}, content_type='text/xml', follow=False, **meta)
        response.content = response.content.strip()
        self.assert_status(response, 202)
        return response

    def delete_container(self, account, container):
        path = '/v1/%s/%s' %(account, container)
        response = self.client.delete(path)
        response.content = response.content.strip()
        self.assert_status(response, [204, 409])
        return response

    def get_object_meta(self, account, container, name):
        path = '/v1/%s/%s/%s' %(account, container, name)
        response = self.client.head(path)
        response.content = response.content.strip()
        self.assert_status(response, 204)
        return response

    def get_object(self, account, container, name, **headers):
        path = '/v1/%s/%s/%s' %(account, container, name)
        response = self.client.get(path, **headers)
        response.content = response.content.strip()
        self.assert_status(response, [200, 206, 304, 412, 416])
        if response.status_code in [200, 206]:
            self.assert_headers(response, 'object')
        return response

    def upload_object(self, account, container, name, data, content_type='application/json', **headers):
        path = '/v1/%s/%s/%s' %(account, container, name)
        response = self.client.put(path, data, content_type, **headers)
        response.content = response.content.strip()
        self.assert_status(response, [201, 411, 422])
        if response.status_code == 201:
            self.assertTrue(response['Etag'])
        return response

    def copy_object(self, account, container, name, src, **headers):
        path = '/v1/%s/%s/%s' %(account, container, name)
        headers['X-Copy-From'] = src
        response = self.client.put(path, **headers)
        response.content = response.content.strip()
        self.assert_status(response, 201)
        return response

    def move_object(self, account, container, name, **headers):
        path = '/v1/%s/%s/%s' % account, container, name
        response = self.client.move(path, **headers)
        response.content = response.content.strip()
        self.assert_status(response, 201)
        return response

    def update_object_meta(self, account, container, name, **headers):
        path = '/v1/%s/%s/%s' %(account, container, name)
        response = self.client.post(path, **headers)
        response.content = response.content.strip()
        self.assert_status(response, 202)
        return response

    def delete_object(self, account, container, name):
        path = '/v1/%s/%s/%s' %(account, container, name)
        response = self.client.delete(path)
        response.content = response.content.strip()
        self.assert_status(response, 204)
        return response

    def assert_headers(self, response, type):
        for item in self.headers[type]:
            self.assertTrue(response[item])

    def assert_extended(self, response, format, type, size):
        self.assertEqual(response['Content-Type'].find(self.contentTypes[format]), 0)
        if format == 'xml':
            self.assert_xml(response, type, size)
        elif format == 'json':
            self.assert_json(response, type, size)

    def assert_json(self, response, type, size):
        convert = lambda s: s.lower()
        info = [convert(elem) for elem in self.extended[type]]
        data = json.loads(response.content)
        self.assertTrue(len(data) <= size)
        for item in info:
            for i in data:
                if 'subdir' in i.keys():
                    continue
                self.assertTrue(item in i.keys())

    def assert_xml(self, response, type, size):
        convert = lambda s: s.lower()
        info = [convert(elem) for elem in self.extended[type]]
        xml = minidom.parseString(response.content)
        for item in info:
            nodes = xml.getElementsByTagName(item)
            self.assertTrue(nodes)
            self.assertTrue(len(nodes) <= size)

class ListContainers(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        #create some containers
        self.containers = ['apples', 'bananas', 'kiwis', 'oranges', 'pears']
        for item in self.containers:
            self.create_container(self.account, item)

    def tearDown(self):
        for c in get_content_splitted(self.list_containers(self.account)):
            response = self.delete_container(self.account, c)

    def test_list(self):
        #list containers
        response = self.list_containers(self.account)
        containers = get_content_splitted(response)
        self.assertEquals(self.containers, containers)

    #def test_list_204(self):
    #    response = self.list_containers('non-existing-account')
    #    self.assertEqual(response.status_code, 204)

    def test_list_with_limit(self):
        limit = 2
        response = self.list_containers(self.account, limit=limit)
        containers = get_content_splitted(response)
        self.assertEquals(len(containers), limit)
        self.assertEquals(self.containers[:2], containers)

    def test_list_with_marker(self):
        limit = 2
        marker = 'bananas'
        response = self.list_containers(self.account, limit=limit, marker=marker)
        containers =  get_content_splitted(response)
        i = self.containers.index(marker) + 1
        self.assertEquals(self.containers[i:(i+limit)], containers)
        
        marker = 'oranges'
        response = self.list_containers(self.account, limit=limit, marker=marker)
        containers = get_content_splitted(response)
        i = self.containers.index(marker) + 1
        self.assertEquals(self.containers[i:(i+limit)], containers)

    def test_extended_list(self):
        self.list_containers(self.account, limit=3, format='xml')
        self.list_containers(self.account, limit=3, format='json')

    def test_list_json_with_marker(self):
        limit = 2
        marker = 'bananas'
        response = self.list_containers(self.account, limit=limit, marker=marker, format='json')
        containers = json.loads(response.content)
        self.assertEqual(containers[0]['name'], 'kiwis')
        self.assertEqual(containers[1]['name'], 'oranges')

    def test_list_xml_with_marker(self):
        limit = 2
        marker = 'oranges'
        response = self.list_containers(self.account, limit=limit, marker=marker, format='xml')
        xml = minidom.parseString(response.content)
        nodes = xml.getElementsByTagName('name')
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].childNodes[0].data, 'pears')

class AccountMetadata(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.containers = ['apples', 'bananas', 'kiwis', 'oranges', 'pears']
        for item in self.containers:
            self.create_container(self.account, item)

    def tearDown(self):
        for c in  get_content_splitted(self.list_containers(self.account)):
            self.delete_container(self.account, c)

    def test_get_account_meta(self):
        response = self.get_account_meta(self.account)
        r2 = self.list_containers(self.account)
        containers =  get_content_splitted(r2)
        self.assertEqual(response['X-Account-Container-Count'], str(len(containers)))
        size = 0
        for c in containers:
            r = self.get_container_meta(self.account, c)
            size = size + int(r['X-Container-Bytes-Used'])
        self.assertEqual(response['X-Account-Bytes-Used'], str(size))

    #def test_get_account_401(self):
    #    response = self.get_account_meta('non-existing-account')
    #    print response
    #    self.assertEqual(response.status_code, 401)

    def test_update_meta(self):
        meta = {'HTTP_X_ACCOUNT_META_TEST':'test', 'HTTP_X_ACCOUNT_META_TOST':'tost'}
        response = self.update_account_meta(self.account, **meta)
        response = self.get_account_meta(self.account)
        for k,v in meta.items():
            key = '-'.join(elem.capitalize() for elem in k.split('_')[1:])
            self.assertTrue(response[key])
            self.assertEqual(response[key], v)

    #def test_invalid_account_update_meta(self):
    #    with AssertInvariant(self.get_account_meta, self.account):
    #        meta = {'HTTP_X_ACCOUNT_META_TEST':'test', 'HTTP_X_ACCOUNT_META_TOST':'tost'}
    #        response = self.update_account_meta('non-existing-account', **meta)

class ListObjects(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.container = ['pears', 'apples']
        self.create_container(self.account, self.container[0])
        self.l = [
            {'name':'kate.jpg',
             'meta':{'HTTP_ETAG':'99914b932bd37a50b983c5e7c90ae93b',
                     'HTTP_CONTENT-LENGTH':23,
                     'HTTP_CONTENT_TYPE':'image/jpeg',
                     'HTTP_CONTENT_ENCODING':'utf8',
                     'HTTP_X_OBJECT_MANIFEST':123,
                     'HTTP_X_OBJECT_META_TEST':'test1'}},
            {'name':'kate_beckinsale.jpg',
             'meta':{'HTTP_ETAG':'99914b932bd37a50b983c5e7c90ae93b',
                     'HTTP_CONTENT-LENGTH':23,
                     'HTTP_CONTENT_TYPE':'image/jpeg',
                     'HTTP_CONTENT_ENCODING':'utf8',
                     'HTTP_X_OBJECT_MANIFEST':123,
                     'HTTP_X_OBJECT_META_TEST':'test1'}},
            {'name':'How To Win Friends And Influence People.pdf',
             'meta':{'HTTP_ETAG':'99914b932bd37a50b983c5e7c90ae93b',
                     'HTTP_CONTENT-LENGTH':28,
                     'HTTP_CONTENT_TYPE':'application/pdf',
                     'HTTP_CONTENT_ENCODING':'utf8',
                     'HTTP_X_OBJECT_MANIFEST':123,
                     'HTTP_X_OBJECT_META_TEST':'test2'}},
            {'name':'moms_birthday.jpg',
             'meta':{'HTTP_ETAG':'99914b932bd37a50b983c5e7c90ae93b',
                     'HTTP_CONTENT-LENGTH':255, 'HTTP_CONTENT_TYPE':'image/jpeg',
                     'HTTP_CONTENT_ENCODING':'utf8',
                     'HTTP_X_OBJECT_MANIFEST':123,
                     'HTTP_X_OBJECT_META_TEST':'test3'}},
            {'name':'poodle_strut.mov',
             'meta':{'HTTP_ETAG':'99914b932bd37a50b983c5e7c90ae93b',
                     'HTTP_CONTENT-LENGTH':23,
                     'HTTP_CONTENT_TYPE':'image/jpeg',
                     'HTTP_CONTENT_ENCODING':'utf8',
                     'HTTP_X_OBJECT_MANIFEST':123,
                     'HTTP_X_OBJECT_META_TEST':'test4'}},
            {'name':'Disturbed - Down With The Sickness.mp3',
             'meta':{'HTTP_ETAG':'99914b932bd37a50b983c5e7c90ae93b',
                     'HTTP_CONTENT-LENGTH':23,
                     'HTTP_CONTENT_TYPE':'image/jpeg',
                     'HTTP_CONTENT_ENCODING':'utf8',
                     'HTTP_X_OBJECT_MANIFEST':123,
                     'HTTP_X_OBJECT_META_TEST':'test5'}},
            {'name':'army_of_darkness.avi',
             'meta':{'HTTP_ETAG':'99914b932bd37a50b983c5e7c90ae93b',
                     'HTTP_CONTENT-LENGTH':23,
                     'HTTP_CONTENT_TYPE':'image/jpeg',
                     'HTTP_CONTENT_ENCODING':'utf8',
                     'HTTP_X_OBJECT_MANIFEST':123,
                     'HTTP_X_OBJECT_META_':'test6'}},
            {'name':'the_mad.avi',
             'meta':{'HTTP_ETAG':'wrong-hash',
                     'HTTP_CONTENT-LENGTH':23,
                     'HTTP_CONTENT_TYPE':'image/jpeg',
                     'HTTP_CONTENT_ENCODING':'utf8',
                     'HTTP_X_OBJECT_MANIFEST':123,
                     'HTTP_X_OBJECT_META_TEST':'test7'}}
        ]
        for item in self.l[:-1]:
            response = self.upload_object(self.account, self.container[0], item['name'], json.dumps({}), **item['meta'])
        self.create_container(self.account, self.container[1])
        l = [
            {'name':'photos/animals/dogs/poodle.jpg',
             'meta':{'HTTP_ETAG':'99914b932bd37a50b983c5e7c90ae93b',
                     'HTTP_CONTENT-LENGTH':23,
                     'HTTP_CONTENT_TYPE':'image/jpeg',
                     'HTTP_CONTENT_ENCODING':'utf8',
                     'HTTP_X_OBJECT_MANIFEST':123,
                     'HTTP_X_OBJECT_META_TEST':'test1'}},
            {'name':'photos/animals/dogs/terrier.jpg',
             'meta':{'HTTP_ETAG':'99914b932bd37a50b983c5e7c90ae93b',
                     'HTTP_CONTENT-LENGTH':23,
                     'HTTP_CONTENT_TYPE':'image/jpeg',
                     'HTTP_CONTENT_ENCODING':'utf8',
                     'HTTP_X_OBJECT_MANIFEST':123,
                     'HTTP_X_OBJECT_META_TEST':'test1'}},
            {'name':'photos/animals/cats/persian.jpg',
             'meta':{'HTTP_ETAG':'99914b932bd37a50b983c5e7c90ae93b',
                     'HTTP_CONTENT-LENGTH':28,
                     'HTTP_CONTENT_TYPE':'application/pdf',
                     'HTTP_CONTENT_ENCODING':'utf8',
                     'HTTP_X_OBJECT_MANIFEST':123,
                     'HTTP_X_OBJECT_META_TEST':'test2'}},
            {'name':'photos/animals/cats/siamese.jpg',
             'meta':{'HTTP_ETAG':'99914b932bd37a50b983c5e7c90ae93b',
                     'HTTP_CONTENT-LENGTH':255,
                     'HTTP_CONTENT_TYPE':'image/jpeg',
                     'HTTP_CONTENT_ENCODING':'utf8',
                     'HTTP_X_OBJECT_MANIFEST':123,
                     'HTTP_X_OBJECT_META_TEST':'test3'}},
            {'name':'photos/plants/fern.jpg',
             'meta':{'HTTP_ETAG':'99914b932bd37a50b983c5e7c90ae93b',
                     'HTTP_CONTENT-LENGTH':23,
                     'HTTP_CONTENT_TYPE':'image/jpeg',
                     'HTTP_CONTENT_ENCODING':'utf8',
                     'HTTP_X_OBJECT_MANIFEST':123,
                     'HTTP_X_OBJECT_META_TEST':'test4'}},
            {'name':'photos/plants/rose.jpg',
             'meta':{'HTTP_ETAG':'99914b932bd37a50b983c5e7c90ae93b',
                     'HTTP_CONTENT-LENGTH':23,
                     'HTTP_CONTENT_TYPE':'image/jpeg',
                     'HTTP_CONTENT_ENCODING':'utf8',
                     'HTTP_X_OBJECT_MANIFEST':123,
                     'XHTTP__OBJECT_META_TEST':'test5'}},
            {'name':'photos/me.jpg',
             'meta':{'HTTP_ETAG':'99914b932bd37a50b983c5e7c90ae93b',
                     'HTTP_CONTENT-LENGTH':23,
                     'HTTP_CONTENT_TYPE':'image/jpeg',
                     'HTTP_CONTENT_ENCODING':'utf8',
                     'X_OBJECT_MANIFEST':123,
                     'HTTP_X_OBJECT_META_TEST':'test6'}},
        ]
        for item in l:
            response = self.upload_object(self.account, self.container[1], item['name'], json.dumps({}), **item['meta'])

    def tearDown(self):
        for c in self.container:
            self.delete_container_recursively(c)

    def delete_container_recursively(self, c):
        for obj in get_content_splitted(self.list_objects(self.account, c)):
            self.delete_object(self.account, c, obj)
        self.delete_container(self.account, c)

    def test_list_objects(self):
        response = self.list_objects(self.account, self.container[0])
        objects = get_content_splitted(response)
        l = [elem['name'] for elem in self.l[:-1]]
        l.sort()
        self.assertEqual(objects, l)

    def test_list_objects_with_limit_marker(self):
        response = self.list_objects(self.account, self.container[0], limit=2)
        objects = get_content_splitted(response)
        l = [elem['name'] for elem in self.l[:-1]]
        l.sort()
        self.assertEqual(objects, l[:2])
        
        response = self.list_objects(self.account, self.container[0], limit=4, marker='How To Win Friends And Influence People.pdf')
        objects = get_content_splitted(response)
        l = [elem['name'] for elem in self.l[:-1]]
        l.sort()
        self.assertEqual(objects, l[2:6])
        
        response = self.list_objects(self.account, self.container[0], limit=4, marker='moms_birthday.jpg')
        objects = get_content_splitted(response)
        l = [elem['name'] for elem in self.l[:-1]]
        l.sort()
        self.assertEqual(objects, l[-1:])

    def test_list_pseudo_hierarchical_folders(self):
        response = self.list_objects(self.account, self.container[1], prefix='photos', delimiter='/')
        objects = get_content_splitted(response)
        self.assertEquals(['photos/animals/', 'photos/me.jpg', 'photos/plants/'], objects)
        
        response = self.list_objects(self.account, self.container[1], prefix='photos/animals', delimiter='/')
        objects = get_content_splitted(response)
        self.assertEquals(['photos/animals/cats/', 'photos/animals/dogs/'], objects)
        
        response = self.list_objects(self.account, self.container[1], path='photos')
        objects = get_content_splitted(response)
        self.assertEquals(['photos/me.jpg'], objects)

    def test_extended_list_json(self):
        response = self.list_objects(self.account, self.container[1], format='json', limit=2, prefix='photos/animals', delimiter='/')
        objects = json.loads(response.content)
        self.assertEqual(objects[0]['subdir'], 'photos/animals/cats/')
        self.assertEqual(objects[1]['subdir'], 'photos/animals/dogs/')

    def test_extended_list_xml(self):
        response = self.list_objects(self.account, self.container[1], format='xml', limit=4, prefix='photos', delimiter='/')
        xml = minidom.parseString(response.content)
        dirs = xml.getElementsByTagName('subdir')
        self.assertEqual(len(dirs), 2)
        self.assertEqual(dirs[0].attributes['name'].value, 'photos/animals/')
        self.assertEqual(dirs[1].attributes['name'].value, 'photos/plants/')
        
        objects = xml.getElementsByTagName('name')
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0].childNodes[0].data, 'photos/me.jpg')

class ContainerMeta(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.container = 'apples'
        self.create_container(self.account, self.container)

    def tearDown(self):
        self.delete_container(self.account, self.container)

    def test_update_meta(self):
        meta = {'HTTP_X_CONTAINER_META_TEST':'test33', 'HTTP_X_CONTAINER_META_TOST':'tost22'}
        response = self.update_container_meta(self.account, self.container, **meta)
        response = self.get_container_meta(self.account, self.container)
        for k,v in meta.items():
            key = '-'.join(elem.capitalize() for elem in k.split('_')[1:])
            self.assertTrue(response[key])
            self.assertEqual(response[key], v)

class CreateContainer(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.containers = ['c1', 'c2']

    def tearDown(self):
        for c in self.containers:
            r = self.delete_container(self.account, c)

    def test_create(self):
        response = self.create_container(self.account, self.containers[0])
        if response.status_code == 201:
            response = self.list_containers(self.account)
            self.assertTrue(self.containers[0] in get_content_splitted(response))
            r = self.get_container_meta(self.account, self.containers[0])
            self.assertEqual(r.status_code, 204)

    def test_create_twice(self):
        response = self.create_container(self.account, self.containers[0])
        if response.status_code == 201:
            self.assertTrue(self.create_container(self.account, self.containers[0]).status_code, 202)

class DeleteContainer(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.containers = ['c1', 'c2']
        for c in self.containers:
            self.create_container(self.account, c)
        obj = {'name':'kate.jpg',
               'meta':{'HTTP_ETAG':'99914b932bd37a50b983c5e7c90ae93b',
                       'HTTP_CONTENT-LENGTH':23,
                       'HTTP_CONTENT_TYPE':'image/jpeg',
                       'HTTP_CONTENT_ENCODING':'utf8',
                       'HTTP_X_OBJECT_MANIFEST':123,
                       'HTTP_X_OBJECT_META_TEST':'test1'
                       }
                }
        self.upload_object(self.account, self.containers[1], obj['name'], json.dumps({}), **obj['meta'])

    def tearDown(self):
        for c in self.containers:
            for o in get_content_splitted(self.list_objects(self.account, c)):
                self.delete_object(self.account, c, o)
            self.delete_container(self.account, c)

    def test_delete(self):
        r = self.delete_container(self.account, self.containers[0])
        self.assertEqual(r.status_code, 204)

    def test_delete_non_empty(self):
        r = self.delete_container(self.account, self.containers[1])
        self.assertNonEmpty(r)

    def test_delete_invalid(self):
        self.assertItemNotFound(self.delete_container(self.account, 'c3'))

class GetObjects(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.containers = ['c1', 'c2']
        for c in self.containers:
            self.create_container(self.account, c)
        self.obj = {'name':'kate.jpg',
               'meta':{'HTTP_ETAG':'99914b932bd37a50b983c5e7c90ae93b',
                       'HTTP_CONTENT-LENGTH':23,
                       'HTTP_CONTENT_TYPE':'image/jpeg',
                       'HTTP_CONTENT_ENCODING':'utf8',
                       'HTTP_X_OBJECT_MANIFEST':123,
                       'HTTP_X_OBJECT_META_TEST':'test1'
                       }
                }
        self.upload_object(self.account, self.containers[1], self.obj['name'], json.dumps({}), **self.obj['meta'])

    def tearDown(self):
        for c in self.containers:
            for o in get_content_splitted(self.list_objects(self.account, c)):
                self.delete_object(self.account, c, o)
            self.delete_container(self.account, c)

    def test_get(self):
        r = self.get_object(self.account, self.containers[1], self.obj['name'])
        self.assertEqual(r.status_code, 200)

    def test_get_invalid(self):
        r = self.get_object(self.account, self.containers[0], self.obj['name'])
        self.assertItemNotFound(r)

    def test_get_with_range(self):
        return
    
    def test_get_with_if_match(self):
        return
    
    def test_get_with_if_none_match(self):
        return
    
    def test_get_with_if_modified_since(self):
        return
    
    def test_get_with_if_unmodified_since(self):
        return
    
    def test_get_with_several_headers(self):
        return

class UploadObject(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.account = 'test'
        self.container = 'c1'
        self.create_container(self.account, self.container)

    def tearDown(self):
        for o in get_content_splitted(self.list_objects(self.account, self.container)):
            self.delete_object(self.account, self.container, o)
        self.delete_container(self.account, self.container)
    
    def test_upload(self):
        filename = './api/tests.py'
        f = open(filename, 'r')
        data = f.read()
        hash = compute_hash(data)
        meta={'HTTP_ETAG':hash,
              'HTTP_CONTENT-LENGTH':os.path.getsize(filename),
              'HTTP_CONTENT_TYPE':'text/x-java',
              'HTTP_CONTENT_ENCODING':'us-ascii',
              'HTTP_X_OBJECT_MANIFEST':123,
              'HTTP_X_OBJECT_META_TEST':'test1'
              }
        r = self.upload_object(self.account, self.container, filename, data, content_type='plain/text',**meta)
        self.assertEqual(r.status_code, 201)
        
class AssertInvariant(object):
    def __init__(self, callable, *args, **kwargs):
        self.callable = callable
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        self.value = self.callable(*self.args, **self.kwargs)
        return self.value

    def __exit__(self, type, value, tb):
        assert self.value == self.callable(*self.args, **self.kwargs)

def get_content_splitted(response):
    if response:
        return response.content.split('\n')

def compute_hash(data):
    md5 = hashlib.md5()
    offset = 0
    md5.update(data)
    return md5.hexdigest().lower()