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

from snf_django.utils.testing import BaseAPITest, mocked_quotaholder
from synnefo.db.models import VirtualMachine, VirtualMachineMetadata
from synnefo.db import models_factory as mfactory
from synnefo.logic.utils import get_rsapi_state
from synnefo.cyclades_settings import cyclades_services
from synnefo.lib.services import get_service_path
from synnefo.lib import join_urls

from mock import patch


class ComputeAPITest(BaseAPITest):
    def setUp(self, *args, **kwargs):
        super(ComputeAPITest, self).setUp(*args, **kwargs)
        self.compute_path = get_service_path(cyclades_services, 'compute',
                                             version='v2.0')
    def myget(self, path, *args, **kwargs):
        path = join_urls(self.compute_path, path)
        return self.get(path, *args, **kwargs)

    def myput(self, path, *args, **kwargs):
        path = join_urls(self.compute_path, path)
        return self.put(path, *args, **kwargs)

    def mypost(self, path, *args, **kwargs):
        path = join_urls(self.compute_path, path)
        return self.post(path, *args, **kwargs)

    def mydelete(self, path, *args, **kwargs):
        path = join_urls(self.compute_path, path)
        return self.delete(path, *args, **kwargs)


class ServerAPITest(ComputeAPITest):
    def setUp(self):
        self.user1 = 'user1'
        self.user2 = 'user2'
        self.vm1 = mfactory.VirtualMachineFactory(userid=self.user1)
        self.vm2 = mfactory.VirtualMachineFactory(userid=self.user2)
        self.vm3 = mfactory.VirtualMachineFactory(deleted=True,
                                                  userid=self.user1)
        self.vm4 = mfactory.VirtualMachineFactory(userid=self.user2)
        super(ServerAPITest, self).setUp()

    def test_server_list_1(self):
        """Test if the expected list of servers is returned."""
        response = self.myget('servers')
        self.assertSuccess(response)
        servers = json.loads(response.content)['servers']
        self.assertEqual(servers, [])

    def test_server_list_2(self):
        """Test if the expected list of servers is returned."""
        response = self.myget('servers', self.user1)
        self.assertSuccess(response)
        servers = json.loads(response.content)['servers']
        db_server = self.vm1
        server = servers[0]
        self.assertEqual(server["name"], db_server.name)
        self.assertEqual(server["id"], db_server.id)

    def test_server_list_detail(self):
        """Test if the servers list details are returned."""
        user = self.user2
        user_vms = {self.vm2.id: self.vm2,
                    self.vm4.id: self.vm4}

        response = self.myget('servers/detail', user)
        servers = json.loads(response.content)['servers']
        self.assertEqual(len(servers), len(user_vms))
        for api_vm in servers:
            db_vm = user_vms[api_vm['id']]
            self.assertEqual(api_vm['flavor']["id"], db_vm.flavor.id)
            self.assertEqual(api_vm['hostId'], db_vm.hostid)
            self.assertEqual(api_vm['id'], db_vm.id)
            self.assertEqual(api_vm['image']["id"], db_vm.imageid)
            self.assertEqual(api_vm['name'], db_vm.name)
            self.assertEqual(api_vm['status'], get_rsapi_state(db_vm))
            self.assertSuccess(response)

    def test_server_detail(self):
        """Test if a server details are returned."""
        db_vm = self.vm2
        user = self.vm2.userid
        net = mfactory.NetworkFactory()
        nic = mfactory.NetworkInterfaceFactory(machine=self.vm2, network=net,
                                              ipv6="::babe")

        db_vm_meta = mfactory.VirtualMachineMetadataFactory(vm=db_vm)

        response = self.myget('servers/%d' % db_vm.id, user)
        server = json.loads(response.content)['server']

        self.assertEqual(server['flavor']["id"], db_vm.flavor.id)
        self.assertEqual(server['hostId'], db_vm.hostid)
        self.assertEqual(server['id'], db_vm.id)
        self.assertEqual(server['image']["id"], db_vm.imageid)
        self.assertEqual(server['name'], db_vm.name)
        self.assertEqual(server['status'], get_rsapi_state(db_vm))
        api_nic = server['attachments'][0]
        self.assertEqual(api_nic['network_id'], str(net.id))
        self.assertEqual(api_nic['mac_address'], nic.mac)
        self.assertEqual(api_nic['firewallProfile'], nic.firewall_profile)
        self.assertEqual(api_nic['ipv4'], nic.ipv4)
        self.assertEqual(api_nic['ipv6'], nic.ipv6)
        self.assertEqual(api_nic['id'], 'nic-%s-%s' % (db_vm.id, nic.index))
        api_address = server["addresses"]
        self.assertEqual(api_address[str(net.id)],
               [{"version": 4, "addr": nic.ipv4, "OS-EXT-IPS:type": "fixed"},
                {"version": 6, "addr": nic.ipv6, "OS-EXT-IPS:type": "fixed"}])

        metadata = server['metadata']
        self.assertEqual(len(metadata), 1)
        self.assertEqual(metadata[db_vm_meta.meta_key], db_vm_meta.meta_value)
        self.assertSuccess(response)

    def test_server_building_nics(self):
        db_vm = self.vm2
        user = self.vm2.userid
        net1 = mfactory.NetworkFactory()
        net2 = mfactory.NetworkFactory()
        net3 = mfactory.NetworkFactory()
        mfactory.NetworkInterfaceFactory(machine=self.vm2, network=net1,
                                         state="BUILDING")
        nic2 = mfactory.NetworkInterfaceFactory(machine=self.vm2, network=net2,
                                                state="ACTIVE")
        mfactory.NetworkInterfaceFactory(machine=self.vm2, network=net3,
                                         state="BUILDING")

        response = self.myget('servers/%d' % db_vm.id, user)
        server = json.loads(response.content)['server']
        nics = server["attachments"]
        self.assertEqual(len(nics), 1)
        self.assertEqual(nics[0]["network_id"], str(nic2.network_id))

    def test_noauthorized(self):
        """Test 404 for detail of other user vm"""
        db_vm = self.vm2

        response = self.myget('servers/%d' % db_vm.id, 'wrong_user')
        self.assertItemNotFound(response)

    def test_wrong_server(self):
        """Test 404 response if server does not exist."""
        response = self.myget('servers/%d' % 5000)
        self.assertItemNotFound(response)

    def test_create_server_empty(self):
        """Test if the create server call returns a 400 badRequest if
           no attributes are specified."""

        response = self.mypost('servers', params={})
        self.assertBadRequest(response)

    def test_rename_server(self):
        vm = self.vm2
        request = {'server': {'name': 'new_name'}}
        response = self.myput('servers/%d' % vm.id, vm.userid,
                              json.dumps(request), 'json')
        self.assertSuccess(response)
        self.assertEqual(VirtualMachine.objects.get(id=vm.id).name, "new_name")

    def test_catch_wrong_api_paths(self):
        response = self.myget('nonexistent')
        self.assertEqual(response.status_code, 400)
        try:
            error = json.loads(response.content)
        except ValueError:
            self.assertTrue(False)

    def test_method_not_allowed(self, *args):
        # /servers/ allows only POST, GET
        response = self.myput('servers', '', '')
        self.assertMethodNotAllowed(response)
        response = self.mydelete('servers')
        self.assertMethodNotAllowed(response)

        # /servers/<srvid>/ allows only GET, PUT, DELETE
        response = self.mypost("servers/42")
        self.assertMethodNotAllowed(response)

        # /imags/<srvid>/metadata/ allows only POST, GET
        response = self.myput('servers/42/metadata', '', '')
        self.assertMethodNotAllowed(response)
        response = self.mydelete('servers/42/metadata')
        self.assertMethodNotAllowed(response)

        # /imags/<srvid>/metadata/ allows only POST, GET
        response = self.myput('servers/42/metadata', '', '')
        self.assertMethodNotAllowed(response)
        response = self.mydelete('servers/42/metadata')
        self.assertMethodNotAllowed(response)

        # /imags/<srvid>/metadata/<key> allows only PUT, GET, DELETE
        response = self.mypost('servers/42/metadata/foo')
        self.assertMethodNotAllowed(response)


@patch('synnefo.api.util.get_image')
@patch('synnefo.logic.rapi_pool.GanetiRapiClient')
class ServerCreateAPITest(ComputeAPITest):
    def test_create_server(self, mrapi, mimage):
        """Test if the create server call returns the expected response
           if a valid request has been speficied."""
        mimage.return_value = {'location': 'pithos://foo',
                               'checksum': '1234',
                               "id": 1,
                               "name": "test_image",
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
        with mocked_quotaholder():
            response = self.mypost('servers', 'test_user',
                                   json.dumps(request), 'json')
        self.assertEqual(response.status_code, 202)
        mrapi().CreateInstance.assert_called_once()

        api_server = json.loads(response.content)['server']
        self.assertEqual(api_server['status'], "BUILD")
        self.assertEqual(api_server['progress'], 0)
        self.assertEqual(api_server['metadata'],
                        {"My Server Name":  "Apache1"})
        self.assertTrue('adminPass' in api_server)

        db_vm = VirtualMachine.objects.get(userid='test_user')
        self.assertEqual(api_server['name'], db_vm.name)
        self.assertEqual(api_server['status'], db_vm.operstate)

        # Test drained flag in Network:
        network.drained = True
        network.save()
        with mocked_quotaholder():
            response = self.mypost('servers', 'test_user',
                                    json.dumps(request), 'json')
        self.assertEqual(response.status_code, 503, "serviceUnavailable")

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
        response = self.mypost('servers', 'test_user',
                               json.dumps(request), 'json')
        self.assertItemNotFound(response)


@patch('synnefo.logic.rapi_pool.GanetiRapiClient')
class ServerDestroyAPITest(ComputeAPITest):
    def test_delete_server(self, mrapi):
        vm = mfactory.VirtualMachineFactory()
        response = self.mydelete('servers/%d' % vm.id, vm.userid)
        self.assertEqual(response.status_code, 204)
        mrapi().DeleteInstance.assert_called_once()

    def test_non_existing_delete_server(self, mrapi):
        vm = mfactory.VirtualMachineFactory()
        response = self.mydelete('servers/%d' % 42, vm.userid)
        self.assertItemNotFound(response)
        self.assertFalse(mrapi.mock_calls)


class ServerMetadataAPITest(ComputeAPITest):
    def setUp(self):
        self.vm = mfactory.VirtualMachineFactory()
        self.metadata = mfactory.VirtualMachineMetadataFactory(vm=self.vm)
        super(ServerMetadataAPITest, self).setUp()

    def test_get_metadata(self):
        vm = self.vm
        create_meta = lambda: mfactory.VirtualMachineMetadataFactory(vm=vm)
        metadata = [create_meta(), create_meta(), create_meta()]
        response = self.myget('servers/%d/metadata' % vm.id, vm.userid)
        self.assertTrue(response.status_code in [200, 203])
        api_metadata = json.loads(response.content)['metadata']
        self.assertEqual(len(api_metadata), len(metadata) + 1)
        for db_m in metadata:
            self.assertEqual(api_metadata[db_m.meta_key], db_m.meta_value)

        request = {'metadata':
                        {'foo': 'bar'},
                        metadata[0].meta_key: 'bar2'
                  }
        response = self.mypost('servers/%d/metadata' % vm.id,
                             vm.userid, json.dumps(request), 'json')
        metadata2 = VirtualMachineMetadata.objects.filter(vm=vm)
        response = self.myget('servers/%d/metadata' % vm.id, vm.userid)
        self.assertTrue(response.status_code in [200, 203])
        api_metadata2 = json.loads(response.content)['metadata']
        self.assertTrue('foo' in api_metadata2.keys())
        self.assertTrue(api_metadata2[metadata[0].meta_key], 'bar2')
        self.assertEqual(len(api_metadata2), len(metadata2))
        for db_m in metadata2:
            self.assertEqual(api_metadata2[db_m.meta_key], db_m.meta_value)

        # Create new meta
        request = {'meta': {'foo2': 'bar2'}}
        response = self.myput('servers/%d/metadata/foo2' % vm.id,
                              vm.userid, json.dumps(request), 'json')

        # Get the new meta
        response = self.myget('servers/%d/metadata/foo2' % vm.id, vm.userid)
        meta = json.loads(response.content)['meta']
        self.assertEqual(meta['foo2'], 'bar2')

        # Delete the new meta
        response = self.mydelete('servers/%d/metadata/foo2' % vm.id, vm.userid)
        self.assertEqual(response.status_code, 204)

        # Try to get the deleted meta: should raise 404
        response = self.myget('servers/%d/metadata/foo2' % vm.id, vm.userid)
        self.assertEqual(response.status_code, 404)

    def test_invalid_metadata(self):
        vm = self.vm
        response = self.mypost('servers/%d/metadata' % vm.id, vm.userid)
        self.assertBadRequest(response)
        self.assertEqual(len(vm.metadata.all()), 1)

    def test_invalid_metadata_server(self):
        response = self.mypost('servers/42/metadata', 'user')
        self.assertItemNotFound(response)

    def test_get_meta_invalid_key(self):
        vm = self.vm
        response = self.myget('servers/%d/metadata/foo2' % vm.id, vm.userid)
        self.assertItemNotFound(response)


@patch('synnefo.api.util.get_image')
@patch('synnefo.logic.rapi_pool.GanetiRapiClient')
class ServerActionAPITest(ComputeAPITest):
    def test_actions(self, mrapi, mimage):
        actions = ['start', 'shutdown', 'reboot']
        vm = mfactory.VirtualMachineFactory()
        vm.operstate = "STOPPED"
        vm.save()
        for action in actions:
            val = {'type': 'HARD'} if action == 'reboot' else {}
            request = {action: val}
            response = self.mypost('servers/%d/action' % vm.id,
                                   vm.userid, json.dumps(request), 'json')
            self.assertEqual(response.status_code, 202)
            if action == 'shutdown':
                self.assertEqual(VirtualMachine.objects.get(id=vm.id).action,
                                 "STOP")
            else:
                self.assertEqual(VirtualMachine.objects.get(id=vm.id).action,
                                 action.upper())

    def test_action_in_building_vm(self, mrapi, mimage):
        """Test building in progress"""
        vm = mfactory.VirtualMachineFactory()
        request = {'start': '{}'}
        response = self.mypost('servers/%d/action' % vm.id,
                               vm.userid, json.dumps(request), 'json')
        self.assertEqual(response.status_code, 409)
        self.assertFalse(mrapi.mock_calls)

    def test_destroy_build_vm(self, mrapi, mimage):
        """Test building in progress"""
        vm = mfactory.VirtualMachineFactory()
        response = self.mydelete('servers/%d' % vm.id, vm.userid)
        self.assertSuccess(response)
        mrapi().RemoveInstance.assert_called_once()

    def test_firewall(self, mrapi, mimage):
        vm = mfactory.VirtualMachineFactory()
        vm.operstate = "STOPPED"
        vm.save()
        request = {'firewallProfile': {'profile': 'PROTECTED'}}
        response = self.mypost('servers/%d/action' % vm.id,
                               vm.userid, json.dumps(request), 'json')
        self.assertEqual(response.status_code, 202)
        mrapi().ModifyInstance.assert_called_once()

    def test_unsupported_firewall(self, mrapi, mimage):
        vm = mfactory.VirtualMachineFactory()
        vm.operstate = "STOPPED"
        vm.save()
        request = {'firewallProfile': {'profile': 'FOO'}}
        response = self.mypost('servers/%d/action' % vm.id,
                               vm.userid, json.dumps(request), 'json')
        self.assertBadRequest(response)
        self.assertFalse(mrapi.mock_calls)


class ServerVNCConsole(ComputeAPITest):
    def test_not_active_server(self):
        """Test console req for not ACTIVE server returns badRequest"""
        vm = mfactory.VirtualMachineFactory()
        data = json.dumps({'console': {'type': 'vnc'}})
        response = self.mypost('servers/%d/action' % vm.id,
                               vm.userid, data, 'json')
        self.assertBadRequest(response)

    def test_active_server(self):
        """Test console req for ACTIVE server"""
        vm = mfactory.VirtualMachineFactory()
        vm.operstate = 'STARTED'
        vm.save()

        data = json.dumps({'console': {'type': 'vnc'}})
        response = self.mypost('servers/%d/action' % vm.id,
                               vm.userid, data, 'json')
        self.assertEqual(response.status_code, 200)
        reply = json.loads(response.content)
        self.assertEqual(reply.keys(), ['console'])
        console = reply['console']
        self.assertEqual(console['type'], 'vnc')
        self.assertEqual(set(console.keys()),
                         set(['type', 'host', 'port', 'password']))

    def test_wrong_console_type(self):
        """Test console req for ACTIVE server"""
        vm = mfactory.VirtualMachineFactory()
        vm.operstate = 'STARTED'
        vm.save()

        data = json.dumps({'console': {'type': 'foo'}})
        response = self.mypost('servers/%d/action' % vm.id,
                               vm.userid, data, 'json')
        self.assertBadRequest(response)
