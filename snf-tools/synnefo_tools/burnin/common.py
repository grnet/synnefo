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
Common utils for burnin tests

"""

import os
import re
import time
import shutil
import socket
import random
import unittest
import datetime
import tempfile
import traceback
import subprocess

from kamaki.clients.cyclades import CycladesClient
from kamaki.clients.astakos import AstakosClient
from kamaki.clients.compute import ComputeClient
from kamaki.clients.pithos import PithosClient
from kamaki.clients.image import ImageClient

from synnefo_tools.burnin.logger import Log


# --------------------------------------------------------------------
# Global variables
logger = None  # Invalid constant name. pylint: disable-msg=C0103
SNF_TEST_PREFIX = "snf-test-"
CONNECTION_RETRY_LIMIT = 2
SYSTEM_USERS = ["images@okeanos.grnet.gr", "images@demo.synnefo.org"]


# --------------------------------------------------------------------
# BurninTestResult class
class BurninTestResult(unittest.TestResult):
    """Modify the TextTestResult class"""
    def __init__(self):
        super(BurninTestResult, self).__init__()

        # Test parameters
        self.failfast = True

    def startTest(self, test):  # noqa
        """Called when the test case test is about to be run"""
        super(BurninTestResult, self).startTest(test)
        logger.log(test.__class__.__name__, test.shortDescription())

    # Method could be a function. pylint: disable-msg=R0201
    def _test_failed(self, test, err):
        """Test failed"""
        # Get class name
        if test.__class__.__name__ == "_ErrorHolder":
            class_name = test.id().split('.')[-1].rstrip(')')
        else:
            class_name = test.__class__.__name__
        err_msg = str(test) + "... failed (%s)."
        timestamp = datetime.datetime.strftime(
            datetime.datetime.now(), "%a %b %d %Y %H:%M:%S")
        logger.error(class_name, err_msg, timestamp)
        (err_type, err_value, err_trace) = err
        trcback = traceback.format_exception(err_type, err_value, err_trace)
        logger.info(class_name, trcback)

    def addError(self, test, err):  # noqa
        """Called when the test case test raises an unexpected exception"""
        super(BurninTestResult, self).addError(test, err)
        self._test_failed(test, err)

    def addFailure(self, test, err):  # noqa
        """Called when the test case test signals a failure"""
        super(BurninTestResult, self).addFailure(test, err)
        self._test_failed(test, err)


# --------------------------------------------------------------------
# BurninTests class
# Too few public methods. pylint: disable-msg=R0903
# Too many instance attributes. pylint: disable-msg=R0902
class Clients(object):
    """Our kamaki clients"""
    auth_url = None
    token = None
    # Astakos
    astakos = None
    retry = CONNECTION_RETRY_LIMIT
    # Compute
    compute = None
    compute_url = None
    # Cyclades
    cyclades = None
    # Pithos
    pithos = None
    pithos_url = None
    # Image
    image = None
    image_url = None


# Too many public methods (45/20). pylint: disable-msg=R0904
class BurninTests(unittest.TestCase):
    """Common class that all burnin tests should implement"""
    clients = Clients()
    run_id = None
    use_ipv6 = None
    action_timeout = None
    action_warning = None
    query_interval = None
    system_user = None
    images = None
    flavors = None

    @classmethod
    def setUpClass(cls):  # noqa
        """Initialize BurninTests"""
        cls.suite_name = cls.__name__
        logger.testsuite_start(cls.suite_name)

        # Set test parameters
        cls.longMessage = True

    def test_000_clients_setup(self):
        """Initializing astakos/cyclades/pithos clients"""
        # Update class attributes
        self.info("Astakos auth url is %s", self.clients.auth_url)
        self.clients.astakos = AstakosClient(
            self.clients.auth_url, self.clients.token)
        self.clients.astakos.CONNECTION_RETRY_LIMIT = self.clients.retry

        self.clients.compute_url = \
            self.clients.astakos.get_service_endpoints('compute')['publicURL']
        self.info("Cyclades url is %s", self.clients.compute_url)
        self.clients.compute = ComputeClient(
            self.clients.compute_url, self.clients.token)
        self.clients.compute.CONNECTION_RETRY_LIMIT = self.clients.retry

        self.clients.cyclades = CycladesClient(
            self.clients.compute_url, self.clients.token)
        self.clients.cyclades.CONNECTION_RETRY_LIMIT = self.clients.retry

        self.clients.pithos_url = self.clients.astakos.\
            get_service_endpoints('object-store')['publicURL']
        self.info("Pithos url is %s", self.clients.pithos_url)
        self.clients.pithos = PithosClient(
            self.clients.pithos_url, self.clients.token)
        self.clients.pithos.CONNECTION_RETRY_LIMIT = self.clients.retry

        self.clients.image_url = \
            self.clients.astakos.get_service_endpoints('image')['publicURL']
        self.info("Image url is %s", self.clients.image_url)
        self.clients.image = ImageClient(
            self.clients.image_url, self.clients.token)
        self.clients.image.CONNECTION_RETRY_LIMIT = self.clients.retry

    # ----------------------------------
    # Loggers helper functions
    def log(self, msg, *args):
        """Pass the section value to logger"""
        logger.log(self.suite_name, msg, *args)

    def info(self, msg, *args):
        """Pass the section value to logger"""
        logger.info(self.suite_name, msg, *args)

    def debug(self, msg, *args):
        """Pass the section value to logger"""
        logger.debug(self.suite_name, msg, *args)

    def warning(self, msg, *args):
        """Pass the section value to logger"""
        logger.warning(self.suite_name, msg, *args)

    def error(self, msg, *args):
        """Pass the section value to logger"""
        logger.error(self.suite_name, msg, *args)

    # ----------------------------------
    # Helper functions that every testsuite may need
    def _get_uuid(self):
        """Get our uuid"""
        authenticate = self.clients.astakos.authenticate()
        uuid = authenticate['access']['user']['id']
        self.info("User's uuid is %s", uuid)
        return uuid

    def _get_username(self):
        """Get our User Name"""
        authenticate = self.clients.astakos.authenticate()
        username = authenticate['access']['user']['name']
        self.info("User's name is %s", username)
        return username

    def _create_tmp_directory(self):
        """Create a tmp directory

        In my machine /tmp has not enough space for an image
        to be saves, so we are going to use the current directory.

        """
        temp_dir = tempfile.mkdtemp(dir=os.getcwd())
        self.info("Temp directory %s created", temp_dir)
        return temp_dir

    def _remove_tmp_directory(self, tmp_dir):
        """Remove a tmp directory"""
        try:
            shutil.rmtree(tmp_dir)
            self.info("Temp directory %s deleted", tmp_dir)
        except OSError:
            pass

    def _get_uuid_of_system_user(self):
        """Get the uuid of the system user

        This is the user that upload the 'official' images.

        """
        self.info("Getting the uuid of the system user")
        system_users = None
        if self.system_user is not None:
            parsed_su = parse_typed_option(self.system_user)
            if parsed_su is None:
                msg = "Invalid system-user format: %s. Must be [id|name]:.+"
                self.warning(msg, self.system_user)
            else:
                su_type, su_value = parsed_su
                if su_type == "name":
                    system_users = [su_value]
                elif su_type == "id":
                    self.info("System user's uuid is %s", su_value)
                    return su_value
                else:
                    self.error("Unrecognized system-user type %s", su_type)
                    self.fail("Unrecognized system-user type")

        if system_users is None:
            system_users = SYSTEM_USERS

        uuids = self.clients.astakos.usernames2uuids(system_users)
        for su_name in system_users:
            self.info("Trying username %s", su_name)
            if su_name in uuids:
                self.info("System user's uuid is %s", uuids[su_name])
                return uuids[su_name]

        self.warning("No system user found")
        return None

    def _try_until_timeout_expires(self, opmsg, check_fun):
        """Try to perform an action until timeout expires"""
        assert callable(check_fun), "Not a function"

        action_timeout = self.action_timeout
        action_warning = self.action_warning
        if action_warning > action_timeout:
            action_warning = action_timeout

        start_time = time.time()
        while (start_time + action_warning) > time.time():
            try:
                return check_fun()
            except Retry:
                time.sleep(self.query_interval)
        self.warning("Operation `%s' is taking too long", opmsg)
        while (start_time + action_timeout) > time.time():
            try:
                return check_fun()
            except Retry:
                time.sleep(self.query_interval)
        self.error("Operation `%s' timed out", opmsg)
        self.fail("time out")

    def _skip_if(self, condition, msg):
        """Skip tests"""
        if condition:
            self.info("Test skipped: %s" % msg)
            self.skipTest(msg)

    # ----------------------------------
    # Flavors
    def _get_list_of_flavors(self, detail=False):
        """Get (detailed) list of flavors"""
        if detail:
            self.info("Getting detailed list of flavors")
        else:
            self.info("Getting simple list of flavors")
        flavors = self.clients.compute.list_flavors(detail=detail)
        return flavors

    def _find_flavors(self, patterns, flavors=None):
        """Find a list of suitable flavors to use

        The patterns is a list of `typed_options'. A list of all flavors
        matching this patterns will be returned.

        """
        if flavors is None:
            flavors = self._get_list_of_flavors(detail=True)

        ret_flavors = []
        for ptrn in patterns:
            parsed_ptrn = parse_typed_option(ptrn)
            if parsed_ptrn is None:
                msg = "Invalid flavor format: %s. Must be [id|name]:.+"
                self.warning(msg, ptrn)
                continue
            flv_type, flv_value = parsed_ptrn
            if flv_type == "name":
                # Filter flavor by name
                msg = "Trying to find a flavor with name %s"
                self.info(msg, flv_value)
                filtered_flvs = \
                    [f for f in flavors if
                     re.search(flv_value, f['name'], flags=re.I) is not None]
            elif flv_type == "id":
                # Filter flavors by id
                msg = "Trying to find a flavor with id %s"
                self.info(msg, flv_value)
                filtered_flvs = \
                    [f for f in flavors if str(f['id']) == flv_value]
            else:
                self.error("Unrecognized flavor type %s", flv_type)
                self.fail("Unrecognized flavor type")

            # Append and continue
            ret_flavors.extend(filtered_flvs)

        self.assertGreater(len(ret_flavors), 0,
                           "No matching flavors found")
        return ret_flavors

    # ----------------------------------
    # Images
    def _get_list_of_images(self, detail=False):
        """Get (detailed) list of images"""
        if detail:
            self.info("Getting detailed list of images")
        else:
            self.info("Getting simple list of images")
        images = self.clients.image.list_public(detail=detail)
        # Remove images registered by burnin
        images = [img for img in images
                  if not img['name'].startswith(SNF_TEST_PREFIX)]
        return images

    def _get_list_of_sys_images(self, images=None):
        """Get (detailed) list of images registered by system user or by me"""
        self.info("Getting list of images registered by system user or by me")
        if images is None:
            images = self._get_list_of_images(detail=True)

        su_uuid = self._get_uuid_of_system_user()
        my_uuid = self._get_uuid()
        ret_images = [i for i in images
                      if i['owner'] == su_uuid or i['owner'] == my_uuid]

        return ret_images

    def _find_images(self, patterns, images=None):
        """Find a list of suitable images to use

        The patterns is a list of `typed_options'. A list of all images
        matching this patterns will be returned.

        """
        if images is None:
            images = self._get_list_of_sys_images()

        ret_images = []
        for ptrn in patterns:
            parsed_ptrn = parse_typed_option(ptrn)
            if parsed_ptrn is None:
                msg = "Invalid image format: %s. Must be [id|name]:.+"
                self.warning(msg, ptrn)
                continue
            img_type, img_value = parsed_ptrn
            if img_type == "name":
                # Filter image by name
                msg = "Trying to find an image with name %s"
                self.info(msg, img_value)
                filtered_imgs = \
                    [i for i in images if
                     re.search(img_value, i['name'], flags=re.I) is not None]
            elif img_type == "id":
                # Filter images by id
                msg = "Trying to find an image with id %s"
                self.info(msg, img_value)
                filtered_imgs = \
                    [i for i in images if
                     i['id'].lower() == img_value.lower()]
            else:
                self.error("Unrecognized image type %s", img_type)
                self.fail("Unrecognized image type")

            # Append and continue
            ret_images.extend(filtered_imgs)

        self.assertGreater(len(ret_images), 0,
                           "No matching images found")
        return ret_images

    # ----------------------------------
    # Pithos
    def _set_pithos_account(self, account):
        """Set the Pithos account"""
        assert account, "No pithos account was given"

        self.info("Setting Pithos account to %s", account)
        self.clients.pithos.account = account

    def _set_pithos_container(self, container):
        """Set the Pithos container"""
        assert container, "No pithos container was given"

        self.info("Setting Pithos container to %s", container)
        self.clients.pithos.container = container

    def _get_list_of_containers(self, account=None):
        """Get list of containers"""
        if account is not None:
            self._set_pithos_account(account)
        self.info("Getting list of containers")
        return self.clients.pithos.list_containers()

    def _create_pithos_container(self, container):
        """Create a pithos container

        If the container exists, nothing will happen

        """
        assert container, "No pithos container was given"

        self.info("Creating pithos container %s", container)
        self.clients.pithos.container = container
        self.clients.pithos.container_put()

    # ----------------------------------
    # Servers
    def _get_list_of_servers(self, detail=False):
        """Get (detailed) list of servers"""
        if detail:
            self.info("Getting detailed list of servers")
        else:
            self.info("Getting simple list of servers")
        return self.clients.cyclades.list_servers(detail=detail)

    def _get_server_details(self, server):
        """Get details for a server"""
        self.info("Getting details for server %s with id %s",
                  server['name'], server['id'])
        return self.clients.cyclades.get_server_details(server['id'])

    def _create_server(self, name, image, flavor):
        """Create a new server"""
        self.info("Creating a server with name %s", name)
        self.info("Using image %s with id %s", image['name'], image['id'])
        self.info("Using flavor %s with id %s", flavor['name'], flavor['id'])
        server = self.clients.cyclades.create_server(
            name, flavor['id'], image['id'])

        self.info("Server id: %s", server['id'])
        self.info("Server password: %s", server['adminPass'])

        self.assertEqual(server['name'], name)
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

    def _insist_on_server_transition(self, server, curr_status, new_status):
        """Insist on server transiting from curr_status to new_status"""
        def check_fun():
            """Check server status"""
            srv = self.clients.cyclades.get_server_details(server['id'])
            if srv['status'] == curr_status:
                raise Retry()
            elif srv['status'] == new_status:
                return
            else:
                msg = "Server %s went to unexpected status %s"
                self.error(msg, server['name'], srv['status'])
                self.fail(msg % (server['name'], srv['status']))
        opmsg = "Waiting for server %s to transit from %s to %s"
        self.info(opmsg, server['name'], curr_status, new_status)
        opmsg = opmsg % (server['name'], curr_status, new_status)
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

    def _get_ip(self, server, version):
        """Get the public IP of a server from the detailed server info"""
        assert version in (4, 6)

        nics = server['attachments']
        public_addrs = None
        for nic in nics:
            net_id = nic['network_id']
            if self.clients.cyclades.get_network_details(net_id)['public']:
                public_addrs = nic['ipv' + str(version)]

        self.assertIsNotNone(public_addrs)
        msg = "Servers %s public IPv%s is %s"
        self.info(msg, server['name'], version, public_addrs)
        return public_addrs

    def _insist_on_ping(self, ip_addr, version):
        """Test server responds to a single IPv4 of IPv6 ping"""
        def check_fun():
            """Ping to server"""
            assert version in (4, 6)
            cmd = ("ping%s -c 3 -w 20 %s" %
                   ("6" if version == 6 else "", ip_addr))
            ping = subprocess.Popen(
                cmd, shell=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            ping.communicate()
            ret = ping.wait()
            if ret != 0:
                raise Retry
        opmsg = "Sent IPv%s ping requests to %s"
        self.info(opmsg, version, ip_addr)
        opmsg = opmsg % (version, ip_addr)
        self._try_until_timeout_expires(opmsg, check_fun)


# --------------------------------------------------------------------
# Initialize Burnin
def initialize(opts, testsuites):
    """Initalize burnin

    Initialize our logger and burnin state

    """
    # Initialize logger
    global logger  # Using global statement. pylint: disable-msg=C0103,W0603
    logger = Log(opts.log_folder, verbose=opts.verbose,
                 use_colors=opts.use_colors, in_parallel=False,
                 quiet=opts.quiet)

    # Initialize clients
    Clients.auth_url = opts.auth_url
    Clients.token = opts.token

    # Pass the rest options to BurninTests
    BurninTests.use_ipv6 = opts.use_ipv6
    BurninTests.action_timeout = opts.action_timeout
    BurninTests.action_warning = opts.action_warning
    BurninTests.query_interval = opts.query_interval
    BurninTests.system_user = opts.system_user
    BurninTests.flavors = opts.flavors
    BurninTests.images = opts.images
    BurninTests.run_id = SNF_TEST_PREFIX + \
        datetime.datetime.strftime(datetime.datetime.now(), "%Y%m%d%H%M%S")

    # Choose tests to run
    if opts.tests != "all":
        testsuites = opts.tests
    if opts.exclude_tests is not None:
        testsuites = [tsuite for tsuite in testsuites
                      if tsuite not in opts.exclude_tests]

    return testsuites


# --------------------------------------------------------------------
# Run Burnin
def run_burnin(testsuites, failfast=False, final_report=False):
    """Run burnin testsuites"""
    global logger  # Using global. pylint: disable-msg=C0103,W0603,W0602

    success = True
    for tcase in testsuites:
        was_success = run_test(tcase)
        success = success and was_success
        if failfast and not success:
            break

    # Are we going to print final report?
    if final_report:
        logger.print_logfile_to_stdout()
    # Clean up our logger
    del(logger)

    # Return
    return 0 if success else 1


def run_test(tcase):
    """Run a testcase"""
    tsuite = unittest.TestLoader().loadTestsFromTestCase(tcase)
    results = tsuite.run(BurninTestResult())

    return was_successful(tcase.__name__, results.wasSuccessful())


# --------------------------------------------------------------------
# Helper functions
def was_successful(tsuite, success):
    """Handle whether a testsuite was succesful or not"""
    if success:
        logger.testsuite_success(tsuite)
        return True
    else:
        logger.testsuite_failure(tsuite)
        return False


def parse_typed_option(value):
    """Parse typed options (flavors and images)

    The options are in the form 'id:123-345' or 'name:^Debian Base$'

    """
    try:
        [type_, val] = value.strip().split(':')
        if type_ not in ["id", "name"]:
            raise ValueError
        return type_, val
    except ValueError:
        return None


class Proper(object):
    """A descriptor used by tests implementing the TestCase class

    Since each instance of the TestCase will only be used to run a single
    test method (a new fixture is created for each test) the attributes can
    not be saved in the class instances. Instead we use descriptors.

    """
    def __init__(self, value=None):
        self.val = value

    def __get__(self, obj, objtype=None):
        return self.val

    def __set__(self, obj, value):
        self.val = value


class Retry(Exception):
    """Retry the action

    This is used by _try_unit_timeout_expires method.

    """
