#
# Copyright (c) 2010 Greek Research and Technology Network
#

from email.utils import parsedate
from random import choice, randint, sample
from time import mktime

import datetime

from django.utils import simplejson as json
from django.test import TestCase
from django.test.client import Client

#from synnefo.api.tests_auth import AuthTestCase
from synnefo.db.models import *
from synnefo.logic import utils


class APITestCase(TestCase):
    fixtures = ['api_test_data']
    test_server_id = 1001
    test_image_id = 1
    test_flavor_id = 1
    test_group_id = 1
    test_wrong_server_id = 99999999
    test_wrong_image_id = 99999999
    test_wrong_flavor_id = 99999999
    test_wrong_group_id = 99999999
    #make the testing with these id's

    def setUp(self):
        self.client = Client()

    def test_api_version(self):
        """Check API version."""
        
        response = self.client.get('/api/v1.1/')
        self.assertEqual(response.status_code, 200)
        api_version = json.loads(response.content)['version']
        self.assertEqual(api_version['id'], 'v1.1')
        self.assertEqual(api_version['status'], 'CURRENT')

    def test_server_list(self):
        """Test if the expected list of servers is returned."""
        
        response = self.client.get('/api/v1.1/servers')
        vms_from_api = json.loads(response.content)['servers']['values']
        vms_from_db = VirtualMachine.objects.filter(deleted=False)
        self.assertEqual(len(vms_from_api), len(vms_from_db))
        self.assertTrue(response.status_code in [200, 203])
        for vm_from_api in vms_from_api:
            vm_from_db = VirtualMachine.objects.get(id=vm_from_api['id'])
            self.assertEqual(vm_from_api['id'], vm_from_db.id)
            self.assertEqual(vm_from_api['name'], vm_from_db.name)

    def test_server_details(self):
        """Test if the expected server is returned."""
        
        response = self.client.get('/api/v1.1/servers/%d' % self.test_server_id)
        vm_from_api = json.loads(response.content)['server']
        vm_from_db = VirtualMachine.objects.get(id=self.test_server_id)
        self.assertEqual(vm_from_api['flavorRef'], vm_from_db.flavor.id)
        self.assertEqual(vm_from_api['hostId'], vm_from_db.hostid)
        self.assertEqual(vm_from_api['id'], vm_from_db.id)
        self.assertEqual(vm_from_api['imageRef'], vm_from_db.flavor.id)
        self.assertEqual(vm_from_api['name'], vm_from_db.name)
        self.assertEqual(vm_from_api['status'], utils.get_rsapi_state(vm_from_db))
        self.assertTrue(response.status_code in [200, 203])

    def test_servers_details(self):
        """Test if the servers details are returned."""
        
        response = self.client.get('/api/v1.1/servers/detail')

        # Make sure both DB and API responses are sorted by id,
        # to allow for 1-1 comparisons
        vms_from_db = VirtualMachine.objects.filter(deleted=False).order_by('id')
        vms_from_api = json.loads(response.content)['servers']['values']
        vms_from_api = sorted(vms_from_api, key=lambda vm: vm['id'])
        self.assertEqual(len(vms_from_db), len(vms_from_api))

        id_list = [vm.id for vm in vms_from_db]
        number = 0
        for vm_id in id_list:
            vm_from_api = vms_from_api[number]
            vm_from_db = VirtualMachine.objects.get(id=vm_id)
            self.assertEqual(vm_from_api['flavorRef'], vm_from_db.flavor.id)
            self.assertEqual(vm_from_api['hostId'], vm_from_db.hostid)
            self.assertEqual(vm_from_api['id'], vm_from_db.id)
            self.assertEqual(vm_from_api['imageRef'], vm_from_db.flavor.id)
            self.assertEqual(vm_from_api['name'], vm_from_db.name)
            self.assertEqual(vm_from_api['status'], utils.get_rsapi_state(vm_from_db))
            number += 1
        for vm_from_api in vms_from_api:
            vm_from_db = VirtualMachine.objects.get(id=vm_from_api['id'])
            self.assertEqual(vm_from_api['flavorRef'], vm_from_db.flavor.id)
            self.assertEqual(vm_from_api['hostId'], vm_from_db.hostid)
            self.assertEqual(vm_from_api['id'], vm_from_db.id)
            self.assertEqual(vm_from_api['imageRef'], vm_from_db.flavor.id)
            self.assertEqual(vm_from_api['name'], vm_from_db.name)
            self.assertEqual(vm_from_api['status'], utils.get_rsapi_state(vm_from_db))
        self.assertTrue(response.status_code in [200,203])

    def test_wrong_server(self):
        """Test 404 response if server does not exist."""
        
        response = self.client.get('/api/v1.1/servers/%d' % self.test_wrong_server_id)
        self.assertEqual(response.status_code, 404)

    def test_create_server_empty(self):
        """Test if the create server call returns a 400 badRequest if
           no attributes are specified."""
        
        response = self.client.post('/api/v1.1/servers', {})
        self.assertEqual(response.status_code, 400)

    def test_create_server(self):
        """Test if the create server call returns the expected response
           if a valid request has been speficied."""
        
        request = {
                    "server": {
                        "name": "new-server-test",
                        "imageRef": 1,
                        "flavorRef": 1,
                        "metadata": {
                            "My Server Name": "Apache1"
                        },
                        "personality": []
                    }
        }
        response = self.client.post('/api/v1.1/servers', json.dumps(request),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 202)
        #TODO: check response.content
        #TODO: check create server with wrong options (eg non existing flavor)

    def test_server_polling(self):
        """Test if the server polling works as expected."""
        
        response = self.client.get('/api/v1.1/servers/detail')
        vms_from_api_initial = json.loads(response.content)['servers']['values']
        ts = mktime(parsedate(response['Date']))
        since = datetime.datetime.fromtimestamp(ts).isoformat() + 'Z'
        response = self.client.get('/api/v1.1/servers/detail?changes-since=%s' % since)
        self.assertEqual(len(response.content), 0)

        #now create a machine. Then check if it is on the list
        request = {
                    "server": {
                        "name": "new-server-test",
                        "imageRef": 1,
                        "flavorRef": 1,
                        "metadata": {
                            "My Server Name": "Apache1"
                        },
                        "personality": []
                    }
        }
        
        path = '/api/v1.1/servers'
        response = self.client.post(path, json.dumps(request), content_type='application/json')
        self.assertEqual(response.status_code, 202)

        response = self.client.get('/api/v1.1/servers/detail?changes-since=%s' % since)
        self.assertEqual(response.status_code, 200)
        vms_from_api_after = json.loads(response.content)['servers']['values']
        #make sure the newly created server is included on the updated list
        self.assertEqual(len(vms_from_api_after), 1)

    def test_reboot_server(self):
        """Test if the specified server is rebooted."""
        
        request = {'reboot': {'type': 'HARD'}}
        path = '/api/v1.1/servers/%d/action' % self.test_server_id
        response = self.client.post(path, json.dumps(request), content_type='application/json')
        self.assertEqual(response.status_code, 202)
        #server id that does not exist
        path = '/api/v1.1/servers/%d/action' % self.test_wrong_server_id
        response = self.client.post(path, json.dumps(request), content_type='application/json')
        self.assertEqual(response.status_code, 404)

    def test_shutdown_server(self):
        """Test if the specified server is shutdown."""
        
        request = {'shutdown': {}}
        path = '/api/v1.1/servers/%d/action' % self.test_server_id
        response = self.client.post(path, json.dumps(request), content_type='application/json')
        self.assertEqual(response.status_code, 202)
        #server id that does not exist
        path = '/api/v1.1/servers/%d/action' % self.test_wrong_server_id
        response = self.client.post(path, json.dumps(request), content_type='application/json')
        self.assertEqual(response.status_code, 404)

    def test_start_server(self):
        """Test if the specified server is started."""
        
        request = {'start': {}}
        path = '/api/v1.1/servers/%d/action' % self.test_server_id
        response = self.client.post(path, json.dumps(request), content_type='application/json')
        self.assertEqual(response.status_code, 202)
        #server id that does not exist
        path = '/api/v1.1/servers/%d/action' % self.test_wrong_server_id
        response = self.client.post(path, json.dumps(request), content_type='application/json')
        self.assertEqual(response.status_code, 404)

    def test_delete_server(self):
        """Test if the specified server is deleted."""
        response = self.client.delete('/api/v1.1/servers/%d' % self.test_server_id)
        self.assertEqual(response.status_code, 204)
        #server id that does not exist
        response = self.client.delete('/api/v1.1/servers/%d' % self.test_wrong_server_id)
        self.assertEqual(response.status_code, 404)

    def test_flavor_list(self):
        """Test if the expected list of flavors is returned by."""
        
        response = self.client.get('/api/v1.1/flavors')
        flavors_from_api = json.loads(response.content)['flavors']['values']
        flavors_from_db = Flavor.objects.all()
        self.assertEqual(len(flavors_from_api), len(flavors_from_db))
        self.assertTrue(response.status_code in [200, 203])
        for flavor_from_api in flavors_from_api:
            flavor_from_db = Flavor.objects.get(id=flavor_from_api['id'])
            self.assertEqual(flavor_from_api['id'], flavor_from_db.id)
            self.assertEqual(flavor_from_api['name'], flavor_from_db.name)

    def test_flavors_details(self):
        """Test if the flavors details are returned."""
        
        response = self.client.get('/api/v1.1/flavors/detail')
        flavors_from_db = Flavor.objects.all()
        flavors_from_api = json.loads(response.content)['flavors']['values']

        # Assert that all flavors in the db appear inthe API call result
        for i in range(0, len(flavors_from_db)):
            flavor_from_api = flavors_from_api[i]
            flavor_from_db = Flavor.objects.get(id=flavors_from_db[i].id)
            self.assertEqual(flavor_from_api['cpu'], flavor_from_db.cpu)
            self.assertEqual(flavor_from_api['id'], flavor_from_db.id)
            self.assertEqual(flavor_from_api['disk'], flavor_from_db.disk)
            self.assertEqual(flavor_from_api['name'], flavor_from_db.name)
            self.assertEqual(flavor_from_api['ram'], flavor_from_db.ram)

        # Assert that all flavors returned by the API also exist in the db
        for flavor_from_api in flavors_from_api:
            flavor_from_db = Flavor.objects.get(id=flavor_from_api['id'])
            self.assertEqual(flavor_from_api['cpu'], flavor_from_db.cpu)
            self.assertEqual(flavor_from_api['id'], flavor_from_db.id)
            self.assertEqual(flavor_from_api['disk'], flavor_from_db.disk)
            self.assertEqual(flavor_from_api['name'], flavor_from_db.name)
            self.assertEqual(flavor_from_api['ram'], flavor_from_db.ram)

        # Check if we have the right status_code
        self.assertTrue(response.status_code in [200, 203])

    def test_flavor_details(self):
        """Test if the expected flavor is returned."""
        
        response = self.client.get('/api/v1.1/flavors/%d' % self.test_flavor_id)
        flavor_from_api = json.loads(response.content)['flavor']
        flavor_from_db = Flavor.objects.get(id=self.test_flavor_id)
        self.assertEqual(flavor_from_api['cpu'], flavor_from_db.cpu)
        self.assertEqual(flavor_from_api['id'], flavor_from_db.id)
        self.assertEqual(flavor_from_api['disk'], flavor_from_db.disk)
        self.assertEqual(flavor_from_api['name'], flavor_from_db.name)
        self.assertEqual(flavor_from_api['ram'], flavor_from_db.ram)
        self.assertTrue(response.status_code in [200, 203])

    def test_wrong_flavor(self):
        """Test 404 result when requesting a flavor that does not exist."""
        
        response = self.client.get('/api/v1.1/flavors/%d' % self.test_wrong_flavor_id)
        self.assertTrue(response.status_code in [404, 503])

    def test_image_list(self):
        """Test if the expected list of images is returned by the API."""
        
        response = self.client.get('/api/v1.1/images')
        images_from_api = json.loads(response.content)['images']['values']
        images_from_db = Image.objects.all()
        self.assertEqual(len(images_from_api), len(images_from_db))
        self.assertTrue(response.status_code in [200, 203])
        for image_from_api in images_from_api:
            image_from_db = Image.objects.get(id=image_from_api['id'])
            self.assertEqual(image_from_api['id'], image_from_db.id)
            self.assertEqual(image_from_api['name'], image_from_db.name)

    def test_image_details(self):
        """Test if the expected image is returned."""
        
        response = self.client.get('/api/v1.1/images/%d' % self.test_image_id)
        image_from_api = json.loads(response.content)['image']
        image_from_db = Image.objects.get(id=self.test_image_id)
        self.assertEqual(image_from_api['name'], image_from_db.name)
        self.assertEqual(image_from_api['id'], image_from_db.id)
        self.assertEqual(image_from_api.get('serverRef', ''),
                        image_from_db.sourcevm and image_from_db.sourcevm.id or '')
        self.assertEqual(image_from_api['status'], image_from_db.state)
        self.assertTrue(response.status_code in [200, 203])

    def test_images_details(self):
        """Test if the images details are returned."""
        
        response = self.client.get('/api/v1.1/images/detail')
        images_from_api = json.loads(response.content)['images']['values']
        images_from_db = Image.objects.all()
        for i in range(0, len(images_from_db)):
            image_from_db = Image.objects.get(id=images_from_db[i].id)
            image_from_api = images_from_api[i]
            self.assertEqual(image_from_api['name'], image_from_db.name)
            self.assertEqual(image_from_api['id'], image_from_db.id)
            self.assertEqual(image_from_api.get('serverRef', ''),
                             image_from_db.sourcevm and
                             image_from_db.sourcevm.id or "")
            self.assertEqual(image_from_api['status'], image_from_db.state)

        for image_from_api in images_from_api:
            image_from_db = Image.objects.get(id=image_from_api['id'])
            self.assertEqual(image_from_api['name'], image_from_db.name)
            self.assertEqual(image_from_api['id'], image_from_db.id)
            self.assertEqual(image_from_api.get('serverRef', ''),
                             image_from_db.sourcevm and
                             image_from_db.sourcevm.id or "")
            self.assertEqual(image_from_api['status'], image_from_db.state)

        self.assertTrue(response.status_code in [200, 203])

    def test_wrong_image(self):
        """Test 404 result if a non existent image is requested."""
        
        response = self.client.get('/api/v1.1/images/%d' % self.test_wrong_image_id)
        self.assertEqual(response.status_code, 404)

    def test_server_metadata(self):
        """Test server's metadata (add, edit)."""
        
        key = 'name'
        request = {'meta': {key: 'a fancy name'}}
        
        path = '/api/v1.1/servers/%d/meta/%s' % (self.test_server_id, key)
        response = self.client.put(path, json.dumps(request), content_type='application/json')
        self.assertEqual(response.status_code, 201)


def create_users(n=1):
    for i in range(n):
        SynnefoUser.objects.create(
            name='User %d' % i,
            credit=0)

def create_flavors(n=1):
    for i in range(n):
        Flavor.objects.create(
            cpu=randint(1, 4),
            ram=randint(1, 8) * 512,
            disk=randint(1, 40))

def create_images(n=1):
    users = SynnefoUser.objects.all()
    for i in range(n):
        Image.objects.create(
            name='Image %d' % (i + 1),
            state='ACTIVE',
            owner=choice(users))

def create_servers(n=1):
    users = SynnefoUser.objects.all()
    flavors = Flavor.objects.all()
    images = Image.objects.all()
    for i in range(n):
        VirtualMachine.objects.create(
            name='Server %d' % (i + 1),
            owner=choice(users),
            sourceimage=choice(images),
            hostid=str(i),
            ipfour='0.0.0.0',
            ipsix='::1',
            flavor=choice(flavors))

def create_server_metadata(n=1):
    servers = VirtualMachine.objects.all()
    for i in range(n):
        VirtualMachineMetadata.objects.create(
            meta_key='Key%d' % (i + 1),
            meta_value='Value %d' % (i + 1),
            vm = choice(servers))


class BaseTestCase(TestCase):
    USERS = 1
    FLAVORS = 1
    IMAGES = 1
    SERVERS = 1
    SERVER_METADATA = 0
    
    def setUp(self):
        self.client = Client()
        create_users(self.USERS)
        create_flavors(self.FLAVORS)
        create_images(self.IMAGES)
        create_servers(self.SERVERS)
        create_server_metadata(self.SERVER_METADATA)
    
    def assertFault(self, response, status_code, name):
        self.assertEqual(response.status_code, status_code)
        fault = json.loads(response.content)
        self.assertEqual(fault.keys(), [name])
    
    def assertBadRequest(self, response):
        self.assertFault(response, 400, 'badRequest')

    def assertItemNotFound(self, response):
        self.assertFault(response, 404, 'itemNotFound')
    
    def get_server_metadata(self, server_id):
        vm_meta = VirtualMachineMetadata.objects.filter(vm=int(server_id))
        return dict((m.meta_key, m.meta_value) for m in vm_meta)
    
    def verify_server_metadata(self, server_id, metadata):
        server_metadata = self.get_server_metadata(server_id)
        self.assertEqual(server_metadata, metadata)


class ListServerMetadata(BaseTestCase):
    SERVERS = 4
    
    def list_metadata(self, server_id):
        response = self.client.get('/api/v1.1/servers/%d/meta' % server_id)
        self.assertTrue(response.status_code in (200, 203))
        reply = json.loads(response.content)
        self.assertEqual(reply.keys(), ['metadata'])
        self.assertEqual(reply['metadata'].keys(), ['values'])
        return reply['metadata']['values']
    
    def verify_all_metadata(self):
        for vm in VirtualMachine.objects.all():
            server_metadata = self.get_server_metadata(vm.id)
            response_metadata = self.list_metadata(vm.id)
            self.assertEqual(response_metadata, server_metadata)
    
    def test_list_metadata(self):
        self.verify_all_metadata()
        create_server_metadata(100)
        self.verify_all_metadata()
    
    def test_invalid_server(self):
        response = self.client.get('/api/v1.1/servers/100/meta')
        self.assertItemNotFound(response)


class UpdateServerMetadata(BaseTestCase):
    SERVER_METADATA = 10
    
    def update_meta(self, metadata):
        path = '/api/v1.1/servers/1/meta'
        data = json.dumps({'metadata': metadata})
        response = self.client.post(path, data, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        reply = json.loads(response.content)
        self.assertEqual(reply.keys(), ['metadata'])
        return reply['metadata']
    
    def test_update_metadata(self):
        metadata = self.get_server_metadata(1)
        new_metadata = {}
        for key in sample(metadata.keys(), 3):
            new_metadata[key] = 'New %s value' % key
        response_metadata = self.update_meta(new_metadata)
        self.assertEqual(response_metadata, new_metadata)
        metadata.update(new_metadata)
        self.verify_server_metadata(1, metadata)
    
    def test_does_not_create(self):
        metadata = self.get_server_metadata(1)
        new_metadata = {'Foo': 'Bar'}
        response_metadata = self.update_meta(new_metadata)
        self.assertEqual(response_metadata, {})
        self.verify_server_metadata(1, metadata)
    
    def test_invalid_data(self):
        metadata = self.get_server_metadata(1)
        path = '/api/v1.1/servers/1/meta'
        response = self.client.post(path, 'metadata', content_type='application/json')
        self.assertBadRequest(response)
        self.verify_server_metadata(1, metadata)
    
    def test_invalid_server(self):
        metadata = self.get_server_metadata(1)
        path = '/api/v1.1/servers/2/meta'
        data = json.dumps({'metadata': {'Key1': 'A Value'}})
        response = self.client.post(path, data, content_type='application/json')
        self.assertItemNotFound(response)
        self.verify_server_metadata(1, metadata)


class GetServerMetadataItem(BaseTestCase):
    SERVER_METADATA = 10
    
    def test_get_metadata_item(self):
        metadata = self.get_server_metadata(1)
        key = choice(metadata.keys())
        path = '/api/v1.1/servers/1/meta/' + key
        response = self.client.get(path)
        self.assertTrue(response.status_code in (200, 203))
        reply = json.loads(response.content)
        self.assertEqual(reply['meta'], {key: metadata[key]})
        self.verify_server_metadata(1, metadata)
    
    def test_invalid_key(self):
        metadata = self.get_server_metadata(1)
        response = self.client.get('/api/v1.1/servers/1/meta/foo')
        self.assertItemNotFound(response)
        self.verify_server_metadata(1, metadata)
    
    def test_invalid_server(self):
        metadata = self.get_server_metadata(1)
        response = self.client.get('/api/v1.1/servers/2/meta/foo')
        self.assertItemNotFound(response)
        self.verify_server_metadata(1, metadata)


class CreateServerMetadataItem(BaseTestCase):
    SERVER_METADATA = 10
    
    def create_meta(self, meta):
        key = meta.keys()[0]
        path = '/api/v1.1/servers/1/meta/' + key
        data = json.dumps({'meta': meta})
        response = self.client.put(path, data, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        reply = json.loads(response.content)
        self.assertEqual(reply.keys(), ['meta'])
        response_meta = reply['meta']
        self.assertEqual(response_meta, meta)
    
    def test_create_metadata(self):
        metadata = self.get_server_metadata(1)
        meta = {'Foo': 'Bar'}
        self.create_meta(meta)
        metadata.update(meta)
        self.verify_server_metadata(1, metadata)
    
    def test_update_metadata(self):
        metadata = self.get_server_metadata(1)
        key = choice(metadata.keys())
        meta = {key: 'New Value'}
        self.create_meta(meta)
        metadata.update(meta)
        self.verify_server_metadata(1, metadata)
    
    def test_invalid_server(self):
        metadata = self.get_server_metadata(1)
        path = '/api/v1.1/servers/2/meta/foo'
        data = json.dumps({'meta': {'foo': 'bar'}})
        response = self.client.put(path, data, content_type='application/json')
        self.assertItemNotFound(response)
        self.verify_server_metadata(1, metadata)
    
    def test_invalid_key(self):
        metadata = self.get_server_metadata(1)
        path = '/api/v1.1/servers/1/meta/baz'
        data = json.dumps({'meta': {'foo': 'bar'}})
        response = self.client.put(path, data, content_type='application/json')
        self.assertBadRequest(response)
        self.verify_server_metadata(1, metadata)
    
    def test_invalid_data(self):
        metadata = self.get_server_metadata(1)
        path = '/api/v1.1/servers/1/meta/foo'
        response = self.client.put(path, 'meta', content_type='application/json')
        self.assertBadRequest(response)
        self.verify_server_metadata(1, metadata)


class DeleteServerMetadataItem(BaseTestCase):
    SERVER_METADATA = 10
    
    def test_delete_metadata(self):
        metadata = self.get_server_metadata(1)
        key = choice(metadata.keys())
        path = '/api/v1.1/servers/1/meta/' + key
        response = self.client.delete(path)
        self.assertEqual(response.status_code, 204)
        metadata.pop(key)
        self.verify_server_metadata(1, metadata)
    
    def test_invalid_server(self):
        metadata = self.get_server_metadata(1)
        response = self.client.delete('/api/v1.1/servers/2/meta/Key1')
        self.assertItemNotFound(response)
        self.verify_server_metadata(1, metadata)
    
    def test_invalid_key(self):
        metadata = self.get_server_metadata(1)
        response = self.client.delete('/api/v1.1/servers/1/meta/foo')
        self.assertItemNotFound(response)
        self.verify_server_metadata(1, metadata)
