#
# Unit Tests for api
#
# Provides automated tests for api module
#
# Copyright 2011 Greek Research and Technology Network
#

from django.test import TestCase
from django.test.client import Client
import simplejson as json
from synnefo.db.models import VirtualMachine, Flavor, Image

class APITestCase(TestCase):
    fixtures = [ 'api_test_data' ]
    test_server_id = 1001
    test_image_id = 1
    test_flavor_id = 1
    test_wrong_server_id = 99999999
    test_wrong_image_id = 99999999
    test_wrong_flavor_id = 99999999
    #make the testing with these id's


    def setUp(self):
        self.client = Client()

    def testAPIVersion(self):
        """ check rackspace cloud servers API version
        """
        response = self.client.get('/api/v1.0/')
        # Check that the response is 200 OK.
        self.assertEqual(response.status_code, 200)
        api_version = json.loads(response.content)['version']
        self.assertEqual(api_version['status'], 'CURRENT')
        self.assertEqual(api_version['wadl'], 'http://docs.rackspacecloud.com/servers/api/v1.0/application.wadl')
        self.assertEqual(api_version['docURL'], 'http://docs.rackspacecloud.com/servers/api/v1.0/cs-devguide-20110112.pdf')
        self.assertEqual(api_version['id'], 'v1.0')


    def testServerList(self):
        """ test if the expected list of servers is returned by the API
        """        
        response = self.client.get('/api/v1.0/servers')
        vms_from_api = json.loads(response.content)['servers']
        vms_from_db = VirtualMachine.objects.filter(deleted=False)
        self.assertEqual(len(vms_from_api), len(vms_from_db))
        self.assertTrue(response.status_code in [200,203])
        for vm_from_api in vms_from_api:
            vm_from_db = VirtualMachine.objects.get(id=vm_from_api['id'])
            self.assertEqual(vm_from_api['id'], vm_from_db.id)
            self.assertEqual(vm_from_api['name'], vm_from_db.name)


    def testServerDetails(self):
        """ test if the expected server is returned by the API
        """        
        response = self.client.get('/api/v1.0/servers/' + str(self.test_server_id))
        vm_from_api = json.loads(response.content)['server']
        vm_from_db = VirtualMachine.objects.get(id=self.test_server_id)
        self.assertEqual(vm_from_api['flavorId'], vm_from_db.flavor.id)
        self.assertEqual(vm_from_api['hostId'], vm_from_db.hostid)
        self.assertEqual(vm_from_api['id'], vm_from_db.id)
        self.assertEqual(vm_from_api['imageId'], vm_from_db.flavor.id)
        self.assertEqual(vm_from_api['name'], vm_from_db.name)
        self.assertEqual(vm_from_api['status'], vm_from_db.rsapi_state)
        self.assertTrue(response.status_code in [200,203])


    def testServersDetails(self):
        """ test if the servers details are returned by the API
        """
        response = self.client.get('/api/v1.0/servers/detail')     
        vms_from_db = VirtualMachine.objects.filter(deleted=False)
        id_list = [vm.id for vm in vms_from_db]
        number = 0
        for vm_id in id_list:
            vm_from_api = json.loads(response.content)['servers'][number]
            vm_from_db = VirtualMachine.objects.get(id=vm_id)
            self.assertEqual(vm_from_api['flavorId'], vm_from_db.flavor.id)
            self.assertEqual(vm_from_api['hostId'], vm_from_db.hostid)
            self.assertEqual(vm_from_api['id'], vm_from_db.id)
            self.assertEqual(vm_from_api['imageId'], vm_from_db.flavor.id)
            self.assertEqual(vm_from_api['name'], vm_from_db.name)
            self.assertEqual(vm_from_api['status'], vm_from_db.rsapi_state)
            number += 1
        vms_from_api = json.loads(response.content)['servers']
        for vm_from_api in vms_from_api:
            vm_from_db = VirtualMachine.objects.get(id=vm_from_api['id'])
            self.assertEqual(vm_from_api['flavorId'], vm_from_db.flavor.id)
            self.assertEqual(vm_from_api['hostId'], vm_from_db.hostid)
            self.assertEqual(vm_from_api['id'], vm_from_db.id)
            self.assertEqual(vm_from_api['imageId'], vm_from_db.flavor.id)
            self.assertEqual(vm_from_api['name'], vm_from_db.name)
            self.assertEqual(vm_from_api['status'], vm_from_db.rsapi_state)            
        self.assertTrue(response.status_code in [200,203])


    def testWrongServer(self):
        """ test if a non existent server is asked, if a 404 itemNotFound returned
        """
        response = self.client.get('/api/v1.0/servers/' + str(self.test_wrong_server_id))
        self.assertEqual(response.status_code, 404)


    def testCreateServerEmpty(self):
        """ test if the create server call returns a 400 badRequest if no
            attributes are specified
        """
        response = self.client.post('/api/v1.0/servers',{})
        self.assertEqual(response.status_code, 400)


    def testCreateServer(self):
        """ test if the create server call returns the expected response
            if a valid request has been speficied
        """
        request = {
                    "server": {
                        "name"          : "new-server-test",
                        "imageId"       : 1,
                        "flavorId"      : 1,
                        "metadata"      : {
                            "My Server Name": "Apache1"
                        },
                        "personality"   : []
                    }
        }
        response = self.client.post('/api/v1.0/servers', 
                                    json.dumps(request), 
                                    content_type='application/json')
        self.assertEqual(response.status_code, 202)
        #TODO: check response.content      
        #TODO: check create server with wrong options (eg flavor that not exist)
    

    def testRebootServer(self):
        """ test if the specified server is rebooted
        """
        request = {
            "reboot": '{"type" : "HARD"}'
            }
        response = self.client.post('/api/v1.0/servers/' + str(self.test_server_id) + '/action', 
                                    json.dumps(request),
                                    content_type='application/json')  
        self.assertEqual(response.status_code, 202)
        #server id that does not exist
        response = self.client.post('/api/v1.0/servers/' + str(self.test_wrong_server_id) + '/action', 
                                   json.dumps(request), 
                                   content_type='application/json')
        self.assertEqual(response.status_code, 404)


    def testShutdownServer(self):
        """ test if the specified server is shutdown
        """
        request = {
            "shutdown": {"timeout" : "5"}
            }
        response = self.client.post('/api/v1.0/servers/' + str(self.test_server_id) + '/action',
                                    json.dumps(request), 
                                    content_type='application/json')  
        self.assertEqual(response.status_code, 202)
        #server id that does not exist
        response = self.client.post('/api/v1.0/servers/' + str(self.test_wrong_server_id) + '/action',
                                    json.dumps(request), 
                                    content_type='application/json')
        self.assertEqual(response.status_code, 404)


    def testStartServer(self):
        """ test if the specified server is started
        """
        request = {
            "start": {"type" : "NORMAL"}
            }
        response = self.client.post('/api/v1.0/servers/' + str(self.test_server_id) + '/action', 
                                    json.dumps(request),
                                    content_type='application/json')  
        self.assertEqual(response.status_code, 202)
        #server id that does not exist
        response = self.client.post('/api/v1.0/servers/' + str(self.test_wrong_server_id) + '/action', 
                                    json.dumps(request), 
                                    content_type='application/json')
        self.assertEqual(response.status_code, 404)

    def testDeleteServer(self):
        """ test if the specified server is deleted
        """
        response = self.client.delete('/api/v1.0/servers/' + str(self.test_server_id))
        self.assertEqual(response.status_code, 202)
        #server id that does not exist      
        response = self.client.delete('/api/v1.0/servers/' + str(self.test_wrong_server_id))  
        self.assertEqual(response.status_code, 404)


    def testFlavorList(self):
        """ test if the expected list of flavors is returned by the API
        """        
        response = self.client.get('/api/v1.0/flavors')
        flavors_from_api = json.loads(response.content)['flavors']
        flavors_from_db = Flavor.objects.all()
        self.assertEqual(len(flavors_from_api), len(flavors_from_db))
        self.assertTrue(response.status_code in [200,203])
        for flavor_from_api in flavors_from_api:
            flavor_from_db = Flavor.objects.get(id=flavor_from_api['id'])
            self.assertEqual(flavor_from_api['id'], flavor_from_db.id)
            self.assertEqual(flavor_from_api['name'], flavor_from_db.name)


    def testFlavorsDetails(self):
        """ test if the flavors details are returned by the API
        """
        response = self.client.get('/api/v1.0/flavors/detail')     
        for number in range(0, len(Flavor.objects.all())):
            flavor_from_api = json.loads(response.content)['flavors'][number]
            flavor_from_db = Flavor.objects.get(id=number+1)
            self.assertEqual(flavor_from_api['cpu'], flavor_from_db.cpu)
            self.assertEqual(flavor_from_api['id'], flavor_from_db.id)
            self.assertEqual(flavor_from_api['disk'], flavor_from_db.disk)
            self.assertEqual(flavor_from_api['name'], flavor_from_db.name)
            self.assertEqual(flavor_from_api['ram'], flavor_from_db.ram)
        flavors_from_api = json.loads(response.content)['flavors']
        for flavor_from_api in flavors_from_api:
            flavor_from_db = Flavor.objects.get(id=flavor_from_api['id'])
            self.assertEqual(flavor_from_api['cpu'], flavor_from_db.cpu)
            self.assertEqual(flavor_from_api['id'], flavor_from_db.id)
            self.assertEqual(flavor_from_api['disk'], flavor_from_db.disk)
            self.assertEqual(flavor_from_api['name'], flavor_from_db.name)
            self.assertEqual(flavor_from_api['ram'], flavor_from_db.ram)
        self.assertTrue(response.status_code in [200,203])


    def testFlavorDetails(self):
        """ test if the expected flavor is returned by the API
        """
        response = self.client.get('/api/v1.0/flavors/' + str(self.test_flavor_id))
        flavor_from_api = json.loads(response.content)['flavor']
        flavor_from_db = Flavor.objects.get(id=self.test_flavor_id)
        self.assertEqual(flavor_from_api['cpu'], flavor_from_db.cpu)
        self.assertEqual(flavor_from_api['id'], flavor_from_db.id)
        self.assertEqual(flavor_from_api['disk'], flavor_from_db.disk)
        self.assertEqual(flavor_from_api['name'], flavor_from_db.name)
        self.assertEqual(flavor_from_api['ram'], flavor_from_db.ram)
        self.assertTrue(response.status_code in [200,203])


    def testWrongFlavor(self):
        """ test if a non existent flavor is asked, if a 404 itemNotFound returned
        """
        response = self.client.get('/api/v1.0/flavors/' + str(self.test_wrong_flavor_id))
        self.assertEqual(response.status_code, 404)


    def testImageList(self):
        """ test if the expected list of images is returned by the API
        """        
        response = self.client.get('/api/v1.0/images')
        images_from_api = json.loads(response.content)['images']
        images_from_db = Image.objects.all()
        self.assertEqual(len(images_from_api), len(images_from_db))
        self.assertTrue(response.status_code in [200,203])
        for image_from_api in images_from_api:
            image_from_db = Image.objects.get(id=image_from_api['id'])
            self.assertEqual(image_from_api['id'], image_from_db.id)
            self.assertEqual(image_from_api['name'], image_from_db.name)


    def testImageDetails(self):
        """ test if the expected image is returned by the API
        """
        response = self.client.get('/api/v1.0/images/' + str(self.test_image_id))
        image_from_api = json.loads(response.content)['image']
        image_from_db = Image.objects.get(id=self.test_image_id)
        self.assertEqual(image_from_api['name'], image_from_db.name)
        self.assertEqual(image_from_api['id'], image_from_db.id)
        self.assertEqual(image_from_api['serverId'], image_from_db.sourcevm and image_from_db.sourcevm.id or "")
        self.assertEqual(image_from_api['size'], image_from_db.size)
        self.assertEqual(image_from_api['status'], image_from_db.state)
        self.assertEqual(image_from_api['description'], image_from_db.description)
        self.assertTrue(response.status_code in [200,203])


    def testImagesDetails(self):
        """ test if the images details are returned by the API
        """
        response = self.client.get('/api/v1.0/images/detail')     
        for number in range(0, len(Image.objects.all())):
            image_from_api = json.loads(response.content)['images'][number]
            image_from_db = Image.objects.get(id=number+1)
            self.assertEqual(image_from_api['name'], image_from_db.name)
            self.assertEqual(image_from_api['id'], image_from_db.id)
            self.assertEqual(image_from_api['serverId'], image_from_db.sourcevm and image_from_db.sourcevm.id or "")
            self.assertEqual(image_from_api['size'], image_from_db.size)
            self.assertEqual(image_from_api['status'], image_from_db.state)
            self.assertEqual(image_from_api['description'], image_from_db.description)
        images_from_api = json.loads(response.content)['images']
        for image_from_api in images_from_api:
            image_from_db = Image.objects.get(id=image_from_api['id'])
            self.assertEqual(image_from_api['name'], image_from_db.name)
            self.assertEqual(image_from_api['id'], image_from_db.id)
            self.assertEqual(image_from_api['serverId'], image_from_db.sourcevm and image_from_db.sourcevm.id or "")
            self.assertEqual(image_from_api['size'], image_from_db.size)
            self.assertEqual(image_from_api['status'], image_from_db.state)
            self.assertEqual(image_from_api['description'], image_from_db.description)
        self.assertTrue(response.status_code in [200,203])


    def testWrongImage(self):
        """ test if a non existent image is asked, if a 404 itemNotFound returned
        """
        response = self.client.get('/api/v1.0/images/' + str(self.test_wrong_image_id))
        self.assertEqual(response.status_code, 404)
