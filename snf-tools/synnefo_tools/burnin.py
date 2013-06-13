#!/usr/bin/env python

# Copyright 2011 GRNET S.A. All rights reserved.
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

"""Perform integration testing on a running Synnefo deployment"""

#import __main__
import datetime
import inspect
import logging
import os
import os.path
import paramiko
import prctl
import subprocess
import signal
import socket
import sys
import time
import tempfile
from base64 import b64encode
from IPy import IP
from multiprocessing import Process, Queue
from random import choice, randint
from optparse import OptionParser, OptionValueError

from kamaki.clients.compute import ComputeClient
from kamaki.clients.cyclades import CycladesClient
from kamaki.clients.image import ImageClient
from kamaki.clients.pithos import PithosClient
from kamaki.clients.astakos import AstakosClient
from kamaki.clients import ClientError

from vncauthproxy.d3des import generate_response as d3des_generate_response

# Use backported unittest functionality if Python < 2.7
try:
    import unittest2 as unittest
except ImportError:
    if sys.version_info < (2, 7):
        raise Exception("The unittest2 package is required for Python < 2.7")
    import unittest

# --------------------------------------------------------------------
# Global Variables
AUTH_URL = None
TOKEN = None
PLANKTON_USER = None
NO_IPV6 = None
DEFAULT_PLANKTON_USER = "images@okeanos.grnet.gr"
NOFAILFAST = None
VERBOSE = None

# A unique id identifying this test run
TEST_RUN_ID = datetime.datetime.strftime(datetime.datetime.now(),
                                         "%Y%m%d%H%M%S")
SNF_TEST_PREFIX = "snf-test-"

red = '\x1b[31m'
yellow = '\x1b[33m'
green = '\x1b[32m'
normal = '\x1b[0m'


# --------------------------------------------------------------------
# Global functions
def _ssh_execute(hostip, username, password, command):
    """Execute a command via ssh"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(hostip, username=username, password=password)
    except socket.error, err:
        raise AssertionError(err)
    try:
        stdin, stdout, stderr = ssh.exec_command(command)
    except paramiko.SSHException, err:
        raise AssertionError(err)
    status = stdout.channel.recv_exit_status()
    output = stdout.readlines()
    ssh.close()
    return output, status


def _get_user_id():
    """Authenticate to astakos and get unique users id"""
    astakos = AstakosClient(AUTH_URL, TOKEN)
    authenticate = astakos.authenticate()
    return authenticate['access']['user']['id']


# --------------------------------------------------------------------
# BurninTestReulst class
class BurninTestResult(unittest.TextTestResult):
    def addSuccess(self, test):
        super(BurninTestResult, self).addSuccess(test)
        if self.showAll:
            if hasattr(test, 'result_dict'):
                run_details = test.result_dict

                self.stream.write("\n")
                for i in run_details:
                    self.stream.write("%s : %s \n" % (i, run_details[i]))
                self.stream.write("\n")

        elif self.dots:
            self.stream.write('.')
            self.stream.flush()

    def addError(self, test, err):
        super(BurninTestResult, self).addError(test, err)
        if self.showAll:
            self.stream.writeln("ERROR")
            if hasattr(test, 'result_dict'):
                run_details = test.result_dict

                self.stream.write("\n")
                for i in run_details:
                    self.stream.write("%s : %s \n" % (i, run_details[i]))
                self.stream.write("\n")

        elif self.dots:
            self.stream.write('E')
            self.stream.flush()

    def addFailure(self, test, err):
        super(BurninTestResult, self).addFailure(test, err)
        if self.showAll:
            self.stream.writeln("FAIL")
            if hasattr(test, 'result_dict'):
                run_details = test.result_dict

                self.stream.write("\n")
                for i in run_details:
                    self.stream.write("%s : %s \n" % (i, run_details[i]))
                self.stream.write("\n")

        elif self.dots:
            self.stream.write('F')
            self.stream.flush()


# --------------------------------------------------------------------
# Format Results
class burninFormatter(logging.Formatter):
    err_fmt = red + "ERROR: %(msg)s" + normal
    dbg_fmt = green + "* %(msg)s" + normal
    info_fmt = "%(msg)s"

    def __init__(self, fmt="%(levelno)s: %(msg)s"):
        logging.Formatter.__init__(self, fmt)

    def format(self, record):
        format_orig = self._fmt
        # Replace the original format with one customized by logging level
        if record.levelno == 10:    # DEBUG
            self._fmt = burninFormatter.dbg_fmt
        elif record.levelno == 20:  # INFO
            self._fmt = burninFormatter.info_fmt
        elif record.levelno == 40:  # ERROR
            self._fmt = burninFormatter.err_fmt
        result = logging.Formatter.format(self, record)
        self._fmt = format_orig
        return result

log = logging.getLogger("burnin")
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(burninFormatter())
log.addHandler(handler)


# --------------------------------------------------------------------
# UnauthorizedTestCase class
class UnauthorizedTestCase(unittest.TestCase):
    """Test unauthorized access"""
    @classmethod
    def setUpClass(cls):
        cls.astakos = AstakosClient(AUTH_URL, TOKEN)
        cls.compute_url = \
            cls.astakos.get_service_endpoints('compute')['publicURL']
        cls.result_dict = dict()

    def test_unauthorized_access(self):
        """Test access without a valid token fails"""
        log.info("Authentication test")
        falseToken = '12345'
        c = ComputeClient(self.compute_url, falseToken)

        with self.assertRaises(ClientError) as cm:
            c.list_servers()
            self.assertEqual(cm.exception.status, 401)


# --------------------------------------------------------------------
# This class gest replicated into Images TestCases dynamically
class ImagesTestCase(unittest.TestCase):
    """Test image lists for consistency"""
    @classmethod
    def setUpClass(cls):
        """Initialize kamaki, get (detailed) list of images"""
        log.info("Getting simple and detailed list of images")
        cls.astakos_client = AstakosClient(AUTH_URL, TOKEN)
        # Compute Client
        compute_url = \
            cls.astakos_client.get_service_endpoints('compute')['publicURL']
        cls.compute_client = ComputeClient(compute_url, TOKEN)
        # Image Client
        image_url = \
            cls.astakos_client.get_service_endpoints('image')['publicURL']
        cls.image_client = ImageClient(image_url, TOKEN)
        # Pithos Client
        pithos_url = cls.astakos_client.\
            get_service_endpoints('object-store')['publicURL']
        cls.pithos_client = PithosClient(pithos_url, TOKEN)

        # Get images
        cls.images = \
            filter(lambda x: not x['name'].startswith(SNF_TEST_PREFIX),
                   cls.image_client.list_public())
        cls.dimages = \
            filter(lambda x: not x['name'].startswith(SNF_TEST_PREFIX),
                   cls.image_client.list_public(detail=True))
        cls.result_dict = dict()
        # Get uniq user id
        cls.uuid = _get_user_id()
        log.info("Uniq user id = %s" % cls.uuid)
        # Create temp directory and store it inside our class
        # XXX: In my machine /tmp has not enough space
        #      so use current directory to be sure.
        cls.temp_dir = tempfile.mkdtemp(dir=os.getcwd())
        cls.temp_image_name = \
            SNF_TEST_PREFIX + cls.imageid + ".diskdump"

    @classmethod
    def tearDownClass(cls):
        """Remove local files"""
        try:
            temp_file = os.path.join(cls.temp_dir, cls.temp_image_name)
            os.unlink(temp_file)
        except:
            pass
        try:
            os.rmdir(cls.temp_dir)
        except:
            pass

    def test_001_list_images(self):
        """Test image list actually returns images"""
        self.assertGreater(len(self.images), 0)

    def test_002_list_images_detailed(self):
        """Test detailed image list is the same length as list"""
        self.assertEqual(len(self.dimages), len(self.images))

    def test_003_same_image_names(self):
        """Test detailed and simple image list contain same names"""
        names = sorted(map(lambda x: x["name"], self.images))
        dnames = sorted(map(lambda x: x["name"], self.dimages))
        self.assertEqual(names, dnames)

# XXX: Find a way to resolve owner's uuid to username.
#      (maybe use astakosclient)
#    def test_004_unique_image_names(self):
#        """Test system images have unique names"""
#        sys_images = filter(lambda x: x['owner'] == PLANKTON_USER,
#                            self.dimages)
#        names = sorted(map(lambda x: x["name"], sys_images))
#        self.assertEqual(sorted(list(set(names))), names)

    def test_005_image_metadata(self):
        """Test every image has specific metadata defined"""
        keys = frozenset(["osfamily", "root_partition"])
        details = self.compute_client.list_images(detail=True)
        for i in details:
            self.assertTrue(keys.issubset(i["metadata"].keys()))

    def test_006_download_image(self):
        """Download image from pithos+"""
        # Get image location
        image = filter(
            lambda x: x['id'] == self.imageid, self.dimages)[0]
        image_location = \
            image['location'].replace("://", " ").replace("/", " ").split()
        log.info("Download image, with owner %s\n\tcontainer %s, and name %s"
                 % (image_location[1], image_location[2], image_location[3]))
        self.pithos_client.account = image_location[1]
        self.pithos_client.container = image_location[2]
        temp_file = os.path.join(self.temp_dir, self.temp_image_name)
        with open(temp_file, "wb+") as f:
            self.pithos_client.download_object(image_location[3], f)

    def test_007_upload_image(self):
        """Upload and register image"""
        temp_file = os.path.join(self.temp_dir, self.temp_image_name)
        log.info("Upload image to pithos+")
        # Create container `images'
        self.pithos_client.account = self.uuid
        self.pithos_client.container = "images"
        self.pithos_client.container_put()
        with open(temp_file, "rb+") as f:
            self.pithos_client.upload_object(self.temp_image_name, f)
        log.info("Register image to plankton")
        location = "pithos://" + self.uuid + \
            "/images/" + self.temp_image_name
        params = {'is_public': True}
        properties = {'OSFAMILY': "linux", 'ROOT_PARTITION': 1}
        self.image_client.register(
            self.temp_image_name, location, params, properties)
        # Get image id
        details = self.image_client.list_public(detail=True)
        detail = filter(lambda x: x['location'] == location, details)
        self.assertEqual(len(detail), 1)
        cls = type(self)
        cls.temp_image_id = detail[0]['id']
        log.info("Image registered with id %s" % detail[0]['id'])

    def test_008_cleanup_image(self):
        """Cleanup image test"""
        log.info("Cleanup image test")
        # Remove image from pithos+
        self.pithos_client.account = self.uuid
        self.pithos_client.container = "images"
        self.pithos_client.del_object(self.temp_image_name)


# --------------------------------------------------------------------
# FlavorsTestCase class
class FlavorsTestCase(unittest.TestCase):
    """Test flavor lists for consistency"""
    @classmethod
    def setUpClass(cls):
        """Initialize kamaki, get (detailed) list of flavors"""
        log.info("Getting simple and detailed list of flavors")
        cls.astakos_client = AstakosClient(AUTH_URL, TOKEN)
        # Compute Client
        compute_url = \
            cls.astakos_client.get_service_endpoints('compute')['publicURL']
        cls.compute_client = ComputeClient(compute_url, TOKEN)
        cls.flavors = cls.compute_client.list_flavors()
        cls.dflavors = cls.compute_client.list_flavors(detail=True)
        cls.result_dict = dict()

    def test_001_list_flavors(self):
        """Test flavor list actually returns flavors"""
        self.assertGreater(len(self.flavors), 0)

    def test_002_list_flavors_detailed(self):
        """Test detailed flavor list is the same length as list"""
        self.assertEquals(len(self.dflavors), len(self.flavors))

    def test_003_same_flavor_names(self):
        """Test detailed and simple flavor list contain same names"""
        names = sorted(map(lambda x: x["name"], self.flavors))
        dnames = sorted(map(lambda x: x["name"], self.dflavors))
        self.assertEqual(names, dnames)

    def test_004_unique_flavor_names(self):
        """Test flavors have unique names"""
        names = sorted(map(lambda x: x["name"], self.flavors))
        self.assertEqual(sorted(list(set(names))), names)

    def test_005_well_formed_flavor_names(self):
        """Test flavors have names of the form CxxRyyDzz
        Where xx is vCPU count, yy is RAM in MiB, zz is Disk in GiB
        """
        for f in self.dflavors:
            flavor = (f["vcpus"], f["ram"], f["disk"], f["SNF:disk_template"])
            self.assertEqual("C%dR%dD%d%s" % flavor,
                             f["name"],
                             "Flavor %s does not match its specs." % f["name"])


# --------------------------------------------------------------------
# ServersTestCase class
class ServersTestCase(unittest.TestCase):
    """Test server lists for consistency"""
    @classmethod
    def setUpClass(cls):
        """Initialize kamaki, get (detailed) list of servers"""
        log.info("Getting simple and detailed list of servers")

        cls.astakos_client = AstakosClient(AUTH_URL, TOKEN)
        # Compute Client
        compute_url = \
            cls.astakos_client.get_service_endpoints('compute')['publicURL']
        cls.compute_client = ComputeClient(compute_url, TOKEN)
        cls.servers = cls.compute_client.list_servers()
        cls.dservers = cls.compute_client.list_servers(detail=True)
        cls.result_dict = dict()

    # def test_001_list_servers(self):
    #     """Test server list actually returns servers"""
    #     self.assertGreater(len(self.servers), 0)

    def test_002_list_servers_detailed(self):
        """Test detailed server list is the same length as list"""
        self.assertEqual(len(self.dservers), len(self.servers))

    def test_003_same_server_names(self):
        """Test detailed and simple flavor list contain same names"""
        names = sorted(map(lambda x: x["name"], self.servers))
        dnames = sorted(map(lambda x: x["name"], self.dservers))
        self.assertEqual(names, dnames)


# --------------------------------------------------------------------
# Pithos Test Cases
class PithosTestCase(unittest.TestCase):
    """Test pithos functionality"""
    @classmethod
    def setUpClass(cls):
        """Initialize kamaki, get list of containers"""
        # Get uniq user id
        cls.uuid = _get_user_id()
        log.info("Uniq user id = %s" % cls.uuid)
        log.info("Getting list of containers")

        cls.astakos_client = AstakosClient(AUTH_URL, TOKEN)
        # Pithos Client
        pithos_url = cls.astakos_client.\
            get_service_endpoints('object-store')['publicURL']
        cls.pithos_client = PithosClient(pithos_url, TOKEN, cls.uuid)

        cls.containers = cls.pithos_client.list_containers()
        cls.result_dict = dict()

    def test_001_list_containers(self):
        """Test container list actually returns containers"""
        self.assertGreater(len(self.containers), 0)

    def test_002_unique_containers(self):
        """Test if containers have unique names"""
        names = [n['name'] for n in self.containers]
        names = sorted(names)
        self.assertEqual(sorted(list(set(names))), names)

    def test_003_create_container(self):
        """Test create a container"""
        rand_num = randint(1000, 9999)
        rand_name = "%s%s" % (SNF_TEST_PREFIX, rand_num)
        names = [n['name'] for n in self.containers]
        while rand_name in names:
            rand_num = randint(1000, 9999)
            rand_name = "%s%s" % (SNF_TEST_PREFIX, rand_num)
        # Create container
        self.pithos_client.container = rand_name
        self.pithos_client.container_put()
        # Get list of containers
        new_containers = self.pithos_client.list_containers()
        new_container_names = [n['name'] for n in new_containers]
        self.assertIn(rand_name, new_container_names)

    def test_004_upload(self):
        """Test uploading something to pithos+"""
        # Create a tmp file
        with tempfile.TemporaryFile() as f:
            f.write("This is a temp file")
            f.seek(0, 0)
            # Where to save file
            self.pithos_client.upload_object("test.txt", f)

    def test_005_download(self):
        """Test download something from pithos+"""
        # Create tmp directory to save file
        tmp_dir = tempfile.mkdtemp()
        tmp_file = os.path.join(tmp_dir, "test.txt")
        with open(tmp_file, "wb+") as f:
            self.pithos_client.download_object("test.txt", f)
            # Read file
            f.seek(0, 0)
            content = f.read()
        # Remove files
        os.unlink(tmp_file)
        os.rmdir(tmp_dir)
        # Compare results
        self.assertEqual(content, "This is a temp file")

    def test_006_remove(self):
        """Test removing files and containers"""
        cont_name = self.pithos_client.container
        self.pithos_client.del_object("test.txt")
        self.pithos_client.purge_container()
        # List containers
        containers = self.pithos_client.list_containers()
        cont_names = [n['name'] for n in containers]
        self.assertNotIn(cont_name, cont_names)


# --------------------------------------------------------------------
# This class gets replicated into actual TestCases dynamically
class SpawnServerTestCase(unittest.TestCase):
    """Test scenario for server of the specified image"""
    @classmethod
    def setUpClass(cls):
        """Initialize a kamaki instance"""
        log.info("Spawning server for image `%s'" % cls.imagename)

        cls.astakos_client = AstakosClient(AUTH_URL, TOKEN)
        # Cyclades Client
        compute_url = \
            cls.astakos_client.get_service_endpoints('compute')['publicURL']
        cls.cyclades_client = CycladesClient(compute_url, TOKEN)

        cls.result_dict = dict()

    def _get_ipv4(self, server):
        """Get the public IPv4 of a server from the detailed server info"""

        nics = server["attachments"]

        for nic in nics:
            net_id = nic["network_id"]
            if self.cyclades_client.get_network_details(net_id)["public"]:
                public_addrs = nic["ipv4"]

        self.assertTrue(public_addrs is not None)

        return public_addrs

    def _get_ipv6(self, server):
        """Get the public IPv6 of a server from the detailed server info"""

        nics = server["attachments"]

        for nic in nics:
            net_id = nic["network_id"]
            if self.cyclades_client.get_network_details(net_id)["public"]:
                public_addrs = nic["ipv6"]

        self.assertTrue(public_addrs is not None)

        return public_addrs

    def _connect_loginname(self, os_value):
        """Return the login name for connections based on the server OS"""
        if os_value in ("Ubuntu", "Kubuntu", "Fedora"):
            return "user"
        elif os_value in ("windows", "windows_alpha1"):
            return "Administrator"
        else:
            return "root"

    def _verify_server_status(self, current_status, new_status):
        """Verify a server has switched to a specified status"""
        server = self.cyclades_client.get_server_details(self.serverid)
        if server["status"] not in (current_status, new_status):
            return None  # Do not raise exception, return so the test fails
        self.assertEquals(server["status"], new_status)

    def _get_connected_tcp_socket(self, family, host, port):
        """Get a connected socket from the specified family to host:port"""
        sock = None
        for res in \
            socket.getaddrinfo(host, port, family, socket.SOCK_STREAM, 0,
                               socket.AI_PASSIVE):
            af, socktype, proto, canonname, sa = res
            try:
                sock = socket.socket(af, socktype, proto)
            except socket.error:
                sock = None
                continue
            try:
                sock.connect(sa)
            except socket.error:
                sock.close()
                sock = None
                continue
        self.assertIsNotNone(sock)
        return sock

    def _ping_once(self, ipv6, ip):
        """Test server responds to a single IPv4 or IPv6 ping"""
        cmd = "ping%s -c 2 -w 3 %s" % ("6" if ipv6 else "", ip)
        ping = subprocess.Popen(cmd, shell=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdout, stderr) = ping.communicate()
        ret = ping.wait()
        self.assertEquals(ret, 0)

    def _get_hostname_over_ssh(self, hostip, username, password):
        lines, status = _ssh_execute(
            hostip, username, password, "hostname")
        self.assertEqual(len(lines), 1)
        return lines[0]

    def _try_until_timeout_expires(self, warn_timeout, fail_timeout,
                                   opmsg, callable, *args, **kwargs):
        if warn_timeout == fail_timeout:
            warn_timeout = fail_timeout + 1
        warn_tmout = time.time() + warn_timeout
        fail_tmout = time.time() + fail_timeout
        while True:
            self.assertLess(time.time(), fail_tmout,
                            "operation `%s' timed out" % opmsg)
            if time.time() > warn_tmout:
                log.warning("Server %d: `%s' operation `%s' not done yet",
                            self.serverid, self.servername, opmsg)
            try:
                log.info("%s... " % opmsg)
                return callable(*args, **kwargs)
            except AssertionError:
                pass
            time.sleep(self.query_interval)

    def _insist_on_tcp_connection(self, family, host, port):
        familystr = {socket.AF_INET: "IPv4", socket.AF_INET6: "IPv6",
                     socket.AF_UNSPEC: "Unspecified-IPv4/6"}
        msg = "connect over %s to %s:%s" % \
              (familystr.get(family, "Unknown"), host, port)
        sock = self._try_until_timeout_expires(
            self.action_timeout, self.action_timeout,
            msg, self._get_connected_tcp_socket,
            family, host, port)
        return sock

    def _insist_on_status_transition(self, current_status, new_status,
                                     fail_timeout, warn_timeout=None):
        msg = "Server %d: `%s', waiting for %s -> %s" % \
              (self.serverid, self.servername, current_status, new_status)
        if warn_timeout is None:
            warn_timeout = fail_timeout
        self._try_until_timeout_expires(warn_timeout, fail_timeout,
                                        msg, self._verify_server_status,
                                        current_status, new_status)
        # Ensure the status is actually the expected one
        server = self.cyclades_client.get_server_details(self.serverid)
        self.assertEquals(server["status"], new_status)

    def _insist_on_ssh_hostname(self, hostip, username, password):
        msg = "SSH to %s, as %s/%s" % (hostip, username, password)
        hostname = self._try_until_timeout_expires(
            self.action_timeout, self.action_timeout,
            msg, self._get_hostname_over_ssh,
            hostip, username, password)

        # The hostname must be of the form 'prefix-id'
        self.assertTrue(hostname.endswith("-%d\n" % self.serverid))

    def _check_file_through_ssh(self, hostip, username, password,
                                remotepath, content):
        msg = "Trying file injection through SSH to %s, as %s/%s" % \
            (hostip, username, password)
        log.info(msg)
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostip, username=username, password=password)
            ssh.close()
        except socket.error, err:
            raise AssertionError(err)

        transport = paramiko.Transport((hostip, 22))
        transport.connect(username=username, password=password)

        localpath = '/tmp/' + SNF_TEST_PREFIX + 'injection'
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.get(remotepath, localpath)
        sftp.close()
        transport.close()

        f = open(localpath)
        remote_content = b64encode(f.read())

        # Check if files are the same
        return (remote_content == content)

    def _skipIf(self, condition, msg):
        if condition:
            self.skipTest(msg)

    def test_001_submit_create_server(self):
        """Test submit create server request"""

        log.info("Submit new server request")
        server = self.cyclades_client.create_server(
            self.servername, self.flavorid, self.imageid, self.personality)

        log.info("Server id: " + str(server["id"]))
        log.info("Server password: " + server["adminPass"])
        self.assertEqual(server["name"], self.servername)
        self.assertEqual(server["flavor"], self.flavorid)
        self.assertEqual(server["image"], self.imageid)
        self.assertEqual(server["status"], "BUILD")

        # Update class attributes to reflect data on building server
        cls = type(self)
        cls.serverid = server["id"]
        cls.username = None
        cls.passwd = server["adminPass"]

        self.result_dict["Server ID"] = str(server["id"])
        self.result_dict["Password"] = str(server["adminPass"])

    def test_002a_server_is_building_in_list(self):
        """Test server is in BUILD state, in server list"""
        log.info("Server in BUILD state in server list")

        self.result_dict.clear()

        servers = self.cyclades_client.list_servers(detail=True)
        servers = filter(lambda x: x["name"] == self.servername, servers)

        server = servers[0]
        self.assertEqual(server["name"], self.servername)
        self.assertEqual(server["flavor"], self.flavorid)
        self.assertEqual(server["image"], self.imageid)
        self.assertEqual(server["status"], "BUILD")

    def test_002b_server_is_building_in_details(self):
        """Test server is in BUILD state, in details"""

        log.info("Server in BUILD state in details")

        server = self.cyclades_client.get_server_details(self.serverid)
        self.assertEqual(server["name"], self.servername)
        self.assertEqual(server["flavor"], self.flavorid)
        self.assertEqual(server["image"], self.imageid)
        self.assertEqual(server["status"], "BUILD")

    def test_002c_set_server_metadata(self):

        log.info("Creating server metadata")

        image = self.cyclades_client.get_image_details(self.imageid)
        os_value = image["metadata"]["os"]
        users = image["metadata"].get("users", None)
        self.cyclades_client.update_server_metadata(self.serverid, OS=os_value)

        userlist = users.split()

        # Determine the username to use for future connections
        # to this host
        cls = type(self)

        if "root" in userlist:
            cls.username = "root"
        elif users is None:
            cls.username = self._connect_loginname(os_value)
        else:
            cls.username = choice(userlist)

        self.assertIsNotNone(cls.username)

    def test_002d_verify_server_metadata(self):
        """Test server metadata keys are set based on image metadata"""

        log.info("Verifying image metadata")

        servermeta = self.cyclades_client.get_server_metadata(self.serverid)
        imagemeta = self.cyclades_client.get_image_metadata(self.imageid)

        self.assertEqual(servermeta["OS"], imagemeta["os"])

    def test_003_server_becomes_active(self):
        """Test server becomes ACTIVE"""

        log.info("Waiting for server to become ACTIVE")

        self._insist_on_status_transition(
            "BUILD", "ACTIVE", self.build_fail, self.build_warning)

    def test_003a_get_server_oob_console(self):
        """Test getting OOB server console over VNC

        Implementation of RFB protocol follows
        http://www.realvnc.com/docs/rfbproto.pdf.

        """
        console = self.cyclades_client.get_server_console(self.serverid)
        self.assertEquals(console['type'], "vnc")
        sock = self._insist_on_tcp_connection(
            socket.AF_INET, console["host"], console["port"])

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

    def test_004_server_has_ipv4(self):
        """Test active server has a valid IPv4 address"""

        log.info("Validate server's IPv4")

        server = self.cyclades_client.get_server_details(self.serverid)
        ipv4 = self._get_ipv4(server)

        self.result_dict.clear()
        self.result_dict["IPv4"] = str(ipv4)

        self.assertEquals(IP(ipv4).version(), 4)

    def test_005_server_has_ipv6(self):
        """Test active server has a valid IPv6 address"""
        self._skipIf(NO_IPV6, "--no-ipv6 flag enabled")

        log.info("Validate server's IPv6")

        server = self.cyclades_client.get_server_details(self.serverid)
        ipv6 = self._get_ipv6(server)

        self.result_dict.clear()
        self.result_dict["IPv6"] = str(ipv6)

        self.assertEquals(IP(ipv6).version(), 6)

    def test_006_server_responds_to_ping_IPv4(self):
        """Test server responds to ping on IPv4 address"""

        log.info("Testing if server responds to pings in IPv4")
        self.result_dict.clear()

        server = self.cyclades_client.get_server_details(self.serverid)
        ip = self._get_ipv4(server)
        self._try_until_timeout_expires(self.action_timeout,
                                        self.action_timeout,
                                        "PING IPv4 to %s" % ip,
                                        self._ping_once,
                                        False, ip)

    def test_007_server_responds_to_ping_IPv6(self):
        """Test server responds to ping on IPv6 address"""
        self._skipIf(NO_IPV6, "--no-ipv6 flag enabled")
        log.info("Testing if server responds to pings in IPv6")

        server = self.cyclades_client.get_server_details(self.serverid)
        ip = self._get_ipv6(server)
        self._try_until_timeout_expires(self.action_timeout,
                                        self.action_timeout,
                                        "PING IPv6 to %s" % ip,
                                        self._ping_once,
                                        True, ip)

    def test_008_submit_shutdown_request(self):
        """Test submit request to shutdown server"""

        log.info("Shutting down server")

        self.cyclades_client.shutdown_server(self.serverid)

    def test_009_server_becomes_stopped(self):
        """Test server becomes STOPPED"""

        log.info("Waiting until server becomes STOPPED")
        self._insist_on_status_transition(
            "ACTIVE", "STOPPED", self.action_timeout, self.action_timeout)

    def test_010_submit_start_request(self):
        """Test submit start server request"""

        log.info("Starting server")

        self.cyclades_client.start_server(self.serverid)

    def test_011_server_becomes_active(self):
        """Test server becomes ACTIVE again"""

        log.info("Waiting until server becomes ACTIVE")
        self._insist_on_status_transition(
            "STOPPED", "ACTIVE", self.action_timeout, self.action_timeout)

    def test_011a_server_responds_to_ping_IPv4(self):
        """Test server OS is actually up and running again"""

        log.info("Testing if server is actually up and running")

        self.test_006_server_responds_to_ping_IPv4()

    def test_012_ssh_to_server_IPv4(self):
        """Test SSH to server public IPv4 works, verify hostname"""

        self._skipIf(self.is_windows, "only valid for Linux servers")
        server = self.cyclades_client.get_server_details(self.serverid)
        self._insist_on_ssh_hostname(self._get_ipv4(server),
                                     self.username, self.passwd)

    def test_013_ssh_to_server_IPv6(self):
        """Test SSH to server public IPv6 works, verify hostname"""
        self._skipIf(self.is_windows, "only valid for Linux servers")
        self._skipIf(NO_IPV6, "--no-ipv6 flag enabled")

        server = self.cyclades_client.get_server_details(self.serverid)
        self._insist_on_ssh_hostname(self._get_ipv6(server),
                                     self.username, self.passwd)

    def test_014_rdp_to_server_IPv4(self):
        "Test RDP connection to server public IPv4 works"""
        self._skipIf(not self.is_windows, "only valid for Windows servers")
        server = self.cyclades_client.get_server_details(self.serverid)
        ipv4 = self._get_ipv4(server)
        sock = self._insist_on_tcp_connection(socket.AF_INET, ipv4, 3389)

        # No actual RDP processing done. We assume the RDP server is there
        # if the connection to the RDP port is successful.
        # FIXME: Use rdesktop, analyze exit code? see manpage [costasd]
        sock.close()

    def test_015_rdp_to_server_IPv6(self):
        "Test RDP connection to server public IPv6 works"""
        self._skipIf(not self.is_windows, "only valid for Windows servers")
        self._skipIf(NO_IPV6, "--no-ipv6 flag enabled")

        server = self.cyclades_client.get_server_details(self.serverid)
        ipv6 = self._get_ipv6(server)
        sock = self._get_tcp_connection(socket.AF_INET6, ipv6, 3389)

        # No actual RDP processing done. We assume the RDP server is there
        # if the connection to the RDP port is successful.
        sock.close()

    def test_016_personality_is_enforced(self):
        """Test file injection for personality enforcement"""
        self._skipIf(self.is_windows, "only implemented for Linux servers")
        self._skipIf(self.personality is None, "No personality file selected")

        log.info("Trying to inject file for personality enforcement")

        server = self.cyclades_client.get_server_details(self.serverid)

        for inj_file in self.personality:
            equal_files = self._check_file_through_ssh(self._get_ipv4(server),
                                                       inj_file['owner'],
                                                       self.passwd,
                                                       inj_file['path'],
                                                       inj_file['contents'])
            self.assertTrue(equal_files)

    def test_017_submit_delete_request(self):
        """Test submit request to delete server"""

        log.info("Deleting server")

        self.cyclades_client.delete_server(self.serverid)

    def test_018_server_becomes_deleted(self):
        """Test server becomes DELETED"""

        log.info("Testing if server becomes DELETED")

        self._insist_on_status_transition(
            "ACTIVE", "DELETED", self.action_timeout, self.action_timeout)

    def test_019_server_no_longer_in_server_list(self):
        """Test server is no longer in server list"""

        log.info("Test if server is no longer listed")

        servers = self.cyclades_client.list_servers()
        self.assertNotIn(self.serverid, [s["id"] for s in servers])


class NetworkTestCase(unittest.TestCase):
    """ Testing networking in cyclades """

    @classmethod
    def setUpClass(cls):
        "Initialize kamaki, get list of current networks"

        cls.astakos_client = AstakosClient(AUTH_URL, TOKEN)
        # Cyclades Client
        compute_url = \
            cls.astakos_client.get_service_endpoints('compute')['publicURL']
        cls.cyclades_client = CycladesClient(compute_url, TOKEN)

        cls.servername = "%s%s for %s" % (SNF_TEST_PREFIX,
                                          TEST_RUN_ID,
                                          cls.imagename)

        #Dictionary initialization for the vms credentials
        cls.serverid = dict()
        cls.username = dict()
        cls.password = dict()
        cls.is_windows = cls.imagename.lower().find("windows") >= 0

        cls.result_dict = dict()

    def _skipIf(self, condition, msg):
        if condition:
            self.skipTest(msg)

    def _get_ipv4(self, server):
        """Get the public IPv4 of a server from the detailed server info"""

        nics = server["attachments"]

        for nic in nics:
            net_id = nic["network_id"]
            if self.cyclades_client.get_network_details(net_id)["public"]:
                public_addrs = nic["ipv4"]

        self.assertTrue(public_addrs is not None)

        return public_addrs

    def _connect_loginname(self, os_value):
        """Return the login name for connections based on the server OS"""
        if os_value in ("Ubuntu", "Kubuntu", "Fedora"):
            return "user"
        elif os_value in ("windows", "windows_alpha1"):
            return "Administrator"
        else:
            return "root"

    def _ping_once(self, ip):

        """Test server responds to a single IPv4 or IPv6 ping"""
        cmd = "ping -c 2 -w 3 %s" % (ip)
        ping = subprocess.Popen(cmd, shell=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdout, stderr) = ping.communicate()
        ret = ping.wait()

        return (ret == 0)

    def test_00001a_submit_create_server_A(self):
        """Test submit create server request"""

        log.info("Creating test server A")

        serverA = self.cyclades_client.create_server(
            self.servername, self.flavorid, self.imageid, personality=None)

        self.assertEqual(serverA["name"], self.servername)
        self.assertEqual(serverA["flavor"], self.flavorid)
        self.assertEqual(serverA["image"], self.imageid)
        self.assertEqual(serverA["status"], "BUILD")

        # Update class attributes to reflect data on building server
        self.serverid['A'] = serverA["id"]
        self.username['A'] = None
        self.password['A'] = serverA["adminPass"]

        log.info("Server A id:" + str(serverA["id"]))
        log.info("Server password " + (self.password['A']))

        self.result_dict["Server A ID"] = str(serverA["id"])
        self.result_dict["Server A password"] = serverA["adminPass"]

    def test_00001b_serverA_becomes_active(self):
        """Test server becomes ACTIVE"""

        log.info("Waiting until test server A becomes ACTIVE")
        self.result_dict.clear()

        fail_tmout = time.time() + self.action_timeout
        while True:
            d = self.cyclades_client.get_server_details(self.serverid['A'])
            status = d['status']
            if status == 'ACTIVE':
                active = True
                break
            elif time.time() > fail_tmout:
                self.assertLess(time.time(), fail_tmout)
            else:
                time.sleep(self.query_interval)

        self.assertTrue(active)

    def test_00002a_submit_create_server_B(self):
        """Test submit create server request"""

        log.info("Creating test server B")

        serverB = self.cyclades_client.create_server(
            self.servername, self.flavorid, self.imageid, personality=None)

        self.assertEqual(serverB["name"], self.servername)
        self.assertEqual(serverB["flavor"], self.flavorid)
        self.assertEqual(serverB["image"], self.imageid)
        self.assertEqual(serverB["status"], "BUILD")

        # Update class attributes to reflect data on building server
        self.serverid['B'] = serverB["id"]
        self.username['B'] = None
        self.password['B'] = serverB["adminPass"]

        log.info("Server B id: " + str(serverB["id"]))
        log.info("Password " + (self.password['B']))

        self.result_dict.clear()
        self.result_dict["Server B ID"] = str(serverB["id"])
        self.result_dict["Server B password"] = serverB["adminPass"]

    def test_00002b_serverB_becomes_active(self):
        """Test server becomes ACTIVE"""

        log.info("Waiting until test server B becomes ACTIVE")
        self.result_dict.clear()

        fail_tmout = time.time() + self.action_timeout
        while True:
            d = self.cyclades_client.get_server_details(self.serverid['B'])
            status = d['status']
            if status == 'ACTIVE':
                active = True
                break
            elif time.time() > fail_tmout:
                self.assertLess(time.time(), fail_tmout)
            else:
                time.sleep(self.query_interval)

        self.assertTrue(active)

    def test_001_create_network(self):
        """Test submit create network request"""

        log.info("Submit new network request")
        self.result_dict.clear()

        name = SNF_TEST_PREFIX + TEST_RUN_ID
        #previous_num = len(self.client.list_networks())
        network = self.cyclades_client.create_network(
            name, cidr='10.0.1.0/28', dhcp=True)

        #Test if right name is assigned
        self.assertEqual(network['name'], name)

        # Update class attributes
        cls = type(self)
        cls.networkid = network['id']
        #networks = self.client.list_networks()

        fail_tmout = time.time() + self.action_timeout

        #Test if new network is created
        while True:
            d = self.cyclades_client.get_network_details(network['id'])
            if d['status'] == 'ACTIVE':
                connected = True
                break
            elif time.time() > fail_tmout:
                self.assertLess(time.time(), fail_tmout)
            else:
                log.info("Waiting for network to become ACTIVE")
                time.sleep(self.query_interval)

        self.assertTrue(connected)

        self.result_dict["Private network ID"] = str(network['id'])

    def test_002_connect_to_network(self):
        """Test connect VMs to network"""

        log.info("Connect VMs to private network")
        self.result_dict.clear()

        self.cyclades_client.connect_server(self.serverid['A'], self.networkid)
        self.cyclades_client.connect_server(self.serverid['B'], self.networkid)

        #Insist on connecting until action timeout
        fail_tmout = time.time() + self.action_timeout

        while True:

            netsA = [x['network_id']
                     for x in self.cyclades_client.get_server_details(
                         self.serverid['A'])['attachments']]
            netsB = [x['network_id']
                     for x in self.cyclades_client.get_server_details(
                         self.serverid['B'])['attachments']]

            if (self.networkid in netsA) and (self.networkid in netsB):
                conn_exists = True
                break
            elif time.time() > fail_tmout:
                self.assertLess(time.time(), fail_tmout)
            else:
                time.sleep(self.query_interval)

        #Adding private IPs to class attributes
        cls = type(self)
        cls.priv_ip = dict()

        nicsA = self.cyclades_client.get_server_details(
            self.serverid['A'])['attachments']
        nicsB = self.cyclades_client.get_server_details(
            self.serverid['B'])['attachments']

        if conn_exists:
            for nic in nicsA:
                if nic["network_id"] == self.networkid:
                    cls.priv_ip["A"] = nic["ipv4"]
            self.result_dict["Server A private IP"] = str(cls.priv_ip["A"])

            for nic in nicsB:
                if nic["network_id"] == self.networkid:
                    cls.priv_ip["B"] = nic["ipv4"]
            self.result_dict["Server B private IP"] = str(cls.priv_ip["B"])

        self.assertTrue(conn_exists)
        self.assertIsNot(cls.priv_ip["A"], None)
        self.assertIsNot(cls.priv_ip["B"], None)

    def test_002a_reboot(self):
        """Rebooting server A"""

        log.info("Rebooting server A")

        self.cyclades_client.shutdown_server(self.serverid['A'])

        fail_tmout = time.time() + self.action_timeout
        while True:
            d = self.cyclades_client.get_server_details(self.serverid['A'])
            status = d['status']
            if status == 'STOPPED':
                break
            elif time.time() > fail_tmout:
                self.assertLess(time.time(), fail_tmout)
            else:
                time.sleep(self.query_interval)

        self.cyclades_client.start_server(self.serverid['A'])

        while True:
            d = self.cyclades_client.get_server_details(self.serverid['A'])
            status = d['status']
            if status == 'ACTIVE':
                active = True
                break
            elif time.time() > fail_tmout:
                self.assertLess(time.time(), fail_tmout)
            else:
                time.sleep(self.query_interval)

        self.assertTrue(active)

    def test_002b_ping_server_A(self):
        "Test if server A responds to IPv4 pings"

        log.info("Testing if server A responds to IPv4 pings ")
        self.result_dict.clear()

        server = self.cyclades_client.get_server_details(self.serverid['A'])
        ip = self._get_ipv4(server)

        fail_tmout = time.time() + self.action_timeout

        s = False

        self.result_dict["Server A public IP"] = str(ip)

        while True:

            if self._ping_once(ip):
                s = True
                break

            elif time.time() > fail_tmout:
                self.assertLess(time.time(), fail_tmout)

            else:
                time.sleep(self.query_interval)

        self.assertTrue(s)

    def test_002c_reboot(self):
        """Reboot server B"""

        log.info("Rebooting server B")
        self.result_dict.clear()

        self.cyclades_client.shutdown_server(self.serverid['B'])

        fail_tmout = time.time() + self.action_timeout
        while True:
            d = self.cyclades_client.get_server_details(self.serverid['B'])
            status = d['status']
            if status == 'STOPPED':
                break
            elif time.time() > fail_tmout:
                self.assertLess(time.time(), fail_tmout)
            else:
                time.sleep(self.query_interval)

        self.cyclades_client.start_server(self.serverid['B'])

        while True:
            d = self.cyclades_client.get_server_details(self.serverid['B'])
            status = d['status']
            if status == 'ACTIVE':
                active = True
                break
            elif time.time() > fail_tmout:
                self.assertLess(time.time(), fail_tmout)
            else:
                time.sleep(self.query_interval)

        self.assertTrue(active)

    def test_002d_ping_server_B(self):
        """Test if server B responds to IPv4 pings"""

        log.info("Testing if server B responds to IPv4 pings")
        self.result_dict.clear()

        server = self.cyclades_client.get_server_details(self.serverid['B'])
        ip = self._get_ipv4(server)

        fail_tmout = time.time() + self.action_timeout

        s = False

        self.result_dict["Server B public IP"] = str(ip)

        while True:
            if self._ping_once(ip):
                s = True
                break

            elif time.time() > fail_tmout:
                self.assertLess(time.time(), fail_tmout)

            else:
                time.sleep(self.query_interval)

        self.assertTrue(s)

    def test_003a_setup_interface_A(self):
        """Setup eth1 for server A"""

        self._skipIf(self.is_windows, "only valid for Linux servers")

        log.info("Setting up interface eth1 for server A")
        self.result_dict.clear()

        server = self.cyclades_client.get_server_details(self.serverid['A'])
        image = self.cyclades_client.get_image_details(self.imageid)
        os_value = image['metadata']['os']

        users = image["metadata"].get("users", None)
        userlist = users.split()

        if "root" in userlist:
            loginname = "root"
        elif users is None:
            loginname = self._connect_loginname(os_value)
        else:
            loginname = choice(userlist)

        hostip = self._get_ipv4(server)
        myPass = self.password['A']

        log.info("SSH in server A as %s/%s" % (loginname, myPass))
        command = "ifconfig eth1 %s && ifconfig eth1 | " \
                  "grep 'inet addr:' | cut -d: -f2 | awk '{ print $1}'" \
                  % self.priv_ip["A"]
        output, status = _ssh_execute(
            hostip, loginname, myPass, command)

        self.assertEquals(status, 0)
        self.assertEquals(output[0].strip(), self.priv_ip["A"])

    def test_003b_setup_interface_B(self):
        """Setup eth1 for server B"""

        self._skipIf(self.is_windows, "only valid for Linux servers")

        log.info("Setting up interface eth1 for server B")

        server = self.cyclades_client.get_server_details(self.serverid['B'])
        image = self.cyclades_client.get_image_details(self.imageid)
        os_value = image['metadata']['os']

        users = image["metadata"].get("users", None)
        userlist = users.split()

        if "root" in userlist:
            loginname = "root"
        elif users is None:
            loginname = self._connect_loginname(os_value)
        else:
            loginname = choice(userlist)

        hostip = self._get_ipv4(server)
        myPass = self.password['B']

        log.info("SSH in server B as %s/%s" % (loginname, myPass))
        command = "ifconfig eth1 %s && ifconfig eth1 | " \
                  "grep 'inet addr:' | cut -d: -f2 | awk '{ print $1}'" \
                  % self.priv_ip["B"]
        output, status = _ssh_execute(
            hostip, loginname, myPass, command)

        self.assertEquals(status, 0)
        self.assertEquals(output[0].strip(), self.priv_ip["B"])

    def test_003c_test_connection_exists(self):
        """Ping server B from server A to test if connection exists"""

        self._skipIf(self.is_windows, "only valid for Linux servers")

        log.info("Testing if server A is actually connected to server B")

        server = self.cyclades_client.get_server_details(self.serverid['A'])
        image = self.cyclades_client.get_image_details(self.imageid)
        os_value = image['metadata']['os']
        hostip = self._get_ipv4(server)

        users = image["metadata"].get("users", None)
        userlist = users.split()

        if "root" in userlist:
            loginname = "root"
        elif users is None:
            loginname = self._connect_loginname(os_value)
        else:
            loginname = choice(userlist)

        myPass = self.password['A']

        cmd = "if ping -c 2 -w 3 %s >/dev/null; \
               then echo \'True\'; fi;" % self.priv_ip["B"]
        lines, status = _ssh_execute(
            hostip, loginname, myPass, cmd)

        exists = False

        if 'True\n' in lines:
            exists = True

        self.assertTrue(exists)

    def test_004_disconnect_from_network(self):
        "Disconnecting server A and B from network"

        log.info("Disconnecting servers from private network")

        prev_state = self.cyclades_client.get_network_details(self.networkid)
        prev_nics = prev_state['attachments']
        #prev_conn = len(prev_nics)

        nicsA = [x['id']
                 for x in self.cyclades_client.get_server_details(
                     self.serverid['A'])['attachments']]
        nicsB = [x['id']
                 for x in self.cyclades_client.get_server_details(
                     self.serverid['B'])['attachments']]

        for nic in prev_nics:
            if nic in nicsA:
                self.cyclades_client.disconnect_server(self.serverid['A'], nic)
            if nic in nicsB:
                self.cyclades_client.disconnect_server(self.serverid['B'], nic)

        #Insist on deleting until action timeout
        fail_tmout = time.time() + self.action_timeout

        while True:
            netsA = [x['network_id']
                     for x in self.cyclades_client.get_server_details(
                         self.serverid['A'])['attachments']]
            netsB = [x['network_id']
                     for x in self.cyclades_client.get_server_details(
                         self.serverid['B'])['attachments']]

            #connected = (self.client.get_network_details(self.networkid))
            #connections = connected['attachments']
            if (self.networkid not in netsA) and (self.networkid not in netsB):
                conn_exists = False
                break
            elif time.time() > fail_tmout:
                self.assertLess(time.time(), fail_tmout)
            else:
                time.sleep(self.query_interval)

        self.assertFalse(conn_exists)

    def test_005_destroy_network(self):
        """Test submit delete network request"""

        log.info("Submitting delete network request")

        self.cyclades_client.delete_network(self.networkid)

        fail_tmout = time.time() + self.action_timeout

        while True:

            curr_net = []
            networks = self.cyclades_client.list_networks()

            for net in networks:
                curr_net.append(net['id'])

            if self.networkid not in curr_net:
                self.assertTrue(self.networkid not in curr_net)
                break

            elif time.time() > fail_tmout:
                self.assertLess(time.time(), fail_tmout)

            else:
                time.sleep(self.query_interval)

    def test_006_cleanup_servers(self):
        """Cleanup servers created for this test"""

        log.info("Delete servers created for this test")

        self.cyclades_client.delete_server(self.serverid['A'])
        self.cyclades_client.delete_server(self.serverid['B'])

        fail_tmout = time.time() + self.action_timeout

        #Ensure server gets deleted
        status = dict()

        while True:
            details = \
                self.cyclades_client.get_server_details(self.serverid['A'])
            status['A'] = details['status']
            details = \
                self.cyclades_client.get_server_details(self.serverid['B'])
            status['B'] = details['status']
            if (status['A'] == 'DELETED') and (status['B'] == 'DELETED'):
                deleted = True
                break
            elif time.time() > fail_tmout:
                self.assertLess(time.time(), fail_tmout)
            else:
                time.sleep(self.query_interval)

        self.assertTrue(deleted)


class TestRunnerProcess(Process):
    """A distinct process used to execute part of the tests in parallel"""
    def __init__(self, **kw):
        Process.__init__(self, **kw)
        kwargs = kw["kwargs"]
        self.testq = kwargs["testq"]
        self.worker_folder = kwargs["worker_folder"]

    def run(self):
        # Make sure this test runner process dies with the parent
        # and is not left behind.
        #
        # WARNING: This uses the prctl(2) call and is
        # Linux-specific.

        prctl.set_pdeathsig(signal.SIGHUP)

        multi = logging.getLogger("multiprocess")

        while True:
            multi.debug("I am process %d, GETting from queue is %s" %
                        (os.getpid(), self.testq))
            msg = self.testq.get()

            multi.debug("Dequeued msg: %s" % msg)

            if msg == "TEST_RUNNER_TERMINATE":
                raise SystemExit

            elif issubclass(msg, unittest.TestCase):
                # Assemble a TestSuite, and run it

                log_file = os.path.join(self.worker_folder, 'details_' +
                                        (msg.__name__) + "_" +
                                        TEST_RUN_ID + '.log')

                fail_file = os.path.join(self.worker_folder, 'failed_' +
                                         (msg.__name__) + "_" +
                                         TEST_RUN_ID + '.log')
                error_file = os.path.join(self.worker_folder, 'error_' +
                                          (msg.__name__) + "_" +
                                          TEST_RUN_ID + '.log')

                f = open(log_file, 'w')
                fail = open(fail_file, 'w')
                error = open(error_file, 'w')

                log.info(yellow + '* Starting testcase: %s' % msg + normal)

                runner = unittest.TextTestRunner(
                    f, verbosity=2, failfast=True,
                    resultclass=BurninTestResult)
                suite = unittest.TestLoader().loadTestsFromTestCase(msg)
                result = runner.run(suite)

                for res in result.errors:
                    log.error("snf-burnin encountered an error in "
                              "testcase: %s" % msg)
                    log.error("See log for details")
                    error.write(str(res[0]) + '\n')
                    error.write(str(res[0].shortDescription()) + '\n')
                    error.write('\n')

                for res in result.failures:
                    log.error("snf-burnin failed in testcase: %s" % msg)
                    log.error("See log for details")
                    fail.write(str(res[0]) + '\n')
                    fail.write(str(res[0].shortDescription()) + '\n')
                    fail.write('\n')
                    if not NOFAILFAST:
                        sys.exit()

                if (len(result.failures) == 0) and (len(result.errors) == 0):
                    log.debug("Passed testcase: %s" % msg)

                f.close()
                fail.close()
                error.close()

            else:
                raise Exception("Cannot handle msg: %s" % msg)


def _run_cases_in_series(cases, image_folder):
    """Run instances of TestCase in series"""

    for case in cases:

        test = case.__name__

        log.info(yellow + '* Starting testcase: %s' % test + normal)
        log_file = os.path.join(image_folder, 'details_' +
                                (case.__name__) + "_" +
                                TEST_RUN_ID + '.log')
        fail_file = os.path.join(image_folder, 'failed_' +
                                 (case.__name__) + "_" +
                                 TEST_RUN_ID + '.log')
        error_file = os.path.join(image_folder, 'error_' +
                                  (case.__name__) + "_" +
                                  TEST_RUN_ID + '.log')

        f = open(log_file, "w")
        fail = open(fail_file, "w")
        error = open(error_file, "w")

        suite = unittest.TestLoader().loadTestsFromTestCase(case)
        runner = unittest.TextTestRunner(
            f, verbosity=2, failfast=True,
            resultclass=BurninTestResult)
        result = runner.run(suite)

        for res in result.errors:
            log.error("snf-burnin encountered an error in "
                      "testcase: %s" % test)
            log.error("See log for details")
            error.write(str(res[0]) + '\n')
            error.write(str(res[0].shortDescription()) + '\n')
            error.write('\n')

        for res in result.failures:
            log.error("snf-burnin failed in testcase: %s" % test)
            log.error("See log for details")
            fail.write(str(res[0]) + '\n')
            fail.write(str(res[0].shortDescription()) + '\n')
            fail.write('\n')
            if not NOFAILFAST:
                sys.exit()

        if (len(result.failures) == 0) and (len(result.errors) == 0):
            log.debug("Passed testcase: %s" % test)


def _run_cases_in_parallel(cases, fanout, image_folder):
    """Run instances of TestCase in parallel, in a number of distinct processes

    The cases iterable specifies the TestCases to be executed in parallel,
    by test runners running in distinct processes.
    The fanout parameter specifies the number of processes to spawn,
    and defaults to 1.
    The runner argument specifies the test runner class to use inside each
    runner process.

    """

    multi = logging.getLogger("multiprocess")
    handler = logging.StreamHandler()
    multi.addHandler(handler)

    if VERBOSE:
        multi.setLevel(logging.DEBUG)
    else:
        multi.setLevel(logging.INFO)

    testq = []
    worker_folder = []
    runners = []

    for i in xrange(0, fanout):
        testq.append(Queue())
        worker_folder.append(os.path.join(image_folder, 'process'+str(i)))
        os.mkdir(worker_folder[i])

    for i in xrange(0, fanout):
        kwargs = dict(testq=testq[i], worker_folder=worker_folder[i])
        runners.append(TestRunnerProcess(kwargs=kwargs))

    multi.debug("Spawning %d test runner processes" % len(runners))

    for p in runners:
        p.start()

    # Enqueue test cases
    for i in xrange(0, fanout):
        map(testq[i].put, cases)
        testq[i].put("TEST_RUNNER_TERMINATE")

    multi.debug("Spawned %d test runners, PIDs are %s" %
                (len(runners), [p.pid for p in runners]))

    multi.debug("Joining %d processes" % len(runners))

    for p in runners:
        p.join()

    multi.debug("Done joining %d processes" % len(runners))


def _images_test_case(**kwargs):
    """Construct a new unit test case class from ImagesTestCase"""
    name = "ImagesTestCase_%s" % kwargs["imageid"]
    cls = type(name, (ImagesTestCase,), kwargs)

    #Patch extra parameters into test names by manipulating method docstrings
    for (mname, m) in \
            inspect.getmembers(cls, lambda x: inspect.ismethod(x)):
        if hasattr(m, __doc__):
            m.__func__.__doc__ = "[%s] %s" % (cls.imagename, m.__doc__)

    # Make sure the class can be pickled, by listing it among
    # the attributes of __main__. A PicklingError is raised otherwise.
    thismodule = sys.modules[__name__]
    setattr(thismodule, name, cls)
    return cls


def _spawn_server_test_case(**kwargs):
    """Construct a new unit test case class from SpawnServerTestCase"""

    name = "SpawnServerTestCase_%s" % kwargs["imageid"]
    cls = type(name, (SpawnServerTestCase,), kwargs)

    # Patch extra parameters into test names by manipulating method docstrings
    for (mname, m) in \
            inspect.getmembers(cls, lambda x: inspect.ismethod(x)):
        if hasattr(m, __doc__):
            m.__func__.__doc__ = "[%s] %s" % (cls.imagename, m.__doc__)

    # Make sure the class can be pickled, by listing it among
    # the attributes of __main__. A PicklingError is raised otherwise.

    thismodule = sys.modules[__name__]
    setattr(thismodule, name, cls)
    return cls


def _spawn_network_test_case(**kwargs):
    """Construct a new unit test case class from NetworkTestCase"""

    name = "NetworkTestCase" + TEST_RUN_ID
    cls = type(name, (NetworkTestCase,), kwargs)

    # Make sure the class can be pickled, by listing it among
    # the attributes of __main__. A PicklingError is raised otherwise.

    thismodule = sys.modules[__name__]
    setattr(thismodule, name, cls)
    return cls


# --------------------------------------------------------------------
# Clean up servers/networks functions
def cleanup_servers(timeout, query_interval, delete_stale=False):

    astakos_client = AstakosClient(AUTH_URL, TOKEN)
    # Compute Client
    compute_url = astakos_client.get_service_endpoints('compute')['publicURL']
    compute_client = ComputeClient(compute_url, TOKEN)

    servers = compute_client.list_servers()
    stale = [s for s in servers if s["name"].startswith(SNF_TEST_PREFIX)]

    if len(stale) == 0:
        return

    # Show staled servers
    print >>sys.stderr, yellow + \
        "Found these stale servers from previous runs:" + \
        normal
    print >>sys.stderr, "    " + \
        "\n    ".join(["%d: %s" % (s["id"], s["name"]) for s in stale])

    # Delete staled servers
    if delete_stale:
        print >> sys.stderr, "Deleting %d stale servers:" % len(stale)
        fail_tmout = time.time() + timeout
        for s in stale:
            compute_client.delete_server(s["id"])
        # Wait for all servers to be deleted
        while True:
            servers = compute_client.list_servers()
            stale = [s for s in servers
                     if s["name"].startswith(SNF_TEST_PREFIX)]
            if len(stale) == 0:
                print >> sys.stderr, green + "    ...done" + normal
                break
            elif time.time() > fail_tmout:
                print >> sys.stderr, red + \
                    "Not all stale servers deleted. Action timed out." + \
                    normal
                sys.exit(1)
            else:
                time.sleep(query_interval)
    else:
        print >> sys.stderr, "Use --delete-stale to delete them."


def cleanup_networks(action_timeout, query_interval, delete_stale=False):

    astakos_client = AstakosClient(AUTH_URL, TOKEN)
    # Cyclades Client
    compute_url = astakos_client.get_service_endpoints('compute')['publicURL']
    cyclades_client = CycladesClient(compute_url, TOKEN)

    networks = cyclades_client.list_networks()
    stale = [n for n in networks if n["name"].startswith(SNF_TEST_PREFIX)]

    if len(stale) == 0:
        return

    # Show staled networks
    print >> sys.stderr, yellow + \
        "Found these stale networks from previous runs:" + \
        normal
    print "    " + \
        "\n    ".join(["%s: %s" % (str(n["id"]), n["name"]) for n in stale])

    # Delete staled networks
    if delete_stale:
        print >> sys.stderr, "Deleting %d stale networks:" % len(stale)
        fail_tmout = time.time() + action_timeout
        for n in stale:
            cyclades_client.delete_network(n["id"])
        # Wait for all networks to be deleted
        while True:
            networks = cyclades_client.list_networks()
            stale = [n for n in networks
                     if n["name"].startswith(SNF_TEST_PREFIX)]
            if len(stale) == 0:
                print >> sys.stderr, green + "    ...done" + normal
                break
            elif time.time() > fail_tmout:
                print >> sys.stderr, red + \
                    "Not all stale networks deleted. Action timed out." + \
                    normal
                sys.exit(1)
            else:
                time.sleep(query_interval)
    else:
        print >> sys.stderr, "Use --delete-stale to delete them."


# --------------------------------------------------------------------
# Parse arguments functions
def parse_comma(option, opt, value, parser):
    tests = set(['all', 'auth', 'images', 'flavors',
                 'pithos', 'servers', 'server_spawn',
                 'network_spawn'])
    parse_input = value.split(',')

    if not (set(parse_input)).issubset(tests):
        raise OptionValueError("The selected set of tests is invalid")

    setattr(parser.values, option.dest, value.split(','))


def parse_arguments(args):

    kw = {}
    kw["usage"] = "%prog [options]"
    kw["description"] = \
        "%prog runs a number of test scenarios on a " \
        "Synnefo deployment."

    parser = OptionParser(**kw)
    parser.disable_interspersed_args()

    parser.add_option("--auth-url",
                      action="store", type="string", dest="auth_url",
                      help="The AUTH URI to use to reach the Synnefo API",
                      default=None)
    parser.add_option("--plankton-user",
                      action="store", type="string", dest="plankton_user",
                      help="Owner of system images",
                      default=DEFAULT_PLANKTON_USER)
    parser.add_option("--token",
                      action="store", type="string", dest="token",
                      help="The token to use for authentication to the API")
    parser.add_option("--nofailfast",
                      action="store_true", dest="nofailfast",
                      help="Do not fail immediately if one of the tests "
                           "fails (EXPERIMENTAL)",
                      default=False)
    parser.add_option("--no-ipv6",
                      action="store_true", dest="no_ipv6",
                      help="Disables ipv6 related tests",
                      default=False)
    parser.add_option("--action-timeout",
                      action="store", type="int", dest="action_timeout",
                      metavar="TIMEOUT",
                      help="Wait SECONDS seconds for a server action to "
                           "complete, then the test is considered failed",
                      default=100)
    parser.add_option("--build-warning",
                      action="store", type="int", dest="build_warning",
                      metavar="TIMEOUT",
                      help="Warn if TIMEOUT seconds have passed and a "
                           "build operation is still pending",
                      default=600)
    parser.add_option("--build-fail",
                      action="store", type="int", dest="build_fail",
                      metavar="BUILD_TIMEOUT",
                      help="Fail the test if TIMEOUT seconds have passed "
                           "and a build operation is still incomplete",
                      default=900)
    parser.add_option("--query-interval",
                      action="store", type="int", dest="query_interval",
                      metavar="INTERVAL",
                      help="Query server status when requests are pending "
                           "every INTERVAL seconds",
                      default=3)
    parser.add_option("--fanout",
                      action="store", type="int", dest="fanout",
                      metavar="COUNT",
                      help="Spawn up to COUNT child processes to execute "
                           "in parallel, essentially have up to COUNT "
                           "server build requests outstanding (EXPERIMENTAL)",
                      default=1)
    parser.add_option("--force-flavor",
                      action="store", type="int", dest="force_flavorid",
                      metavar="FLAVOR ID",
                      help="Force all server creations to use the specified "
                           "FLAVOR ID instead of a randomly chosen one, "
                           "useful if disk space is scarce",
                      default=None)
    parser.add_option("--image-id",
                      action="store", type="string", dest="force_imageid",
                      metavar="IMAGE ID",
                      help="Test the specified image id, use 'all' to test "
                           "all available images (mandatory argument)",
                      default=None)
    parser.add_option("--show-stale",
                      action="store_true", dest="show_stale",
                      help="Show stale servers from previous runs, whose "
                           "name starts with `%s'" % SNF_TEST_PREFIX,
                      default=False)
    parser.add_option("--delete-stale",
                      action="store_true", dest="delete_stale",
                      help="Delete stale servers from previous runs, whose "
                           "name starts with `%s'" % SNF_TEST_PREFIX,
                      default=False)
    parser.add_option("--force-personality",
                      action="store", type="string", dest="personality_path",
                      help="Force a personality file injection.\
                            File path required. ",
                      default=None)
    parser.add_option("--log-folder",
                      action="store", type="string", dest="log_folder",
                      help="Define the absolute path where the output \
                            log is stored. ",
                      default="/var/log/burnin/")
    parser.add_option("--verbose", "-V",
                      action="store_true", dest="verbose",
                      help="Print detailed output about multiple "
                           "processes spawning",
                      default=False)
    parser.add_option("--set-tests",
                      action="callback",
                      dest="tests",
                      type="string",
                      help='Set comma seperated tests for this run. \
                            Available tests: auth, images, flavors, \
                                             servers, server_spawn, \
                                             network_spawn, pithos. \
                            Default = all',
                      default='all',
                      callback=parse_comma)

    (opts, args) = parser.parse_args(args)

    # -----------------------
    # Verify arguments

    # `delete_stale' implies `show_stale'
    if opts.delete_stale:
        opts.show_stale = True

    # `token' is mandatory
    _mandatory_argument(opts.token, "--token")
    # `auth_url' is mandatory
    _mandatory_argument(opts.auth_url, "--auth-url")

    if not opts.show_stale:
        # `image-id' is mandatory
        _mandatory_argument(opts.force_imageid, "--image_id")
        if opts.force_imageid != 'all':
            try:
                opts.force_imageid = str(opts.force_imageid)
            except ValueError:
                print >>sys.stderr, red + \
                    "Invalid value specified for" + \
                    "--image-id. Use a valid id, or `all'." + \
                    normal
                sys.exit(1)

    return (opts, args)


def _mandatory_argument(Arg, Str):
    if (Arg is None) or (Arg == ""):
        print >>sys.stderr, red + \
            "The " + Str + " argument is mandatory.\n" + \
            normal
        sys.exit(1)


# --------------------------------------------------------------------
# Burnin main function
def main():
    """Assemble test cases into a test suite, and run it

    IMPORTANT: Tests have dependencies and have to be run in the specified
    order inside a single test case. They communicate through attributes of the
    corresponding TestCase class (shared fixtures). Distinct subclasses of
    TestCase MAY SHARE NO DATA, since they are run in parallel, in distinct
    test runner processes.

    """

    # Parse arguments using `optparse'
    (opts, args) = parse_arguments(sys.argv[1:])

    # Some global variables
    global AUTH_URL, TOKEN, PLANKTON_USER
    global NO_IPV6, VERBOSE, NOFAILFAST
    AUTH_URL = opts.auth_url
    TOKEN = opts.token
    PLANKTON_USER = opts.plankton_user
    NO_IPV6 = opts.no_ipv6
    VERBOSE = opts.verbose
    NOFAILFAST = opts.nofailfast

    # If `show_stale', cleanup stale servers
    # from previous runs and exit
    if opts.show_stale:
        # We must clean the servers first
        cleanup_servers(opts.action_timeout, opts.query_interval,
                        delete_stale=opts.delete_stale)
        cleanup_networks(opts.action_timeout, opts.query_interval,
                         delete_stale=opts.delete_stale)
        return 0

    # Initialize a kamaki instance, get flavors, images
    astakos_client = AstakosClient(AUTH_URL, TOKEN)
    # Compute Client
    compute_url = astakos_client.get_service_endpoints('compute')['publicURL']
    compute_client = ComputeClient(compute_url, TOKEN)
    DIMAGES = compute_client.list_images(detail=True)
    DFLAVORS = compute_client.list_flavors(detail=True)

    # FIXME: logging, log, LOG PID, TEST_RUN_ID, arguments
    # Run them: FIXME: In parallel, FAILEARLY, catchbreak?
    #unittest.main(verbosity=2, catchbreak=True)

    # Get a list of images we are going to test
    if opts.force_imageid == 'all':
        test_images = DIMAGES
    else:
        test_images = filter(lambda x: x["id"] == opts.force_imageid, DIMAGES)

    # Create output (logging) folder
    if not os.path.exists(opts.log_folder):
        os.mkdir(opts.log_folder)
    test_folder = os.path.join(opts.log_folder, TEST_RUN_ID)
    os.mkdir(test_folder)

    for image in test_images:
        imageid = str(image["id"])
        imagename = image["name"]
        # Choose a flavor (given from user or random)
        if opts.force_flavorid:
            flavorid = opts.force_flavorid
        else:
            flavorid = choice([f["id"] for f in DFLAVORS if f["disk"] >= 20])
        # Personality dictionary for file injection test
        if opts.personality_path is not None:
            f = open(opts.personality_path)
            content = b64encode(f.read())
            personality = []
            st = os.stat(opts.personality_path)
            personality.append({
                'path': '/root/test_inj_file',
                'owner': 'root',
                'group': 'root',
                'mode': 0x7777 & st.st_mode,
                'contents': content})
        else:
            personality = None
        # Give a name to our test servers
        servername = "%s%s for %s" % (SNF_TEST_PREFIX, TEST_RUN_ID, imagename)
        is_windows = imagename.lower().find("windows") >= 0

        # Create Server TestCases
        ServerTestCase = _spawn_server_test_case(
            imageid=imageid,
            flavorid=flavorid,
            imagename=imagename,
            personality=personality,
            servername=servername,
            is_windows=is_windows,
            action_timeout=opts.action_timeout,
            build_warning=opts.build_warning,
            build_fail=opts.build_fail,
            query_interval=opts.query_interval)
        # Create Network TestCases
        NetworkTestCase = _spawn_network_test_case(
            action_timeout=opts.action_timeout,
            imageid=imageid,
            flavorid=flavorid,
            imagename=imagename,
            query_interval=opts.query_interval)
        # Create Images TestCase
        CImagesTestCase = _images_test_case(
            action_timeout=opts.action_timeout,
            imageid=imageid,
            flavorid=flavorid,
            imagename=imagename,
            query_interval=opts.query_interval)

        # Choose the tests we are going to run
        test_dict = {'auth': UnauthorizedTestCase,
                     'images': CImagesTestCase,
                     'flavors': FlavorsTestCase,
                     'servers': ServersTestCase,
                     'pithos': PithosTestCase,
                     'server_spawn': ServerTestCase,
                     'network_spawn': NetworkTestCase}
        seq_cases = []
        if 'all' in opts.tests:
            seq_cases = [UnauthorizedTestCase, CImagesTestCase,
                         FlavorsTestCase, ServersTestCase,
                         PithosTestCase, ServerTestCase,
                         NetworkTestCase]
        else:
            for test in opts.tests:
                seq_cases.append(test_dict[test])

        # Folder for each image
        image_folder = os.path.join(test_folder, imageid)
        os.mkdir(image_folder)

        # Run each test
        if opts.fanout > 1:
            _run_cases_in_parallel(seq_cases, opts.fanout, image_folder)
        else:
            _run_cases_in_series(seq_cases, image_folder)


# --------------------------------------------------------------------
# Call main
if __name__ == "__main__":
    sys.exit(main())
