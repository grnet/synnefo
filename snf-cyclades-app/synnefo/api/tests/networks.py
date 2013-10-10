from snf_django.utils.testing import BaseAPITest
from django.utils import simplejson as json
from synnefo.cyclades_settings import cyclades_services
from synnefo.lib.services import get_service_path
from synnefo.lib import join_urls
import json
import synnefo.db.models_factory as dbmf


COMPUTE_URL = get_service_path(cyclades_services, 'compute',
                                             version='v2.0')
NETWORKS_URL = join_urls(COMPUTE_URL, "networks/")


class NetworkTest(BaseAPITest):

    def test_list_networks(self):
        response = self.get(NETWORKS_URL)
        self.assertSuccess(response)
        networks = json.loads(response.content)
        self.assertEqual(networks, {"networks": []})

    def test_create_network(self):
        request = {
            "network": {
                "name": "sample_network",
                "type": "MAC_FILTERED"
                }
        }
        response = self.post(NETWORKS_URL, params=json.dumps(request))
        code = response.status_code
        self.assertEqual(code, 201)

    def test_get_unfound_network(self):
        url = join_urls(NETWORKS_URL, "123")
        response = self.get(url)
        self.assertItemNotFound(response)

    def test_get_network(self):
        test_net = dbmf.NetworkFactory.create()
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
        test_net = dbmf.NetworkFactory.create()
        url = join_urls(NETWORKS_URL, str(test_net.id))
        self.delete(url, user=test_net.userid)
        response = self.get(url, user=test_net.userid)
        self.assertEqual(response.status_code, 400)

    def test_delete_unfound_network(self):
        url = join_urls(NETWORKS_URL, "123")
        response = self.delete(url)
        self.assertItemNotFound(response)

    def test_delete_network(self):
        test_net = dbmf.NetworkFactory.create()
        subnet = dbmf.IPv4SubnetFactory.create(network=test_net)
        url = join_urls(NETWORKS_URL, str(test_net.id))
        response = self.delete(url, user=test_net.userid)
        self.assertEqual(response.status_code, 204)

    def test_delete_network_in_use(self):
        test_net = dbmf.NetworkFactory.create()
        test_iface = dbmf.NetworkInterfaceFactory.create(network=test_net)
        url = join_urls(NETWORKS_URL, str(test_net.id))
        response = self.delete(url, user=test_net.userid)
        self.assertEqual(response.status_code, 409)

    def test_put_unfound_network(self):
        url = join_urls(NETWORKS_URL, "123")
        response = self.delete(url)
        self.assertItemNotFound(response)

    def test_put_network(self):
        test_net = dbmf.NetworkFactory.create()
        url = join_urls(NETWORKS_URL, str(test_net.id))
        request = {
            "network": {
                "name": "new_name"}
        }
        response = self.put(url, params=json.dumps(request),
                            user=test_net.userid)
        self.assertEqual(response.status_code, 200)

    def test_put_network_wrong_data(self):
        test_net = dbmf.NetworkFactory.create()
        url = join_urls(NETWORKS_URL, str(test_net.id))
        request = {
            "network": {
                "wrong_field": "new_name"}
        }
        response = self.put(url, params=json.dumps(request),
                            user=test_net.userid)
        self.assertEqual(response.status_code, 400)

    def test_put_no_data(self):
        test_net = dbmf.NetworkFactory.create()
        url = join_urls(NETWORKS_URL, str(test_net.id))
        response = self.put(url, params="", user=test_net.userid)
        self.assertEqual(response.status_code, 400)
