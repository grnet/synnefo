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
Utility functions for Cyclades Tests
Cyclades require a lot helper functions and `common'
had grown too much.

"""

import time
import base64
import socket
import random
import paramiko
import tempfile
import subprocess

from synnefo_tools.burnin.common import BurninTests


# Too many public methods. pylint: disable-msg=R0904
class CycladesTests(BurninTests):
    """Extends the BurninTests class for Cyclades"""
    def _try_until_timeout_expires(self, opmsg, check_fun):
        """Try to perform an action until timeout expires"""
        assert callable(check_fun), "Not a function"

        action_timeout = self.action_timeout
        action_warning = self.action_warning
        if action_warning > action_timeout:
            action_warning = action_timeout

        start_time = int(time.time())
        end_time = start_time + action_warning
        while end_time > time.time():
            try:
                ret_value = check_fun()
                self.info("Operation `%s' finished in %s seconds",
                          opmsg, int(time.time()) - start_time)
                return ret_value
            except Retry:
                time.sleep(self.query_interval)
        self.warning("Operation `%s' is taking too long after %s seconds",
                     opmsg, int(time.time()) - start_time)

        end_time = start_time + action_timeout
        while end_time > time.time():
            try:
                ret_value = check_fun()
                self.info("Operation `%s' finished in %s seconds",
                          opmsg, int(time.time()) - start_time)
                return ret_value
            except Retry:
                time.sleep(self.query_interval)
        self.error("Operation `%s' timed out after %s seconds",
                   opmsg, int(time.time()) - start_time)
        self.fail("time out")

    def _get_list_of_servers(self, detail=False):
        """Get (detailed) list of servers"""
        if detail:
            self.info("Getting detailed list of servers")
        else:
            self.info("Getting simple list of servers")
        return self.clients.cyclades.list_servers(detail=detail)

    def _get_list_of_networks(self, detail=False):
        """Get (detailed) list of networks"""
        if detail:
            self.info("Getting detailed list of networks")
        else:
            self.info("Getting simple list of networks")
        return self.clients.cyclades.list_networks(detail=detail)

    def _get_server_details(self, server, quiet=False):
        """Get details for a server"""
        if not quiet:
            self.info("Getting details for server %s with id %s",
                      server['name'], server['id'])
        return self.clients.cyclades.get_server_details(server['id'])

    def _create_server(self, image, flavor, personality=None):
        """Create a new server"""
        servername = "%s for %s" % (self.run_id, image['name'])
        self.info("Creating a server with name %s", servername)
        self.info("Using image %s with id %s", image['name'], image['id'])
        self.info("Using flavor %s with id %s", flavor['name'], flavor['id'])
        server = self.clients.cyclades.create_server(
            servername, flavor['id'], image['id'], personality=personality)

        self.info("Server id: %s", server['id'])
        self.info("Server password: %s", server['adminPass'])

        self.assertEqual(server['name'], servername)
        self.assertEqual(server['flavor']['id'], flavor['id'])
        self.assertEqual(server['image']['id'], image['id'])
        self.assertEqual(server['status'], "BUILD")

        return server

    def _get_connection_username(self, server):
        """Determine the username to use to connect to the server"""
        users = server['metadata'].get("users", None)
        ret_user = None
        if users is not None:
            user_list = users.split()
            if "root" in user_list:
                ret_user = "root"
            else:
                ret_user = random.choice(user_list)
        else:
            # Return the login name for connections based on the server OS
            self.info("Could not find `users' metadata in server. Let's guess")
            os_value = server['metadata'].get("os")
            if os_value in ("Ubuntu", "Kubuntu", "Fedora"):
                ret_user = "user"
            elif os_value in ("windows", "windows_alpha1"):
                ret_user = "Administrator"
            else:
                ret_user = "root"

        self.assertIsNotNone(ret_user)
        self.info("User's login name: %s", ret_user)
        return ret_user

    def _insist_on_server_transition(self, server, curr_statuses, new_status):
        """Insist on server transiting from curr_statuses to new_status"""
        def check_fun():
            """Check server status"""
            srv = self._get_server_details(server, quiet=True)
            if srv['status'] in curr_statuses:
                raise Retry()
            elif srv['status'] == new_status:
                return
            else:
                msg = "Server \"%s\" with id %s went to unexpected status %s"
                self.error(msg, server['name'], server['id'], srv['status'])
                self.fail(msg % (server['name'], server['id'], srv['status']))
        opmsg = "Waiting for server \"%s\" to become %s"
        self.info(opmsg, server['name'], new_status)
        opmsg = opmsg % (server['name'], new_status)
        self._try_until_timeout_expires(opmsg, check_fun)

    def _insist_on_network_transition(self, network,
                                      curr_statuses, new_status):
        """Insist on network transiting from curr_statuses to new_status"""
        def check_fun():
            """Check network status"""
            ntw = self.clients.cyclades.get_network_details(network['id'])
            if ntw['status'] in curr_statuses:
                raise Retry()
            elif ntw['status'] == new_status:
                return
            else:
                msg = "Network %s with id %s went to unexpected status %s"
                self.error(msg, network['name'], network['id'], ntw['status'])
                self.fail(msg %
                          (network['name'], network['id'], ntw['status']))
        opmsg = "Waiting for network \"%s\" to become %s"
        self.info(opmsg, network['name'], new_status)
        opmsg = opmsg % (network['name'], new_status)
        self._try_until_timeout_expires(opmsg, check_fun)

    def _insist_on_network_connection(self, server, network, disconnect=False):
        """Insist that the server has connected to the network"""
        def check_fun():
            """Check network connection"""
            dsrv = self._get_server_details(server, quiet=True)
            nets = [s['network_id'] for s in dsrv['attachments']]
            if not disconnect and network['id'] not in nets:
                raise Retry()
            if disconnect and network['id'] in nets:
                raise Retry()
        if disconnect:
            opmsg = \
                "Waiting for server \"%s\" to disconnect from network \"%s\""
        else:
            opmsg = "Waiting for server \"%s\" to connect to network \"%s\""
        self.info(opmsg, server['name'], network['name'])
        opmsg = opmsg % (server['name'], network['name'])
        self._try_until_timeout_expires(opmsg, check_fun)

    def _insist_on_tcp_connection(self, family, host, port):
        """Insist on tcp connection"""
        def check_fun():
            """Get a connected socket from the specified family to host:port"""
            sock = None
            for res in socket.getaddrinfo(host, port, family,
                                          socket.SOCK_STREAM, 0,
                                          socket.AI_PASSIVE):
                fam, socktype, proto, _, saddr = res
                try:
                    sock = socket.socket(fam, socktype, proto)
                except socket.error:
                    sock = None
                    continue
                try:
                    sock.connect(saddr)
                except socket.error:
                    sock.close()
                    sock = None
                    continue
            if sock is None:
                raise Retry
            return sock
        familystr = {socket.AF_INET: "IPv4", socket.AF_INET6: "IPv6",
                     socket.AF_UNSPEC: "Unspecified-IPv4/6"}
        opmsg = "Connecting over %s to %s:%s"
        self.info(opmsg, familystr.get(family, "Unknown"), host, port)
        opmsg = opmsg % (familystr.get(family, "Unknown"), host, port)
        return self._try_until_timeout_expires(opmsg, check_fun)

    def _get_ip(self, server, version=4, network=None):
        """Get the IP of a server from the detailed server info

        If network not given then get the public IP. Else the ip
        attached to that network

        """
        assert version in (4, 6)

        nics = server['attachments']
        addrs = None
        for nic in nics:
            net_id = nic['network_id']
            if network is None:
                if self.clients.cyclades.get_network_details(net_id)['public']:
                    if nic['ipv' + str(version)]:
                        addrs = nic['ipv' + str(version)]
                        break
            else:
                if net_id == network['id']:
                    if nic['ipv' + str(version)]:
                        addrs = nic['ipv' + str(version)]
                        break

        self.assertIsNotNone(addrs, "Can not get IP from server attachments")
        if network is None:
            msg = "Server's public IPv%s is %s"
            self.info(msg, version, addrs)
        else:
            msg = "Server's IPv%s attached to network \"%s\" is %s"
            self.info(msg, version, network['id'], addrs)
        return addrs

    def _insist_on_ping(self, ip_addr, version=4):
        """Test server responds to a single IPv4 of IPv6 ping"""
        def check_fun():
            """Ping to server"""
            cmd = ("ping%s -c 3 -w 20 %s" %
                   ("6" if version == 6 else "", ip_addr))
            ping = subprocess.Popen(
                cmd, shell=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            ping.communicate()
            ret = ping.wait()
            if ret != 0:
                raise Retry
        assert version in (4, 6)
        opmsg = "Sent IPv%s ping requests to %s"
        self.info(opmsg, version, ip_addr)
        opmsg = opmsg % (version, ip_addr)
        self._try_until_timeout_expires(opmsg, check_fun)

    def _image_is(self, image, osfamily):
        """Return true if the image is of `osfamily'"""
        d_image = self.clients.cyclades.get_image_details(image['id'])
        return d_image['metadata']['osfamily'].lower().find(osfamily) >= 0

    def _ssh_execute(self, hostip, username, password, command):
        """Execute a command via ssh"""
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(hostip, username=username, password=password)
        except socket.error as err:
            self.fail(err)
        try:
            _, stdout, _ = ssh.exec_command(command)
        except paramiko.SSHException as err:
            self.fail(err)
        status = stdout.channel.recv_exit_status()
        output = stdout.readlines()
        ssh.close()
        return output, status

    def _insist_get_hostname_over_ssh(self, hostip, username, password):
        """Connect to server using ssh and get it's hostname"""
        def check_fun():
            """Get hostname"""
            try:
                lines, status = self._ssh_execute(
                    hostip, username, password, "hostname")
                self.assertEqual(status, 0)
                self.assertEqual(len(lines), 1)
                # Remove new line
                return lines[0].strip('\n')
            except AssertionError:
                raise Retry()
        opmsg = "Connecting to server using ssh and get it's hostname"
        self.info(opmsg)
        hostname = self._try_until_timeout_expires(opmsg, check_fun)
        self.info("Server's hostname is %s", hostname)
        return hostname

    # Too many arguments. pylint: disable-msg=R0913
    def _check_file_through_ssh(self, hostip, username, password,
                                remotepath, content):
        """Fetch file from server and compare contents"""
        self.info("Fetching file %s from remote server", remotepath)
        transport = paramiko.Transport((hostip, 22))
        transport.connect(username=username, password=password)
        with tempfile.NamedTemporaryFile() as ftmp:
            sftp = paramiko.SFTPClient.from_transport(transport)
            sftp.get(remotepath, ftmp.name)
            sftp.close()
            transport.close()
            self.info("Comparing file contents")
            remote_content = base64.b64encode(ftmp.read())
            self.assertEqual(content, remote_content)

    def _disconnect_from_network(self, server, network):
        """Disconnect server from network"""
        nid = None
        for nic in server['attachments']:
            if nic['network_id'] == network['id']:
                nid = nic['id']
                break
        self.assertIsNotNone(nid, "Could not find network card")
        self.clients.cyclades.disconnect_server(server['id'], nid)


class Retry(Exception):
    """Retry the action

    This is used by _try_unit_timeout_expires method.

    """
