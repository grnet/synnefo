#!/usr/bin/env python

"""
Synnefo ci utils module
"""

import os
import sys
import time
import logging
import fabric.api as fabric
from ConfigParser import ConfigParser, DuplicateSectionError

from kamaki.clients.astakos import AstakosClient
from kamaki.clients.cyclades import CycladesClient
from kamaki.clients.image import ImageClient


def _run(cmd, verbose):
    """Run fabric with verbose level"""
    if verbose:
        args = ('running',)
    else:
        args = ('running', 'stdout',)
    with fabric.hide(*args):
        return fabric.run(cmd)


def _red(msg):
    """Red color"""
    #return "\x1b[31m" + str(msg) + "\x1b[0m"
    return str(msg)


def _yellow(msg):
    """Yellow color"""
    #return "\x1b[33m" + str(msg) + "\x1b[0m"
    return str(msg)


def _green(msg):
    """Green color"""
    #return "\x1b[32m" + str(msg) + "\x1b[0m"
    return str(msg)


def _check_fabric(fun):
    """Check if fabric env has been set"""
    def wrapper(self, *args):
        """wrapper function"""
        if not self.fabric_installed:
            self.setup_fabric()
        return fun(self, *args)
    return wrapper


def _check_kamaki(fun):
    """Check if kamaki has been initialized"""
    def wrapper(self, *args):
        """wrapper function"""
        if not self.kamaki_installed:
            self.setup_kamaki()
        return fun(self, *args)
    return wrapper


class _MyFormatter(logging.Formatter):
    """Logging Formatter"""
    def format(self, record):
        format_orig = self._fmt
        if record.levelno == logging.DEBUG:
            self._fmt = "  %(msg)s"
        elif record.levelno == logging.INFO:
            self._fmt = "%(msg)s"
        elif record.levelno == logging.WARNING:
            self._fmt = _yellow("[W] %(msg)s")
        elif record.levelno == logging.ERROR:
            self._fmt = _red("[E] %(msg)s")
        result = logging.Formatter.format(self, record)
        self._fmt = format_orig
        return result


class SynnefoCI(object):
    """SynnefoCI python class"""

    def __init__(self, cleanup_config=False):
        """ Initialize SynnefoCI python class

        Setup logger, local_dir, config and kamaki
        """
        # Setup logger
        self.logger = logging.getLogger('synnefo-ci')
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(_MyFormatter())
        self.logger.addHandler(handler)

        # Get our local dir
        self.ci_dir = os.path.dirname(os.path.abspath(__file__))
        self.repo_dir = os.path.dirname(self.ci_dir)

        # Read config file
        default_conffile = os.path.join(self.ci_dir, "new_config")
        self.conffile = os.environ.get("SYNNEFO_CI_CONFIG_FILE",
                                       default_conffile)

        self.config = ConfigParser()
        self.config.optionxform = str
        self.config.read(self.conffile)
        temp_config = self.config.get('Global', 'temporary_config')
        if cleanup_config:
            try:
                os.remove(temp_config)
            except:
                pass
        else:
            self.config.read(self.config.get('Global', 'temporary_config'))

        # Initialize variables
        self.fabric_installed = False
        self.kamaki_installed = False
        self.cyclades_client = None
        self.image_client = None

    def setup_kamaki(self):
        """Initialize kamaki

        Setup cyclades_client and image_client
        """
        self.logger.info("Setup kamaki client..")
        auth_url = self.config.get('Deployment', 'auth_url')
        self.logger.debug("Authentication URL is %s" % _green(auth_url))
        token = self.config.get('Deployment', 'token')
        #self.logger.debug("Token is %s" % _green(token))

        astakos_client = AstakosClient(auth_url, token)

        cyclades_url = \
            astakos_client.get_service_endpoints('compute')['publicURL']
        self.logger.debug("Cyclades API url is %s" % _green(cyclades_url))
        self.cyclades_client = CycladesClient(cyclades_url, token)
        self.cyclades_client.CONNECTION_RETRY_LIMIT = 2

        image_url = \
            astakos_client.get_service_endpoints('image')['publicURL']
        self.logger.debug("Images API url is %s" % _green(image_url))
        self.image_client = ImageClient(cyclades_url, token)
        self.image_client.CONNECTION_RETRY_LIMIT = 2

    def _wait_transition(self, server_id, current_status, new_status):
        """Wait for server to go from current_status to new_status"""
        self.logger.debug("Waiting for server to become %s" % new_status)
        timeout = self.config.getint('Global', 'build_timeout')
        sleep_time = 5
        while True:
            server = self.cyclades_client.get_server_details(server_id)
            if server['status'] == new_status:
                return server
            elif timeout < 0:
                self.logger.error(
                    "Waiting for server to become %s timed out" % new_status)
                self.destroy_server(False)
                sys.exit(-1)
            elif server['status'] == current_status:
                # Sleep for #n secs and continue
                timeout = timeout - sleep_time
                time.sleep(sleep_time)
            else:
                self.logger.error(
                    "Server failed with status %s" % server['status'])
                self.destroy_server(False)
                sys.exit(-1)

    @_check_kamaki
    def destroy_server(self, wait=True):
        """Destroy slave server"""
        server_id = self.config.getint('Temporary Options', 'server_id')
        self.logger.info("Destoying server with id %s " % server_id)
        self.cyclades_client.delete_server(server_id)
        if wait:
            self._wait_transition(server_id, "ACTIVE", "DELETED")

    @_check_kamaki
    def create_server(self):
        """Create slave server"""
        self.logger.info("Create a new server..")
        image = self._find_image()
        self.logger.debug("Will use image \"%s\"" % _green(image['name']))
        self.logger.debug("Image has id %s" % _green(image['id']))
        server = self.cyclades_client.create_server(
            self.config.get('Deployment', 'server_name'),
            self.config.getint('Deployment', 'flavor_id'),
            image['id'])
        server_id = server['id']
        self.write_config('server_id', server_id)
        self.logger.debug("Server got id %s" % _green(server_id))
        server_user = server['metadata']['users']
        self.write_config('server_user', server_user)
        self.logger.debug("Server's admin user is %s" % _green(server_user))
        server_passwd = server['adminPass']
        self.write_config('server_passwd', server_passwd)

        server = self._wait_transition(server_id, "BUILD", "ACTIVE")
        self._get_server_ip_and_port(server)
        self._copy_ssh_keys()

        self.setup_fabric()
        self.logger.info("Setup firewall")
        accept_ssh_from = self.config.get('Global', 'filter_access_network')
        self.logger.debug("Block ssh except from %s" % accept_ssh_from)
        cmd = """
        local_ip=$(/sbin/ifconfig eth0 | grep 'inet addr:' | \
            cut -d':' -f2 | cut -d' ' -f1)
        iptables -A INPUT -s localhost -j ACCEPT
        iptables -A INPUT -s $local_ip -j ACCEPT
        iptables -A INPUT -s {0} -p tcp --dport 22 -j ACCEPT
        iptables -A INPUT -p tcp --dport 22 -j DROP
        """.format(accept_ssh_from)
        _run(cmd, False)

    def _find_image(self):
        """Find a suitable image to use

        It has to belong to the `system_uuid' user and
        contain the word `image_name'
        """
        system_uuid = self.config.get('Deployment', 'system_uuid')
        image_name = self.config.get('Deployment', 'image_name').lower()
        images = self.image_client.list_public(detail=True)['images']
        # Select images by `system_uuid' user
        images = [x for x in images if x['user_id'] == system_uuid]
        # Select images with `image_name' in their names
        images = \
            [x for x in images if x['name'].lower().find(image_name) != -1]
        # Let's select the first one
        return images[0]

    def _get_server_ip_and_port(self, server):
        """Compute server's IPv4 and ssh port number"""
        self.logger.info("Get server connection details..")
        # XXX: check if this IP is from public network
        server_ip = server['attachments'][0]['ipv4']
        if self.config.get('Deployment', 'deploy_on_io') == "True":
            tmp1 = int(server_ip.split(".")[2])
            tmp2 = int(server_ip.split(".")[3])
            server_ip = "gate.okeanos.io"
            server_port = 10000 + tmp1 * 256 + tmp2
        else:
            server_port = 22
        self.write_config('server_ip', server_ip)
        self.logger.debug("Server's IPv4 is %s" % _green(server_ip))
        self.write_config('server_port', server_port)
        self.logger.debug("Server's ssh port is %s" % _green(server_port))

    @_check_fabric
    def _copy_ssh_keys(self):
        authorized_keys = self.config.get("Deployment",
                                          "ssh_keys")
        if os.path.exists(authorized_keys):
            keyfile = '/tmp/%s.pub' % fabric.env.user
            _run('mkdir -p ~/.ssh && chmod 700 ~/.ssh', False)
            fabric.put(authorized_keys, keyfile)
            _run('cat %s >> ~/.ssh/authorized_keys' % keyfile, False)
            _run('rm %s' % keyfile, False)
            self.logger.debug("Uploaded ssh authorized keys")
        else:
            self.logger.debug("No ssh keys found")

    def write_config(self, option, value, section="Temporary Options"):
        """Write changes back to config file"""
        try:
            self.config.add_section(section)
        except DuplicateSectionError:
            pass
        self.config.set(section, option, str(value))
        temp_conf_file = self.config.get('Global', 'temporary_config')
        with open(temp_conf_file, 'wb') as tcf:
            self.config.write(tcf)

    def setup_fabric(self):
        """Setup fabric environment"""
        self.logger.info("Setup fabric parameters..")
        fabric.env.user = self.config.get('Temporary Options', 'server_user')
        fabric.env.host_string = \
            self.config.get('Temporary Options', 'server_ip')
        fabric.env.port = self.config.getint('Temporary Options',
                                             'server_port')
        fabric.env.password = self.config.get('Temporary Options',
                                              'server_passwd')
        fabric.env.connection_attempts = 10
        fabric.env.shell = "/bin/bash -c"
        fabric.env.disable_known_hosts = True
        fabric.env.output_prefix = None

    def _check_hash_sum(self, localfile, remotefile):
        """Check hash sums of two files"""
        self.logger.debug("Check hash sum for local file %s" % localfile)
        hash1 = os.popen("sha256sum %s" % localfile).read().split(' ')[0]
        self.logger.debug("Local file has sha256 hash %s" % hash1)
        self.logger.debug("Check hash sum for remote file %s" % remotefile)
        hash2 = _run("sha256sum %s" % remotefile, False)
        hash2 = hash2.split(' ')[0]
        self.logger.debug("Remote file has sha256 hash %s" % hash2)
        if hash1 != hash2:
            self.logger.error("Hashes differ.. aborting")
            sys.exit(-1)

    @_check_fabric
    def clone_repo(self):
        """Clone Synnefo repo from slave server"""
        self.logger.info("Configure repositories on remote server..")
        self.logger.debug("Setup apt, install curl and git")
        cmd = """
        echo 'APT::Install-Suggests "false";' >> /etc/apt/apt.conf
        apt-get update
        apt-get install curl git --yes
        echo -e "\n\ndeb {0}" >> /etc/apt/sources.list
        curl https://dev.grnet.gr/files/apt-grnetdev.pub | apt-key add -
        apt-get update
        git config --global user.name {1}
        git config --global user.mail {2}
        """.format(self.config.get('Global', 'apt_repo'),
                   self.config.get('Global', 'git_config_name'),
                   self.config.get('Global', 'git_config_mail'))
        _run(cmd, False)

        synnefo_repo = self.config.get('Global', 'synnefo_repo')
        synnefo_branch = self.config.get('Global', 'synnefo_branch')
        # Currently clonning synnefo can fail unexpectedly
        cloned = False
        for i in range(3):
            self.logger.debug("Clone synnefo from %s" % synnefo_repo)
            cmd = ("git clone --branch %s %s"
                   % (synnefo_branch, synnefo_repo))
            try:
                _run(cmd, False)
                cloned = True
                break
            except:
                self.logger.warning("Clonning synnefo failed.. retrying %s"
                                    % i)
        if not cloned:
            self.logger.error("Can not clone Synnefo repo.")
            sys.exit(-1)

        deploy_repo = self.config.get('Global', 'deploy_repo')
        self.logger.debug("Clone snf-deploy from %s" % deploy_repo)
        _run("git clone --depth 1 %s" % deploy_repo, False)

    @_check_fabric
    def build_synnefo(self):
        """Build Synnefo packages"""
        self.logger.info("Build Synnefo packages..")
        self.logger.debug("Install development packages")
        cmd = """
        apt-get update
        apt-get install zlib1g-dev dpkg-dev debhelper git-buildpackage \
                python-dev python-all python-pip --yes
        pip install devflow
        """
        _run(cmd, False)

        if self.config.get('Global', 'patch_pydist') == "True":
            self.logger.debug("Patch pydist.py module")
            cmd = r"""
            sed -r -i 's/(\(\?P<name>\[A-Za-z\]\[A-Za-z0-9_\.)/\1\\\-/' \
                /usr/share/python/debpython/pydist.py
            """
            _run(cmd, False)

        self.logger.debug("Build snf-deploy package")
        cmd = """
        git checkout -t origin/debian
        git-buildpackage --git-upstream-branch=master \
                --git-debian-branch=debian \
                --git-export-dir=../snf-deploy_build-area \
                -uc -us
        """
        with fabric.cd("snf-deploy"):
            _run(cmd, True)

        self.logger.debug("Install snf-deploy package")
        cmd = """
        dpkg -i snf-deploy*.deb
        apt-get -f install --yes
        """
        with fabric.cd("snf-deploy_build-area"):
            with fabric.settings(warn_only=True):
                _run(cmd, True)

        self.logger.debug("Build synnefo packages")
        cmd = """
        devflow-autopkg snapshot -b ~/synnefo_build-area --no-sign
        """
        with fabric.cd("synnefo"):
            _run(cmd, True)

        self.logger.debug("Copy synnefo debs to snf-deploy packages dir")
        cmd = """
        cp ~/synnefo_build-area/*.deb /var/lib/snf-deploy/packages/
        """
        _run(cmd, False)

    @_check_fabric
    def deploy_synnefo(self):
        """Deploy Synnefo using snf-deploy"""
        self.logger.info("Deploy Synnefo..")
        schema = self.config.get('Global', 'schema')
        schema_files = os.path.join(self.ci_dir, "schemas/%s/*" % schema)
        self.logger.debug("Will use %s schema" % schema)

        self.logger.debug("Upload schema files to server")
        with fabric.quiet():
            fabric.put(schema_files, "/etc/snf-deploy/")

        self.logger.debug("Change password in nodes.conf file")
        cmd = """
        sed -i 's/^password =.*/password = {0}/' /etc/snf-deploy/nodes.conf
        """.format(fabric.env.password)
        _run(cmd, False)

        self.logger.debug("Run snf-deploy")
        cmd = """
        snf-deploy all --autoconf
        """
        _run(cmd, True)

    @_check_fabric
    def unit_test(self):
        """Run Synnefo unit test suite"""
        self.logger.info("Run Synnefo unit test suite")
        component = self.config.get('Unit Tests', 'component')

        self.logger.debug("Install needed packages")
        cmd = """
        pip install mock
        pip install factory_boy
        """
        _run(cmd, False)

        self.logger.debug("Upload tests.sh file")
        unit_tests_file = os.path.join(self.ci_dir, "tests.sh")
        with fabric.quiet():
            fabric.put(unit_tests_file, ".")

        self.logger.debug("Run unit tests")
        cmd = """
        bash tests.sh {0}
        """.format(component)
        _run(cmd, True)

    @_check_fabric
    def run_burnin(self):
        """Run burnin functional test suite"""
        self.logger.info("Run Burnin functional test suite")
        cmd = """
        auth_url=$(grep -e '^url =' .kamakirc | cut -d' ' -f3)
        token=$(grep -e '^token =' .kamakirc | cut -d' ' -f3)
        images_user=$(kamaki image list -l | grep owner | \
                      cut -d':' -f2 | tr -d ' ')
        snf-burnin --auth-url=$auth_url --token=$token \
            --force-flavor=2 --image-id=all \
            --system-images-user=$images_user \
            {0}
        log_folder=$(ls -1d /var/log/burnin/* | tail -n1)
        for i in $(ls $log_folder/*/details*); do
            echo -e "\\n\\n"
            echo -e "***** $i\\n"
            cat $i
        done
        """.format(self.config.get('Burnin', 'cmd_options'))
        _run(cmd, True)

    @_check_fabric
    def fetch_packages(self):
        """Download Synnefo packages"""
        self.logger.info("Download Synnefo packages")
        self.logger.debug("Create tarball with packages")
        cmd = """
        tar czf synnefo_build-area.tgz synnefo_build-area
        """
        _run(cmd, False)

        pkgs_dir = self.config.get('Global', 'pkgs_dir')
        self.logger.debug("Fetch packages to local dir %s" % pkgs_dir)
        os.makedirs(pkgs_dir)
        with fabric.quiet():
            fabric.get("synnefo_build-area.tgz", pkgs_dir)

        pkgs_file = os.path.join(pkgs_dir, "synnefo_build-area.tgz")
        self._check_hash_sum(pkgs_file, "synnefo_build-area.tgz")

        self.logger.debug("Untar packages file %s" % pkgs_file)
        os.system("cd %s; tar xzf synnefo_build-area.tgz" % pkgs_dir)
