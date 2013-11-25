# Copyright 2013 GRNET S.A. All rights reserved.
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

"""
This is the burnin class that tests the Servers' functionality

"""

import sys
import IPy
import stat
import base64
import random
import socket

from vncauthproxy.d3des import generate_response as d3des_generate_response

from synnefo_tools.burnin.common import BurninTests, Proper, run_test
from synnefo_tools.burnin.cyclades_common import CycladesTests


# Too many public methods. pylint: disable-msg=R0904
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
            self.use_image, self.use_flavor, self.personality)
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

        self.ipv4 = self._get_ip(server, version=4)
        self.assertEquals(IPy.IP(self.ipv4).version(), 4)

    def test_008_server_has_ipv6(self):
        """Test active server has a valid IPv6 address"""
        self._skip_if(not self.use_ipv6, "--no-ipv6 flag enabled")

        self.ipv6 = self._get_ip(self.server, version=6)
        self.assertEquals(IPy.IP(self.ipv6).version(), 6)

    def test_009_server_ping_ipv4(self):
        """Test server responds to ping on IPv4 address"""
        self._insist_on_ping(self.ipv4, version=4)

    def test_010_server_ping_ipv6(self):
        """Test server responds to ping on IPv6 address"""
        self._skip_if(not self.use_ipv6, "--no-ipv6 flag enabled")
        self._insist_on_ping(self.ipv6, version=6)

    def test_011_submit_shutdown(self):
        """Test submit request to shutdown server"""
        self.clients.cyclades.shutdown_server(self.server['id'])

    def test_012_server_becomes_stopped(self):
        """Test server becomes STOPPED"""
        self._insist_on_server_transition(self.server, ["ACTIVE"], "STOPPED")

    def test_013_submit_start(self):
        """Test submit start server request"""
        self.clients.cyclades.start_server(self.server['id'])

    def test_014_server_becomes_active(self):
        """Test server becomes ACTIVE again"""
        self._insist_on_server_transition(self.server, ["STOPPED"], "ACTIVE")

    def test_015_server_ping_ipv4(self):
        """Test server OS is actually up and running again"""
        self.test_009_server_ping_ipv4()

    def test_016_ssh_to_server_ipv4(self):
        """Test SSH to server public IPv4 works, verify hostname"""
        self._skip_if(not self._image_is(self.use_image, "linux"),
                      "only valid for Linux servers")
        hostname = self._insist_get_hostname_over_ssh(
            self.ipv4, self.username, self.password)
        # The hostname must be of the form 'prefix-id'
        self.assertTrue(hostname.endswith("-%d" % self.server['id']))

    def test_017_ssh_to_server_ipv6(self):
        """Test SSH to server public IPv6 works, verify hostname"""
        self._skip_if(not self._image_is(self.use_image, "linux"),
                      "only valid for Linux servers")
        self._skip_if(not self.use_ipv6, "--no-ipv6 flag enabled")
        hostname = self._insist_get_hostname_over_ssh(
            self.ipv6, self.username, self.password)
        # The hostname must be of the form 'prefix-id'
        self.assertTrue(hostname.endswith("-%d" % self.server['id']))

    def test_018_rdp_to_server_ipv4(self):
        """Test RDP connection to server public IPv4 works"""
        self._skip_if(not self._image_is(self.use_image, "windows"),
                      "only valid for Windows servers")
        sock = self._insist_on_tcp_connection(socket.AF_INET, self.ipv4, 3389)
        # No actual RDP processing done. We assume the RDP server is there
        # if the connection to the RDP port is successful.
        # pylint: disable-msg=W0511
        # FIXME: Use rdesktop, analyze exit code? see manpage
        sock.close()

    def test_019_rdp_to_server_ipv6(self):
        """Test RDP connection to server public IPv6 works"""
        self._skip_if(not self._image_is(self.use_image, "windows"),
                      "only valid for Windows servers")
        self._skip_if(not self.use_ipv6, "--no-ipv6 flag enabled")
        sock = self._insist_on_tcp_connection(socket.AF_INET, self.ipv6, 3389)
        # No actual RDP processing done. We assume the RDP server is there
        # if the connection to the RDP port is successful.
        # pylint: disable-msg=W0511
        # FIXME: Use rdesktop, analyze exit code? see manpage
        sock.close()

    def test_020_personality(self):
        """Test file injection for personality enforcement"""
        self._skip_if(not self._image_is(self.use_image, "linux"),
                      "only implemented for linux servers")
        assert self.personality is not None, "No personality used"

        for inj_file in self.personality:
            self._check_file_through_ssh(
                self.ipv4, inj_file['owner'], self.password,
                inj_file['path'], inj_file['contents'])

    def test_021_submit_delete_request(self):
        """Test submit request to delete server"""
        self.clients.cyclades.delete_server(self.server['id'])

    def test_022_server_becomes_deleted(self):
        """Test server becomes DELETED"""
        self._insist_on_server_transition(self.server, ["ACTIVE"], "DELETED")
        # Verify quotas
        self._verify_quotas_deleted([self.use_flavor])

    def test_023_server_no_longer(self):
        """Test server is no longer in server list"""
        servers = self._get_list_of_servers()
        self.assertNotIn(self.server['id'], [s['id'] for s in servers])


# --------------------------------------------------------------------
# The actuall test class. We use this class to dynamically create
# tests from the GeneratedServerTestSuite class. Each of these classes
# will run the same tests using different images and or flavors.
# The creation and running of our GeneratedServerTestSuite class will
# happen as a testsuite itself (everything here is a test!).
class ServerTestSuite(BurninTests):
    """Generate and run the GeneratedServerTestSuite

    We will generate as many testsuites as the number of images given.
    Each of these testsuites will use the given flavors at will (random).

    """
    avail_images = Proper(value=None)
    avail_flavors = Proper(value=None)
    gen_classes = Proper(value=None)

    def test_001_images_to_use(self):
        """Find images to be used by GeneratedServerTestSuite"""
        if self.images is None:
            self.info("No --images given. Will use the default %s",
                      "^Debian Base$")
            filters = ["name:^Debian Base$"]
        else:
            filters = self.images

        self.avail_images = self._find_images(filters)
        self.info("Found %s images. Let's create an equal number of tests",
                  len(self.avail_images))

    def test_002_flavors_to_use(self):
        """Find flavors to be used by GeneratedServerTestSuite"""
        flavors = self._get_list_of_flavors(detail=True)

        if self.flavors is None:
            self.info("No --flavors given. Will use all of them")
            self.avail_flavors = flavors
        else:
            self.avail_flavors = self._find_flavors(
                self.flavors, flavors=flavors)
        self.info("Found %s flavors to choose from", len(self.avail_flavors))

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
        for gen_cls in self.gen_classes:
            self.info("Running testsuite %s", gen_cls.__name__)
            run_test(gen_cls)
