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
Common utils for burnin tests

"""

import hashlib
import re
import shutil
import unittest
import datetime
import tempfile
import traceback
from tempfile import NamedTemporaryFile
from os import urandom
from string import ascii_letters
from StringIO import StringIO
from binascii import hexlify

from kamaki.clients.cyclades import CycladesClient, CycladesNetworkClient
from kamaki.clients.astakos import AstakosClient
from kamaki.clients.compute import ComputeClient
from kamaki.clients.pithos import PithosClient
from kamaki.clients.image import ImageClient
from kamaki.clients.blockstorage import BlockStorageClient

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

QADD = 1
QREMOVE = -1

QDISK = "cyclades.disk"
QVM = "cyclades.vm"
QPITHOS = "pithos.diskspace"
QRAM = "cyclades.ram"
QIP = "cyclades.floating_ip"
QCPU = "cyclades.cpu"
QNET = "cyclades.network.private"


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
        logger.log(
            test.__class__.__name__,
            test.shortDescription() or 'Test %s' % test.__class__.__name__)

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

    # pylint: disable=fixme
    def addSkip(self, test, reason):  # noqa
        """Called when the test case test is skipped

        If reason starts with "__SkipClass__: " then
        we should stop the execution of all the TestSuite.

        TODO: There should be a better way to do this

        """
        super(BurninTestResult, self).addSkip(test, reason)
        if reason.startswith("__SkipClass__: "):
            self.stop()


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

        self.compute_url = self.astakos.get_endpoint_url(
            ComputeClient.service_type)
        self.compute = ComputeClient(self.compute_url, self.token)
        self.compute.CONNECTION_RETRY_LIMIT = self.retry

        self.cyclades_url = self.astakos.get_endpoint_url(
            CycladesClient.service_type)
        self.cyclades = CycladesClient(self.cyclades_url, self.token)
        self.cyclades.CONNECTION_RETRY_LIMIT = self.retry

        self.block_storage_url = self.astakos.get_endpoint_url(
            BlockStorageClient.service_type)
        self.block_storage = BlockStorageClient(self.block_storage_url,
                                                self.token)
        self.block_storage.CONNECTION_RETRY_LIMIT = self.retry

        self.network_url = self.astakos.get_endpoint_url(
            CycladesNetworkClient.service_type)
        self.network = CycladesNetworkClient(self.network_url, self.token)
        self.network.CONNECTION_RETRY_LIMIT = self.retry

        self.pithos_url = self.astakos.get_endpoint_url(
            PithosClient.service_type)
        self.pithos = PithosClient(self.pithos_url, self.token)
        self.pithos.CONNECTION_RETRY_LIMIT = self.retry

        self.image_url = self.astakos.get_endpoint_url(
            ImageClient.service_type)
        self.image = ImageClient(self.image_url, self.token)
        self.image.CONNECTION_RETRY_LIMIT = self.retry


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


def file_read_iterator(fp, size=1024):
    while True:
        data = fp.read(size)
        if not data:
            break
        yield data


class HashMap(list):

    def __init__(self, blocksize, blockhash):
        super(HashMap, self).__init__()
        self.blocksize = blocksize
        self.blockhash = blockhash

    def _hash_raw(self, v):
        h = hashlib.new(self.blockhash)
        h.update(v)
        return h.digest()

    def _hash_block(self, v):
        return self._hash_raw(v.rstrip('\x00'))

    def hash(self):
        if len(self) == 0:
            return self._hash_raw('')
        if len(self) == 1:
            return self.__getitem__(0)

        h = list(self)
        s = 2
        while s < len(h):
            s = s * 2
        h += [('\x00' * len(h[0]))] * (s - len(h))
        while len(h) > 1:
            h = [self._hash_raw(h[x] + h[x + 1]) for x in range(0, len(h), 2)]
        return h[0]

    def load(self, data):
        self.size = 0
        fp = StringIO(data)
        for block in file_read_iterator(fp, self.blocksize):
            self.append(self._hash_block(block))
            self.size += len(block)


def merkle(data, blocksize, blockhash):
    hashes = HashMap(blocksize, blockhash)
    hashes.load(data)
    return hexlify(hashes.hash())


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
    temp_containers = []

    quotas = Proper(value=None)
    uuid = Proper(value=None)

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

        self.quotas = self._get_quotas()
        for puuid, quotas in self.quotas.items():
            project_name = self._get_project_name(puuid)
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
        self.fail(msg % args)

    # ----------------------------------
    # Helper functions that every testsuite may need
    def _get_uuid(self):
        """Get our uuid"""
        if self.uuid is None:
            authenticate = self.clients.astakos.authenticate()
            self.uuid = authenticate['access']['user']['id']
            self.info("User's uuid is %s", self.uuid)
        return self.uuid

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

    def _create_large_file(self, size):
        """Create a large file at fs"""
        named_file = NamedTemporaryFile()
        seg = size / 8
        self.debug('Create file %s  ', named_file.name)
        for sbytes in [b * seg for b in range(size / seg)]:
            named_file.seek(sbytes)
            named_file.write(urandom(seg))
            named_file.flush()
        named_file.seek(0)
        return named_file

    def _create_file(self, size):
        """Create a file and compute its merkle hash"""

        tmp_file = NamedTemporaryFile()
        self.debug('\tCreate file %s  ' % tmp_file.name)
        meta = self.clients.pithos.get_container_info()
        block_size = int(meta['x-container-block-size'])
        block_hash_algorithm = meta['x-container-block-hash']
        num_of_blocks = size / block_size
        hashmap = HashMap(block_size, block_hash_algorithm)
        s = 0
        for i in range(num_of_blocks):
            seg = urandom(block_size)
            tmp_file.write(seg)
            hashmap.load(seg)
            s += len(seg)
        else:
            rest = size - s
            if rest:
                seg = urandom(rest)
                tmp_file.write(seg)
                hashmap.load(seg)
                s += len(seg)
        tmp_file.seek(0)
        tmp_file.hash = hexlify(hashmap.hash())
        return tmp_file

    def _create_boring_file(self, num_of_blocks):
        """Create a file with some blocks being the same"""

        def chargen():
            """10 + 2 * 26 + 26 = 88"""
            while True:
                for char in xrange(10):
                    yield '%s' % char
                for char in ascii_letters:
                    yield char
                for char in '~!@#$%^&*()_+`-=:";|<>?,./':
                    yield char

        tmp_file = NamedTemporaryFile()
        self.debug('\tCreate file %s  ' % tmp_file.name)
        block_size = 4 * 1024 * 1024
        chars = chargen()
        while num_of_blocks:
            fslice = 3 if num_of_blocks > 3 else num_of_blocks
            tmp_file.write(fslice * block_size * chars.next())
            num_of_blocks -= fslice
        tmp_file.seek(0)
        return tmp_file

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

    def _skip_suite_if(self, condition, msg):
        """Skip the whole testsuite"""
        if condition:
            self.info("TestSuite skipped: %s" % msg)
            self.skipTest("__SkipClass__: %s" % msg)

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
        def _is_true(value):
            """Boolean or string value that represents a bool"""
            if isinstance(value, bool):
                return value
            elif isinstance(value, str):
                return value in ["True", "true"]
            else:
                self.warning("Unrecognized boolean value %s", value)
                return False

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

            # Get only flavors that are allowed to create a machine
            filtered_flvs = [f for f in filtered_flvs
                             if _is_true(f['SNF:allow_create'])]

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
        self.clients.pithos.create_container(container)
        self.temp_containers.append(container)

    # ----------------------------------
    # Quotas
    def _get_quotas(self):
        """Get quotas"""
        self.info("Getting quotas")
        return dict(self.clients.astakos.get_quotas())

    # pylint: disable=invalid-name
    # pylint: disable=too-many-arguments
    def _check_quotas(self, changes):
        """Check that quotas' changes are consistent

        @param changes: A dict of the changes that have been made in quotas

        """
        def dicts_are_equal(d1, d2):
            """Helper function to check dict equality"""
            self.assertEqual(set(d1), set(d2))
            for key, val in d1.items():
                if isinstance(val, (list, tuple)):
                    self.assertEqual(set(val), set(d2[key]))
                elif isinstance(val, dict):
                    dicts_are_equal(val, d2[key])
                else:
                    self.assertEqual(val, d2[key])

        if not changes:
            return

        self.info("Check that quotas' changes are consistent")
        old_quotas = self.quotas
        new_quotas = self._get_quotas()
        self.quotas = new_quotas

        self.assertListEqual(sorted(old_quotas.keys()),
                             sorted(new_quotas.keys()))

        # Take old_quotas and apply changes
        for prj, values in changes.items():
            self.assertIn(prj, old_quotas.keys())
            for q_name, q_mult, q_value, q_unit in values:
                if q_unit is None:
                    q_unit = 1
                q_value = q_mult*int(q_value)*q_unit
                assert isinstance(q_value, int), \
                    "Project %s: %s value has to be integer" % (prj, q_name)
                old_quotas[prj][q_name]['usage'] += q_value
                old_quotas[prj][q_name]['project_usage'] += q_value

        dicts_are_equal(old_quotas, new_quotas)

    # ----------------------------------
    # Projects
    def _get_project_name(self, puuid):
        """Get the name of a project"""
        uuid = self._get_uuid()
        if puuid == uuid:
            return "base"
        else:
            project_info = self.clients.astakos.get_project(puuid)
            return project_info['name']

    def _get_merkle_hash(self, data):
        self.clients.pithos._assert_account()
        meta = self.clients.pithos.get_container_info()
        block_size = int(meta['x-container-block-size'])
        block_hash_algorithm = meta['x-container-block-hash']
        hashes = HashMap(block_size, block_hash_algorithm)
        hashes.load(data)
        return hexlify(hashes.hash())


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
    BurninTests.obj_upload_num = opts.obj_upload_num
    BurninTests.obj_upload_min_size = opts.obj_upload_min_size
    BurninTests.obj_upload_max_size = opts.obj_upload_max_size

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
