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

import re
import shutil
import unittest
import datetime
import tempfile
import traceback

from kamaki.clients.cyclades import CycladesClient, CycladesNetworkClient
from kamaki.clients.astakos import AstakosClient, parse_endpoints
from kamaki.clients.compute import ComputeClient
from kamaki.clients.pithos import PithosClient
from kamaki.clients.image import ImageClient

from synnefo_tools.burnin.logger import Log


# --------------------------------------------------------------------
# Global variables
logger = None   # pylint: disable=invalid-name
success = None  # pylint: disable=invalid-name
SNF_TEST_PREFIX = "snf-test-"
CONNECTION_RETRY_LIMIT = 2
SYSTEM_USERS = ["images@okeanos.grnet.gr", "images@demo.synnefo.org"]
KB = 2**10
MB = 2**20
GB = 2**30


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

    # pylint: disable=no-self-use
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
# Helper Classes
# pylint: disable=too-few-public-methods
# pylint: disable=too-many-instance-attributes
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
    # Network
    network = None
    network_url = None
    # Pithos
    pithos = None
    pithos_url = None
    # Image
    image = None
    image_url = None

    def initialize_clients(self):
        """Initialize all the Kamaki Clients"""
        self.astakos = AstakosClient(self.auth_url, self.token)
        self.astakos.CONNECTION_RETRY_LIMIT = self.retry

        endpoints = self.astakos.authenticate()

        self.compute_url = _get_endpoint_url(endpoints, "compute")
        self.compute = ComputeClient(self.compute_url, self.token)
        self.compute.CONNECTION_RETRY_LIMIT = self.retry

        self.cyclades = CycladesClient(self.compute_url, self.token)
        self.cyclades.CONNECTION_RETRY_LIMIT = self.retry

        self.network_url = _get_endpoint_url(endpoints, "network")
        self.network = CycladesNetworkClient(self.network_url, self.token)
        self.network.CONNECTION_RETRY_LIMIT = self.retry

        self.pithos_url = _get_endpoint_url(endpoints, "object-store")
        self.pithos = PithosClient(self.pithos_url, self.token)
        self.pithos.CONNECTION_RETRY_LIMIT = self.retry

        self.image_url = _get_endpoint_url(endpoints, "image")
        self.image = ImageClient(self.image_url, self.token)
        self.image.CONNECTION_RETRY_LIMIT = self.retry


def _get_endpoint_url(endpoints, endpoint_type):
    """Get the publicURL for the specified endpoint"""

    service_catalog = parse_endpoints(endpoints, ep_type=endpoint_type)
    return service_catalog[0]['endpoints'][0]['publicURL']


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


# --------------------------------------------------------------------
# BurninTests class
# pylint: disable=too-many-public-methods
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
    delete_stale = False
    temp_directory = None
    failfast = None

    quotas = Proper(value=None)

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
        self.clients.initialize_clients()
        self.info("Astakos auth url is %s", self.clients.auth_url)
        self.info("Cyclades url is %s", self.clients.compute_url)
        self.info("Network url is %s", self.clients.network_url)
        self.info("Pithos url is %s", self.clients.pithos_url)
        self.info("Image url is %s", self.clients.image_url)

        user_uuid = self._get_uuid()
        self.quotas = self._get_quotas()
        for puuid, quotas in self.quotas.items():
            project_name = self._get_project_name(puuid, user_uuid)
            self.info("  Project %s:", project_name)
            self.info("    Disk usage is         %s bytes",
                      quotas['cyclades.disk']['usage'])
            self.info("    VM usage is           %s",
                      quotas['cyclades.vm']['usage'])
            self.info("    DiskSpace usage is    %s bytes",
                      quotas['pithos.diskspace']['usage'])
            self.info("    Ram usage is          %s bytes",
                      quotas['cyclades.ram']['usage'])
            self.info("    Floating IPs usage is %s",
                      quotas['cyclades.floating_ip']['usage'])
            self.info("    CPU usage is          %s",
                      quotas['cyclades.cpu']['usage'])
            self.info("    Network usage is      %s",
                      quotas['cyclades.network.private']['usage'])

    def _run_tests(self, tcases):
        """Run some generated testcases"""
        global success  # pylint: disable=invalid-name, global-statement

        for tcase in tcases:
            self.info("Running testsuite %s", tcase.__name__)
            success = run_test(tcase) and success
            if self.failfast and not success:
                break

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
        """Create a tmp directory"""
        temp_dir = tempfile.mkdtemp(dir=self.temp_directory)
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
            try:
                su_type, su_value = parse_typed_option(self.system_user)
                if su_type == "name":
                    system_users = [su_value]
                elif su_type == "id":
                    self.info("System user's uuid is %s", su_value)
                    return su_value
                else:
                    self.error("Unrecognized system-user type %s", su_type)
                    self.fail("Unrecognized system-user type")
            except ValueError:
                msg = "Invalid system-user format: %s. Must be [id|name]:.+"
                self.warning(msg, self.system_user)

        if system_users is None:
            system_users = SYSTEM_USERS

        uuids = self.clients.astakos.get_uuids(system_users)
        for su_name in system_users:
            self.info("Trying username %s", su_name)
            if su_name in uuids:
                self.info("System user's uuid is %s", uuids[su_name])
                return uuids[su_name]

        self.warning("No system user found")
        return None

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
            try:
                flv_type, flv_value = parse_typed_option(ptrn)
            except ValueError:
                msg = "Invalid flavor format: %s. Must be [id|name]:.+"
                self.warning(msg, ptrn)
                continue

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
            try:
                img_type, img_value = parse_typed_option(ptrn)
            except ValueError:
                msg = "Invalid image format: %s. Must be [id|name]:.+"
                self.warning(msg, ptrn)
                continue

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
    # Quotas
    def _get_quotas(self):
        """Get quotas"""
        self.info("Getting quotas")
        return dict(self.clients.astakos.get_quotas())

    # pylint: disable=invalid-name
    # pylint: disable=too-many-arguments
    def _check_quotas(self, puuid=None, disk=None, vm=None, diskspace=None,
                      ram=None, ip=None, cpu=None, network=None):
        """Check that quotas' changes are consistent

        @param puuid: The uuid of the project, quotas are assigned to

        """

        assert any(v is None for v in
                   [disk, vm, diskspace, ram, ip, cpu, network]), \
            "_check_quotas require arguments"

        self.info("Check that quotas' changes are consistent")
        old_quotas = self.quotas
        new_quotas = self._get_quotas()
        self.quotas = new_quotas

        user_uuid = self._get_uuid()
        if puuid is None:
            puuid = user_uuid

        self.assertListEqual(sorted(old_quotas.keys()),
                             sorted(new_quotas.keys()))
        for project in old_quotas.keys():
            # Check Disk usage
            project_name = self._get_project_name(project, user_uuid)
            self._check_quotas_aux(old_quotas[project], new_quotas[project],
                                   project_name, "cyclades.disk",
                                   disk, project == puuid)
            # Check VM usage
            self._check_quotas_aux(old_quotas[project], new_quotas[project],
                                   project_name, "cyclades.vm",
                                   vm, project == puuid)
            # Check DiskSpace usage
            self._check_quotas_aux(old_quotas[project], new_quotas[project],
                                   project_name, "pithos.diskspace",
                                   diskspace, project == puuid)
            # Check Ram usage
            self._check_quotas_aux(old_quotas[project], new_quotas[project],
                                   project_name, "cyclades.ram",
                                   ram, project == puuid)
            # Check Floating IPs usage
            self._check_quotas_aux(old_quotas[project], new_quotas[project],
                                   project_name, "cyclades.floating_ip",
                                   ip, project == puuid)
            # Check CPU usage
            self._check_quotas_aux(old_quotas[project], new_quotas[project],
                                   project_name, "cyclades.cpu",
                                   cpu, project == puuid)
            # Check Network usage
            self._check_quotas_aux(old_quotas[project], new_quotas[project],
                                   project_name, "cyclades.network.private",
                                   network, project == puuid)

    def _check_quotas_aux(self, old_quotas, new_quotas,
                          project_name, resource, value, check):
        """Auxiliary function for _check_quotas"""
        old_value = old_quotas[resource]['usage']
        new_value = new_quotas[resource]['usage']
        if check and value is not None:
            assert isinstance(value, int), \
                "%s value has to be integer" % resource
            old_value += value
        self.assertEqual(old_value, new_value,
                         "Project %s: %s quotas don't match" %
                         (project_name, resource))

    # ----------------------------------
    # Projects
    def _get_project_name(self, puuid, uuid=None):
        """Get the name of a project"""
        if uuid is None:
            uuid = self._get_uuid()
        if puuid == uuid:
            return "base"
        else:
            project_info = self.clients.astakos.get_project(puuid)
            return project_info['name']


# --------------------------------------------------------------------
# Initialize Burnin
def initialize(opts, testsuites, stale_testsuites):
    """Initalize burnin

    Initialize our logger and burnin state

    """
    # Initialize logger
    global logger  # pylint: disable=invalid-name, global-statement
    curr_time = datetime.datetime.now()
    logger = Log(opts.log_folder, verbose=opts.verbose,
                 use_colors=opts.use_colors, in_parallel=False,
                 log_level=opts.log_level, curr_time=curr_time)

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
    BurninTests.delete_stale = opts.delete_stale
    BurninTests.temp_directory = opts.temp_directory
    BurninTests.failfast = opts.failfast
    BurninTests.run_id = SNF_TEST_PREFIX + \
        datetime.datetime.strftime(curr_time, "%Y%m%d%H%M%S")

    # Choose tests to run
    if opts.show_stale:
        # We will run the stale_testsuites
        return (stale_testsuites, True)

    if opts.tests != "all":
        testsuites = opts.tests
    if opts.exclude_tests is not None:
        testsuites = [tsuite for tsuite in testsuites
                      if tsuite not in opts.exclude_tests]

    return (testsuites, opts.failfast)


# --------------------------------------------------------------------
# Run Burnin
def run_burnin(testsuites, failfast=False):
    """Run burnin testsuites"""
    # pylint: disable=invalid-name,global-statement
    # pylint: disable=global-variable-not-assigned
    global logger, success

    success = True
    run_tests(testsuites, failfast=failfast)

    # Clean up our logger
    del logger

    # Return
    return 0 if success else 1


def run_tests(tcases, failfast=False):
    """Run some testcases"""
    # pylint: disable=invalid-name,global-statement
    # pylint: disable=global-variable-not-assigned
    global success

    for tcase in tcases:
        was_success = run_test(tcase)
        success = success and was_success
        if failfast and not success:
            break


def run_test(tcase):
    """Run a testcase"""
    tsuite = unittest.TestLoader().loadTestsFromTestCase(tcase)
    results = tsuite.run(BurninTestResult())

    return was_successful(tcase.__name__, results.wasSuccessful())


# --------------------------------------------------------------------
# Helper functions
def was_successful(tsuite, successful):
    """Handle whether a testsuite was succesful or not"""
    if successful:
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
        raise
