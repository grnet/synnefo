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
This is the burnin class that tests the Networks' functionality

"""

import random

from synnefo_tools.burnin.common import Proper
from synnefo_tools.burnin.cyclades_common import CycladesTests


# Too many public methods. pylint: disable-msg=R0904
class NetworkTestSuite(CycladesTests):
    """Test Networking in Cyclades"""
    avail_images = Proper(value=None)
    avail_flavors = Proper(value=None)
    server_a = Proper(value=None)
    server_b = Proper(value=None)
    network = Proper(value=None)

    def test_001_images_to_use(self):
        """Find images to be used to create our machines"""
        if self.images is None:
            self.info("No --images given. Will use the default %s",
                      "^Debian Base$")
            filters = ["name:^Debian Base$"]
        else:
            filters = self.images

        self.avail_images = self._find_images(filters)
        self.info("Found %s images to choose from", len(self.avail_images))

    def test_002_flavors_to_use(self):
        """Find flavors to be used to create our machines"""
        flavors = self._get_list_of_flavors(detail=True)

        if self.flavors is None:
            self.info("No --flavors given. Will use all of them")
            self.avail_flavors = flavors
        else:
            self.avail_flavors = self._find_flavors(
                self.flavors, flavors=flavors)
        self.info("Found %s flavors to choose from", len(self.avail_flavors))

    def test_003_submit_create_server_a(self):
        """Submit create server request for server A"""
        use_image = random.choice(self.avail_images)
        use_flavor = random.choice(self.avail_flavors)
        server = self._create_server(use_image, use_flavor, network=True)

        self.server_a = {}
        self.server_a['server'] = server
        self.server_a['image'] = use_image
        self.server_a['flavor'] = use_flavor
        self.server_a['username'] = self._get_connection_username(server)
        self.server_a['password'] = server['adminPass']

    def test_004_submit_create_server_b(self):
        """Submit create server request for server B"""
        use_image = random.choice(self.avail_images)
        use_flavor = random.choice(self.avail_flavors)
        server = self._create_server(use_image, use_flavor, network=True)

        self.server_b = {}
        self.server_b['server'] = server
        self.server_b['image'] = use_image
        self.server_b['flavor'] = use_flavor
        self.server_b['username'] = self._get_connection_username(server)
        self.server_b['password'] = server['adminPass']

    def test_005_server_a_active(self):
        """Test that server A becomes ACTIVE"""
        self._insist_on_server_transition(
            self.server_a['server'], ["BUILD"], "ACTIVE")

    def test_005_server_b_active(self):
        """Test that server B becomes ACTIVE"""
        self._insist_on_server_transition(
            self.server_b['server'], ["BUILD"], "ACTIVE")

    def test_006_create_network(self):
        """Submit a create network request"""
        self.network = self._create_network()

        self._insist_on_network_transition(
            self.network, ["BUILD"], "ACTIVE")

    def test_007_connect_to_network(self):
        """Connect the two VMs to the newly created network"""
        self._create_port(self.network['id'], self.server_a['server']['id'])
        self._create_port(self.network['id'], self.server_b['server']['id'])

        # Update servers
        self.server_a['server'] = self._get_server_details(
            self.server_a['server'])
        self.server_b['server'] = self._get_server_details(
            self.server_b['server'])

        # Check that servers got private IPs
        ipv4 = self._get_ips(self.server_a['server'], network=self.network)
        self.assertEqual(len(ipv4), 1)
        self.server_a['pr_ipv4'] = ipv4[0]
        ipv4 = self._get_ips(self.server_b['server'], network=self.network)
        self.assertEqual(len(ipv4), 1)
        self.server_b['pr_ipv4'] = ipv4

    def test_008_reboot_server_a(self):
        """Rebooting server A"""
        self.clients.cyclades.shutdown_server(self.server_a['server']['id'])
        self._insist_on_server_transition(
            self.server_a['server'], ["ACTIVE"], "STOPPED")

        self.clients.cyclades.start_server(self.server_a['server']['id'])
        self._insist_on_server_transition(
            self.server_a['server'], ["STOPPED"], "ACTIVE")

    def test_009_ping_server_a(self):
        """Test if server A responds to IPv4 pings"""
        self._insist_on_ping(self._get_ips(self.server_a['server'])[0])

    def test_010_reboot_server_b(self):
        """Rebooting server B"""
        self.clients.cyclades.shutdown_server(self.server_b['server']['id'])
        self._insist_on_server_transition(
            self.server_b['server'], ["ACTIVE"], "STOPPED")

        self.clients.cyclades.start_server(self.server_b['server']['id'])
        self._insist_on_server_transition(
            self.server_b['server'], ["STOPPED"], "ACTIVE")

    def test_011_ping_server_b(self):
        """Test that server B responds to IPv4 pings"""
        self._insist_on_ping(self._get_ips(self.server_b['server'])[0])

    def test_012_test_connection_exists(self):
        """Ping server B from server A to test if connection exists"""
        self._skip_if(not self._image_is(self.server_a['image'], "linux"),
                      "only valid for Linux servers")
        self._skip_if(not self._image_is(self.server_b['image'], "linux"),
                      "only valid for Linux servers")

        server_a_public_ip = self._get_ips(self.server_a['server'])[0]
        server_b_private_ip = self._get_ips(
            self.server_b['server'], network=self.network)[0]
        msg = "Will try to connect to server A (%s) and ping to server B (%s)"
        self.info(msg, server_a_public_ip, server_b_private_ip)

        cmd = "for i in {1..7}; do if ping -c 3 -w 20 %s > /dev/null; " \
            "then echo 'True'; break; fi; done" % server_b_private_ip
        lines, status = self._ssh_execute(
            server_a_public_ip, self.server_a['username'],
            self.server_a['password'], cmd)

        self.assertEqual(status, 0)
        self.assertEqual(lines, ['True\n'])

    def test_013_disconnect_network(self):
        """Disconnecting servers A and B from network"""
        self._disconnect_from_network(self.server_a['server'], self.network)
        self._disconnect_from_network(self.server_b['server'], self.network)

    def test_014_destroy_network(self):
        """Submit delete network request"""
        self._delete_networks([self.network])

    def test_015_cleanup_servers(self):
        """Cleanup servers created for this test"""
        self._delete_servers([self.server_a['server'],
                              self.server_b['server']])
