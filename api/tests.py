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
from synnefo.db.models import VirtualMachine, Flavor, Image, VirtualMachineGroup

class APITestCase(TestCase):
    fixtures = [ 'api_test_data' ]
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
        self.assertEqual(vm_from_api['flavorRef'], vm_from_db.flavor.id)
        self.assertEqual(vm_from_api['hostId'], vm_from_db.hostid)
        self.assertEqual(vm_from_api['id'], vm_from_db.id)
        self.assertEqual(vm_from_api['imageRef'], vm_from_db.flavor.id)
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
            self.assertEqual(vm_from_api['flavorRef'], vm_from_db.flavor.id)
            self.assertEqual(vm_from_api['hostId'], vm_from_db.hostid)
            self.assertEqual(vm_from_api['id'], vm_from_db.id)
            self.assertEqual(vm_from_api['imageRef'], vm_from_db.flavor.id)
            self.assertEqual(vm_from_api['name'], vm_from_db.name)
            self.assertEqual(vm_from_api['status'], vm_from_db.rsapi_state)
            number += 1
        vms_from_api = json.loads(response.content)['servers']
        for vm_from_api in vms_from_api:
            vm_from_db = VirtualMachine.objects.get(id=vm_from_api['id'])
            self.assertEqual(vm_from_api['flavorRef'], vm_from_db.flavor.id)
            self.assertEqual(vm_from_api['hostId'], vm_from_db.hostid)
            self.assertEqual(vm_from_api['id'], vm_from_db.id)
            self.assertEqual(vm_from_api['imageRef'], vm_from_db.flavor.id)
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
                        "imageRef"       : 1,
                        "flavorRef"      : 1,
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
        flavors_from_db = Flavor.objects.all()
        flavors_from_api = json.loads(response.content)['flavors']
        
        # Assert that all flavors in the db appear inthe API call result
        for i in range(0, len(flavors_from_db)):
            flavor_from_api = flavors_from_api[i]
            flavor_from_db = Flavor.objects.get(id=flavors_from_db[i].id)
            self.assertEqual(flavor_from_api['cpu'], flavor_from_db.cpu)
            self.assertEqual(flavor_from_api['id'], flavor_from_db.id)
            self.assertEqual(flavor_from_api['disk'], flavor_from_db.disk)
            self.assertEqual(flavor_from_api['name'], flavor_from_db.name)
            self.assertEqual(flavor_from_api['ram'], flavor_from_db.ram)

        # Assert that all flavors that appear in the API call result are also in the db             
        for flavor_from_api in flavors_from_api:
            flavor_from_db = Flavor.objects.get(id=flavor_from_api['id'])
            self.assertEqual(flavor_from_api['cpu'], flavor_from_db.cpu)
            self.assertEqual(flavor_from_api['id'], flavor_from_db.id)
            self.assertEqual(flavor_from_api['disk'], flavor_from_db.disk)
            self.assertEqual(flavor_from_api['name'], flavor_from_db.name)
            self.assertEqual(flavor_from_api['ram'], flavor_from_db.ram)
        
        # Check if we have the right status_code
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
        self.assertTrue(response.status_code in [404, 503])

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
        images_from_api = json.loads(response.content)['images']
        images_from_db = Image.objects.all()
        for i in range(0, len(images_from_db)):
            image_from_db = Image.objects.get(id=images_from_db[i].id)
            image_from_api = images_from_api[i]
            self.assertEqual(image_from_api['name'], image_from_db.name)
            self.assertEqual(image_from_api['id'], image_from_db.id)
            self.assertEqual(image_from_api['serverId'], image_from_db.sourcevm and image_from_db.sourcevm.id or "")
            self.assertEqual(image_from_api['size'], image_from_db.size)
            self.assertEqual(image_from_api['status'], image_from_db.state)
            self.assertEqual(image_from_api['description'], image_from_db.description)

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


    def testServerMetadata(self):
        """ test server's metadata (add, edit)
        """
        request = {
            "metadata": {"metadata_key" : "name", "metadata_value" : "a fancy name"}
            }
        response = self.client.put('/api/v1.0/servers' + str(self.test_server_id), 
                                    json.dumps(request),
                                    content_type='application/json')  
        self.assertEqual(response.status_code, 404)
        #TODO: not working atm, due to problem with django piston and PUT

    def testVMgroupList(self):
        """ test if the expected list of groups is returned by the API
        """        
        response = self.client.get('/api/v1.0/groups')
        groups_from_api = json.loads(response.content)['groups']
        groups_from_db = VirtualMachineGroup.objects.all()
        self.assertEqual(len(groups_from_api), len(groups_from_db))
        self.assertTrue(response.status_code in [200,203])
        for group_from_api in groups_from_api:
            group_from_db = VirtualMachineGroup.objects.get(id=group_from_api['id'])
            self.assertEqual(group_from_api['id'], group_from_db.id)
            self.assertEqual(group_from_api['name'], group_from_db.name)

    def testVMgroupDetails(self):
        """ test if the expected virtual machine group is returned by the API
        """
        response = self.client.get('/api/v1.0/groups/' + str(self.test_group_id))
        group_from_api = json.loads(response.content)['group']
        group_from_db = VirtualMachineGroup.objects.get(id=self.test_group_id)
        self.assertEqual(group_from_api['name'], group_from_db.name)
        self.assertEqual(group_from_api['id'], group_from_db.id)
        self.assertEqual(group_from_api['server_id'], [machine.id for machine in group_from_db.machines.all()])
        self.assertTrue(response.status_code in [200,203])

    def testWrongVMgroup(self):
        """ test if a non existent VMgroup is asked, if a 404 itemNotFound returned
        """
        response = self.client.get('/api/v1.0/groups/' + str(self.test_wrong_group_id))
        self.assertEqual(response.status_code, 404)

    def testgroupsDetails(self):
        """ test if the groups details are returned by the API
        """
        response = self.client.get('/api/v1.0/groups/detail')
        groups_from_api = json.loads(response.content)['groups']
        groups_from_db = VirtualMachineGroup.objects.all()
        for i in range(0, len(groups_from_db)):
            group_from_db = VirtualMachineGroup.objects.get(id=groups_from_db[i].id)
            group_from_api = groups_from_api[i]
            self.assertEqual(group_from_api['name'], group_from_db.name)
            self.assertEqual(group_from_api['id'], group_from_db.id)
            self.assertEqual(group_from_api['server_id'], [machine.id for machine in group_from_db.machines.all()])
        for group_from_api in groups_from_api:
            group_from_db = VirtualMachineGroup.objects.get(id=group_from_api['id'])
            self.assertEqual(group_from_api['name'], group_from_db.name)
            self.assertEqual(group_from_api['id'], group_from_db.id)
            self.assertEqual(group_from_api['server_id'], [machine.id for machine in group_from_db.machines.all()])            
        self.assertTrue(response.status_code in [200,203])

