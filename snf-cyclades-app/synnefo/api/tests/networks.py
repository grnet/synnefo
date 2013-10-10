# Copyright 2012-2013 GRNET S.A. All rights reserved.
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

from snf_django.utils.testing import (BaseAPITest, override_settings)
from django.utils import simplejson as json
from synnefo.cyclades_settings import cyclades_services
from synnefo.lib.services import get_service_path
from synnefo.lib import join_urls
import synnefo.db.models_factory as dbmf
from synnefo.db.models import Network
from django.conf import settings

COMPUTE_URL = get_service_path(cyclades_services, 'compute',
                               version='v2.0')
NETWORKS_URL = join_urls(COMPUTE_URL, "networks/")


class NetworkTest(BaseAPITest):
    def test_list_networks(self):
        response = self.get(NETWORKS_URL)
        self.assertSuccess(response)
        networks = json.loads(response.content)
        self.assertEqual(networks, {"networks": []})

    def test_invalid_create(self):
        """Test invalid flavor"""
        request = {'network': {}}
        response = self.post(NETWORKS_URL, "user1", params=json.dumps(request))
        self.assertBadRequest(response)
        request = {'network': {"type": "foo"}}
        response = self.post(NETWORKS_URL, "user1", params=json.dumps(request))
        self.assertBadRequest(response)
        request = {'network': {"type": "MAC_FILTERED"}}
        with override_settings(settings,
                               API_ENABLED_NETWORK_FLAVORS=["CUSTOM"]):
            response = self.post(NETWORKS_URL, "user1",
                                 params=json.dumps(request))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(Network.objects.filter(userid='user1')), 0)

    def test_create(self):
        request = {
            "network": {
                "name": "sample_network",
                "type": "MAC_FILTERED"
            }
        }
        response = self.post(NETWORKS_URL, params=json.dumps(request))
        code = response.status_code
        self.assertEqual(code, 503)  # No MAC prefix pool
        dbmf.MacPrefixPoolTableFactory()
        response = self.post(NETWORKS_URL, params=json.dumps(request))
        code = response.status_code
        self.assertEqual(code, 201)
        res = json.loads(response.content)
        self.assertEqual(res["network"]["name"], "sample_network")

        # TEST QUOTAS!!!
        name, args, kwargs =\
            self.mocked_quotaholder.issue_one_commission.mock_calls[0]
        commission_resources = args[3]
        self.assertEqual(commission_resources, {"cyclades.network.private": 1})
        name, args, kwargs =\
            self.mocked_quotaholder.resolve_commissions.mock_calls[0]
        serial = Network.objects.get().serial.serial
        accepted_serials = args[1]
        rejected_serials = args[2]
        self.assertEqual(accepted_serials, [serial])
        self.assertEqual(rejected_serials, [])

        # test no name
        request["network"].pop("name")
        response = self.post(NETWORKS_URL, params=json.dumps(request))
        code = response.status_code
        self.assertEqual(code, 201)
        res = json.loads(response.content)
        self.assertEqual(res["network"]["name"], "")

    def test_get_unfound_network(self):
        url = join_urls(NETWORKS_URL, "123")
        response = self.get(url)
        self.assertItemNotFound(response)

    def test_get_network(self):
        test_net = dbmf.NetworkFactory()
        url = join_urls(NETWORKS_URL, str(test_net.id))
        response = self.get(url, user=test_net.userid)
        # validate response
        res = json.loads(response.content)
        net = res['network']
        keys = net.keys()
        must_send = set(["status", "subnets", "name", "admin_state_up",
                        "tenant_id", "id"])
        self.assertEqual(set(keys).issuperset(must_send), True)
        self.assertEqual(response.status_code, 200)

    def test_get_deleted_network(self):
        test_net = dbmf.NetworkFactory(flavor="CUSTOM")
        url = join_urls(NETWORKS_URL, str(test_net.id))
        self.delete(url, user=test_net.userid)
        response = self.get(url, user=test_net.userid)
        self.assertEqual(response.status_code, 200)

    def test_delete_unfound_network(self):
        url = join_urls(NETWORKS_URL, "123")
        response = self.delete(url)
        self.assertItemNotFound(response)

    def test_delete_network(self):
        test_net = dbmf.NetworkFactory()
        dbmf.IPv4SubnetFactory(network=test_net)
        url = join_urls(NETWORKS_URL, str(test_net.id))
        response = self.delete(url, user=test_net.userid)
        self.assertEqual(response.status_code, 204)
        # But not the public network!!
        test_net.public = True
        test_net.save()
        response = self.delete(url, user=test_net.userid)
        self.assertFault(response, 403, 'forbidden')

    def test_delete_network_in_use(self):
        test_net = dbmf.NetworkFactory()
        dbmf.NetworkInterfaceFactory(network=test_net)
        url = join_urls(NETWORKS_URL, str(test_net.id))
        response = self.delete(url, user=test_net.userid)
        self.assertEqual(response.status_code, 409)

    def test_delete_network_with_floating_ips(self):
        test_net = dbmf.NetworkFactory()
        dbmf.IPv4AddressFactory(network=test_net, floating_ip=True, nic=None)
        url = join_urls(NETWORKS_URL, str(test_net.id))
        response = self.delete(url, user=test_net.userid)
        self.assertEqual(response.status_code, 409)

    def test_put_unfound_network(self):
        url = join_urls(NETWORKS_URL, "123")
        response = self.delete(url)
        self.assertItemNotFound(response)

    def test_put_network(self):
        test_net = dbmf.NetworkFactory()
        url = join_urls(NETWORKS_URL, str(test_net.id))
        request = {
            "network": {
                "name": "new_name"}
        }
        response = self.put(url, params=json.dumps(request),
                            user=test_net.userid)
        self.assertEqual(response.status_code, 200)

    def test_put_network_wrong_data(self):
        test_net = dbmf.NetworkFactory()
        url = join_urls(NETWORKS_URL, str(test_net.id))
        request = {
            "network": {
                "wrong_field": "new_name"}
        }
        response = self.put(url, params=json.dumps(request),
                            user=test_net.userid)
        self.assertEqual(response.status_code, 400)

    def test_put_no_data(self):
        test_net = dbmf.NetworkFactory()
        url = join_urls(NETWORKS_URL, str(test_net.id))
        response = self.put(url, params="", user=test_net.userid)
        self.assertEqual(response.status_code, 400)

    def test_rename_network(self):
        test_net = dbmf.NetworkFactory(name="foo")
        url = join_urls(NETWORKS_URL, str(test_net.id))
        request = {'network': {'name': "new_name"}}
        response = self.put(url, test_net.userid, json.dumps(request), 'json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Network.objects.get(id=test_net.id).name, "new_name")
        # test if server deleted
        test_net.deleted = True
        test_net.save()
        response = self.put(url, test_net.userid, json.dumps(request), 'json')
        self.assertBadRequest(response)
        test_net.deleted = False
        test_net.public = True
        test_net.save()
        response = self.put(url, test_net.userid, json.dumps(request), 'json')
        self.assertFault(response, 403, 'forbidden')

    def test_method_not_allowed(self, *args):
        # /networks/ allows only POST, GET
        response = self.put(NETWORKS_URL, '', '')
        self.assertMethodNotAllowed(response)
        response = self.delete(NETWORKS_URL)
        self.assertMethodNotAllowed(response)

        # /networks/<srvid>/ allows only GET, PUT, DELETE
        url = join_urls(NETWORKS_URL, "42")
        response = self.post(url)
        self.assertMethodNotAllowed(response)


#class NetworkNICsAPITest(BaseAPITest):
#    def test_get_network_building_nics(self, mrapi):
#        net = dbmf.NetworkFactory()
#        machine = dbmf.VirtualMachineFactory(userid=net.userid)
#        dbmf.NetworkInterfaceFactory(network=net, machine=machine,
#                                     state="BUILDING")
#        response = self.myget('networks/%d' % net.id, net.userid)
#        self.assertSuccess(response)
#        api_net = json.loads(response.content)["network"]
#        self.assertEqual(len(api_net["attachments"]), 0)
#
#
#    def test_add_nic(self, mrapi):
#        user = 'userr'
#        vm = dbmf.VirtualMachineFactory(name='yo', userid=user)
#        net = dbmf.NetworkFactory(state='ACTIVE', userid=user)
#        mrapi().ModifyInstance.return_value = 1
#        request = {'add': {'serverRef': vm.id}}
#        response = self.mypost('networks/%d/action' % net.id,
#                               net.userid, json.dumps(request), 'json')
#        self.assertEqual(response.status_code, 202)
#
#    def test_add_nic_to_deleted_network(self, mrapi):
#        user = 'userr'
#        vm = dbmf.VirtualMachineFactory(name='yo', userid=user,
#                                            operstate="ACTIVE")
#        net = dbmf.NetworkFactory(state='ACTIVE', userid=user,
#                                      deleted=True)
#        request = {'add': {'serverRef': vm.id}}
#        response = self.mypost('networks/%d/action' % net.id,
#                               net.userid, json.dumps(request), 'json')
#        self.assertBadRequest(response)
#        self.assertFalse(mrapi.called)
#
#    def test_add_nic_to_public_network(self, mrapi):
#        user = 'userr'
#        vm = dbmf.VirtualMachineFactory(name='yo', userid=user)
#        net = dbmf.NetworkFactory(state='ACTIVE', userid=user, public=True)
#        request = {'add': {'serverRef': vm.id}}
#        response = self.mypost('networks/%d/action' % net.id,
#                               net.userid, json.dumps(request), 'json')
#        self.assertFault(response, 403, 'forbidden')
#        self.assertFalse(mrapi.called)
#
#    def test_add_nic_malformed_1(self, mrapi):
#        user = 'userr'
#        vm = dbmf.VirtualMachineFactory(name='yo', userid=user)
#        net = dbmf.NetworkFactory(state='ACTIVE', userid=user)
#        request = {'add': {'serveRef': vm.id}}
#        response = self.mypost('networks/%d/action' % net.id,
#                               net.userid, json.dumps(request), 'json')
#        self.assertBadRequest(response)
#        self.assertFalse(mrapi.called)
#
#    def test_add_nic_malformed_2(self, mrapi):
#        user = 'userr'
#        vm = dbmf.VirtualMachineFactory(name='yo', userid=user)
#        net = dbmf.NetworkFactory(state='ACTIVE', userid=user)
#        request = {'add': {'serveRef': [vm.id, 22]}}
#        response = self.mypost('networks/%d/action' % net.id,
#                               net.userid, json.dumps(request), 'json')
#        self.assertBadRequest(response)
#        self.assertFalse(mrapi.called)
#
#    def test_add_nic_not_active(self, mrapi):
#        """Test connecting VM to non-active network"""
#        user = 'dummy'
#        vm = dbmf.VirtualMachineFactory(name='yo', userid=user)
#        net = dbmf.NetworkFactory(state='PENDING', subnet='10.0.0.0/31',
#                                      userid=user)
#        request = {'add': {'serverRef': vm.id}}
#        response = self.mypost('networks/%d/action' % net.id,
#                               net.userid, json.dumps(request), 'json')
#        # Test that returns BuildInProgress
#        self.assertEqual(response.status_code, 409)
#        self.assertFalse(mrapi.called)
#
#    def test_add_nic_full_network(self, mrapi):
#        """Test connecting VM to a full network"""
#        user = 'userr'
#        vm = dbmf.VirtualMachineFactory(name='yo', userid=user,
#                                            operstate="STARTED")
#        net = dbmf.NetworkFactory(state='ACTIVE', subnet='10.0.0.0/30',
#                                      userid=user, dhcp=True)
#        pool = net.get_pool()
#        while not pool.empty():
#            pool.get()
#        pool.save()
#        pool = net.get_pool()
#        self.assertTrue(pool.empty())
#        request = {'add': {'serverRef': vm.id}}
#        response = self.mypost('networks/%d/action' % net.id,
#                               net.userid, json.dumps(request), 'json')
#        # Test that returns OverLimit
#        self.assertEqual(response.status_code, 413)
#        self.assertFalse(mrapi.called)
#
#    def test_remove_nic(self, mrapi):
#        user = 'userr'
#        vm = dbmf.VirtualMachineFactory(name='yo', userid=user,
#                                            operstate="ACTIVE")
#        net = dbmf.NetworkFactory(state='ACTIVE', userid=user)
#        nic = dbmf.NetworkInterfaceFactory(machine=vm, network=net)
#        mrapi().ModifyInstance.return_value = 1
#        request = {'remove': {'attachment': "%s" % nic.id}}
#        response = self.mypost('networks/%d/action' % net.id,
#                               net.userid, json.dumps(request), 'json')
#        self.assertEqual(response.status_code, 202)
#        vm.task = None
#        vm.task_job_id = None
#        vm.save()
#
#    def test_remove_nic_malformed(self, mrapi):
#        user = 'userr'
#        vm = dbmf.VirtualMachineFactory(name='yo', userid=user)
#        net = dbmf.NetworkFactory(state='ACTIVE', userid=user)
#        nic = dbmf.NetworkInterfaceFactory(machine=vm, network=net)
#        request = {'remove': {'att234achment': '%s' % nic.id}}
#        response = self.mypost('networks/%d/action' % net.id,
#                               net.userid, json.dumps(request), 'json')
#        self.assertBadRequest(response)
#
#    def test_remove_nic_malformed_2(self, mrapi):
#        user = 'userr'
#        vm = dbmf.VirtualMachineFactory(name='yo', userid=user)
#        net = dbmf.NetworkFactory(state='ACTIVE', userid=user)
#        request = {'remove': {'attachment': 'nic-%s' % vm.id}}
#        response = self.mypost('networks/%d/action' % net.id,
#                               net.userid, json.dumps(request), 'json')
#        self.assertBadRequest(response)
