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

"""
This is the burnin class that tests the Servers' functionality

"""

import sys
import stat
import base64
import random
import socket

from vncauthproxy.d3des import generate_response as d3des_generate_response

from synnefo_tools.burnin.common import Proper
from synnefo_tools.burnin.cyclades_common import CycladesTests


# pylint: disable=too-many-public-methods,too-many-instance-attributes
# This class gets replicated into actual TestCases dynamically
class GeneratedServerTestSuite(CycladesTests):
    """Test Spawning Serverfunctionality"""
    use_image = Proper(value=None)
    personality = Proper(value=None)
    avail_flavors = Proper(value=None)
    use_flavor = Proper(value=None)
    server = Proper(value=None)
    ipv4 = Proper(value=None)
    ipv6 = Proper(value=None)
    username = Proper(value=None)
    password = Proper(value=None)

    def test_001_submit_create_server(self):
        """Submit a create server request"""
        if self._image_is(self.use_image, "linux"):
            # Enforce personality test
            self.info("Creating personality content to be used")
            self.personality = [{
                'path': "/root/test_inj_file",
                'owner': "root",
                'group': "root",
                'mode': stat.S_IRUSR | stat.S_IWUSR,
                'contents': base64.b64encode("This is a personality file")
            }]
        self.use_flavor = random.choice(self.avail_flavors)

        self.server = self._create_server(
            self.use_image, self.use_flavor,
            personality=self.personality, network=True)
        self.username = self._get_connection_username(self.server)
        self.password = self.server['adminPass']

    def test_002_server_build_list(self):
        """Test server is in BUILD state, in server list"""
        servers = self._get_list_of_servers(detail=True)
        servers = [s for s in servers if s['id'] == self.server['id']]

        self.assertEqual(len(servers), 1)
        server = servers[0]
        self.assertEqual(server['name'], self.server['name'])
        self.assertEqual(server['flavor']['id'], self.use_flavor['id'])
        self.assertEqual(server['image']['id'], self.use_image['id'])
        self.assertEqual(server['status'], "BUILD")

    def test_003_server_build_details(self):
        """Test server is in BUILD state, in details"""
        server = self._get_server_details(self.server)
        self.assertEqual(server['name'], self.server['name'])
        self.assertEqual(server['flavor']['id'], self.use_flavor['id'])
        self.assertEqual(server['image']['id'], self.use_image['id'])
        self.assertEqual(server['status'], "BUILD")

    def test_004_set_server_metadata(self):
        """Test setting some of the server's metadata"""
        image = self.clients.cyclades.get_image_details(self.use_image['id'])
        os_value = image['metadata']['os']
        self.clients.cyclades.update_server_metadata(
            self.server['id'], OS=os_value)

        servermeta = \
            self.clients.cyclades.get_server_metadata(self.server['id'])
        imagemeta = \
            self.clients.cyclades.get_image_metadata(self.use_image['id'])
        self.assertEqual(servermeta['OS'], imagemeta['os'])

    def test_005_server_becomes_active(self):
        """Test server becomes ACTIVE"""
        self._insist_on_server_transition(self.server, ["BUILD"], "ACTIVE")

    def test_006_get_server_oob_console(self):
        """Test getting OOB server console over VNC

        Implementation of RFB protocol follows
        http://www.realvnc.com/docs/rfbproto.pdf.

        """
        console = self.clients.cyclades.get_server_console(self.server['id'])
        self.assertEquals(console['type'], "vnc")
        sock = self._insist_on_tcp_connection(
            socket.AF_INET, console['host'], console['port'])

        # Step 1. ProtocolVersion message (par. 6.1.1)
        version = sock.recv(1024)
        self.assertEquals(version, 'RFB 003.008\n')
        sock.send(version)

        # Step 2. Security (par 6.1.2): Only VNC Authentication supported
        sec = sock.recv(1024)
        self.assertEquals(list(sec), ['\x01', '\x02'])

        # Step 3. Request VNC Authentication (par 6.1.2)
        sock.send('\x02')

        # Step 4. Receive Challenge (par 6.2.2)
        challenge = sock.recv(1024)
        self.assertEquals(len(challenge), 16)

        # Step 5. DES-Encrypt challenge, use password as key (par 6.2.2)
        response = d3des_generate_response(
            (console["password"] + '\0' * 8)[:8], challenge)
        sock.send(response)

        # Step 6. SecurityResult (par 6.1.3)
        result = sock.recv(4)
        self.assertEquals(list(result), ['\x00', '\x00', '\x00', '\x00'])
        sock.close()

    def test_007_server_has_ipv4(self):
        """Test active server has a valid IPv4 address"""
        server = self.clients.cyclades.get_server_details(self.server['id'])
        # Update the server attribute
        self.server = server

        self.ipv4 = self._get_ips(server, version=4)

    def test_008_server_has_ipv6(self):
        """Test active server has a valid IPv6 address"""
        self._skip_if(not self.use_ipv6, "--no-ipv6 flag enabled")

        self.ipv6 = self._get_ips(self.server, version=6)

    def test_009_server_ping_ipv4(self):
        """Test server responds to ping on IPv4 address"""
        for ipv4 in self.ipv4:
            self._insist_on_ping(ipv4, version=4)

    def test_010_server_ping_ipv6(self):
        """Test server responds to ping on IPv6 address"""
        self._skip_if(not self.use_ipv6, "--no-ipv6 flag enabled")
        self._insist_on_ping(self.ipv6[0], version=6)

    def test_011_attach_second_network(self):
        """Attach a second public IP to our server"""
        floating_ip = self._create_floating_ip()
        self._create_port(floating_ip['floating_network_id'],
                          device_id=self.server['id'],
                          floating_ip=floating_ip)

        # Update server attributes
        server = self.clients.cyclades.get_server_details(self.server['id'])
        self.server = server
        self.ipv4 = self._get_ips(server, version=4)
        self.assertEqual(len(self.ipv4), 2)

        # Test new IPv4
        self.test_009_server_ping_ipv4()

    def test_012_submit_shutdown(self):
        """Test submit request to shutdown server"""
        self.clients.cyclades.shutdown_server(self.server['id'])

    def test_013_server_becomes_stopped(self):
        """Test server becomes STOPPED"""
        self._insist_on_server_transition(self.server, ["ACTIVE"], "STOPPED")

    def test_014_submit_start(self):
        """Test submit start server request"""
        self.clients.cyclades.start_server(self.server['id'])

    def test_015_server_becomes_active(self):
        """Test server becomes ACTIVE again"""
        self._insist_on_server_transition(self.server, ["STOPPED"], "ACTIVE")

    def test_016_server_ping_ipv4(self):
        """Test server OS is actually up and running again"""
        self.test_009_server_ping_ipv4()

    def test_017_ssh_to_server_ipv4(self):
        """Test SSH to server public IPv4 works, verify hostname"""
        self._skip_if(not self._image_is(self.use_image, "linux"),
                      "only valid for Linux servers")
        hostname1 = self._insist_get_hostname_over_ssh(
            self.ipv4[0], self.username, self.password)
        hostname2 = self._insist_get_hostname_over_ssh(
            self.ipv4[1], self.username, self.password)
        # The hostname must be of the form 'prefix-id'
        self.assertTrue(hostname1.endswith("-%d" % self.server['id']))
        self.assertEqual(hostname1, hostname2)

    def test_018_ssh_to_server_ipv6(self):
        """Test SSH to server public IPv6 works, verify hostname"""
        self._skip_if(not self._image_is(self.use_image, "linux"),
                      "only valid for Linux servers")
        self._skip_if(not self.use_ipv6, "--no-ipv6 flag enabled")
        hostname = self._insist_get_hostname_over_ssh(
            self.ipv6[0], self.username, self.password)
        # The hostname must be of the form 'prefix-id'
        self.assertTrue(hostname.endswith("-%d" % self.server['id']))

    def test_019_rdp_to_server_ipv4(self):
        """Test RDP connection to server public IPv4 works"""
        self._skip_if(not self._image_is(self.use_image, "windows"),
                      "only valid for Windows servers")
        sock = self._insist_on_tcp_connection(
            socket.AF_INET, self.ipv4[0], 3389)
        # No actual RDP processing done. We assume the RDP server is there
        # if the connection to the RDP port is successful.
        # pylint: disable=fixme
        # FIXME: Use rdesktop, analyze exit code? see manpage
        sock.close()

    def test_020_rdp_to_server_ipv6(self):
        """Test RDP connection to server public IPv6 works"""
        self._skip_if(not self._image_is(self.use_image, "windows"),
                      "only valid for Windows servers")
        self._skip_if(not self.use_ipv6, "--no-ipv6 flag enabled")
        sock = self._insist_on_tcp_connection(
            socket.AF_INET, self.ipv6[0], 3389)
        # No actual RDP processing done. We assume the RDP server is there
        # if the connection to the RDP port is successful.
        # pylint: disable=fixme
        # FIXME: Use rdesktop, analyze exit code? see manpage
        sock.close()

    def test_021_personality(self):
        """Test file injection for personality enforcement"""
        self._skip_if(not self._image_is(self.use_image, "linux"),
                      "only implemented for linux servers")
        assert self.personality is not None, "No personality used"

        for inj_file in self.personality:
            self._check_file_through_ssh(
                self.ipv4[0], inj_file['owner'], self.password,
                inj_file['path'], inj_file['contents'])

    def test_022_destroy_floating_ips(self):
        """Destroy the floating IPs"""
        self._disconnect_from_network(self.server)

    def test_023_submit_delete_request(self):
        """Test submit request to delete server"""
        self._delete_servers([self.server])


# --------------------------------------------------------------------
# The actuall test class. We use this class to dynamically create
# tests from the GeneratedServerTestSuite class. Each of these classes
# will run the same tests using different images and or flavors.
# The creation and running of our GeneratedServerTestSuite class will
# happen as a testsuite itself (everything here is a test!).
class ServerTestSuite(CycladesTests):
    """Generate and run the GeneratedServerTestSuite

    We will generate as many testsuites as the number of images given.
    Each of these testsuites will use the given flavors at will (random).

    """
    avail_images = Proper(value=None)
    avail_flavors = Proper(value=None)
    gen_classes = Proper(value=None)

    def test_001_images_to_use(self):
        """Find images to be used by GeneratedServerTestSuite"""
        self.avail_images = self._parse_images()

    def test_002_flavors_to_use(self):
        """Find flavors to be used by GeneratedServerTestSuite"""
        self.avail_flavors = self._parse_flavors()

    def test_003_create_testsuites(self):
        """Generate the GeneratedServerTestSuite tests"""
        gen_classes = []
        for img in self.avail_images:
            name = (str("GeneratedServerTestSuite_(%s)" %
                    img['name']).replace(" ", "_"))
            self.info("Constructing class %s", name)
            class_dict = {
                'use_image': Proper(value=img),
                'avail_flavors': Proper(value=self.avail_flavors)
            }
            cls = type(name, (GeneratedServerTestSuite,), class_dict)
            # Make sure the class can be pickled, by listing it among
            # the attributes of __main__. A PicklingError is raised otherwise.
            thismodule = sys.modules[__name__]
            setattr(thismodule, name, cls)
            # Append the generated class
            gen_classes.append(cls)

        self.gen_classes = gen_classes

    def test_004_run_testsuites(self):
        """Run the generated tests"""
        self._run_tests(self.gen_classes)
