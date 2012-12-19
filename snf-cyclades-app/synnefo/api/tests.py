# Copyright 2012 GRNET S.A. All rights reserved.
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

from __future__ import with_statement

from django.utils import simplejson as json
from django.test import TestCase

from mock import patch, Mock
from contextlib import contextmanager
from functools import wraps

from synnefo.db.models import *
from synnefo.db import models_factory as mfactory
from synnefo.logic.utils import get_rsapi_state

from synnefo.api import faults


@contextmanager
def astakos_user(user):
    """
    Context manager to mock astakos response.

    usage:
    with astakos_user("user@user.com"):
        .... make api calls ....

    """
    def dummy_get_user(request, *args, **kwargs):
        request.user = {'username': user, 'groups': []}
        request.user_uniq = user

    with patch('synnefo.api.util.get_user') as m:
        m.side_effect = dummy_get_user
        yield


class BaseAPITest(TestCase):
    def get(self, url, user='user', *args, **kwargs):
        with astakos_user(user):
            response = self.client.get(url, *args, **kwargs)
        return response

    def delete(self, url, user='user'):
        with astakos_user(user):
            response = self.client.delete(url)
        return response

    def post(self, url, user='user', params={}, ctype='json', *args, **kwargs):
        if ctype == 'json':
            content_type = 'application/json'
        with astakos_user(user):
            response = self.client.post(url, params, content_type=content_type,
                                        *args, **kwargs)
        return response

    def put(self, url, user='user', params={}, ctype='json', *args, **kwargs):
        if ctype == 'json':
            content_type = 'application/json'
        with astakos_user(user):
            response = self.client.put(url, params, content_type=content_type,
                    *args, **kwargs)
        return response

    def assertSuccess(self, response):
        self.assertTrue(response.status_code in [200, 203, 204])

    def assertFault(self, response, status_code, name):
        self.assertEqual(response.status_code, status_code)
        fault = json.loads(response.content)
        self.assertEqual(fault.keys(), [name])

    def assertBadRequest(self, response):
        self.assertFault(response, 400, 'badRequest')

    def assertItemNotFound(self, response):
        self.assertFault(response, 404, 'itemNotFound')


class FlavorAPITest(BaseAPITest):

    def setUp(self):
        self.flavor1 = mfactory.FlavorFactory()
        self.flavor2 = mfactory.FlavorFactory(deleted=True)
        self.flavor3 = mfactory.FlavorFactory()

    def test_flavor_list(self):
        """Test if the expected list of flavors is returned by."""
        response = self.get('/api/v1.1/flavors')
        self.assertSuccess(response)

        flavors_from_api = json.loads(response.content)['flavors']['values']
        flavors_from_db = Flavor.objects.filter(deleted=False)
        self.assertEqual(len(flavors_from_api), len(flavors_from_db))
        for flavor_from_api in flavors_from_api:
            flavor_from_db = Flavor.objects.get(id=flavor_from_api['id'])
            self.assertEqual(flavor_from_api['id'], flavor_from_db.id)
            self.assertEqual(flavor_from_api['name'], flavor_from_db.name)

    def test_flavors_details(self):
        """Test if the flavors details are returned."""
        response = self.get('/api/v1.1/flavors/detail')
        self.assertSuccess(response)

        flavors_from_db = Flavor.objects.filter(deleted=False)
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

    def test_flavor_details(self):
        """Test if the expected flavor is returned."""
        flavor = self.flavor3

        response = self.get('/api/v1.1/flavors/%d' % flavor.id)
        self.assertSuccess(response)

        flavor_from_api = json.loads(response.content)['flavor']
        flavor_from_db = Flavor.objects.get(id=flavor.id)
        self.assertEqual(flavor_from_api['cpu'], flavor_from_db.cpu)
        self.assertEqual(flavor_from_api['id'], flavor_from_db.id)
        self.assertEqual(flavor_from_api['disk'], flavor_from_db.disk)
        self.assertEqual(flavor_from_api['name'], flavor_from_db.name)
        self.assertEqual(flavor_from_api['ram'], flavor_from_db.ram)

    def test_deleted_flavor_details(self):
        """Test that API returns details for deleted flavors"""
        flavor = self.flavor2
        response = self.get('/api/v1.1/flavors/%d' % flavor.id)
        self.assertSuccess(response)
        flavor_from_api = json.loads(response.content)['flavor']
        self.assertEquals(flavor_from_api['name'], flavor.name)

    def test_deleted_flavors_list(self):
        """Test that deleted flavors do not appear to flavors list"""
        response = self.get('/api/v1.1/flavors')
        self.assertSuccess(response)
        flavors_from_api = json.loads(response.content)['flavors']['values']
        self.assertEqual(len(flavors_from_api), 2)

    def test_deleted_flavors_details(self):
        """Test that deleted flavors do not appear to flavors detail list"""
        mfactory.FlavorFactory(deleted=True)
        response = self.get('/api/v1.1/flavors/detail')
        self.assertSuccess(response)
        flavors_from_api = json.loads(response.content)['flavors']['values']
        self.assertEqual(len(flavors_from_api), 2)

    def test_wrong_flavor(self):
        """Test 404 result when requesting a flavor that does not exist."""

        response = self.get('/api/v1.1/flavors/%d' % 22)
        self.assertItemNotFound(response)


class ServerAPITest(BaseAPITest):
    def setUp(self):
        self.user1 = 'user1'
        self.user2 = 'user2'
        self.vm1 = mfactory.VirtualMachineFactory(userid=self.user1)
        self.vm2 = mfactory.VirtualMachineFactory(userid=self.user2)
        self.vm3 = mfactory.VirtualMachineFactory(deleted=True,
                                                  userid=self.user1)
        self.vm4 = mfactory.VirtualMachineFactory(userid=self.user2)

    def test_server_list_1(self):
        """Test if the expected list of servers is returned."""
        response = self.get('/api/v1.1/servers')
        self.assertSuccess(response)
        servers = json.loads(response.content)['servers']['values']
        self.assertEqual(servers, [])

    def test_server_list_2(self):
        """Test if the expected list of servers is returned."""
        response = self.get('/api/v1.1/servers', self.user1)
        self.assertSuccess(response)
        servers = json.loads(response.content)['servers']['values']
        db_server = self.vm1
        self.assertEqual(servers, [{'name': db_server.name,
                                    'id': db_server.id}])

    def test_server_list_detail(self):
        """Test if the servers list details are returned."""
        user = self.user2
        user_vms = {self.vm2.id: self.vm2,
                    self.vm4.id: self.vm4}

        response = self.get('/api/v1.1/servers/detail', user)
        servers = json.loads(response.content)['servers']['values']
        self.assertEqual(len(servers), len(user_vms))
        for api_vm in servers:
            db_vm = user_vms[api_vm['id']]
            self.assertEqual(api_vm['flavorRef'], db_vm.flavor.id)
            self.assertEqual(api_vm['hostId'], db_vm.hostid)
            self.assertEqual(api_vm['id'], db_vm.id)
            self.assertEqual(api_vm['imageRef'], db_vm.imageid)
            self.assertEqual(api_vm['name'], db_vm.name)
            self.assertEqual(api_vm['status'], get_rsapi_state(db_vm))
            self.assertSuccess(response)

    def test_server_detail(self):
        """Test if a server details are returned."""
        db_vm = self.vm2
        user = self.vm2.userid
        db_vm_meta = mfactory.VirtualMachineMetadataFactory(vm=db_vm)

        response = self.get('/api/v1.1/servers/%d' % db_vm.id, user)
        server = json.loads(response.content)['server']

        self.assertEqual(server['flavorRef'], db_vm.flavor.id)
        self.assertEqual(server['hostId'], db_vm.hostid)
        self.assertEqual(server['id'], db_vm.id)
        self.assertEqual(server['imageRef'], db_vm.imageid)
        self.assertEqual(server['name'], db_vm.name)
        self.assertEqual(server['status'], get_rsapi_state(db_vm))

        metadata = server['metadata']['values']
        self.assertEqual(len(metadata), 1)
        self.assertEqual(metadata[db_vm_meta.meta_key], db_vm_meta.meta_value)
        self.assertSuccess(response)

    def test_noauthorized(self):
        """Test 404 for detail of other user vm"""
        db_vm = self.vm2

        response = self.get('/api/v1.1/servers/%d' % db_vm.id, 'wrong_user')
        self.assertItemNotFound(response)

    def test_wrong_server(self):
        """Test 404 response if server does not exist."""
        response = self.get('/api/v1.1/servers/%d' % 5000)
        self.assertItemNotFound(response)

    def test_create_server_empty(self):
        """Test if the create server call returns a 400 badRequest if
           no attributes are specified."""

        response = self.post('/api/v1.1/servers', params={})
        self.assertBadRequest(response)


@patch('synnefo.api.util.get_image')
@patch('synnefo.logic.rapi_pool.GanetiRapiClient')
class ServerCreateAPITest(BaseAPITest):
    def test_create_server(self, mrapi, mimage):
        """Test if the create server call returns the expected response
           if a valid request has been speficied."""
        mimage.return_value = {'location': 'pithos://foo',
                               'disk_format': 'diskdump'}
        mrapi().CreateInstance.return_value = 12
        flavor = mfactory.FlavorFactory()
        # Create public network and backend
        network = mfactory.NetworkFactory(public=True)
        backend = mfactory.BackendFactory()
        mfactory.BackendNetworkFactory(network=network, backend=backend)

        request = {
                    "server": {
                        "name": "new-server-test",
                        "userid": "test_user",
                        "imageRef": 1,
                        "flavorRef": flavor.id,
                        "metadata": {
                            "My Server Name": "Apache1"
                        },
                        "personality": []
                    }
        }
        response = self.post('/api/v1.1/servers', 'test_user',
                                 json.dumps(request), 'json')
        self.assertEqual(response.status_code, 202)
        mrapi().CreateInstance.assert_called_once()

        api_server = json.loads(response.content)['server']
        self.assertEqual(api_server['status'], "BUILD")
        self.assertEqual(api_server['progress'], 0)
        self.assertEqual(api_server['metadata']['values'],
                        {"My Server Name":  "Apache1"})
        self.assertTrue('adminPass' in api_server)

        db_vm = VirtualMachine.objects.get(userid='test_user')
        self.assertEqual(api_server['name'], db_vm.name)
        self.assertEqual(api_server['status'], db_vm.operstate)

    def test_create_server_no_flavor(self, mrapi, mimage):
        request = {
                    "server": {
                        "name": "new-server-test",
                        "userid": "test_user",
                        "imageRef": 1,
                        "flavorRef": 42,
                        "metadata": {
                            "My Server Name": "Apache1"
                        },
                        "personality": []
                    }
        }
        response = self.post('/api/v1.1/servers', 'test_user',
                                 json.dumps(request), 'json')
        self.assertItemNotFound(response)


@patch('synnefo.logic.rapi_pool.GanetiRapiClient')
class ServerDestroyAPITest(BaseAPITest):
    def test_delete_server(self, mrapi):
        vm = mfactory.VirtualMachineFactory()
        response = self.delete('/api/v1.1/servers/%d' % vm.id, vm.userid)
        self.assertEqual(response.status_code, 204)
        mrapi().DeleteInstance.assert_called_once()

    def test_non_existing_delete_server(self, mrapi):
        vm = mfactory.VirtualMachineFactory()
        response = self.delete('/api/v1.1/servers/%d' % 42, vm.userid)
        self.assertItemNotFound(response)
        mrapi().DeleteInstance.assert_not_called()


@patch('synnefo.api.util.get_image')
@patch('synnefo.logic.rapi_pool.GanetiRapiClient')
class ServerActionAPITest(BaseAPITest):
    def test_actions(self, mrapi, mimage):
        actions = ['start', 'shutdown', 'reboot']
        vm = mfactory.VirtualMachineFactory()
        vm.operstate = "STOPPED"
        vm.save()
        for action in actions:
            val = {'type': 'HARD'} if action == 'reboot' else {}
            request = {action: val}
            response = self.post('/api/v1.1/servers/%d/action' % vm.id,
                                vm.userid, json.dumps(request), 'json')
            self.assertEqual(response.status_code, 202)
            if action == 'shutdown':
                self.assertEqual(VirtualMachine.objects.get(id=vm.id).action,
                                 "STOP")
            else:
                self.assertEqual(VirtualMachine.objects.get(id=vm.id).action,
                                 action.upper())

    def test_firewall(self, mrapi, mimage):
        vm = mfactory.VirtualMachineFactory()
        vm.operstate = "STOPPED"
        vm.save()
        request = {'firewallProfile': {'profile': 'PROTECTED'}}
        response = self.post('/api/v1.1/servers/%d/action' % vm.id,
                             vm.userid, json.dumps(request), 'json')
        self.assertEqual(response.status_code, 202)
        mrapi().ModifyInstance.assert_called_once()


class ServerMetadataAPITest(BaseAPITest):
    def setUp(self):
        self.vm = mfactory.VirtualMachineFactory()
        self.metadata = mfactory.VirtualMachineMetadataFactory(vm=self.vm)

    def test_get_metadata(self):
        vm = self.vm
        create_meta = lambda: mfactory.VirtualMachineMetadataFactory(vm=vm)
        metadata = [create_meta(), create_meta(), create_meta()]
        response = self.get('/api/v1.1/servers/%d/meta' % vm.id, vm.userid)
        self.assertTrue(response.status_code in [200, 203])
        api_metadata = json.loads(response.content)['metadata']['values']
        self.assertEqual(len(api_metadata), len(metadata) + 1)
        for db_m in metadata:
            self.assertEqual(api_metadata[db_m.meta_key], db_m.meta_value)

        request = {'metadata':
                        {'foo': 'bar'},
                        metadata[0].meta_key: 'bar2'
                  }
        response = self.post('/api/v1.1/servers/%d/meta' % vm.id, vm.userid,
                             json.dumps(request), 'json')
        metadata2 = VirtualMachineMetadata.objects.filter(vm=vm)
        response = self.get('/api/v1.1/servers/%d/meta' % vm.id, vm.userid)
        self.assertTrue(response.status_code in [200, 203])
        api_metadata2 = json.loads(response.content)['metadata']['values']
        self.assertTrue('foo' in api_metadata2.keys())
        self.assertTrue(api_metadata2[metadata[0].meta_key], 'bar2')
        self.assertEqual(len(api_metadata2), len(metadata2))
        for db_m in metadata2:
            self.assertEqual(api_metadata2[db_m.meta_key], db_m.meta_value)

        # Create new meta
        request = {'meta': {'foo2': 'bar2'}}
        response = self.put('/api/v1.1/servers/%d/meta/foo2' % vm.id,
                            vm.userid, json.dumps(request), 'json')

        # Get the new meta
        response = self.get('/api/v1.1/servers/%d/meta/foo2' % vm.id,
                            vm.userid)
        meta = json.loads(response.content)['meta']
        self.assertEqual(meta['foo2'], 'bar2')

        # Delete the new meta
        response = self.delete('/api/v1.1/servers/%d/meta/foo2' % vm.id,
                               vm.userid)
        self.assertEqual(response.status_code, 204)

        # Try to get the deleted meta: should raise 404
        response = self.get('/api/v1.1/servers/%d/meta/foo2' % vm.id,
                            vm.userid)
        self.assertEqual(response.status_code, 404)

    def test_invalid_metadata(self):
        vm = self.vm
        response = self.post('/api/v1.1/servers/%d/meta' % vm.id, vm.userid)
        self.assertBadRequest(response)
        self.assertEqual(len(vm.metadata.all()), 1)

    def test_invalid_metadata_server(self):
        response = self.post('/api/v1.1/servers/42/meta', 'user')
        self.assertItemNotFound(response)

    def test_get_meta_invalid_key(self):
        vm = self.vm
        response = self.get('/api/v1.1/servers/%d/meta/foo2' % vm.id,
                            vm.userid)
        self.assertItemNotFound(response)


@patch('synnefo.logic.rapi_pool.GanetiRapiClient')
class NetworkAPITest(BaseAPITest):
    def setUp(self):
        self.mac_prefixes = mfactory.MacPrefixPoolTableFactory()
        self.bridges = mfactory.BridgePoolTableFactory()
        self.user = 'dummy-user'
        self.net1 = mfactory.NetworkFactory(userid=self.user)
        self.net2 = mfactory.NetworkFactory(userid=self.user)

    def assertNetworksEqual(self, db_net, api_net, detail=False):
        self.assertEqual(str(db_net.id), api_net["id"])
        self.assertEqual(db_net.name, api_net['name'])
        if detail:
            self.assertEqual(db_net.state, api_net['status'])
            self.assertEqual(db_net.flavor, api_net['type'])
            self.assertEqual(db_net.subnet, api_net['cidr'])
            self.assertEqual(db_net.subnet6, api_net['cidr6'])
            self.assertEqual(db_net.gateway, api_net['gateway'])
            self.assertEqual(db_net.gateway6, api_net['gateway6'])
            self.assertEqual(db_net.dhcp, api_net['dhcp'])

    def test_create_network_1(self, mrapi):
        request = {
            'network': {'name': 'foo'}
            }
        response = self.post('/api/v1.1/networks/', 'user1',
                             json.dumps(request), 'json')
        self.assertEqual(response.status_code, 202)
        db_networks = Network.objects.filter(userid='user1')
        self.assertEqual(len(db_networks), 1)
        db_net = db_networks[0]
        api_net = json.loads(response.content)['network']
        self.assertNetworksEqual(db_net, api_net)
        mrapi.CreateNetwork.assert_called()
        mrapi.ConnectNetwork.assert_called()

    def test_invalid_data_1(self, mrapi):
        """Test invalid flavor"""
        request = {
            'network': {'name': 'foo', 'type': 'LoLo'}
            }
        response = self.post('/api/v1.1/networks/', 'user1',
                             json.dumps(request), 'json')
        self.assertBadRequest(response)
        self.assertEqual(len(Network.objects.filter(userid='user1')), 0)

    def test_invalid_data_2(self, mrapi):
        """Test invalid subnet"""
        request = {
            'network': {'name': 'foo', 'cidr': '10.0.0.0/8'}
            }
        response = self.post('/api/v1.1/networks/', 'user1',
                             json.dumps(request), 'json')
        self.assertFault(response, 413, "overLimit")

    def test_invalid_data_3(self, mrapi):
        """Test unauthorized to create public network"""
        request = {
                'network': {'name': 'foo', 'public': True}
            }
        response = self.post('/api/v1.1/networks/', 'user1',
                             json.dumps(request), 'json')
        self.assertFault(response, 403, "forbidden")

    def test_list_networks(self, mrapi):
        mfactory.NetworkFactory(userid=self.user, deleted=True)
        response = self.get('/api/v1.1/networks/', self.user)
        self.assertSuccess(response)
        db_nets = Network.objects.filter(userid=self.user, deleted=False)
        api_nets = json.loads(response.content)["networks"]["values"]
        self.assertEqual(len(db_nets), len(api_nets))
        for api_net in api_nets:
            net_id = api_net['id']
            self.assertNetworksEqual(Network.objects.get(id=net_id), api_net)

    def test_list_networks_detail(self, mrapi):
        mfactory.NetworkFactory(userid=self.user, deleted=True)
        response = self.get('/api/v1.1/networks/detail', self.user)
        self.assertSuccess(response)
        db_nets = Network.objects.filter(userid=self.user, deleted=False)
        api_nets = json.loads(response.content)["networks"]["values"]
        self.assertEqual(len(db_nets), len(api_nets))
        for api_net in api_nets:
            net_id = api_net['id']
            self.assertNetworksEqual(Network.objects.get(id=net_id), api_net,
                                     detail=True)

    def test_network_details_1(self, mrapi):
        response = self.get('/api/v1.1/networks/%d' % self.net1.id,
                            self.net1.userid)
        self.assertSuccess(response)
        api_net = json.loads(response.content)["network"]
        self.assertNetworksEqual(self.net1, api_net, detail=True)

    def test_invalid_network(self, mrapi):
        response = self.get('/api/v1.1/networks/%d' % 42,
                            self.net1.userid)
        self.assertItemNotFound(response)

    def test_rename_network(self, mrapi):
        request = {'network': {'name': "new_name"}}
        response = self.put('/api/v1.1/networks/%d' % self.net2.id,
                            self.net2.userid, json.dumps(request), 'json')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Network.objects.get(id=self.net2.id).name, "new_name")

    def test_rename_public_network(self, mrapi):
        net = mfactory.NetworkFactory(public=True)
        request = {'network': {'name': "new_name"}}
        response = self.put('/api/v1.1/networks/%d' % net.id,
                            self.net2.userid, json.dumps(request), 'json')
        self.assertFault(response, 403, 'forbidden')

    def test_delete_network(self, mrapi):
        response = self.delete('/api/v1.1/networks/%d' % self.net2.id,
                                self.net2.userid)
        self.assertEqual(response.status_code, 204)
        net = Network.objects.get(id=self.net2.id, userid=self.net2.userid)
        self.assertEqual(net.action, 'DESTROY')
        mrapi.DeleteNetwork.assert_called()

    def test_delete_public_network(self, mrapi):
        net = mfactory.NetworkFactory(public=True)
        response = self.delete('/api/v1.1/networks/%d' % net.id,
                                self.net2.userid)
        self.assertFault(response, 403, 'forbidden')
        mrapi.DeleteNetwork.assert_not_called()

    def test_add_nic(self, mrapi):
        user = 'userr'
        vm = mfactory.VirtualMachineFactory(name='yo', userid=user)
        net = mfactory.NetworkFactory(state='ACTIVE', userid=user)
        request = {'add': {'serverRef': vm.id}}
        response = self.post('/api/v1.1/networks/%d/action' % net.id,
                             net.userid, json.dumps(request), 'json')
        self.assertEqual(response.status_code, 202)

    def test_add_nic_malformed(self, mrapi):
        user = 'userr'
        vm = mfactory.VirtualMachineFactory(name='yo', userid=user)
        net = mfactory.NetworkFactory(state='ACTIVE', userid=user)
        request = {'add': {'serveRef': vm.id}}
        response = self.post('/api/v1.1/networks/%d/action' % net.id,
                             net.userid, json.dumps(request), 'json')
        self.assertBadRequest(response)

    def test_remove_nic(self, mrapi):
        user = 'userr'
        vm = mfactory.VirtualMachineFactory(name='yo', userid=user)
        net = mfactory.NetworkFactory(state='ACTIVE', userid=user)
        nic = mfactory.NetworkInterfaceFactory(machine=vm, network=net)
        request = {'remove': {'attachment': 'nic-%s-%s' % (vm.id, nic.index)}}
        response = self.post('/api/v1.1/networks/%d/action' % net.id,
                             net.userid, json.dumps(request), 'json')
        self.assertEqual(response.status_code, 202)
        self.assertTrue(NetworkInterface.objects.get(id=nic.id).dirty)
        # Remove dirty nic
        response = self.post('/api/v1.1/networks/%d/action' % net.id,
                             net.userid, json.dumps(request), 'json')
        self.assertFault(response, 409, 'buildInProgress')

    def test_remove_nic_malformed(self, mrapi):
        user = 'userr'
        vm = mfactory.VirtualMachineFactory(name='yo', userid=user)
        net = mfactory.NetworkFactory(state='ACTIVE', userid=user)
        nic = mfactory.NetworkInterfaceFactory(machine=vm, network=net)
        request = {'remove':
                    {'att234achment': 'nic-%s-%s' % (vm.id, nic.index)}
                  }
        response = self.post('/api/v1.1/networks/%d/action' % net.id,
                             net.userid, json.dumps(request), 'json')
        self.assertBadRequest(response)


class ServerVNCConsole(BaseAPITest):

    def test_not_active_server(self):
        """Test console req for not ACTIVE server returns badRequest"""
        vm = mfactory.VirtualMachineFactory()
        data = json.dumps({'console': {'type': 'vnc'}})
        response = self.post('/api/v1.1/servers/%d/action' % vm.id,
                             vm.userid, data, 'json')
        self.assertBadRequest(response)

    def test_active_server(self):
        """Test console req for ACTIVE server"""
        vm = mfactory.VirtualMachineFactory()
        vm.operstate = 'STARTED'
        vm.save()

        data = json.dumps({'console': {'type': 'vnc'}})
        response = self.post('/api/v1.1/servers/%d/action' % vm.id,
                             vm.userid, data, 'json')
        self.assertEqual(response.status_code, 200)
        reply = json.loads(response.content)
        self.assertEqual(reply.keys(), ['console'])
        console = reply['console']
        self.assertEqual(console['type'], 'vnc')
        self.assertEqual(set(console.keys()),
                         set(['type', 'host', 'port', 'password']))


def assert_backend_closed(func):
    @wraps(func)
    def wrapper(self, backend):
        result = func(self, backend)
        if backend.called is True:
            backend.return_value.close.assert_called_once_with()
        return result
    return wrapper


@patch('synnefo.api.images.ImageBackend')
class ImageAPITest(BaseAPITest):
    @assert_backend_closed
    def test_create_image(self, mimage):
        """Test that create image is not implemented"""
        response = self.post('/api/v1.1/images/', 'user', json.dumps(''),
                             'json')
        self.assertEqual(response.status_code, 503)

    @assert_backend_closed
    def test_list_images(self, mimage):
        """Test that expected list of images is returned"""
        images = [{'id': 1, 'name': 'image-1'},
                  {'id': 2, 'name': 'image-2'},
                  {'id': 3, 'name': 'image-3'}]
        mimage().list.return_value = images
        response = self.get('/api/v1.1/images/', 'user')
        self.assertSuccess(response)
        api_images = json.loads(response.content)['images']['values']
        self.assertEqual(images, api_images)

    @assert_backend_closed
    def test_list_images_detail(self, mimage):
        images = [{'id': 1,
                   'name': 'image-1',
                   'status':'available',
                   'created_at': '2012-11-26 11:52:54',
                   'updated_at': '2012-12-26 11:52:54',
                   'deleted_at': '',
                   'properties': {'foo':'bar'}},
                  {'id': 2,
                   'name': 'image-2',
                   'status': 'deleted',
                   'created_at': '2012-11-26 11:52:54',
                   'updated_at': '2012-12-26 11:52:54',
                   'deleted_at': '2012-12-27 11:52:54',
                   'properties': ''},
                  {'id': 3,
                   'name': 'image-3',
                   'status': 'available',
                   'created_at': '2012-11-26 11:52:54',
                   'deleted_at': '',
                   'updated_at': '2012-12-26 11:52:54',
                   'properties': ''}]
        result_images = [
                  {'id': 1,
                   'name': 'image-1',
                   'status':'ACTIVE',
                   'progress': 100,
                   'created': '2012-11-26T11:52:54+00:00',
                   'updated': '2012-12-26T11:52:54+00:00',
                   'metadata': {'values': {'foo':'bar'}}},
                  {'id': 2,
                   'name': 'image-2',
                   'status': 'DELETED',
                   'progress': 0,
                   'created': '2012-11-26T11:52:54+00:00',
                   'updated': '2012-12-26T11:52:54+00:00'},
                  {'id': 3,
                   'name': 'image-3',
                   'status': 'ACTIVE',
                   'progress': 100,
                   'created': '2012-11-26T11:52:54+00:00',
                   'updated': '2012-12-26T11:52:54+00:00'}]
        mimage().list.return_value = images
        response = self.get('/api/v1.1/images/detail', 'user')
        self.assertSuccess(response)
        api_images = json.loads(response.content)['images']['values']
        self.assertEqual(len(result_images), len(api_images))
        self.assertEqual(result_images, api_images)

    @assert_backend_closed
    def test_get_image_details(self, mimage):
        image = {'id': 42,
                 'name': 'image-1',
                 'status': 'available',
                 'created_at': '2012-11-26 11:52:54',
                 'updated_at': '2012-12-26 11:52:54',
                 'deleted_at': '',
                 'properties': {'foo': 'bar'}}
        result_image = \
                  {'id': 42,
                   'name': 'image-1',
                   'status': 'ACTIVE',
                   'progress': 100,
                   'created': '2012-11-26T11:52:54+00:00',
                   'updated': '2012-12-26T11:52:54+00:00',
                   'metadata': {'values': {'foo': 'bar'}}}
        with patch('synnefo.api.util.get_image') as m:
            m.return_value = image
            response = self.get('/api/v1.1/images/42', 'user')
        self.assertSuccess(response)
        api_image = json.loads(response.content)['image']
        self.assertEqual(api_image, result_image)

    @assert_backend_closed
    def test_invalid_image(self, mimage):
        with patch('synnefo.api.util.get_image') as m:
            m.side_effect = faults.ItemNotFound('Image not found')
            response = self.get('/api/v1.1/images/42', 'user')
        self.assertItemNotFound(response)

    def test_delete_image(self, mimage):
        # TODO
        pass


@patch('synnefo.api.util.ImageBackend')
class ImageMetadataAPITest(BaseAPITest):
    def setUp(self):
        self.image = {'id': 42,
                 'name': 'image-1',
                 'status': 'available',
                 'created_at': '2012-11-26 11:52:54',
                 'updated_at': '2012-12-26 11:52:54',
                 'deleted_at': '',
                 'properties': {'foo': 'bar', 'foo2': 'bar2'}}
        self.result_image = \
                  {'id': 42,
                   'name': 'image-1',
                   'status': 'ACTIVE',
                   'progress': 100,
                   'created': '2012-11-26T11:52:54+00:00',
                   'updated': '2012-12-26T11:52:54+00:00',
                   'metadata': {'values': {'foo': 'bar'}}}

    @assert_backend_closed
    def test_list_metadata(self, backend):
        backend.return_value.get_image.return_value = self.image
        response = self.get('/api/v1.1/images/42/meta', 'user')
        self.assertSuccess(response)
        meta = json.loads(response.content)['metadata']['values']
        self.assertEqual(meta, self.image['properties'])

    @assert_backend_closed
    def test_get_metadata(self, backend):
        backend.return_value.get_image.return_value = self.image
        response = self.get('/api/v1.1/images/42/meta/foo', 'user')
        self.assertSuccess(response)
        meta = json.loads(response.content)['meta']
        self.assertEqual(meta['foo'], 'bar')

    @assert_backend_closed
    def test_get_invalid_metadata(self, backend):
        backend.return_value.get_image.return_value = self.image
        response = self.get('/api/v1.1/images/42/meta/not_found', 'user')
        self.assertItemNotFound(response)

    @assert_backend_closed
    def test_delete_metadata_item(self, backend):
        backend.return_value.get_image.return_value = self.image
        with patch("synnefo.api.images.ImageBackend") as m:
            response = self.delete('/api/v1.1/images/42/meta/foo', 'user')
            self.assertEqual(response.status_code, 204)
            m.return_value.update.assert_called_once_with('42',
                                        {'properties': {'foo2': 'bar2'}})

    @assert_backend_closed
    def test_create_metadata_item(self, backend):
        backend.return_value.get_image.return_value = self.image
        with patch("synnefo.api.images.ImageBackend") as m:
                request = {'meta': {'foo3': 'bar3'}}
                response = self.put('/api/v1.1/images/42/meta/foo3', 'user',
                                    json.dumps(request), 'json')
                self.assertEqual(response.status_code, 201)
                m.return_value.update.assert_called_once_with('42',
                        {'properties':
                            {'foo': 'bar', 'foo2': 'bar2', 'foo3': 'bar3'}})

    @assert_backend_closed
    def test_update_metadata_item(self, backend):
        backend.return_value.get_image.return_value = self.image
        with patch("synnefo.api.images.ImageBackend") as m:
                request = {'metadata': {'foo': 'bar_new', 'foo4': 'bar4'}}
                response = self.post('/api/v1.1/images/42/meta', 'user',
                                    json.dumps(request), 'json')
                self.assertEqual(response.status_code, 201)
                m.return_value.update.assert_called_once_with('42',
                        {'properties':
                            {'foo': 'bar_new', 'foo2': 'bar2', 'foo4': 'bar4'}
                        })


class APITest(TestCase):
    def test_api_version(self):
        """Check API version."""
        with astakos_user('user'):
            response = self.client.get('/api/v1.1/')
        self.assertEqual(response.status_code, 200)
        api_version = json.loads(response.content)['version']
        self.assertEqual(api_version['id'], 'v1.1')
        self.assertEqual(api_version['status'], 'CURRENT')
