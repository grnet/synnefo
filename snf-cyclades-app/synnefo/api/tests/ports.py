from snf_django.utils.testing import BaseAPITest
from django.utils import simplejson as json
from synnefo.cyclades_settings import cyclades_services
from synnefo.lib.services import get_service_path
from synnefo.lib import join_urls
import json
import synnefo.db.models_factory as dbmf

COMPUTE_URL = get_service_path(cyclades_services, 'compute',
                               version='v2.0')
PORTS_URL = join_urls(COMPUTE_URL, "ports/")


class PortTest(BaseAPITest):
    def test_get_ports(self):
        url = join_urls(PORTS_URL)
        response = self.get(url)
        self.assertEqual(response.status_code, 200)
        ports = json.loads(response.content)
        self.assertEqual(ports, {"ports": []})

    def test_get_port_unfound(self):
        url = join_urls(PORTS_URL, "123")
        response = self.get(url)
        self.assertEqual(response.status_code, 404)

    def test_get_port(self):
        nic = dbmf.NetworkInterfaceFactory.create()
        url = join_urls(PORTS_URL, str(nic.id))
        response = self.get(url, user=nic.network.userid)
        self.assertEqual(response.status_code, 200)

    def test_delete_port(self):
        nic = dbmf.NetworkInterfaceFactory.create(device_owner='vm')
        url = join_urls(PORTS_URL, str(nic.id))
        response = self.delete(url, user=nic.network.userid)
        self.assertEqual(response.status_code, 204)

    def test_update_port_name(self):
        nic = dbmf.NetworkInterfaceFactory.create(device_owner='vm')
        url = join_urls(PORTS_URL, str(nic.id))
        request = {'port': {"name": "test-name"}}
        response = self.put(url, params=json.dumps(request),
                            user=nic.network.userid)
        self.assertEqual(response.status_code, 200)
        res = json.loads(response.content)
        self.assertEqual(res['port']['name'], "test-name")

    def test_update_port_sg_unfound(self):
        sg1 = dbmf.SecurityGroupFactory.create()
        nic =dbmf.NetworkInterfaceFactory.create(device_owner='vm')
        nic.security_groups.add(sg1)
        nic.save()
        url = join_urls(PORTS_URL, str(nic.id))
        request = {'port': {"security_groups": ["123"]}}
        response = self.put(url, params=json.dumps(request),
                            user=nic.network.userid)
        self.assertEqual(response.status_code, 404)

    def test_update_port_sg(self):
        sg1 = dbmf.SecurityGroupFactory.create()
        sg2 = dbmf.SecurityGroupFactory.create()
        sg3 = dbmf.SecurityGroupFactory.create()
        nic = dbmf.NetworkInterfaceFactory.create(device_owner='vm')
        nic.security_groups.add(sg1)
        nic.save()
        url = join_urls(PORTS_URL, str(nic.id))
        request = {'port': {"security_groups": [str(sg2.id), str(sg3.id)]}}
        response = self.put(url, params=json.dumps(request),
                            user=nic.network.userid)
        res = json.loads(response.content)
        self.assertEqual(res['port']['security_groups'],
                         [str(sg2.id), str(sg3.id)])


    def test_create_port_no_network(self):
        request = {
            "port": {
                "device_id": "123",
                "name": "port1",
                "network_id": "123"
            }
        }
        response = self.post(PORTS_URL, params=json.dumps(request))
        self.assertEqual(response.status_code, 404)

    def test_create_port(self):
        net = dbmf.NetworkFactory.create()
        subnet1 = dbmf.IPv4SubnetFactory.create(network=net)
        subnet2 = dbmf.IPv6SubnetFactory.create(network=net)
        sg1 = dbmf.SecurityGroupFactory.create()
        sg2 = dbmf.SecurityGroupFactory.create()
        vm = dbmf.VirtualMachineFactory.create(userid=net.userid)
        request = {
            "port": {
                "name": "port1",
                "network_id": str(net.id),
                "device_id": str(vm.id),
                "security_groups": [str(sg1.id), str(sg2.id)]
            }
        }
        response = self.post(PORTS_URL, params=json.dumps(request),
                             user=net.userid)
        self.assertEqual(response.status_code, 201)
