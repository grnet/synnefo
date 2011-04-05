#
# Copyright (c) 2010 Greek Research and Technology Network
#

import datetime

from django.utils import simplejson as json
from django.test import TestCase
from django.test.client import Client

#from synnefo.api.tests_auth import AuthTestCase
from synnefo.db.models import VirtualMachine, VirtualMachineGroup
from synnefo.db.models import Flavor, Image
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
        vms_from_db = VirtualMachine.objects.filter(deleted=False)
        id_list = [vm.id for vm in vms_from_db]
        number = 0
        for vm_id in id_list:
            vm_from_api = json.loads(response.content)['servers']['values'][number]
            vm_from_db = VirtualMachine.objects.get(id=vm_id)
            self.assertEqual(vm_from_api['flavorRef'], vm_from_db.flavor.id)
            self.assertEqual(vm_from_api['hostId'], vm_from_db.hostid)
            self.assertEqual(vm_from_api['id'], vm_from_db.id)
            self.assertEqual(vm_from_api['imageRef'], vm_from_db.flavor.id)
            self.assertEqual(vm_from_api['name'], vm_from_db.name)
            self.assertEqual(vm_from_api['status'], utils.get_rsapi_state(vm_from_db))
            number += 1
        vms_from_api = json.loads(response.content)['servers']['values']
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
        then = datetime.datetime.now().isoformat().split('.')[0] + 'Z'

        #isoformat also gives miliseconds that are not needed
        response = self.client.get('/api/v1.1/servers/detail?changes-since=%s' % then)
        self.assertEqual(len(response.content), 0)
        #no changes were made

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

        response = self.client.get('/api/v1.1/servers/detail?changes-since=%s' % then)
        vms_from_api_after = json.loads(response.content)['servers']
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


class APITestCase2(TestCase):
    """An attempt for a more thorough test scenario."""
    
    fixtures = [ 'api_test_data2' ]

    def setUp(self):
        self.client = Client()
        self.server_id = 0

    def create_server_name(self):
        self.server_id += 1
        return 'server%d' % self.server_id

    def test_create_server_json(self):
        TEMPLATE = '''
        {
            "server" : {
                "name" : "%(name)s",
                "flavorRef" : "%(flavorRef)s",
                "imageRef" : "%(imageRef)s"
            }
        }
        '''

        def new_server(imageRef=1, flavorRef=1):
            name = self.create_server_name()
            return name, TEMPLATE % dict(name=name, imageRef=imageRef, flavorRef=flavorRef)

        def verify_response(response, name):
            assert response.status_code == 202
            reply =  json.loads(response.content)
            server = reply['server']
            assert server['name'] == name
            assert server['imageRef'] == 1
            assert server['flavorRef'] == 1
            assert server['status'] == 'BUILD'
            assert server['adminPass']
            assert server['addresses']

        def verify_error(response, code, name):
            assert response.status_code == code
            reply =  json.loads(response.content)
            assert name in reply
            assert reply[name]['code'] == code

        name, data = new_server()
        url = '/api/v1.1/servers'
        response = self.client.post(url, content_type='application/json', data=data)
        verify_response(response, name)

        name, data = new_server()
        url = '/api/v1.1/servers.json'
        response = self.client.post(url, content_type='application/json', data=data)
        verify_response(response, name)

        name, data = new_server()
        url = '/api/v1.1/servers.json'
        response = self.client.post(url, content_type='application/json', data=data,
                                    HTTP_ACCEPT='application/xml')
        verify_response(response, name)

        name, data = new_server(imageRef=0)
        url = '/api/v1.1/servers'
        response = self.client.post(url, content_type='application/json', data=data)
        verify_error(response, 404, 'itemNotFound')

        name, data = new_server(flavorRef=0)
        url = '/api/v1.1/servers'
        response = self.client.post(url, content_type='application/json', data=data)
        verify_error(response, 404, 'itemNotFound')

        url = '/api/v1.1/servers'
        response = self.client.post(url, content_type='application/json', data='INVALID')
        verify_error(response, 400, 'badRequest')
