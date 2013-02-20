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

import json
from mock import patch

from synnefo.api.tests import BaseAPITest
from synnefo.db.models import Network, NetworkInterface
from synnefo.db import models_factory as mfactory


@patch('synnefo.logic.rapi_pool.GanetiRapiClient')
class NetworkAPITest(BaseAPITest):
    def setUp(self):
        self.mac_prefixes = mfactory.MacPrefixPoolTableFactory()
        self.bridges = mfactory.BridgePoolTableFactory()
        self.user = 'dummy-user'
        self.net1 = mfactory.NetworkFactory(userid=self.user)
        self.vm1 = mfactory.VirtualMachineFactory(userid=self.user)
        self.nic1 = mfactory.NetworkInterfaceFactory(network=self.net1,
                                                     machine=self.vm1)
        self.nic2 = mfactory.NetworkInterfaceFactory(network=self.net1,
                                                     machine=self.vm1)
        self.net2 = mfactory.NetworkFactory(userid=self.user)
        self.nic3 = mfactory.NetworkInterfaceFactory(network=self.net2)

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
            self.assertEqual(db_net.public, api_net['public'])
            db_nics = ["nic-%d-%d" % (nic.machine.id, nic.index) for nic in
                       db_net.nics.filter(machine__userid=db_net.userid)]
            self.assertEqual(db_nics, api_net['attachments']['values'])

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

    def test_invalid_data_4(self, mrapi):
        """Test unauthorized to create network not in settings"""
        request = {
                'network': {'name': 'foo', 'type': 'CUSTOM'}
            }
        response = self.post('/api/v1.1/networks/', 'user1',
                             json.dumps(request), 'json')
        self.assertFault(response, 403, "forbidden")

    def test_invalid_subnet(self, mrapi):
        """Test invalid subnet"""
        request = {
            'network': {'name': 'foo', 'cidr': '10.0.0.10/27'}
            }
        response = self.post('/api/v1.1/networks/', 'user1',
                             json.dumps(request), 'json')
        self.assertBadRequest(response)

    def test_list_networks(self, mrapi):
        """Test that expected list of networks is returned."""
        # Create a deleted network
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
        """Test that expected networks details are returned."""
        # Create a deleted network
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
        """Test that expected details for a network are returned"""
        response = self.get('/api/v1.1/networks/%d' % self.net1.id,
                            self.net1.userid)
        self.assertSuccess(response)
        api_net = json.loads(response.content)["network"]
        self.assertNetworksEqual(self.net1, api_net, detail=True)

    def test_invalid_network(self, mrapi):
        """Test details for non-existing network."""
        response = self.get('/api/v1.1/networks/%d' % 42,
                            self.net1.userid)
        self.assertItemNotFound(response)

    def test_rename_network(self, mrapi):
        request = {'network': {'name': "new_name"}}
        response = self.put('/api/v1.1/networks/%d' % self.net2.id,
                            self.net2.userid, json.dumps(request), 'json')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Network.objects.get(id=self.net2.id).name, "new_name")
        # Check invalid
        request = {'name': "new_name"}
        response = self.put('/api/v1.1/networks/%d' % self.net2.id,
                            self.net2.userid, json.dumps(request), 'json')
        self.assertBadRequest(response)

    def test_rename_deleted_network(self, mrapi):
        net = mfactory.NetworkFactory(deleted=True)
        request = {'network': {'name': "new_name"}}
        response = self.put('/api/v1.1/networks/%d' % net.id,
                            net.userid, json.dumps(request), 'json')
        self.assertBadRequest(response)

    def test_rename_public_network(self, mrapi):
        net = mfactory.NetworkFactory(public=True)
        request = {'network': {'name': "new_name"}}
        response = self.put('/api/v1.1/networks/%d' % net.id,
                            self.net2.userid, json.dumps(request), 'json')
        self.assertFault(response, 403, 'forbidden')

    def test_delete_network(self, mrapi):
        net = mfactory.NetworkFactory()
        response = self.delete('/api/v1.1/networks/%d' % net.id,
                                net.userid)
        self.assertEqual(response.status_code, 204)
        net = Network.objects.get(id=net.id, userid=net.userid)
        self.assertEqual(net.action, 'DESTROY')
        mrapi.DeleteNetwork.assert_called()

    def test_delete_public_network(self, mrapi):
        net = mfactory.NetworkFactory(public=True)
        response = self.delete('/api/v1.1/networks/%d' % net.id,
                                self.net2.userid)
        self.assertFault(response, 403, 'forbidden')
        self.assertFalse(mrapi.called)

    def test_delete_deleted_network(self, mrapi):
        net = mfactory.NetworkFactory(deleted=True)
        response = self.delete('/api/v1.1/networks/%d' % net.id,
                                net.userid)
        self.assertBadRequest(response)

    def test_delete_network_in_use(self, mrapi):
        net = self.net1
        response = self.delete('/api/v1.1/networks/%d' % net.id,
                                net.userid)
        self.assertFault(response, 421, 'networkInUse')
        self.assertFalse(mrapi.called)

    def test_add_nic(self, mrapi):
        user = 'userr'
        vm = mfactory.VirtualMachineFactory(name='yo', userid=user)
        net = mfactory.NetworkFactory(state='ACTIVE', userid=user)
        request = {'add': {'serverRef': vm.id}}
        response = self.post('/api/v1.1/networks/%d/action' % net.id,
                             net.userid, json.dumps(request), 'json')
        self.assertEqual(response.status_code, 202)

    def test_add_nic_to_deleted_network(self, mrapi):
        user = 'userr'
        vm = mfactory.VirtualMachineFactory(name='yo', userid=user)
        net = mfactory.NetworkFactory(state='ACTIVE', userid=user,
                                      deleted=True)
        request = {'add': {'serverRef': vm.id}}
        response = self.post('/api/v1.1/networks/%d/action' % net.id,
                             net.userid, json.dumps(request), 'json')
        self.assertBadRequest(response)
        self.assertFalse(mrapi.called)

    def test_add_nic_to_public_network(self, mrapi):
        user = 'userr'
        vm = mfactory.VirtualMachineFactory(name='yo', userid=user)
        net = mfactory.NetworkFactory(state='ACTIVE', userid=user, public=True)
        request = {'add': {'serverRef': vm.id}}
        response = self.post('/api/v1.1/networks/%d/action' % net.id,
                             net.userid, json.dumps(request), 'json')
        self.assertFault(response, 403, 'forbidden')
        self.assertFalse(mrapi.called)

    def test_add_nic_malformed_1(self, mrapi):
        user = 'userr'
        vm = mfactory.VirtualMachineFactory(name='yo', userid=user)
        net = mfactory.NetworkFactory(state='ACTIVE', userid=user)
        request = {'add': {'serveRef': vm.id}}
        response = self.post('/api/v1.1/networks/%d/action' % net.id,
                             net.userid, json.dumps(request), 'json')
        self.assertBadRequest(response)
        self.assertFalse(mrapi.called)

    def test_add_nic_malformed_2(self, mrapi):
        user = 'userr'
        vm = mfactory.VirtualMachineFactory(name='yo', userid=user)
        net = mfactory.NetworkFactory(state='ACTIVE', userid=user)
        request = {'add': {'serveRef': [vm.id, 22]}}
        response = self.post('/api/v1.1/networks/%d/action' % net.id,
                             net.userid, json.dumps(request), 'json')
        self.assertBadRequest(response)
        self.assertFalse(mrapi.called)

    def test_add_nic_not_active(self, mrapi):
        """Test connecting VM to non-active network"""
        user = 'dummy'
        vm = mfactory.VirtualMachineFactory(name='yo', userid=user)
        net = mfactory.NetworkFactory(state='PENDING', subnet='10.0.0.0/31',
                                      userid=user)
        request = {'add': {'serveRef': vm.id}}
        response = self.post('/api/v1.1/networks/%d/action' % net.id,
                             net.userid, json.dumps(request), 'json')
        # Test that returns BuildInProgress
        self.assertEqual(response.status_code, 409)
        self.assertFalse(mrapi.called)

    def test_add_nic_full_network(self, mrapi):
        """Test connecting VM to a full network"""
        user = 'userr'
        vm = mfactory.VirtualMachineFactory(name='yo', userid=user)
        net = mfactory.NetworkFactory(state='ACTIVE', subnet='10.0.0.0/30',
                                      userid=user, dhcp=True)
        pool = net.get_pool()
        while not pool.empty():
            pool.get()
        pool.save()
        pool = net.get_pool()
        self.assertTrue(pool.empty())
        request = {'add': {'serverRef': vm.id}}
        response = self.post('/api/v1.1/networks/%d/action' % net.id,
                             net.userid, json.dumps(request), 'json')
        # Test that returns OverLimit
        self.assertEqual(response.status_code, 413)
        self.assertFalse(mrapi.called)

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

    def test_remove_nic_malformed_2(self, mrapi):
        user = 'userr'
        vm = mfactory.VirtualMachineFactory(name='yo', userid=user)
        net = mfactory.NetworkFactory(state='ACTIVE', userid=user)
        request = {'remove':
                    {'attachment': 'nic-%s' % vm.id}
                  }
        response = self.post('/api/v1.1/networks/%d/action' % net.id,
                             net.userid, json.dumps(request), 'json')
        self.assertBadRequest(response)
