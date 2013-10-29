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
from synnefo.db.models import IPAddress
from synnefo.db import models_factory as mf
from synnefo.db.models_factory import (NetworkFactory,
                                       VirtualMachineFactory)
from mock import patch, Mock
from functools import partial

from synnefo.cyclades_settings import cyclades_services
from synnefo.lib.services import get_service_path
from synnefo.lib import join_urls


compute_path = get_service_path(cyclades_services, "compute", version="v2.0")
URL = join_urls(compute_path, "os-floating-ips")
NETWORKS_URL = join_urls(compute_path, "networks")
SERVERS_URL = join_urls(compute_path, "servers")


floating_ips = IPAddress.objects.filter(floating_ip=True)
FloatingIPPoolFactory = partial(NetworkFactory, public=True, deleted=False,
                                floating_ip_pool=True)


class FloatingIPAPITest(BaseAPITest):
    def setUp(self):
        self.pool = mf.NetworkWithSubnetFactory(floating_ip_pool=True,
                                                public=True,
                                                subnet__cidr="192.168.2.0/24",
                                                subnet__gateway="192.168.2.1")

    def test_no_floating_ip(self):
        response = self.get(URL)
        self.assertSuccess(response)
        self.assertEqual(json.loads(response.content)["floating_ips"], [])

    def test_list_ips(self):
        ip = mf.IPv4AddressFactory(userid="user1", floating_ip=True)
        with mocked_quotaholder():
            response = self.get(URL, "user1")
        self.assertSuccess(response)
        api_ip = json.loads(response.content)["floating_ips"][0]
        self.assertEqual(api_ip,
                         {"instance_id": str(ip.nic.machine_id),
                          "ip": ip.address,
                          "fixed_ip": None,
                          "id": str(ip.id),
                          "pool": str(ip.network_id)})

    def test_get_ip(self):
        ip = mf.IPv4AddressFactory(userid="user1", floating_ip=True)
        with mocked_quotaholder():
            response = self.get(URL + "/%s" % ip.id, "user1")
        self.assertSuccess(response)
        api_ip = json.loads(response.content)["floating_ip"]
        self.assertEqual(api_ip,
                         {"instance_id": str(ip.nic.machine_id),
                          "ip": ip.address,
                          "fixed_ip": None,
                          "id": str(ip.id),
                          "pool": str(ip.network_id)})

    def test_wrong_user(self):
        ip = mf.IPv4AddressFactory(userid="user1", floating_ip=True)
        response = self.delete(URL + "/%s" % ip.id, "user2")
        self.assertItemNotFound(response)

    def test_deleted_ip(self):
        ip = mf.IPv4AddressFactory(userid="user1", floating_ip=True,
                                   deleted=True)
        response = self.delete(URL + "/%s" % ip.id, "user1")
        self.assertItemNotFound(response)

    def test_reserve(self):
        request = {'pool': self.pool.id}
        with mocked_quotaholder():
            response = self.post(URL, "test_user", json.dumps(request), "json")
        self.assertSuccess(response)
        ip = floating_ips.get()
        self.assertEqual(ip.address, "192.168.2.2")
        self.assertEqual(ip.nic, None)
        self.assertEqual(ip.network, self.pool)
        self.assertEqual(json.loads(response.content)["floating_ip"],
                         {"instance_id": None, "ip": "192.168.2.2",
                          "fixed_ip": None, "id": str(ip.id),
                          "pool": str(self.pool.id)})

    def test_reserve_no_pool(self):
        # No floating IP pools
        self.pool.delete()
        response = self.post(URL, "test_user", json.dumps({}), "json")
        self.assertFault(response, 503, 'serviceUnavailable')

        # Full network
        net = mf.NetworkWithSubnetFactory(floating_ip_pool=True,
                                          public=True,
                                          subnet__cidr="192.168.2.0/31",
                                          subnet__gateway="192.168.2.1",
                                          subnet__pool__size=0)
        response = self.post(URL, "test_user", json.dumps({}), "json")
        self.assertFault(response, 503, 'serviceUnavailable')

        request = {'pool': net.id}
        response = self.post(URL, "test_user", json.dumps(request), "json")
        self.assertConflict(response)

    def test_reserve_with_address(self):
        request = {'pool': self.pool.id, "address": "192.168.2.10"}
        with mocked_quotaholder():
            response = self.post(URL, "test_user", json.dumps(request), "json")
        self.assertSuccess(response)
        ip = floating_ips.get()
        self.assertEqual(json.loads(response.content)["floating_ip"],
                         {"instance_id": None, "ip": "192.168.2.10",
                          "fixed_ip": None, "id": str(ip.id),
                          "pool": str(self.pool.id)})

        # Already reserved
        with mocked_quotaholder():
            response = self.post(URL, "test_user", json.dumps(request), "json")
        self.assertFault(response, 409, "conflict")

        # Used by instance
        self.pool.reserve_address("192.168.2.20")
        request = {'pool': self.pool.id, "address": "192.168.2.20"}
        with mocked_quotaholder():
            response = self.post(URL, "test_user", json.dumps(request), "json")
        self.assertFault(response, 409, "conflict")

        # Address out of pool
        request = {'pool': self.pool.id, "address": "192.168.3.5"}
        with mocked_quotaholder():
            response = self.post(URL, "test_user", json.dumps(request), "json")
        self.assertBadRequest(response)

    def test_release_in_use(self):
        ip = mf.IPv4AddressFactory(userid="user1", floating_ip=True)
        vm = ip.nic.machine
        with mocked_quotaholder():
            response = self.delete(URL + "/%s" % ip.id, ip.userid)
        self.assertFault(response, 409, "conflict")
        # Also send a notification to remove the NIC and assert that FIP is in
        # use until notification from ganeti arrives
        request = {"removeFloatingIp": {"address": ip.address}}
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
        ip = mf.IPv4AddressFactory(userid="user1", floating_ip=True, nic=None)
        with mocked_quotaholder():
            response = self.delete(URL + "/%s" % ip.id, ip.userid)
        self.assertSuccess(response)
        ips_after = floating_ips.filter(id=ip.id)
        self.assertEqual(len(ips_after), 0)

    @patch("synnefo.logic.backend", Mock())
    def test_delete_network_with_floating_ips(self):
        ip = mf.IPv4AddressFactory(userid="user1", floating_ip=True,
                                   network=self.pool, nic=None)
        # Mark the network as non-pubic to not get 403
        network = ip.network
        network.public = False
        network.save()
        # Can not remove network with floating IPs
        with mocked_quotaholder():
            response = self.delete(NETWORKS_URL + "/%s" % self.pool.id,
                                   self.pool.userid)
        self.assertConflict(response)
        # But we can with only deleted Floating Ips
        ip.deleted = True
        ip.save()
        with mocked_quotaholder():
            response = self.delete(NETWORKS_URL + "/%s" % self.pool.id,
                                   self.pool.userid)
        self.assertSuccess(response)


POOLS_URL = join_urls(compute_path, "os-floating-ip-pools")


class FloatingIPPoolsAPITest(BaseAPITest):
    def test_no_pool(self):
        response = self.get(POOLS_URL)
        self.assertSuccess(response)
        self.assertEqual(json.loads(response.content)["floating_ip_pools"], [])

    def test_list_pools(self):
        net = mf.NetworkWithSubnetFactory(floating_ip_pool=True,
                                          public=True,
                                          subnet__cidr="192.168.2.0/30",
                                          subnet__gateway="192.168.2.1",
                                          subnet__pool__size=1,
                                          subnet__pool__offset=1)
        mf.NetworkWithSubnetFactory(public=True, deleted=True)
        mf.NetworkWithSubnetFactory(public=False, deleted=False)
        mf.NetworkWithSubnetFactory(public=True, floating_ip_pool=False)
        response = self.get(POOLS_URL)
        self.assertSuccess(response)
        self.assertEqual(json.loads(response.content)["floating_ip_pools"],
                         [{"name": str(net.id), "size": 1, "free": 1}])


class FloatingIPActionsTest(BaseAPITest):
    def setUp(self):
        self.vm = VirtualMachineFactory()
        self.vm.operstate = "ACTIVE"
        self.vm.save()

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
        ip = mf.IPv4AddressFactory(floating_ip=True, userid=self.vm.userid)
        request = {"addFloatingIp": {"address": ip.address}}
        response = self.post(url, self.vm.userid, json.dumps(request), "json")
        self.assertConflict(response)
        # Success
        ip = mf.IPv4AddressFactory(floating_ip=True, nic=None,
                                   userid=self.vm.userid)
        request = {"addFloatingIp": {"address": ip.address}}
        mock().ModifyInstance.return_value = 1
        response = self.post(url, self.vm.userid, json.dumps(request), "json")
        self.assertEqual(response.status_code, 202)
        ip_after = floating_ips.get(id=ip.id)
        self.assertEqual(ip_after.nic.machine, self.vm)
        nic = self.vm.nics.get()
        nic.state = "ACTIVE"
        nic.save()
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
        self.assertBadRequest(response)
        # Not In Use
        ip = mf.IPv4AddressFactory(floating_ip=True, nic=None,
                                   userid=self.vm.userid)
        request = {"removeFloatingIp": {"address": ip.address}}
        response = self.post(url, self.vm.userid, json.dumps(request), "json")
        self.assertBadRequest(response)
        # Success
        ip = mf.IPv4AddressFactory(floating_ip=True,
                                   userid=self.vm.userid, nic__machine=self.vm)
        request = {"removeFloatingIp": {"address": ip.address}}
        mock().ModifyInstance.return_value = 2
        response = self.post(url, self.vm.userid, json.dumps(request), "json")
        self.assertEqual(response.status_code, 202)
        # Yet used. Wait for the callbacks
        ip_after = floating_ips.get(id=ip.id)
        self.assertEqual(ip_after.nic.machine, self.vm)
