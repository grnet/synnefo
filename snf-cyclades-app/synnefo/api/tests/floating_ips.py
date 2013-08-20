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
from synnefo.db.models import FloatingIP
from synnefo.db.models_factory import (FloatingIPFactory, NetworkFactory,
                                       VirtualMachineFactory,
                                       NetworkInterfaceFactory,
                                       BackendNetworkFactory)
from mock import patch, Mock
from functools import partial

from synnefo.cyclades_settings import cyclades_services
from synnefo.lib.services import get_service_path
from synnefo.lib import join_urls


compute_path = get_service_path(cyclades_services, "compute", version="v2.0")
URL = join_urls(compute_path, "os-floating-ips")
NETWORKS_URL = join_urls(compute_path, "networks")
SERVERS_URL = join_urls(compute_path, "servers")

FloatingIPPoolFactory = partial(NetworkFactory, public=True, deleted=False,
                                floating_ip_pool=True)


class FloatingIPAPITest(BaseAPITest):
    def test_no_floating_ip(self):
        response = self.get(URL)
        self.assertSuccess(response)
        self.assertEqual(json.loads(response.content)["floating_ips"], [])

    def test_list_ips(self):
        ip = FloatingIPFactory(userid="user1")
        FloatingIPFactory(userid="user1", deleted=True)
        with mocked_quotaholder():
            response = self.get(URL, "user1")
        self.assertSuccess(response)
        api_ip = json.loads(response.content)["floating_ips"][0]
        self.assertEqual(api_ip,
                         {"instance_id": str(ip.machine.id), "ip": ip.ipv4,
                          "fixed_ip": None, "id": str(ip.id),  "pool":
                          str(ip.network.id)})

    def test_get_ip(self):
        ip = FloatingIPFactory(userid="user1")
        with mocked_quotaholder():
            response = self.get(URL + "/%s" % ip.id, "user1")
        self.assertSuccess(response)
        api_ip = json.loads(response.content)["floating_ip"]
        self.assertEqual(api_ip,
                         {"instance_id": str(ip.machine.id), "ip": ip.ipv4,
                          "fixed_ip": None, "id": str(ip.id),  "pool":
                          str(ip.network.id)})

    def test_wrong_user(self):
        ip = FloatingIPFactory(userid="user1")
        with mocked_quotaholder():
            response = self.delete(URL + "/%s" % ip.id, "user2")
        self.assertItemNotFound(response)

    def test_deleted_ip(self):
        ip = FloatingIPFactory(userid="user1", deleted=True)
        with mocked_quotaholder():
            response = self.delete(URL + "/%s" % ip.id, "user1")
        self.assertItemNotFound(response)

    def test_reserve(self):
        net = FloatingIPPoolFactory(userid="test_user",
                                    subnet="192.168.2.0/24",
                                    gateway=None)
        request = {'pool': net.id}
        with mocked_quotaholder():
            response = self.post(URL, "test_user", json.dumps(request), "json")
        self.assertSuccess(response)
        ip = FloatingIP.objects.get()
        self.assertEqual(ip.ipv4, "192.168.2.1")
        self.assertEqual(ip.machine, None)
        self.assertEqual(ip.network, net)
        self.assertEqual(json.loads(response.content)["floating_ip"],
                         {"instance_id": None, "ip": "192.168.2.1",
                          "fixed_ip": None, "id": str(ip.id),
                          "pool": str(net.id)})

    def test_reserve_no_pool(self):
        # No networks
        with mocked_quotaholder():
            response = self.post(URL, "test_user", json.dumps({}), "json")
        self.assertFault(response, 413, "overLimit")
        # Full network
        FloatingIPPoolFactory(userid="test_user",
                              subnet="192.168.2.0/32",
                              gateway=None)
        with mocked_quotaholder():
            response = self.post(URL, "test_user", json.dumps({}), "json")
        self.assertFault(response, 413, "overLimit")
        # Success
        net2 = FloatingIPPoolFactory(userid="test_user",
                                     subnet="192.168.2.0/24",
                                     gateway=None)
        with mocked_quotaholder():
            response = self.post(URL, "test_user", json.dumps({}), "json")
        self.assertSuccess(response)
        ip = FloatingIP.objects.get()
        self.assertEqual(json.loads(response.content)["floating_ip"],
                         {"instance_id": None, "ip": "192.168.2.1",
                          "fixed_ip": None, "id": str(ip.id),
                          "pool": str(net2.id)})

    def test_reserve_full(self):
        net = FloatingIPPoolFactory(userid="test_user",
                                    subnet="192.168.2.0/32")
        request = {'pool': net.id}
        with mocked_quotaholder():
            response = self.post(URL, "test_user", json.dumps(request), "json")
        self.assertEqual(response.status_code, 413)

    def test_reserve_with_address(self):
        net = FloatingIPPoolFactory(userid="test_user",
                                    subnet="192.168.2.0/24")
        request = {'pool': net.id, "address": "192.168.2.10"}
        with mocked_quotaholder():
            response = self.post(URL, "test_user", json.dumps(request), "json")
        self.assertSuccess(response)
        ip = FloatingIP.objects.get()
        self.assertEqual(json.loads(response.content)["floating_ip"],
                         {"instance_id": None, "ip": "192.168.2.10",
                          "fixed_ip": None, "id": str(ip.id), "pool":
                          str(net.id)})

        # Already reserved
        FloatingIPFactory(network=net, ipv4="192.168.2.3")
        request = {'pool': net.id, "address": "192.168.2.3"}
        with mocked_quotaholder():
            response = self.post(URL, "test_user", json.dumps(request), "json")
        self.assertFault(response, 409, "conflict")

        # Already used
        pool = net.get_pool()
        pool.reserve("192.168.2.5")
        pool.save()
        # ..by another_user
        nic = NetworkInterfaceFactory(network=net, ipv4="192.168.2.5",
                                      machine__userid="test2")
        request = {'pool': net.id, "address": "192.168.2.5"}
        with mocked_quotaholder():
            response = self.post(URL, "test_user", json.dumps(request), "json")
        self.assertFault(response, 409, "conflict")
        # ..and by him
        nic.delete()
        NetworkInterfaceFactory(network=net, ipv4="192.168.2.5",
                                machine__userid="test_user")
        request = {'pool': net.id, "address": "192.168.2.5"}
        with mocked_quotaholder():
            response = self.post(URL, "test_user", json.dumps(request), "json")
        self.assertSuccess(response)

        # Address out of pool
        request = {'pool': net.id, "address": "192.168.3.5"}
        with mocked_quotaholder():
            response = self.post(URL, "test_user", json.dumps(request), "json")
        self.assertBadRequest(response)

    def test_release_in_use(self):
        ip = FloatingIPFactory()
        vm = ip.machine
        vm.operstate = "ACTIVE"
        vm.userid = ip.userid
        vm.save()
        vm.nics.create(index=0, ipv4=ip.ipv4, network=ip.network,
                       state="ACTIVE")
        with mocked_quotaholder():
            response = self.delete(URL + "/%s" % ip.id, ip.userid)
        self.assertFault(response, 409, "conflict")
        # Also send a notification to remove the NIC and assert that FIP is in
        # use until notification from ganeti arrives
        request = {"removeFloatingIp": {"address": ip.ipv4}}
        url = SERVERS_URL + "/%s/action" % vm.id
        with patch('synnefo.logic.rapi_pool.GanetiRapiClient') as c:
            c().ModifyInstance.return_value = 10
            response = self.post(url, vm.userid, json.dumps(request),
                                 "json")
        self.assertEqual(response.status_code, 202)
        with mocked_quotaholder():
            response = self.delete(URL + "/%s" % ip.id, ip.userid)
        self.assertFault(response, 409, "conflict")

    def test_release(self):
        ip = FloatingIPFactory(machine=None)
        with mocked_quotaholder():
            response = self.delete(URL + "/%s" % ip.id, ip.userid)
        self.assertSuccess(response)
        ips_after = FloatingIP.objects.filter(id=ip.id)
        self.assertEqual(len(ips_after), 0)

    @patch("synnefo.logic.backend", Mock())
    def test_delete_network_with_floating_ips(self):
        ip = FloatingIPFactory(machine=None, network__flavor="IP_LESS_ROUTED")
        net = ip.network
        # Can not remove network with floating IPs
        with mocked_quotaholder():
            response = self.delete(NETWORKS_URL + "/%s" % net.id,
                                   net.userid)
        self.assertFault(response, 421, "networkInUse")
        # But we can with only deleted Floating Ips
        ip.deleted = True
        ip.save()
        with mocked_quotaholder():
            response = self.delete(NETWORKS_URL + "/%s" % net.id,
                                   net.userid)
        self.assertSuccess(response)


POOLS_URL = join_urls(compute_path, "os-floating-ip-pools")


class FloatingIPPoolsAPITest(BaseAPITest):
    def test_no_pool(self):
        response = self.get(POOLS_URL)
        self.assertSuccess(response)
        self.assertEqual(json.loads(response.content)["floating_ip_pools"], [])

    def test_list_pools(self):
        net = FloatingIPPoolFactory(subnet="192.168.0.0/30",
                                    gateway="192.168.0.1")
        NetworkFactory(public=True, deleted=True)
        NetworkFactory(public=False, deleted=False)
        NetworkFactory(public=True, deleted=False)
        response = self.get(POOLS_URL)
        self.assertSuccess(response)
        self.assertEqual(json.loads(response.content)["floating_ip_pools"],
                         [{"name": str(net.id), "size": 4, "free": 1}])


class FloatingIPActionsTest(BaseAPITest):
    def setUp(self):
        vm = VirtualMachineFactory()
        vm.operstate = "ACTIVE"
        vm.save()
        self.vm = vm

    def test_bad_request(self):
        url = SERVERS_URL + "/%s/action" % self.vm.id
        response = self.post(url, self.vm.userid, json.dumps({}), "json")
        self.assertBadRequest(response)
        response = self.post(url, self.vm.userid,
                             json.dumps({"addFloatingIp": {}}),
                             "json")
        self.assertBadRequest(response)

    @patch('synnefo.logic.rapi_pool.GanetiRapiClient')
    def test_add_floating_ip(self, mock):
        # Not exists
        url = SERVERS_URL + "/%s/action" % self.vm.id
        request = {"addFloatingIp": {"address": "10.0.0.1"}}
        response = self.post(url, self.vm.userid, json.dumps(request), "json")
        self.assertItemNotFound(response)
        # In use
        vm1 = VirtualMachineFactory()
        ip1 = FloatingIPFactory(userid=self.vm.userid, machine=vm1)
        BackendNetworkFactory(network=ip1.network, backend=vm1.backend,
                              operstate='ACTIVE')
        request = {"addFloatingIp": {"address": ip1.ipv4}}
        response = self.post(url, self.vm.userid, json.dumps(request), "json")
        self.assertFault(response, 409, "conflict")
        # Success
        ip1 = FloatingIPFactory(userid=self.vm.userid, machine=None)
        BackendNetworkFactory(network=ip1.network, backend=self.vm.backend,
                              operstate='ACTIVE')
        request = {"addFloatingIp": {"address": ip1.ipv4}}
        mock().ModifyInstance.return_value = 1
        response = self.post(url, self.vm.userid, json.dumps(request), "json")
        self.assertEqual(response.status_code, 202)
        ip1_after = FloatingIP.objects.get(id=ip1.id)
        self.assertEqual(ip1_after.machine, self.vm)
        self.assertTrue(ip1_after.in_use())
        self.vm.nics.create(ipv4=ip1_after.ipv4, network=ip1_after.network,
                            state="ACTIVE", index=0)
        response = self.get(SERVERS_URL + "/%s" % self.vm.id,
                            self.vm.userid)
        self.assertSuccess(response)
        nic = json.loads(response.content)["server"]["attachments"][0]
        self.assertEqual(nic["OS-EXT-IPS:type"], "floating")

    @patch('synnefo.logic.rapi_pool.GanetiRapiClient')
    def test_remove_floating_ip(self, mock):
        # Not exists
        url = SERVERS_URL + "/%s/action" % self.vm.id
        request = {"removeFloatingIp": {"address": "10.0.0.1"}}
        response = self.post(url, self.vm.userid, json.dumps(request), "json")
        self.assertItemNotFound(response)
        # Not In Use
        ip1 = FloatingIPFactory(userid=self.vm.userid, machine=None)
        request = {"removeFloatingIp": {"address": ip1.ipv4}}
        response = self.post(url, self.vm.userid, json.dumps(request), "json")
        self.assertItemNotFound(response)
        # Success
        ip1 = FloatingIPFactory(userid=self.vm.userid, machine=self.vm)
        NetworkInterfaceFactory(machine=self.vm, ipv4=ip1.ipv4)
        request = {"removeFloatingIp": {"address": ip1.ipv4}}
        mock().ModifyInstance.return_value = 2
        response = self.post(url, self.vm.userid, json.dumps(request), "json")
        self.assertEqual(response.status_code, 202)
        # Yet used. Wait for the callbacks
        ip1_after = FloatingIP.objects.get(id=ip1.id)
        self.assertEqual(ip1_after.machine, self.vm)
        self.assertTrue(ip1_after.in_use())
