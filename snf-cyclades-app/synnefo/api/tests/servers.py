# encoding: utf-8
# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json
from copy import deepcopy

from snf_django.utils.testing import (BaseAPITest, mocked_quotaholder,
                                      override_settings)
from synnefo.db.models import (VirtualMachine, VirtualMachineMetadata,
                               IPAddress, NetworkInterface, Volume)
from synnefo.db import models_factory as mfactory
from synnefo.logic.utils import get_rsapi_state
from synnefo.cyclades_settings import cyclades_services
from synnefo.lib.services import get_service_path
from synnefo.lib import join_urls
from django.conf import settings
from synnefo.logic.rapi import GanetiApiError

from mock import patch, Mock


class ComputeAPITest(BaseAPITest):
    def __init__(self, *args, **kwargs):
        super(ComputeAPITest, self).__init__(*args, **kwargs)
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
        self.vm1 = mfactory.VirtualMachineFactory(userid=self.user1,
                                                  name=u"Hi \u2601")
        self.vm2 = mfactory.VirtualMachineFactory(userid=self.user2)
        self.vm3 = mfactory.VirtualMachineFactory(deleted=True,
                                                  userid=self.user1)
        self.vm4 = mfactory.VirtualMachineFactory(userid=self.user2)

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
        self.assertEqual(server["name"], u"Hi \u2601")
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
        ip4 = mfactory.IPv4AddressFactory(nic__machine=self.vm2)
        nic = ip4.nic
        net = ip4.network
        ip6 = mfactory.IPv6AddressFactory(nic=nic, network=net)
        nic.mac = "aa:00:11:22:33:44"
        nic.save()

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
        self.assertEqual(api_nic['ipv4'], ip4.address)
        self.assertEqual(api_nic['ipv6'], ip6.address)
        self.assertEqual(api_nic['OS-EXT-IPS:type'], "fixed")
        self.assertEqual(api_nic['id'], nic.id)
        api_address = server["addresses"]
        self.assertEqual(api_address[str(net.id)], [
            {"version": 4, "addr": ip4.address, "OS-EXT-IPS:type": "fixed"},
            {"version": 6, "addr": ip6.address, "OS-EXT-IPS:type": "fixed"}
        ])

        metadata = server['metadata']
        self.assertEqual(len(metadata), 1)
        self.assertEqual(metadata[db_vm_meta.meta_key], db_vm_meta.meta_value)
        self.assertSuccess(response)

    def test_server_fqdn(self):
        vm = mfactory.VirtualMachineFactory()
        # Setting set to None
        with override_settings(settings,
                               CYCLADES_SERVERS_FQDN=None):
            response = self.myget("servers/%d" % vm.id, vm.userid)
            server = json.loads(response.content)['server']
            self.assertEqual(server["SNF:fqdn"], None)
        # Unformated setting
        with override_settings(settings,
                               CYCLADES_SERVERS_FQDN="vm.example.org"):
            response = self.myget("servers/%d" % vm.id, vm.userid)
            server = json.loads(response.content)['server']
            self.assertEqual(server["SNF:fqdn"], "vm.example.org")
        # Formatted settings
        with override_settings(settings, CYCLADES_SERVERS_FQDN=
                               "snf-%(id)s.vm.example.org"):
            response = self.myget("servers/%d" % vm.id, vm.userid)
            server = json.loads(response.content)['server']
            self.assertEqual(server["SNF:fqdn"],
                             "snf-%d.vm.example.org" % vm.id)
        with override_settings(settings,
                               CYCLADES_SERVERS_FQDN=
                               "snf-%(id)s.vm-%(id)s.example.org"):
            response = self.myget("servers/%d" % vm.id, vm.userid)
            server = json.loads(response.content)['server']
            self.assertEqual(server["SNF:fqdn"], "snf-%d.vm-%d.example.org" %
                             (vm.id, vm.id))

    def test_server_port_forwarding(self):
        vm = mfactory.VirtualMachineFactory()
        # test None if the server has no public IP
        ports = {
            22: ("foo", 61000),
            80: lambda ip, id, fqdn, user: ("bar", 61001)}
        with override_settings(settings,
                               CYCLADES_PORT_FORWARDING=ports):
            response = self.myget("servers/%d" % vm.id, vm.userid)
        server = json.loads(response.content)['server']
        self.assertEqual(server["SNF:port_forwarding"], {})

        # Add with public IP
        mfactory.IPv4AddressFactory(nic__machine=vm, network__public=True)
        with override_settings(settings,
                               CYCLADES_PORT_FORWARDING=ports):
            response = self.myget("servers/%d" % vm.id, vm.userid)
        server = json.loads(response.content)['server']
        self.assertEqual(server["SNF:port_forwarding"],
                         {"22": {"host": "foo", "port": "61000"},
                          "80": {"host": "bar", "port": "61001"}})

        def _port_from_ip(ip, base):
            fields = ip.split('.', 4)
            return (base + 256*int(fields[2]) + int(fields[3]))

        ports = {
            22: lambda ip, id, fqdn, user:
            ip and ("gate", _port_from_ip(ip, 10000)) or None}
        vm = mfactory.VirtualMachineFactory()
        with override_settings(settings,
                               CYCLADES_PORT_FORWARDING=ports):
            response = self.myget("servers/%d" % vm.id, vm.userid)
            server = json.loads(response.content)['server']
            self.assertEqual(server["SNF:port_forwarding"], {})

        mfactory.IPv4AddressFactory(nic__machine=vm,
                                    network__public=True,
                                    address="192.168.2.2")
        with override_settings(settings,
                               CYCLADES_PORT_FORWARDING=ports):
            response = self.myget("servers/%d" % vm.id, vm.userid)
            server = json.loads(response.content)['server']
            self.assertEqual(server["SNF:port_forwarding"],
                             {"22": {"host": "gate", "port": "10514"}})

    def test_server_building_nics(self):
        db_vm = self.vm2
        user = self.vm2.userid
        net1 = mfactory.NetworkFactory()
        net2 = mfactory.NetworkFactory()
        net3 = mfactory.NetworkFactory()
        mfactory.NetworkInterfaceFactory(machine=self.vm2, network=net1,
                                         state="BUILD")
        nic2 = mfactory.NetworkInterfaceFactory(machine=self.vm2, network=net2,
                                                state="ACTIVE")
        mfactory.NetworkInterfaceFactory(machine=self.vm2, network=net3,
                                         state="BUILD")

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

    def test_rename_server_invalid_name(self):
        vm = self.vm2
        request = {'server': {'name': 'a' * 500}}
        response = self.myput('servers/%d' % vm.id, vm.userid,
                              json.dumps(request), 'json')
        self.assertBadRequest(response)

    def test_catch_wrong_api_paths(self):
        response = self.myget('nonexistent')
        self.assertEqual(response.status_code, 400)
        try:
            json.loads(response.content)
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

fixed_image = Mock()
fixed_image.return_value = {'location': 'pithos://foo',
                            'mapfile': '1234',
                            "id": 1,
                            "name": "test_image",
                            "size": 1024,
                            "is_snapshot": False,
                            "status": "AVAILABLE",
                            'disk_format': 'diskdump'}


@patch('synnefo.api.util.get_image', fixed_image)
@patch('synnefo.volume.util.get_snapshot', fixed_image)
@patch('synnefo.logic.rapi_pool.GanetiRapiClient')
class ServerCreateAPITest(ComputeAPITest):
    def setUp(self):
        self.flavor = mfactory.FlavorFactory()
        self.backend = mfactory.BackendFactory()
        self.request = {
            "server": {
                "name": u"Server in the \u2601",
                "userid": "test_user",
                "imageRef": 1,
                "flavorRef": self.flavor.id,
                "metadata": {
                    u"Meta \u2601": u"Meta in the \u2601"
                },
                "personality": []
            }
        }
        # Create dummy public IPv6 network
        sub6 = mfactory.IPv6SubnetFactory(network__public=True)
        self.net6 = sub6.network
        self.network_settings = {
            "CYCLADES_DEFAULT_SERVER_NETWORKS": [],
            "CYCLADES_FORCED_SERVER_NETWORKS": ["SNF:ANY_PUBLIC_IPV6"]
        }

    def test_create_server(self, mrapi):
        """Test if the create server call returns the expected response
           if a valid request has been speficied."""

        mrapi().CreateInstance.return_value = 12
        with override_settings(settings, **self.network_settings):
            with mocked_quotaholder():
                response = self.mypost('servers', 'test_user',
                                       json.dumps(self.request), 'json')
        self.assertEqual(response.status_code, 202)
        mrapi().CreateInstance.assert_called_once()

        api_server = json.loads(response.content)['server']
        self.assertEqual(api_server['status'], "BUILD")
        self.assertEqual(api_server['progress'], 0)
        self.assertEqual(api_server['metadata'][u"Meta \u2601"],
                         u"Meta in the \u2601")
        self.assertTrue('adminPass' in api_server)

        db_vm = VirtualMachine.objects.get(userid='test_user')
        self.assertEqual(api_server['name'], u"Server in the \u2601")
        self.assertEqual(api_server['status'], db_vm.operstate)

    def test_create_server_wrong_flavor(self, mrapi):
        # Test with a flavor that does not exist
        request = deepcopy(self.request)
        request["server"]["flavorRef"] = 42
        with override_settings(settings, **self.network_settings):
            with mocked_quotaholder():
                response = self.mypost('servers', 'test_user',
                                       json.dumps(request), 'json')
        self.assertItemNotFound(response)

        # Test with an flavor that is not allowed
        flavor = mfactory.FlavorFactory(allow_create=False)
        request["server"]["flavorRef"] = flavor.id
        with override_settings(settings, **self.network_settings):
            with mocked_quotaholder():
                response = self.mypost('servers', 'test_user',
                                       json.dumps(request), 'json')
        self.assertEqual(response.status_code, 403)

    def test_create_server_error(self, mrapi):
        """Test if the create server call returns the expected response
           if a valid request has been speficied."""
        mrapi().CreateInstance.side_effect = GanetiApiError("..ganeti is down")

        request = self.request
        with override_settings(settings, **self.network_settings):
            with mocked_quotaholder():
                response = self.mypost('servers', 'test_user',
                                       json.dumps(request), 'json')
        self.assertEqual(response.status_code, 202)
        mrapi().CreateInstance.assert_called_once()
        vm = VirtualMachine.objects.get()
        # The VM has not been deleted
        self.assertFalse(vm.deleted)
        # but is in "ERROR" operstate
        self.assertEqual(vm.operstate, "ERROR")

    def test_create_network_info(self, mrapi):
        mrapi().CreateInstance.return_value = 12

        # User requested private networks
        s1 = mfactory.IPv4SubnetFactory(network__userid="test")
        s2 = mfactory.IPv6SubnetFactory(network__userid="test")
        # and a public IPv6
        request = deepcopy(self.request)
        request["server"]["networks"] = [{"uuid": s1.network_id},
                                         {"uuid": s2.network_id}]
        with override_settings(settings, **self.network_settings):
            with mocked_quotaholder():
                response = self.mypost('servers', "test",
                                       json.dumps(request), 'json')
        self.assertEqual(response.status_code, 202)
        name, args, kwargs = mrapi().CreateInstance.mock_calls[0]
        self.assertEqual(len(kwargs["nics"]), 3)
        self.assertEqual(kwargs["nics"][0]["network"], self.net6.backend_id)
        self.assertEqual(kwargs["nics"][1]["network"], s1.network.backend_id)
        self.assertEqual(kwargs["nics"][2]["network"], s2.network.backend_id)

        # but fail if others user network
        s3 = mfactory.IPv6SubnetFactory(network__userid="test_other")
        request = deepcopy(self.request)
        request["server"]["networks"] = [{"uuid": s3.network_id}]
        response = self.mypost('servers', "test", json.dumps(request), 'json')
        self.assertEqual(response.status_code, 404)

        # User requested public networks
        # but no floating IP..
        s1 = mfactory.IPv4SubnetFactory(network__public=True)
        request = deepcopy(self.request)
        request["server"]["networks"] = [{"uuid": s1.network_id}]
        response = self.mypost('servers', "test", json.dumps(request), 'json')
        self.assertEqual(response.status_code, 409)

        # Add one floating IP
        fp1 = mfactory.IPv4AddressFactory(userid="test", subnet=s1,
                                          network=s1.network,
                                          floating_ip=True, nic=None)
        self.assertEqual(fp1.nic, None)
        request = deepcopy(self.request)
        request["server"]["networks"] = [{"uuid": s1.network_id,
                                          "fixed_ip": fp1.address}]
        with mocked_quotaholder():
            with override_settings(settings, **self.network_settings):
                response = self.mypost('servers', "test",
                                       json.dumps(request), 'json')
        self.assertEqual(response.status_code, 202)
        server_id = json.loads(response.content)["server"]["id"]
        fp1 = IPAddress.objects.get(id=fp1.id)
        self.assertEqual(fp1.nic.machine_id, server_id)

        # check used floating IP
        response = self.mypost('servers', "test", json.dumps(request), 'json')
        self.assertEqual(response.status_code, 409)

        # Add more floating IP. but check auto-reserve
        fp2 = mfactory.IPv4AddressFactory(userid="test", subnet=s1,
                                          network=s1.network,
                                          floating_ip=True, nic=None)
        self.assertEqual(fp2.nic, None)
        request = deepcopy(self.request)
        request["server"]["networks"] = [{"uuid": s1.network_id}]
        with mocked_quotaholder():
            with override_settings(settings, **self.network_settings):
                response = self.mypost('servers', "test",
                                       json.dumps(request), 'json')
        self.assertEqual(response.status_code, 202)
        server_id = json.loads(response.content)["server"]["id"]
        fp2 = IPAddress.objects.get(id=fp2.id)
        self.assertEqual(fp2.nic.machine_id, server_id)

        name, args, kwargs = mrapi().CreateInstance.mock_calls[-1]
        self.assertEqual(len(kwargs["nics"]), 2)
        self.assertEqual(kwargs["nics"][0]["network"], self.net6.backend_id)
        self.assertEqual(kwargs["nics"][1]["network"], fp2.network.backend_id)

    def test_create_network_settings(self, mrapi):
        mrapi().CreateInstance.return_value = 12
        # User requested private networks
        # no public IPv4
        network_settings = {
            "CYCLADES_DEFAULT_SERVER_NETWORKS": [],
            "CYCLADES_FORCED_SERVER_NETWORKS": ["SNF:ANY_PUBLIC_IPV4"]
        }
        with override_settings(settings, **network_settings):
            response = self.mypost('servers', "test", json.dumps(self.request),
                                   'json')
        self.assertEqual(response.status_code, 503)
        # no public IPv4, IPv6 exists
        network_settings = {
            "CYCLADES_DEFAULT_SERVER_NETWORKS": [],
            "CYCLADES_FORCED_SERVER_NETWORKS": ["SNF:ANY_PUBLIC"]
        }
        with override_settings(settings, **network_settings):
            response = self.mypost('servers', "test", json.dumps(self.request),
                                   'json')
        self.assertEqual(response.status_code, 202)
        server_id = json.loads(response.content)["server"]["id"]
        vm = VirtualMachine.objects.get(id=server_id)
        self.assertEqual(vm.nics.get().ipv4_address, None)

        # IPv4 exists
        mfactory.IPv4SubnetFactory(network__public=True,
                                   cidr="192.168.2.0/24",
                                   pool__offset=2,
                                   pool__size=1)
        with override_settings(settings, **network_settings):
            response = self.mypost('servers', "test", json.dumps(self.request),
                                   'json')
        self.assertEqual(response.status_code, 202)
        server_id = json.loads(response.content)["server"]["id"]
        vm = VirtualMachine.objects.get(id=server_id)
        self.assertEqual(vm.nics.get().ipv4_address, "192.168.2.2")

        # Fixed networks
        net1 = mfactory.NetworkFactory(userid="test")
        net2 = mfactory.NetworkFactory(userid="test")
        net3 = mfactory.NetworkFactory(userid="test")
        network_settings = {
            "CYCLADES_DEFAULT_SERVER_NETWORKS": [],
            "CYCLADES_FORCED_SERVER_NETWORKS": [net1.id, [net2.id, net3.id],
                                                (net3.id, net2.id)]
        }
        with override_settings(settings, **network_settings):
            response = self.mypost('servers', "test", json.dumps(self.request),
                                   'json')
        self.assertEqual(response.status_code, 202)
        server_id = json.loads(response.content)["server"]["id"]
        vm = VirtualMachine.objects.get(id=server_id)
        self.assertEqual(len(vm.nics.all()), 3)

    def test_create_server_with_port(self, mrapi):
        # Test invalid networks
        request = deepcopy(self.request)
        request["server"]["networks"] = {"foo": "lala"}
        with override_settings(settings, **self.network_settings):
            response = self.mypost("servers", "dummy_user",
                                   json.dumps(request), 'json')
        self.assertBadRequest(response)
        request["server"]["networks"] = ['1', '2']
        with override_settings(settings, **self.network_settings):
            response = self.mypost("servers", "dummy_user",
                                   json.dumps(request), 'json')
        self.assertBadRequest(response)
        mrapi().CreateInstance.return_value = 42
        ip = mfactory.IPv4AddressFactory(nic__machine=None)
        port1 = ip.nic
        request = deepcopy(self.request)
        request["server"]["networks"] = [{"port": port1.id}]
        with override_settings(settings, **self.network_settings):
            with mocked_quotaholder():
                response = self.mypost("servers", port1.userid,
                                       json.dumps(request), 'json')
        self.assertEqual(response.status_code, 202)
        vm_id = json.loads(response.content)["server"]["id"]
        port1 = NetworkInterface.objects.get(id=port1.id)
        self.assertEqual(port1.machine_id, vm_id)
        # 409 if already used
        with override_settings(settings, **self.network_settings):
            with mocked_quotaholder():
                response = self.mypost("servers", port1.userid,
                                       json.dumps(request), 'json')
        self.assertConflict(response)
        # Test permissions
        ip = mfactory.IPv4AddressFactory(userid="user1", nic__userid="user1")
        port2 = ip.nic
        request["server"]["networks"] = [{"port": port2.id}]
        with override_settings(settings, **self.network_settings):
            with mocked_quotaholder():
                response = self.mypost("servers", "user2",
                                       json.dumps(request), 'json')
        self.assertEqual(response.status_code, 404)

    def test_create_server_with_volumes(self, mrapi):
        user = "test_user"
        mrapi().CreateInstance.return_value = 42
        # Test creation without any volumes. Server will use flavor+image
        request = deepcopy(self.request)
        request["server"]["block_device_mapping_v2"] = []
        with mocked_quotaholder():
            response = self.mypost("servers", user,
                                   json.dumps(request), 'json')
        self.assertEqual(response.status_code, 202, msg=response.content)
        vm_id = json.loads(response.content)["server"]["id"]
        volume = Volume.objects.get(machine_id=vm_id)
        self.assertEqual(volume.volume_type, self.flavor.volume_type)
        self.assertEqual(volume.size, self.flavor.disk)
        self.assertEqual(volume.source, "image:%s" % fixed_image()["id"])
        self.assertEqual(volume.delete_on_termination, True)
        self.assertEqual(volume.userid, user)

        # Test using an image
        request["server"]["block_device_mapping_v2"] = [
            {"source_type": "image",
             "uuid": fixed_image()["id"],
             "volume_size": 10,
             "delete_on_termination": False}
        ]
        with mocked_quotaholder():
            response = self.mypost("servers", user,
                                   json.dumps(request), 'json')
        self.assertEqual(response.status_code, 202, msg=response.content)
        vm_id = json.loads(response.content)["server"]["id"]
        volume = Volume.objects.get(machine_id=vm_id)
        self.assertEqual(volume.volume_type, self.flavor.volume_type)
        self.assertEqual(volume.size, 10)
        self.assertEqual(volume.source, "image:%s" % fixed_image()["id"])
        self.assertEqual(volume.delete_on_termination, False)
        self.assertEqual(volume.userid, user)
        self.assertEqual(volume.origin, "pithos:" + fixed_image()["mapfile"])

        # Test using a snapshot
        request["server"]["block_device_mapping_v2"] = [
            {"source_type": "snapshot",
             "uuid": fixed_image()["id"],
             "volume_size": 10,
             "delete_on_termination": False}
        ]
        with mocked_quotaholder():
            response = self.mypost("servers", user,
                                   json.dumps(request), 'json')
        self.assertEqual(response.status_code, 202, msg=response.content)
        vm_id = json.loads(response.content)["server"]["id"]
        volume = Volume.objects.get(machine_id=vm_id)
        self.assertEqual(volume.volume_type, self.flavor.volume_type)
        self.assertEqual(volume.size, 10)
        self.assertEqual(volume.source, "snapshot:%s" % fixed_image()["id"])
        self.assertEqual(volume.origin, fixed_image()["mapfile"])
        self.assertEqual(volume.delete_on_termination, False)
        self.assertEqual(volume.userid, user)

        source_volume = volume
        # Test using source volume
        request["server"]["block_device_mapping_v2"] = [
            {"source_type": "volume",
             "uuid": source_volume.id,
             "volume_size": source_volume.size,
             "delete_on_termination": False}
        ]
        with mocked_quotaholder():
            response = self.mypost("servers", user,
                                   json.dumps(request), 'json')
        # This will fail because the volume is not AVAILABLE.
        self.assertBadRequest(response)

        # Test using a blank volume
        request["server"]["block_device_mapping_v2"] = [
            {"source_type": "blank",
             "volume_size": 10,
             "delete_on_termination": True}
        ]
        with mocked_quotaholder():
            response = self.mypost("servers", user,
                                   json.dumps(request), 'json')
        self.assertBadRequest(response)


@patch('synnefo.logic.rapi_pool.GanetiRapiClient')
class ServerDestroyAPITest(ComputeAPITest):
    def test_delete_server(self, mrapi):
        vm = mfactory.VirtualMachineFactory()
        mrapi().DeleteInstance.return_value = 12
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

        request = {
            'metadata': {
                'foo': 'bar'
            },
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
        mrapi().StartupInstance.return_value = 0
        mrapi().ShutdownInstance.return_value = 1
        mrapi().RebootInstance.return_value = 2
        for jobId, action in enumerate(actions):
            if action in ["shutdown", "reboot"]:
                vm.operstate = "STARTED"
            else:
                vm.operstate = "STOPPED"
            vm.task = None
            vm.task_job_id = None
            vm.save()
            val = {'type': 'HARD'} if action == 'reboot' else {}
            request = {action: val}
            response = self.mypost('servers/%d/action' % vm.id,
                                   vm.userid, json.dumps(request), 'json')
            self.assertEqual(response.status_code, 202)
            if action == 'shutdown':
                self.assertEqual(VirtualMachine.objects.get(id=vm.id).task,
                                 "STOP")
            else:
                self.assertEqual(VirtualMachine.objects.get(id=vm.id).task,
                                 action.upper())
            self.assertEqual(VirtualMachine.objects.get(id=vm.id).task_job_id,
                             jobId)

    def test_action_in_building_vm(self, mrapi, mimage):
        """Test building in progress"""
        vm = mfactory.VirtualMachineFactory(operstate="BUILD")
        request = {'start': {}}
        with mocked_quotaholder():
            response = self.mypost('servers/%d/action' % vm.id,
                                   vm.userid, json.dumps(request), 'json')
        self.assertEqual(response.status_code, 409)
        self.assertFalse(mrapi.mock_calls)

    def test_destroy_build_vm(self, mrapi, mimage):
        """Test building in progress"""
        vm = mfactory.VirtualMachineFactory()
        mrapi().DeleteInstance.return_value = 2
        response = self.mydelete('servers/%d' % vm.id,
                                 vm.userid)
        self.assertSuccess(response)
        mrapi().RemoveInstance.assert_called_once()

    def test_firewall(self, mrapi, mimage):
        vm = mfactory.VirtualMachineFactory()
        vm.operstate = "STOPPED"
        vm.save()
        request = {'firewallProfile': {'profile': 'PROTECTED'}}
        response = self.mypost('servers/%d/action' % vm.id,
                               vm.userid, json.dumps(request), 'json')
        self.assertBadRequest(response)
        request = {'firewallProfile': {'profile': 'PROTECTED', "nic": "10"}}
        response = self.mypost('servers/%d/action' % vm.id,
                               vm.userid, json.dumps(request), 'json')
        self.assertItemNotFound(response)
        request = {'firewallProfile': {'profile': 'PROTECTED', "nic": "error"}}
        response = self.mypost('servers/%d/action' % vm.id,
                               vm.userid, json.dumps(request), 'json')
        self.assertBadRequest(response)
        nic = mfactory.NetworkInterfaceFactory(machine=vm)
        request = {'firewallProfile': {'profile': 'PROTECTED', "nic": nic.id}}
        response = self.mypost('servers/%d/action' % vm.id,
                               vm.userid, json.dumps(request), 'json')
        self.assertSuccess(response)
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

    def test_resize_vm(self, mrapi, mimage):
        flavor = mfactory.FlavorFactory(cpu=1, ram=1024)
        # Check building VM
        vm = self.get_vm(flavor=flavor, operstate="BUILD")
        request = {'resize': {'flavorRef': flavor.id}}
        response = self.mypost('servers/%d/action' % vm.id,
                               vm.userid, json.dumps(request), 'json')
        self.assertFault(response, 409, "buildInProgress")
        # Check same Flavor
        vm = self.get_vm(flavor=flavor, operstate="STOPPED")
        request = {'resize': {'flavorRef': flavor.id}}
        response = self.mypost('servers/%d/action' % vm.id,
                               vm.userid, json.dumps(request), 'json')
        self.assertBadRequest(response)
        # Check flavor with different disk
        flavor2 = mfactory.FlavorFactory(disk=1024)
        flavor3 = mfactory.FlavorFactory(disk=2048)
        vm = self.get_vm(flavor=flavor2, operstate="STOPPED")
        request = {'resize': {'flavorRef': flavor3.id}}
        response = self.mypost('servers/%d/action' % vm.id,
                               vm.userid, json.dumps(request), 'json')
        self.assertBadRequest(response)

        # Check flavor with different volume type
        flavor2 = mfactory.FlavorFactory(volume_type__disk_template="foo")
        flavor3 = mfactory.FlavorFactory(volume_type__disk_template="baz")
        vm = self.get_vm(flavor=flavor2, operstate="STOPPED")
        request = {'resize': {'flavorRef': flavor3.id}}
        response = self.mypost('servers/%d/action' % vm.id,
                               vm.userid, json.dumps(request), 'json')
        self.assertBadRequest(response)
        # Check success
        vm = self.get_vm(flavor=flavor, operstate="STOPPED")
        flavor4 = mfactory.FlavorFactory(volume_type=vm.flavor.volume_type,
                                         disk=flavor.disk,
                                         cpu=4, ram=2048)
        request = {'resize': {'flavorRef': flavor4.id}}
        mrapi().ModifyInstance.return_value = 42
        response = self.mypost('servers/%d/action' % vm.id,
                               vm.userid, json.dumps(request), 'json')
        self.assertEqual(response.status_code, 202)
        vm = VirtualMachine.objects.get(id=vm.id)
        self.assertEqual(vm.task_job_id, 42)
        name, args, kwargs = mrapi().ModifyInstance.mock_calls[0]
        self.assertEqual(kwargs["beparams"]["vcpus"], 4)
        self.assertEqual(kwargs["beparams"]["minmem"], 2048)
        self.assertEqual(kwargs["beparams"]["maxmem"], 2048)

    def test_action_on_resizing_vm(self, mrapi, mimage):
        vm = mfactory.VirtualMachineFactory()
        vm.operstate = "RESIZE"
        vm.save()
        for action in VirtualMachine.ACTIONS:
            request = {action[0]: ""}
            response = self.mypost('servers/%d/action' % vm.id,
                                   vm.userid, json.dumps(request), 'json')
            self.assertBadRequest(response)
        # however you can destroy
        mrapi().DeleteInstance.return_value = 42
        response = self.mydelete('servers/%d' % vm.id,
                                 vm.userid)
        self.assertSuccess(response)

    def get_vm(self, flavor, operstate):
        vm = mfactory.VirtualMachineFactory(flavor=flavor)
        vm.operstate = operstate
        vm.backendjobstatus = "success"
        vm.save()
        return vm


class ServerVNCConsole(ComputeAPITest):
    def test_not_active_server(self):
        """Test console req for not ACTIVE server returns badRequest"""
        vm = mfactory.VirtualMachineFactory(operstate="BUILD")
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
        with patch('synnefo.logic.rapi_pool.GanetiRapiClient') as rapi:
            rapi().GetInstance.return_value = {"pnode": "node1",
                                               "network_port": 5055,
                                               "oper_state": True,
                                               "hvparams": {
                                                   "serial_console": False
                                               }}
            with patch("synnefo.logic.servers.request_vnc_forwarding") as vnc:
                vnc.return_value = {"status": "OK",
                                    "source_port": 42}
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


@patch('synnefo.logic.rapi_pool.GanetiRapiClient')
class ServerAttachments(ComputeAPITest):
    def test_list_attachments(self, mrapi):
        # Test default volume
        vol = mfactory.VolumeFactory()
        vm = vol.machine

        response = self.myget("servers/%d/os-volume_attachments" % vm.id,
                              vm.userid)
        self.assertSuccess(response)
        attachments = json.loads(response.content)
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments["volumeAttachments"][0],
                         {"volumeId": vol.id,
                          "serverId": vm.id,
                          "id": vol.id,
                          "device": ""})

        # Test deleted Volume
        dvol = mfactory.VolumeFactory(machine=vm, deleted=True)
        response = self.myget("servers/%d/os-volume_attachments" % vm.id,
                              vm.userid)
        self.assertSuccess(response)
        attachments = json.loads(response.content)["volumeAttachments"]
        self.assertEqual(len([d for d in attachments if d["id"] == dvol.id]),
                         0)

    def test_attach_detach_volume(self, mrapi):
        vol = mfactory.VolumeFactory(status="AVAILABLE")
        vm = vol.machine
        volume_type = vm.flavor.volume_type
        # Test that we cannot detach the root volume
        response = self.mydelete("servers/%d/os-volume_attachments/%d" %
                                 (vm.id, vol.id), vm.userid)
        self.assertBadRequest(response)

        # Test that we cannot attach a used volume
        vol1 = mfactory.VolumeFactory(status="IN_USE",
                                      volume_type=volume_type,
                                      userid=vm.userid)
        request = json.dumps({"volumeAttachment": {"volumeId": vol1.id}})
        response = self.mypost("servers/%d/os-volume_attachments" %
                               vm.id, vm.userid,
                               request, "json")
        self.assertBadRequest(response)

        vol1.status = "AVAILABLE"
        # We cannot attach a volume of different disk template
        volume_type_2 = mfactory.VolumeTypeFactory(disk_template="lalalal")
        vol1.volume_type = volume_type_2
        vol1.save()
        response = self.mypost("servers/%d/os-volume_attachments/" %
                               vm.id, vm.userid,
                               request, "json")
        self.assertBadRequest(response)

        vol1.volume_type = volume_type
        vol1.save()
        mrapi().ModifyInstance.return_value = 43
        response = self.mypost("servers/%d/os-volume_attachments" %
                               vm.id, vm.userid,
                               request, "json")
        self.assertEqual(response.status_code, 202, response.content)
        attachment = json.loads(response.content)["volumeAttachment"]
        self.assertEqual(attachment, {"volumeId": vol1.id,
                                      "serverId": vm.id,
                                      "id": vol1.id,
                                      "device": ""})
        # And we delete it...will fail because of status
        response = self.mydelete("servers/%d/os-volume_attachments/%d" %
                                 (vm.id, vol1.id), vm.userid)
        self.assertBadRequest(response)
        vm.task = None
        vm.save()
        vm.volumes.all().update(status="IN_USE")
        response = self.mydelete("servers/%d/os-volume_attachments/%d" %
                                 (vm.id, vol1.id), vm.userid)
        self.assertEqual(response.status_code, 202, response.content)
