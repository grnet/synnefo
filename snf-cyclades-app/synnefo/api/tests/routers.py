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

from snf_django.utils.testing import BaseAPITest
from django.utils import simplejson as json
from synnefo.cyclades_settings import cyclades_services
from synnefo.lib.services import get_service_path
from synnefo.lib import join_urls
import synnefo.db.models_factory as dbmf


COMPUTE_URL = get_service_path(cyclades_services, 'compute',
                               version='v2.0')
ROUTERS_URL = join_urls(COMPUTE_URL, "routers/")


class RouterTest(BaseAPITest):

    def test_list_empty_routers(self):
        response = self.get(ROUTERS_URL)
        self.assertSuccess(response)
        routers = json.loads(response.content)
        self.assertEqual(routers, {"routers": []})

    def test_list_detail(self):
        response = self.get(join_urls(ROUTERS_URL, 'detail'))
        self.assertEqual(response.status_code, 200)

    def test_create_router_no_net(self):
        request = {
            "router": {
                "name": "test-router",
                "external_gateway_info": {
                    "network_id": "123"}
            }
        }
        response = self.post(ROUTERS_URL, params=json.dumps(request),
                             user='user')
        self.assertEqual(response.status_code, 404)

    def test_create_router_no_external(self):
        net = dbmf.NetworkFactory.create(userid='user', external_router=False)
        request = {
            "router": {
                "name": "test-router",
                "external_gateway_info": {
                    "network_id": str(net.id)
                }
            }
        }
        response = self.post(ROUTERS_URL, params=json.dumps(request),
                             user='user')
        self.assertEqual(response.status_code, 400)

    def test_create_router(self):
        try:
            flavor = dbmf.FlavorFactory.create(id=1)
        except:
            pass
        net = dbmf.NetworkFactory.create(userid='user', external_router=True)
        fip = dbmf.FloatingIPFactory.create(userid='user',
                                          network=net, nic=None)
        request = {
            "router": {
                "name": "test-router",
                "external_gateway_info": {
                    "network_id": str(fip.network.id),
                    "floating_ip": fip.address}
            }
        }
        response = self.post(ROUTERS_URL, params=json.dumps(request),
                             user='user')
        self.assertEqual(response.status_code, 201)

    def test_create_router_no_ip(self):
        try:
            flavor = dbmf.FlavorFactory.create(id=1)
        except:
            pass
        net = dbmf.NetworkFactory.create(userid='user', external_router=True)
        fip = dbmf.FloatingIPFactory.create(userid='user',
                                          network=net, nic=None)
        request = {
            "router": {
                "name": "test-router",
                "external_gateway_info": {
                    "network_id": str(net.id)}
            }
        }
        response = self.post(ROUTERS_URL, params=json.dumps(request),
                             user='user')
        self.assertEqual(response.status_code, 201)

    def test_get_router(self):
        router = dbmf.VirtualMachineFactory.create(router=True)
        nic = dbmf.NetworkInterfaceFactory.create(machine=router)
        fip = dbmf.FloatingIPFactory.create(userid=router.userid, nic=nic,
                                            network=nic.network)
        response = self.get(ROUTERS_URL, user=router.userid)
        self.assertSuccess(response)

    def test_delete_router(self):
        router = dbmf.VirtualMachineFactory.create(router=True)
        url = join_urls(ROUTERS_URL, str(router.id))
        response = self.delete(url, user=router.userid)
        self.assertEqual(response.status_code, 204)

    def test_delete_router_with_private_net(self):
        router = dbmf.VirtualMachineFactory.create(router=True)
        net = dbmf.NetworkFactory.create(external_router=False)
        nic = dbmf.NetworkInterfaceFactory.create(network=net, machine=router)
        url = join_urls(ROUTERS_URL, str(router.id))
        response = self.delete(url, user=router.userid)
        self.assertEqual(response.status_code, 409)

    def test_update_router_network(self):
        router = dbmf.VirtualMachineFactory.create(router=True, userid='user')
        net = dbmf.NetworkFactory.create(userid='user', external_router=True)
        fip = dbmf.FloatingIPFactory.create(userid='user',
                                          network=net, nic=None)
        request = {
            "router": {
                "name": "new_name",
                "external_gateway_info": {"network_id": str(net.id)}
                }
            }
        url = join_urls(ROUTERS_URL, str(router.id))
        response = self.put(url, params=json.dumps(request),
                            user=router.userid)
        info = json.loads(response.content)
        self.assertEqual(info['router']['external_gateway_info']['network_id'],
                         str(net.id))
        self.assertEqual(info['router']['name'], "new_name")

    def test_update_router_both(self):
        router = dbmf.VirtualMachineFactory.create(router=True, userid='user')
        net = dbmf.NetworkFactory.create(userid='user', external_router=True)
        fip = dbmf.FloatingIPFactory.create(userid='user',
                                          network=net, nic=None)
        request = {
            "router": {
                "name": "new_name",
                "external_gateway_info": {"network_id": str(net.id),
                                           "floating_ip": fip.address}
                }
            }
        url = join_urls(ROUTERS_URL, str(router.id))
        response = self.put(url, params=json.dumps(request),
                            user=router.userid)
        info = json.loads(response.content)
        self.assertEqual(info['router']['external_gateway_info']['network_id'],
                         str(net.id))
        self.assertEqual(info['router']['name'], "new_name")

    def test_update_router_conflict(self):
        router = dbmf.VirtualMachineFactory.create(router=True, userid='user')
        net = dbmf.NetworkFactory.create(userid='user', external_router=True)
        fip = dbmf.FloatingIPFactory.create(userid='user', nic=None)
        request = {
            "router": {
                "name": "new_name",
                "external_gateway_info": {"network_id": str(net.id),
                                           "floating_ip": fip.address}
                }
            }
        url = join_urls(ROUTERS_URL, str(router.id))
        response = self.put(url, params=json.dumps(request),
                            user=router.userid)
        self.assertEqual(response.status_code, 409)

    def test_remove_interface_no_body(self):
        url = join_urls(join_urls(ROUTERS_URL, "123"),
                        "remove_router_interface")

        response = self.put(url, params="")
        self.assertEqual(response.status_code, 400)

    def test_remove_interface_unfound_subnet(self):
        router = dbmf.VirtualMachineFactory.create(router=True)
        request = {"subnet_id": "123"}
        url = join_urls(join_urls(ROUTERS_URL, str(router.id)),
                        "remove_router_interface")
        response = self.put(url, params=json.dumps(request),
                            user=router.userid)
        self.assertEqual(response.status_code, 404)

    def test_remove_interface_no_info(self):
        router = dbmf.VirtualMachineFactory.create(router=True)
        request = {"wrong": "123"}
        url = join_urls(join_urls(ROUTERS_URL, str(router.id)),
                        "remove_router_interface")
        response = self.put(url, params=json.dumps(request),
                            user=router.userid)
        self.assertEqual(response.status_code, 400)

    def test_remove_interface_subnet(self):
        router = dbmf.VirtualMachineFactory.create(router=True)
        net1 = dbmf.NetworkFactory.create(external_router=True,
                                          userid=router.userid)
        subnet = dbmf.SubnetFactory.create(network=net1)
        nic = dbmf.NetworkInterfaceFactory.create(network=net1, machine=router)
        request = {"subnet_id": subnet.id}
        url = join_urls(join_urls(ROUTERS_URL, str(router.id)),
                        "remove_router_interface")
        response = self.put(url, params=json.dumps(request),
                            user=router.userid)
        self.assertEqual(response.status_code, 200)

    def test_add_interface_no_info(self):
        url = join_urls(join_urls(ROUTERS_URL, "123"), "add_router_interface")
        response = self.put(url, params="")
        self.assertEqual(response.status_code, 400)

    def test_add_interface_wrong_info(self):
        router = dbmf.VirtualMachineFactory.create(router=True)
        url = join_urls(join_urls(ROUTERS_URL, str(router.id)),
                        "add_router_interface")
        request = {}
        response = self.put(url, params=json.dumps(request),
                            user=router.userid)
        self.assertEqual(response.status_code, 400)

    def test_add_interface_unfound_subnet(self):
        router = dbmf.VirtualMachineFactory.create(router=True)
        url = join_urls(join_urls(ROUTERS_URL, str(router.id)),
                        "add_router_interface")
        request = {"subnet_id": "123"}
        response = self.put(url, params=json.dumps(request),
                            user=router.userid)
        self.assertEqual(response.status_code, 404)

    def test_add_interface_subnet(self):
        router = dbmf.VirtualMachineFactory.create(router=True)
        net1 = dbmf.NetworkFactory.create(external_router=True,
                                          userid=router.userid)
        subnet = dbmf.SubnetFactory.create(network=net1, ipversion=4)
        url = join_urls(join_urls(ROUTERS_URL, str(router.id)),
                        "add_router_interface")
        request = {"subnet_id": subnet.id}
        response = self.put(url, params=json.dumps(request),
                            user=router.userid)
        self.assertEqual(response.status_code, 200)
