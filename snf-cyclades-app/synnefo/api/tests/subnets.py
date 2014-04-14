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

from snf_django.utils.testing import BaseAPITest
from django.utils import simplejson as json
from synnefo.cyclades_settings import cyclades_services
from synnefo.lib.services import get_service_path
from synnefo.lib import join_urls
from ipaddr import IPv4Network
import json
import synnefo.db.models_factory as mf


NETWORK_URL = get_service_path(cyclades_services, 'network', version='v2.0')
SUBNETS_URL = join_urls(NETWORK_URL, "subnets/")


class SubnetTest(BaseAPITest):
    def test_list_subnets(self):
        """Test list subnets without data"""
        response = self.get(SUBNETS_URL)
        self.assertSuccess(response)
        subnets = json.loads(response.content)
        self.assertEqual(subnets, {'subnets': []})

    def test_list_subnets_data(self):
        """Test list subnets with data"""
        test_net = mf.NetworkFactory()
        test_subnet_ipv4 = mf.IPv4SubnetFactory(network=test_net)
        test_subnet_ipv6 = mf.IPv6SubnetFactory(network=test_net, ipversion=6,
                                                cidr=
                                                'fd4b:638e:fd7a:f998::/64')
        response = self.get(SUBNETS_URL, user=test_net.userid)
        self.assertSuccess(response)

    def test_get_subnet(self):
        """Test get info of a single subnet"""
        test_net = mf.NetworkFactory()
        test_subnet = mf.IPv4SubnetFactory(network=test_net)
        url = join_urls(SUBNETS_URL, str(test_subnet.id))
        response = self.get(url, user=test_net.userid)
        self.assertSuccess(response)

    def test_get_subnet_404(self):
        """Test get info of a subnet that doesn't exist"""
        url = join_urls(SUBNETS_URL, '42')
        response = self.get(url)
        self.assertItemNotFound(response)

    def test_subnet_delete(self):
        """Test delete a subnet -- not supported"""
        url = join_urls(SUBNETS_URL, '42')
        response = self.delete(url)
        self.assertBadRequest(response)

    def test_create_subnet_success_ipv4(self):
        """Test create a subnet successfully"""
        test_net = mf.NetworkFactory()
        request = {
            'subnet': {
                'network_id': test_net.id,
                'cidr': '10.0.3.0/24',
                'ip_version': 4}
        }
        response = self.post(SUBNETS_URL, test_net.userid,
                             json.dumps(request), "json")
        self.assertSuccess201(response)
        resp = json.loads(response.content)['subnet']
        self.assertEqual("10.0.3.1", resp['gateway_ip'])
        self.assertEqual([{"start": "10.0.3.2", "end": "10.0.3.254"}],
                         resp['allocation_pools'])
        self.assertEqual(True, resp['enable_dhcp'])

    def test_create_subnet_success_ipv4_with_slaac(self):
        """Test create an IPv4 subnet, with a slaac that will be ingored"""
        test_net = mf.NetworkFactory()
        request = {
            'subnet': {
                'network_id': test_net.id,
                'cidr': '10.0.3.0/24',
                'ip_version': 4,
                'enable_slaac': False}
        }
        response = self.post(SUBNETS_URL, test_net.userid,
                             json.dumps(request), "json")
        self.assertSuccess201(response)

    def test_create_subnet_success_ipv6_with_slaac(self):
        """Test create a subnet with ipv6 and slaac"""
        test_net = mf.NetworkFactory()
        request = {
            'subnet': {
                'network_id': test_net.id,
                'cidr': 'fdc1:4992:1130:fc0b::/64',
                'ip_version': 6,
                'enable_slaac': False}
        }
        response = self.post(SUBNETS_URL, test_net.userid,
                             json.dumps(request), "json")
        self.assertSuccess201(response)
        resp = json.loads(response.content)['subnet']
        self.assertEqual("fdc1:4992:1130:fc0b::1", resp['gateway_ip'])
        self.assertEqual([], resp['allocation_pools'])
        self.assertEqual(False, resp['enable_slaac'])

    def test_create_subnet_with_malformed_slaac(self):
        """Test create a subnet with ipv6 and a malformed slaac"""
        test_net = mf.NetworkFactory()
        request = {
            'subnet': {
                'network_id': test_net.id,
                'cidr': 'fdc1:4992:1130:fc0b::/64',
                'ip_version': 6,
                'enable_slaac': 'Random'}
        }
        response = self.post(SUBNETS_URL, test_net.userid,
                             json.dumps(request), "json")
        self.assertBadRequest(response)

    def test_create_subnet_with_malformed_network_id(self):
        """Test create a subnet with an invalid network ID"""
        test_net = mf.NetworkFactory()
        request = {
            'subnet': {
                'network_id': 'error',
                'cidr': '192.168.42.0/24',
                'ip_version': 4}
        }
        response = self.post(SUBNETS_URL, test_net.userid,
                             json.dumps(request), "json")
        self.assertBadRequest(response)

    def test_create_subnet_success_ipv6(self):
        """Test create an IPv6 subnet successfully"""
        test_net = mf.NetworkFactory()
        request = {
            'subnet': {
                'network_id': test_net.id,
                'cidr': 'fdc1:4992:1130:fc0b::/64',
                'ip_version': 6}
        }
        response = self.post(SUBNETS_URL, test_net.userid,
                             json.dumps(request), "json")
        self.assertSuccess201(response)

    def test_create_subnet_with_ip_pool_allocation(self):
        """Test create a subnet with an IP pool"""
        test_net = mf.NetworkFactory()
        request = {
            'subnet': {
                'network_id': test_net.id,
                'cidr': '10.0.3.0/24',
                'ip_version': 4,
                'allocation_pools': [{
                    'start': '10.0.3.2',
                    'end': '10.0.3.252'}
                ]}
        }
        response = self.post(SUBNETS_URL, test_net.userid,
                             json.dumps(request), "json")
        self.assertSuccess201(response)

    def test_create_subnet_with_multiple_ip_pools(self):
        """Test create a subnet with multiple IP pools"""
        test_net = mf.NetworkFactory()
        request = {
            'subnet': {
                'network_id': test_net.id,
                'cidr': '10.0.3.0/24',
                'ip_version': 4,
                'allocation_pools': [{
                    'start': '10.0.3.2',
                    'end': '10.0.3.100'}, {
                    'start': '10.0.3.200',
                    'end': '10.0.3.220'}
                ]}
        }
        response = self.post(SUBNETS_URL, test_net.userid,
                             json.dumps(request), "json")
        self.assertSuccess201(response)
        resp = json.loads(response.content)['subnet']
        self.assertEqual([{"start": "10.0.3.2", "end": "10.0.3.100"},
                          {"start": "10.0.3.200", "end": "10.0.3.220"}],
                         resp['allocation_pools'])

    def test_create_subnet_with_gateway(self):
        """Test create a subnet with a gateway"""
        test_net = mf.NetworkFactory()
        request = {
            'subnet': {
                'network_id': test_net.id,
                'cidr': '10.0.3.0/24',
                'ip_version': 4,
                'gateway_ip': '10.0.3.150'}
        }
        response = self.post(SUBNETS_URL, test_net.userid,
                             json.dumps(request), "json")
        self.assertSuccess201(response)
        resp = json.loads(response.content)['subnet']
        self.assertEqual("10.0.3.150", resp['gateway_ip'])
        self.assertEqual([{"start": "10.0.3.1", "end": "10.0.3.149"},
                          {"start": "10.0.3.151", "end": "10.0.3.254"}],
                         resp['allocation_pools'])

    def test_create_subnet_with_gateway_inside_of_ip_pool_range(self):
        """Test create a subnet with a gateway IP inside the IP pool range"""
        test_net = mf.NetworkFactory()
        request = {
            'subnet': {
                'network_id': test_net.id,
                'cidr': '10.0.3.0/24',
                'ip_version': 4,
                'gateway_ip': '10.0.3.1',
                'allocation_pools': [{
                    'start': '10.0.3.0',
                    'end': '10.0.3.255'}
                ]}
        }
        response = self.post(SUBNETS_URL, test_net.userid,
                             json.dumps(request), "json")
        self.assertConflict(response)

    def test_create_subnet_with_ip_pool_outside_of_network_range(self):
        """Test create a subnet with an IP pool outside of network range"""
        test_net = mf.NetworkFactory()
        request = {
            'subnet': {
                'network_id': test_net.id,
                'cidr': '10.0.3.0/24',
                'ip_version': 4,
                'allocation_pools': [{
                    'start': '10.0.8.0',
                    'end': '10.0.1.250'}
                ]}
        }
        response = self.post(SUBNETS_URL, test_net.userid,
                             json.dumps(request), "json")
        self.assertConflict(response)

    def test_create_subnet_with_gateway_as_the_last_ip_of_subnet(self):
        """Test create a subnet with a gateway, as the last IP of the subnet"""
        test_net = mf.NetworkFactory()
        request = {
            'subnet': {
                'network_id': test_net.id,
                'cidr': '10.0.3.0/24',
                'ip_version': 4,
                'gateway_ip': '10.0.3.254'}
        }
        response = self.post(SUBNETS_URL, test_net.userid,
                             json.dumps(request), "json")
        self.assertSuccess201(response)
        resp = json.loads(response.content)['subnet']
        self.assertEqual("10.0.3.254", resp['gateway_ip'])
        self.assertEqual([{"start": "10.0.3.1", "end": "10.0.3.253"}],
                         resp['allocation_pools'])

    def test_create_subnet_with_ip_pool_end_lower_than_start(self):
        """Test create a subnet with a pool where end is lower than start"""
        test_net = mf.NetworkFactory()
        request = {
            'subnet': {
                'network_id': test_net.id,
                'cidr': '10.0.3.0/24',
                'ip_version': 4,
                'allocation_pools': [{
                    'start': '10.0.1.10',
                    'end': '10.0.1.5'}
                ]}
        }
        response = self.post(SUBNETS_URL, test_net.userid,
                             json.dumps(request), "json")
        self.assertConflict(response)

    def test_create_subnet_with_ip_pool_in_a_ipv6_subnet(self):
        """Test create a subnet with an ip pool, in an IPv6 subnet """
        test_net = mf.NetworkFactory()
        request = {
            'subnet': {
                'network_id': test_net.id,
                'cidr': 'fd4b:638e:fd7a:f998::/64',
                'ip_version': 6,
                'allocation_pools': [{
                    'start': '10.0.1.10',
                    'end': '10.0.1.5'}
                ]}
        }
        response = self.post(SUBNETS_URL, test_net.userid,
                             json.dumps(request), "json")
        self.assertConflict(response)

    def test_create_subnet_with_invalid_network_id(self):
        """Test create a subnet with a network id that doesn't exist"""
        test_net = mf.NetworkFactory()
        request = {
            'subnet': {
                'network_id': '420000',
                'cidr': '10.0.3.0/24',
                'ip_version': 4}
        }
        response = self.post(SUBNETS_URL, test_net.userid, json.dumps(request),
                             "json")
        self.assertItemNotFound(response)

    def test_create_subnet_with_malformed_ipversion(self):
        """Create a subnet with a malformed ip_version type"""
        test_net = mf.NetworkFactory()
        request = {
            'subnet': {
                'network_id': test_net.id,
                'cidr': '10.0.3.0/24',
                'ip_version': 8}
        }
        response = self.post(SUBNETS_URL, test_net.userid, json.dumps(request),
                             "json")
        self.assertBadRequest(response)

    def test_create_subnet_with_invalid_cidr(self):
        """Create a subnet with an invalid cidr"""
        test_net = mf.NetworkFactory()
        request = {
            'subnet': {
                'network_id': test_net.id,
                'cidr': '192.168.3.0/8'}
        }
        response = self.post(SUBNETS_URL, test_net.userid, json.dumps(request),
                             "json")
        self.assertBadRequest(response)

    def test_create_subnet_with_invalid_gateway(self):
        """Create a subnet with a gateway outside of the subnet range"""
        test_net = mf.NetworkFactory()
        request = {
            'subnet': {
                'network_id': test_net.id,
                'cidr': '192.168.3.0/24',
                'gateway_ip': '192.168.0.1'}
        }
        response = self.post(SUBNETS_URL, test_net.userid, json.dumps(request),
                             "json")
        self.assertBadRequest(response)

    def test_create_subnet_with_invalid_name(self):
        """Create a subnet with an invalid subnet name"""
        test_net = mf.NetworkFactory()
        request = {
            'subnet': {
                'network_id': test_net.id,
                'cidr': '192.168.3.0/24',
                'name': 'a' * 300}
        }
        response = self.post(SUBNETS_URL, test_net.userid, json.dumps(request),
                             "json")
        self.assertBadRequest(response)

    def test_create_subnet_with_invalid_dhcp(self):
        """Create a subnet with an invalid dhcp value"""
        test_net = mf.NetworkFactory()
        request = {
            'subnet': {
                'network_id': test_net.id,
                'cidr': '192.168.3.0/24',
                'enable_dhcp': 'None'}
        }
        response = self.post(SUBNETS_URL, test_net.userid, json.dumps(request),
                             "json")
        self.assertBadRequest(response)

    def test_create_subnet_with_dhcp_set_to_false(self):
        """Create a subnet with a dhcp set to false"""
        test_net = mf.NetworkFactory()
        request = {
            'subnet': {
                'network_id': test_net.id,
                'cidr': '192.168.3.0/24',
                'enable_dhcp': False}
        }
        response = self.post(SUBNETS_URL, test_net.userid, json.dumps(request),
                             "json")
        self.assertSuccess201(response)

    def test_create_subnet_with_dns_nameservers(self):
        """Create a subnet with dns nameservers"""
        test_net = mf.NetworkFactory()
        request = {
            'subnet': {
                'network_id': test_net.id,
                'cidr': '192.168.3.0/24',
                'dns_nameservers': ['8.8.8.8', '1.1.1.1']}
        }
        response = self.post(SUBNETS_URL, test_net.userid, json.dumps(request),
                             "json")
        self.assertSuccess201(response)

    def test_create_subnet_with_host_routes(self):
        """Create a subnet with dns nameservers"""
        test_net = mf.NetworkFactory()
        request = {
            'subnet': {
                'network_id': test_net.id,
                'cidr': '192.168.3.0/24',
                'host_routes': ['8.8.8.8', '1.1.1.1']}
        }
        response = self.post(SUBNETS_URL, test_net.userid, json.dumps(request),
                             "json")
        self.assertSuccess201(response)
        resp = json.loads(response.content)['subnet']
        self.assertEqual(["8.8.8.8", "1.1.1.1"], resp["host_routes"])

    def test_create_subnet_with_same_ipversion(self):
        """
        Create a subnet in a network with another subnet of the same
        ipversion type
        """
        test_net = mf.NetworkFactory()
        test_sub = mf.IPv4SubnetFactory(network=test_net)
        request = {
            'subnet': {
                'network_id': test_net.id,
                'cidr': '192.168.3.0/24'}
        }
        response = self.post(SUBNETS_URL, test_net.userid, json.dumps(request),
                             "json")
        self.assertBadRequest(response)

    def test_update_subnet_ip_version(self):
        """Update the IP version of a subnet, raises 400 BadRequest"""
        test_net = mf.NetworkFactory()
        test_sub = mf.IPv4SubnetFactory(network=test_net)
        request = {
            'subnet': {
                'ip_version': '6'}
        }
        url = join_urls(SUBNETS_URL, str(test_sub.id))
        response = self.put(url, test_net.userid, json.dumps(request), "json")
        self.assertBadRequest(response)

    def test_update_subnet_cidr(self):
        """Update the cidr of a subnet, raises 400 BadRequest"""
        test_net = mf.NetworkFactory()
        test_sub = mf.IPv4SubnetFactory(network=test_net)
        request = {
            'subnet': {
                'cidr': '192.168.42.0/24'}
        }
        url = join_urls(SUBNETS_URL, str(test_sub.id))
        response = self.put(url, test_net.userid, json.dumps(request), "json")
        self.assertBadRequest(response)

    def test_update_subnet_allocation_pools(self):
        """Update the allocation pools of a subnet, raises 400 BadRequest"""
        test_net = mf.NetworkFactory()
        test_sub = mf.IPv4SubnetFactory(network=test_net)
        request = {
            'subnet': {
                'allocation_pools': [{
                    'start': '10.0.3.0',
                    'end': '10.0.3.255'}
                ]}
        }
        url = join_urls(SUBNETS_URL, str(test_sub.id))
        response = self.put(url, test_net.userid, json.dumps(request), "json")
        self.assertBadRequest(response)

    def test_update_subnet_add_dns(self):
        """Update the dns nameservers of a subnet, raises 400 BadRequest"""
        test_net = mf.NetworkFactory()
        test_sub = mf.IPv4SubnetFactory(network=test_net)
        request = {
            'subnet': {
                'dns_nameservers': ['8.8.8.8']}
        }
        url = join_urls(SUBNETS_URL, str(test_sub.id))
        response = self.put(url, test_net.userid, json.dumps(request), "json")
        self.assertBadRequest(response)

    def test_update_subnet_add_host_routes(self):
        """Update the host routes of a subnet, raises 400 BadRequest"""
        test_net = mf.NetworkFactory()
        test_sub = mf.IPv4SubnetFactory(network=test_net)
        request = {
            'subnet': {
                'host_routes': ['8.8.8.8']}
        }
        url = join_urls(SUBNETS_URL, str(test_sub.id))
        response = self.put(url, test_net.userid, json.dumps(request), "json")
        self.assertBadRequest(response)

    def test_update_subnet_with_invalid_dhcp_value(self):
        """Update a subnet with an invalid dhcp value"""
        test_net = mf.NetworkFactory()
        test_sub = mf.IPv4SubnetFactory(network=test_net)
        request = {
            'subnet': {
                'enable_dhcp': 'Random'}
        }
        url = join_urls(SUBNETS_URL, str(test_sub.id))
        response = self.put(url, test_net.userid, json.dumps(request), "json")
        self.assertBadRequest(response)

    def test_update_subnet_with_invalid_name(self):
        """Update a subnet with an invalid name value"""
        test_net = mf.NetworkFactory()
        test_sub = mf.IPv4SubnetFactory(network=test_net)
        request = {
            'subnet': {
                'name': 'a' * 300}
        }
        url = join_urls(SUBNETS_URL, str(test_sub.id))
        response = self.put(url, test_net.userid, json.dumps(request), "json")
        self.assertBadRequest(response)

    def test_update_subnet_with_invalid_gateway(self):
        """Update a subnet with an invalid gateway value"""
        test_net = mf.NetworkFactory()
        test_sub = mf.IPv4SubnetFactory(network=test_net)
        request = {
            'subnet': {
                'gateway_ip': '192.168.200.0/24'}
        }
        url = join_urls(SUBNETS_URL, str(test_sub.id))
        response = self.put(url, test_net.userid, json.dumps(request), "json")
        self.assertBadRequest(response)

    def test_update_subnet_gateway(self):
        """Update the gateway of a subnet"""
        test_net = mf.NetworkFactory()
        test_sub = mf.IPv4SubnetFactory(network=test_net)
        request = {
            'subnet': {
                'gateway_ip': str(IPv4Network(test_sub.gateway).network + 1)}
        }
        url = join_urls(SUBNETS_URL, str(test_sub.id))
        response = self.put(url, test_net.userid, json.dumps(request), "json")
        self.assertBadRequest(response)

    def test_update_subnet_name(self):
        """Update the name of a subnet"""
        test_net = mf.NetworkFactory()
        test_sub = mf.IPv4SubnetFactory(network=test_net)
        request = {
            'subnet': {
                'name': 'Updated Name'}
        }
        url = join_urls(SUBNETS_URL, str(test_sub.id))
        response = self.put(url, test_net.userid, json.dumps(request), "json")
        self.assertSuccess(response)

    def test_update_subnet_dhcp(self):
        """Update the dhcp flag of a subnet"""
        test_net = mf.NetworkFactory()
        test_sub = mf.IPv4SubnetFactory(network=test_net)
        request = {
            'subnet': {
                'enable_dhcp': False}
        }
        url = join_urls(SUBNETS_URL, str(test_sub.id))
        response = self.put(url, test_net.userid, json.dumps(request), "json")
        self.assertBadRequest(response)
