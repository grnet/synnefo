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
from synnefo.db.models import Network, QuotaHolderSerial
from django.conf import settings

NETWORK_URL = get_service_path(cyclades_services, 'network',
                               version='v2.0')
NETWORKS_URL = join_urls(NETWORK_URL, "networks/")


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

    def test_invalid_create2(self):
        """Test invalid name type"""
        request = {
            "network": {
                "type": "MAC_FILTERED",
                "name": ["Test", u"I need\u2602"]
            }
        }
        response = self.post(NETWORKS_URL, params=json.dumps(request))
        self.assertBadRequest(response)

    def test_create(self):
        request = {
            "network": {
                "name": u"Funky Network\u2602",
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
        self.assertEqual(res["network"]["name"], u"Funky Network\u2602")

        # TEST QUOTAS!!!
        name, args, kwargs =\
            self.mocked_quotaholder.issue_one_commission.mock_calls[0]
        commission_resources = args[2]
        self.assertEqual(commission_resources, {"cyclades.network.private": 1})
        name, args, kwargs =\
            self.mocked_quotaholder.resolve_commissions.mock_calls[0]
        serial = QuotaHolderSerial.objects.order_by("-serial")[0]
        accepted_serials = args[0]
        rejected_serials = args[1]
        self.assertEqual(accepted_serials, [serial.serial])
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
        test_net = dbmf.NetworkFactory(flavor="CUSTOM")
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
        request = {'network': {'name': u"Cloud \u2601"}}
        response = self.put(url, test_net.userid, json.dumps(request), 'json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Network.objects.get(id=test_net.id).name,
                         u"Cloud \u2601")
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

    def test_rename_network_invalid_name(self):
        test_net = dbmf.NetworkFactory(name="foo")
        url = join_urls(NETWORKS_URL, str(test_net.id))
        request = {'network': {'name': 'a' * 500}}
        response = self.put(url, test_net.userid, json.dumps(request), 'json')
        self.assertEqual(response.status_code, 400)

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
