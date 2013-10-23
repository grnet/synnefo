#!/usr/bin/env python

"""
Synnefo ci utils module
"""

import os
import re
import sys
import time
import logging
import fabric.api as fabric
import subprocess
import tempfile
from ConfigParser import ConfigParser, DuplicateSectionError

from kamaki.cli import config as kamaki_config
from kamaki.clients.astakos import AstakosClient
from kamaki.clients.cyclades import CycladesClient
from kamaki.clients.image import ImageClient
from kamaki.clients.compute import ComputeClient
import filelocker

DEFAULT_CONFIG_FILE = "ci_wheezy.conf"
# Is our terminal a colorful one?
USE_COLORS = True
# UUID of owner of system images
DEFAULT_SYSTEM_IMAGES_UUID = [
    "25ecced9-bf53-4145-91ee-cf47377e9fb2",  # production (okeanos.grnet.gr)
    "04cbe33f-29b7-4ef1-94fb-015929e5fc06",  # testing (okeanos.io)
]


def _run(cmd, verbose):
    """Run fabric with verbose level"""
    if verbose:
        args = ('running',)
    else:
        args = ('running', 'stdout',)
    with fabric.hide(*args):  # Used * or ** magic. pylint: disable-msg=W0142
        return fabric.run(cmd)


def _put(local, remote):
    """Run fabric put command without output"""
    with fabric.quiet():
        fabric.put(local, remote)


def _red(msg):
    """Red color"""
    ret = "\x1b[31m" + str(msg) + "\x1b[0m" if USE_COLORS else str(msg)
    return ret


def _yellow(msg):
    """Yellow color"""
    ret = "\x1b[33m" + str(msg) + "\x1b[0m" if USE_COLORS else str(msg)
    return ret


def _green(msg):
    """Green color"""
    ret = "\x1b[32m" + str(msg) + "\x1b[0m" if USE_COLORS else str(msg)
    return ret


def _check_fabric(fun):
    """Check if fabric env has been set"""
    def wrapper(self, *args, **kwargs):
        """wrapper function"""
        if not self.fabric_installed:
            self.setup_fabric()
            self.fabric_installed = True
        return fun(self, *args, **kwargs)
    return wrapper


def _check_kamaki(fun):
    """Check if kamaki has been initialized"""
    def wrapper(self, *args, **kwargs):
        """wrapper function"""
        if not self.kamaki_installed:
            self.setup_kamaki()
            self.kamaki_installed = True
        return fun(self, *args, **kwargs)
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


# Too few public methods. pylint: disable-msg=R0903
class _InfoFilter(logging.Filter):
    """Logging Filter that allows DEBUG and INFO messages only"""
    def filter(self, rec):
        """The filter"""
        return rec.levelno in (logging.DEBUG, logging.INFO)


# Too many instance attributes. pylint: disable-msg=R0902
class SynnefoCI(object):
    """SynnefoCI python class"""

    def __init__(self, config_file=None, build_id=None, cloud=None):
        """ Initialize SynnefoCI python class

        Setup logger, local_dir, config and kamaki
        """
        # Setup logger
        self.logger = logging.getLogger('synnefo-ci')
        self.logger.setLevel(logging.DEBUG)

        handler1 = logging.StreamHandler(sys.stdout)
        handler1.setLevel(logging.DEBUG)
        handler1.addFilter(_InfoFilter())
        handler1.setFormatter(_MyFormatter())
        handler2 = logging.StreamHandler(sys.stderr)
        handler2.setLevel(logging.WARNING)
        handler2.setFormatter(_MyFormatter())

        self.logger.addHandler(handler1)
        self.logger.addHandler(handler2)

        # Get our local dir
        self.ci_dir = os.path.dirname(os.path.abspath(__file__))
        self.repo_dir = os.path.dirname(self.ci_dir)

        # Read config file
        if config_file is None:
            config_file = os.path.join(self.ci_dir, DEFAULT_CONFIG_FILE)
        config_file = os.path.abspath(config_file)
        self.config = ConfigParser()
        self.config.optionxform = str
        self.config.read(config_file)

        # Read temporary_config file
        self.temp_config_file = \
            os.path.expanduser(self.config.get('Global', 'temporary_config'))
        self.temp_config = ConfigParser()
        self.temp_config.optionxform = str
        self.temp_config.read(self.temp_config_file)
        self.build_id = build_id
        if build_id is not None:
            self.logger.info("Will use \"%s\" as build id" %
                             _green(self.build_id))

        # Set kamaki cloud
        if cloud is not None:
            self.kamaki_cloud = cloud
        elif self.config.has_option("Deployment", "kamaki_cloud"):
            kamaki_cloud = self.config.get("Deployment", "kamaki_cloud")
            if kamaki_cloud == "":
                self.kamaki_cloud = None
        else:
            self.kamaki_cloud = None

        # Initialize variables
        self.fabric_installed = False
        self.kamaki_installed = False
        self.cyclades_client = None
        self.compute_client = None
        self.image_client = None
        self.astakos_client = None

    def setup_kamaki(self):
        """Initialize kamaki

        Setup cyclades_client, image_client and compute_client
        """

        config = kamaki_config.Config()
        if self.kamaki_cloud is None:
            self.kamaki_cloud = config.get_global("default_cloud")

        self.logger.info("Setup kamaki client, using cloud '%s'.." %
                         self.kamaki_cloud)
        auth_url = config.get_cloud(self.kamaki_cloud, "url")
        self.logger.debug("Authentication URL is %s" % _green(auth_url))
        token = config.get_cloud(self.kamaki_cloud, "token")
        #self.logger.debug("Token is %s" % _green(token))

        self.astakos_client = AstakosClient(auth_url, token)

        cyclades_url = \
            self.astakos_client.get_service_endpoints('compute')['publicURL']
        self.logger.debug("Cyclades API url is %s" % _green(cyclades_url))
        self.cyclades_client = CycladesClient(cyclades_url, token)
        self.cyclades_client.CONNECTION_RETRY_LIMIT = 2

        image_url = \
            self.astakos_client.get_service_endpoints('image')['publicURL']
        self.logger.debug("Images API url is %s" % _green(image_url))
        self.image_client = ImageClient(cyclades_url, token)
        self.image_client.CONNECTION_RETRY_LIMIT = 2

        compute_url = \
            self.astakos_client.get_service_endpoints('compute')['publicURL']
        self.logger.debug("Compute API url is %s" % _green(compute_url))
        self.compute_client = ComputeClient(compute_url, token)
        self.compute_client.CONNECTION_RETRY_LIMIT = 2

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
                sys.exit(1)
            elif server['status'] == current_status:
                # Sleep for #n secs and continue
                timeout = timeout - sleep_time
                time.sleep(sleep_time)
            else:
                self.logger.error(
                    "Server failed with status %s" % server['status'])
                self.destroy_server(False)
                sys.exit(1)

    @_check_kamaki
    def destroy_server(self, wait=True):
        """Destroy slave server"""
        server_id = int(self.read_temp_config('server_id'))
        self.logger.info("Destoying server with id %s " % server_id)
        self.cyclades_client.delete_server(server_id)
        if wait:
            self._wait_transition(server_id, "ACTIVE", "DELETED")

    @_check_kamaki
    def create_server(self, image=None, flavor=None, ssh_keys=None):
        """Create slave server"""
        self.logger.info("Create a new server..")

        # Find a build_id to use
        self._create_new_build_id()

        # Find an image to use
        image_id = self._find_image(image)
        # Find a flavor to use
        flavor_id = self._find_flavor(flavor)

        # Create Server
        server_name = self.config.get("Deployment", "server_name")
        server = self.cyclades_client.create_server(
            "%s(BID: %s)" % (server_name, self.build_id),
            flavor_id,
            image_id)
        server_id = server['id']
        self.write_temp_config('server_id', server_id)
        self.logger.debug("Server got id %s" % _green(server_id))
        server_user = server['metadata']['users']
        self.write_temp_config('server_user', server_user)
        self.logger.debug("Server's admin user is %s" % _green(server_user))
        server_passwd = server['adminPass']
        self.write_temp_config('server_passwd', server_passwd)

        server = self._wait_transition(server_id, "BUILD", "ACTIVE")
        self._get_server_ip_and_port(server)
        self._copy_ssh_keys(ssh_keys)

        # Setup Firewall
        self.setup_fabric()
        self.logger.info("Setup firewall")
        accept_ssh_from = self.config.get('Global', 'accept_ssh_from')
        if accept_ssh_from != "":
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

        # Setup apt, download packages
        self.logger.debug("Setup apt. Install x2goserver and firefox")
        cmd = """
        echo 'APT::Install-Suggests "false";' >> /etc/apt/apt.conf
        apt-get update
        apt-get install curl --yes --force-yes
        echo -e "\n\n{0}" >> /etc/apt/sources.list
        # Synnefo repo's key
        curl https://dev.grnet.gr/files/apt-grnetdev.pub | apt-key add -

        # X2GO Key
        apt-key adv --recv-keys --keyserver keys.gnupg.net E1F958385BFE2B6E
        apt-get install x2go-keyring --yes --force-yes
        apt-get update
        apt-get install x2goserver x2goserver-xsession \
                iceweasel --yes --force-yes

        # xterm published application
        echo '[Desktop Entry]' > /usr/share/applications/xterm.desktop
        echo 'Name=XTerm' >> /usr/share/applications/xterm.desktop
        echo 'Comment=standard terminal emulator for the X window system' >> \
            /usr/share/applications/xterm.desktop
        echo 'Exec=xterm' >> /usr/share/applications/xterm.desktop
        echo 'Terminal=false' >> /usr/share/applications/xterm.desktop
        echo 'Type=Application' >> /usr/share/applications/xterm.desktop
        echo 'Encoding=UTF-8' >> /usr/share/applications/xterm.desktop
        echo 'Icon=xterm-color_48x48' >> /usr/share/applications/xterm.desktop
        echo 'Categories=System;TerminalEmulator;' >> \
                /usr/share/applications/xterm.desktop
        """.format(self.config.get('Global', 'apt_repo'))
        _run(cmd, False)

    def _find_flavor(self, flavor=None):
        """Find a suitable flavor to use

        Search by name (reg expression) or by id
        """
        # Get a list of flavors from config file
        flavors = self.config.get('Deployment', 'flavors').split(",")
        if flavor is not None:
            # If we have a flavor_name to use, add it to our list
            flavors.insert(0, flavor)

        list_flavors = self.compute_client.list_flavors()
        for flv in flavors:
            flv_type, flv_value = parse_typed_option(option="flavor",
                                                     value=flv)
            if flv_type == "name":
                # Filter flavors by name
                self.logger.debug(
                    "Trying to find a flavor with name \"%s\"" % flv_value)
                list_flvs = \
                    [f for f in list_flavors
                     if re.search(flv_value, f['name'], flags=re.I)
                     is not None]
            elif flv_type == "id":
                # Filter flavors by id
                self.logger.debug(
                    "Trying to find a flavor with id \"%s\"" % flv_value)
                list_flvs = \
                    [f for f in list_flavors
                     if str(f['id']) == flv_value]
            else:
                self.logger.error("Unrecognized flavor type %s" % flv_type)

            # Check if we found one
            if list_flvs:
                self.logger.debug("Will use \"%s\" with id \"%s\""
                                  % (_green(list_flvs[0]['name']),
                                     _green(list_flvs[0]['id'])))
                return list_flvs[0]['id']

        self.logger.error("No matching flavor found.. aborting")
        sys.exit(1)

    def _find_image(self, image=None):
        """Find a suitable image to use

        In case of search by name, the image has to belong to one
        of the `DEFAULT_SYSTEM_IMAGES_UUID' users.
        In case of search by id it only has to exist.
        """
        # Get a list of images from config file
        images = self.config.get('Deployment', 'images').split(",")
        if image is not None:
            # If we have an image from command line, add it to our list
            images.insert(0, image)

        auth = self.astakos_client.authenticate()
        user_uuid = auth["access"]["token"]["tenant"]["id"]
        list_images = self.image_client.list_public(detail=True)['images']
        for img in images:
            img_type, img_value = parse_typed_option(option="image", value=img)
            if img_type == "name":
                # Filter images by name
                self.logger.debug(
                    "Trying to find an image with name \"%s\"" % img_value)
                accepted_uuids = DEFAULT_SYSTEM_IMAGES_UUID + [user_uuid]
                list_imgs = \
                    [i for i in list_images if i['user_id'] in accepted_uuids
                     and
                     re.search(img_value, i['name'], flags=re.I) is not None]
            elif img_type == "id":
                # Filter images by id
                self.logger.debug(
                    "Trying to find an image with id \"%s\"" % img_value)
                list_imgs = \
                    [i for i in list_images
                     if i['id'].lower() == img_value.lower()]
            else:
                self.logger.error("Unrecognized image type %s" % img_type)
                sys.exit(1)

            # Check if we found one
            if list_imgs:
                self.logger.debug("Will use \"%s\" with id \"%s\""
                                  % (_green(list_imgs[0]['name']),
                                     _green(list_imgs[0]['id'])))
                return list_imgs[0]['id']

        # We didn't found one
        self.logger.error("No matching image found.. aborting")
        sys.exit(1)

    def _get_server_ip_and_port(self, server):
        """Compute server's IPv4 and ssh port number"""
        self.logger.info("Get server connection details..")
        server_ip = server['attachments'][0]['ipv4']
        if (".okeanos.io" in self.cyclades_client.base_url or
           ".demo.synnefo.org" in self.cyclades_client.base_url):
            tmp1 = int(server_ip.split(".")[2])
            tmp2 = int(server_ip.split(".")[3])
            server_ip = "gate.okeanos.io"
            server_port = 10000 + tmp1 * 256 + tmp2
        else:
            server_port = 22
        self.write_temp_config('server_ip', server_ip)
        self.logger.debug("Server's IPv4 is %s" % _green(server_ip))
        self.write_temp_config('server_port', server_port)
        self.logger.debug("Server's ssh port is %s" % _green(server_port))
        ssh_command = "ssh -p %s %s@%s" \
            % (server_port, server['metadata']['users'], server_ip)
        self.logger.debug("Access server using \"%s\"" %
                          (_green(ssh_command)))

    @_check_fabric
    def _copy_ssh_keys(self, ssh_keys):
        """Upload/Install ssh keys to server"""
        self.logger.debug("Check for authentication keys to use")
        if ssh_keys is None:
            ssh_keys = self.config.get("Deployment", "ssh_keys")

        if ssh_keys != "":
            ssh_keys = os.path.expanduser(ssh_keys)
            self.logger.debug("Will use \"%s\" authentication keys file" %
                              _green(ssh_keys))
            keyfile = '/tmp/%s.pub' % fabric.env.user
            _run('mkdir -p ~/.ssh && chmod 700 ~/.ssh', False)
            if ssh_keys.startswith("http://") or \
                    ssh_keys.startswith("https://") or \
                    ssh_keys.startswith("ftp://"):
                cmd = """
                apt-get update
                apt-get install wget --yes --force-yes
                wget {0} -O {1} --no-check-certificate
                """.format(ssh_keys, keyfile)
                _run(cmd, False)
            elif os.path.exists(ssh_keys):
                _put(ssh_keys, keyfile)
            else:
                self.logger.debug("No ssh keys found")
                return
            _run('cat %s >> ~/.ssh/authorized_keys' % keyfile, False)
            _run('rm %s' % keyfile, False)
            self.logger.debug("Uploaded ssh authorized keys")
        else:
            self.logger.debug("No ssh keys found")

    def _create_new_build_id(self):
        """Find a uniq build_id to use"""
        with filelocker.lock("%s.lock" % self.temp_config_file,
                             filelocker.LOCK_EX):
            # Read temp_config again to get any new entries
            self.temp_config.read(self.temp_config_file)

            # Find a uniq build_id to use
            if self.build_id is None:
                ids = self.temp_config.sections()
                if ids:
                    max_id = int(max(self.temp_config.sections(), key=int))
                    self.build_id = max_id + 1
                else:
                    self.build_id = 1
            self.logger.debug("Will use \"%s\" as build id"
                              % _green(self.build_id))

            # Create a new section
            try:
                self.temp_config.add_section(str(self.build_id))
            except DuplicateSectionError:
                msg = ("Build id \"%s\" already in use. " +
                       "Please use a uniq one or cleanup \"%s\" file.\n") \
                    % (self.build_id, self.temp_config_file)
                self.logger.error(msg)
                sys.exit(1)
            creation_time = \
                time.strftime("%a, %d %b %Y %X", time.localtime())
            self.temp_config.set(str(self.build_id),
                                 "created", str(creation_time))

            # Write changes back to temp config file
            with open(self.temp_config_file, 'wb') as tcf:
                self.temp_config.write(tcf)

    def write_temp_config(self, option, value):
        """Write changes back to config file"""
        # Acquire the lock to write to temp_config_file
        with filelocker.lock("%s.lock" % self.temp_config_file,
                             filelocker.LOCK_EX):

            # Read temp_config again to get any new entries
            self.temp_config.read(self.temp_config_file)

            self.temp_config.set(str(self.build_id), option, str(value))
            curr_time = time.strftime("%a, %d %b %Y %X", time.localtime())
            self.temp_config.set(str(self.build_id), "modified", curr_time)

            # Write changes back to temp config file
            with open(self.temp_config_file, 'wb') as tcf:
                self.temp_config.write(tcf)

    def read_temp_config(self, option):
        """Read from temporary_config file"""
        # If build_id is None use the latest one
        if self.build_id is None:
            ids = self.temp_config.sections()
            if ids:
                self.build_id = int(ids[-1])
            else:
                self.logger.error("No sections in temporary config file")
                sys.exit(1)
            self.logger.debug("Will use \"%s\" as build id"
                              % _green(self.build_id))
        # Read specified option
        return self.temp_config.get(str(self.build_id), option)

    def setup_fabric(self):
        """Setup fabric environment"""
        self.logger.info("Setup fabric parameters..")
        fabric.env.user = self.read_temp_config('server_user')
        fabric.env.host_string = self.read_temp_config('server_ip')
        fabric.env.port = int(self.read_temp_config('server_port'))
        fabric.env.password = self.read_temp_config('server_passwd')
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
            sys.exit(1)

    @_check_fabric
    def clone_repo(self, local_repo=False):
        """Clone Synnefo repo from slave server"""
        self.logger.info("Configure repositories on remote server..")
        self.logger.debug("Install/Setup git")
        cmd = """
        apt-get install git --yes --force-yes
        git config --global user.name {0}
        git config --global user.email {1}
        """.format(self.config.get('Global', 'git_config_name'),
                   self.config.get('Global', 'git_config_mail'))
        _run(cmd, False)

        # Clone synnefo_repo
        synnefo_branch = self.clone_synnefo_repo(local_repo=local_repo)
        # Clone pithos-web-client
        self.clone_pithos_webclient_repo(synnefo_branch)

    @_check_fabric
    def clone_synnefo_repo(self, local_repo=False):
        """Clone Synnefo repo to remote server"""
        # Find synnefo_repo and synnefo_branch to use
        synnefo_repo = self.config.get('Global', 'synnefo_repo')
        synnefo_branch = self.config.get("Global", "synnefo_branch")
        if synnefo_branch == "":
            synnefo_branch = \
                subprocess.Popen(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    stdout=subprocess.PIPE).communicate()[0].strip()
            if synnefo_branch == "HEAD":
                synnefo_branch = \
                    subprocess.Popen(
                        ["git", "rev-parse", "--short", "HEAD"],
                        stdout=subprocess.PIPE).communicate()[0].strip()
        self.logger.debug("Will use branch \"%s\"" % _green(synnefo_branch))

        if local_repo or synnefo_repo == "":
            # Use local_repo
            self.logger.debug("Push local repo to server")
            # Firstly create the remote repo
            _run("git init synnefo", False)
            # Then push our local repo over ssh
            # We have to pass some arguments to ssh command
            # namely to disable host checking.
            (temp_ssh_file_handle, temp_ssh_file) = tempfile.mkstemp()
            os.close(temp_ssh_file_handle)
            # XXX: git push doesn't read the password
            cmd = """
            echo 'exec ssh -o "StrictHostKeyChecking no" \
                           -o "UserKnownHostsFile /dev/null" \
                           -q "$@"' > {4}
            chmod u+x {4}
            export GIT_SSH="{4}"
            echo "{0}" | git push --quiet --mirror ssh://{1}@{2}:{3}/~/synnefo
            rm -f {4}
            """.format(fabric.env.password,
                       fabric.env.user,
                       fabric.env.host_string,
                       fabric.env.port,
                       temp_ssh_file)
            os.system(cmd)
        else:
            # Clone Synnefo from remote repo
            self.logger.debug("Clone synnefo from %s" % synnefo_repo)
            self._git_clone(synnefo_repo)

        # Checkout the desired synnefo_branch
        self.logger.debug("Checkout \"%s\" branch/commit" % synnefo_branch)
        cmd = """
        cd synnefo
        for branch in `git branch -a | grep remotes | grep -v HEAD`; do
            git branch --track ${branch##*/} $branch
        done
        git checkout %s
        """ % (synnefo_branch)
        _run(cmd, False)

        return synnefo_branch

    @_check_fabric
    def clone_pithos_webclient_repo(self, synnefo_branch):
        """Clone Pithos WebClient repo to remote server"""
        # Find pithos_webclient_repo and pithos_webclient_branch to use
        pithos_webclient_repo = \
            self.config.get('Global', 'pithos_webclient_repo')
        pithos_webclient_branch = \
            self.config.get('Global', 'pithos_webclient_branch')

        # Clone pithos-webclient from remote repo
        self.logger.debug("Clone pithos-webclient from %s" %
                          pithos_webclient_repo)
        self._git_clone(pithos_webclient_repo)

        # Track all pithos-webclient branches
        cmd = """
        cd pithos-web-client
        for branch in `git branch -a | grep remotes | grep -v HEAD`; do
            git branch --track ${branch##*/} $branch > /dev/null 2>&1
        done
        git branch
        """
        webclient_branches = _run(cmd, False)
        webclient_branches = webclient_branches.split()

        # If we have pithos_webclient_branch in config file use this one
        # else try to use the same branch as synnefo_branch
        # else use an appropriate one.
        if pithos_webclient_branch == "":
            if synnefo_branch in webclient_branches:
                pithos_webclient_branch = synnefo_branch
            else:
                # If synnefo_branch starts with one of
                # 'master', 'hotfix'; use the master branch
                if synnefo_branch.startswith('master') or \
                        synnefo_branch.startswith('hotfix'):
                    pithos_webclient_branch = "master"
                # If synnefo_branch starts with one of
                # 'develop', 'feature'; use the develop branch
                elif synnefo_branch.startswith('develop') or \
                        synnefo_branch.startswith('feature'):
                    pithos_webclient_branch = "develop"
                else:
                    self.logger.waring(
                        "Cannot determine which pithos-web-client branch to "
                        "use based on \"%s\" synnefo branch. "
                        "Will use develop." % synnefo_branch)
                    pithos_webclient_branch = "develop"
        # Checkout branch
        self.logger.debug("Checkout \"%s\" branch" %
                          _green(pithos_webclient_branch))
        cmd = """
        cd pithos-web-client
        git checkout {0}
        """.format(pithos_webclient_branch)
        _run(cmd, False)

    def _git_clone(self, repo):
        """Clone repo to remote server

        Currently clonning from code.grnet.gr can fail unexpectedly.
        So retry!!

        """
        cloned = False
        for i in range(1, 11):
            try:
                _run("git clone %s" % repo, False)
                cloned = True
                break
            except BaseException:
                self.logger.warning("Clonning failed.. retrying %s/10" % i)
        if not cloned:
            self.logger.error("Can not clone repo.")
            sys.exit(1)

    @_check_fabric
    def build_packages(self):
        """Build packages needed by Synnefo software"""
        self.logger.info("Install development packages")
        cmd = """
        apt-get update
        apt-get install zlib1g-dev dpkg-dev debhelper git-buildpackage \
                python-dev python-all python-pip ant --yes --force-yes
        pip install -U devflow
        """
        _run(cmd, False)

        # Patch pydist bug
        if self.config.get('Global', 'patch_pydist') == "True":
            self.logger.debug("Patch pydist.py module")
            cmd = r"""
            sed -r -i 's/(\(\?P<name>\[A-Za-z\]\[A-Za-z0-9_\.)/\1\\\-/' \
                /usr/share/python/debpython/pydist.py
            """
            _run(cmd, False)

        # Build synnefo packages
        self.build_synnefo()
        # Build pithos-web-client packages
        self.build_pithos_webclient()

    @_check_fabric
    def build_synnefo(self):
        """Build Synnefo packages"""
        self.logger.info("Build Synnefo packages..")

        cmd = """
        devflow-autopkg snapshot -b ~/synnefo_build-area --no-sign
        """
        with fabric.cd("synnefo"):
            _run(cmd, True)

        # Install snf-deploy package
        self.logger.debug("Install snf-deploy package")
        cmd = """
        dpkg -i snf-deploy*.deb
        apt-get -f install --yes --force-yes
        """
        with fabric.cd("synnefo_build-area"):
            with fabric.settings(warn_only=True):
                _run(cmd, True)

        # Setup synnefo packages for snf-deploy
        self.logger.debug("Copy synnefo debs to snf-deploy packages dir")
        cmd = """
        cp ~/synnefo_build-area/*.deb /var/lib/snf-deploy/packages/
        """
        _run(cmd, False)

    @_check_fabric
    def build_pithos_webclient(self):
        """Build pithos-web-client packages"""
        self.logger.info("Build pithos-web-client packages..")

        cmd = """
        devflow-autopkg snapshot -b ~/webclient_build-area --no-sign
        """
        with fabric.cd("pithos-web-client"):
            _run(cmd, True)

        # Setup pithos-web-client packages for snf-deploy
        self.logger.debug("Copy webclient debs to snf-deploy packages dir")
        cmd = """
        cp ~/webclient_build-area/*.deb /var/lib/snf-deploy/packages/
        """
        _run(cmd, False)

    @_check_fabric
    def build_documentation(self):
        """Build Synnefo documentation"""
        self.logger.info("Build Synnefo documentation..")
        _run("pip install -U Sphinx", False)
        with fabric.cd("synnefo"):
            _run("devflow-update-version; "
                 "./ci/make_docs.sh synnefo_documentation", False)

    def fetch_documentation(self, dest=None):
        """Fetch Synnefo documentation"""
        self.logger.info("Fetch Synnefo documentation..")
        if dest is None:
            dest = "synnefo_documentation"
        dest = os.path.abspath(dest)
        if not os.path.exists(dest):
            os.makedirs(dest)
        self.fetch_compressed("synnefo/synnefo_documentation", dest)
        self.logger.info("Downloaded documentation to %s" %
                         _green(dest))

    @_check_fabric
    def deploy_synnefo(self, schema=None):
        """Deploy Synnefo using snf-deploy"""
        self.logger.info("Deploy Synnefo..")
        if schema is None:
            schema = self.config.get('Global', 'schema')
        self.logger.debug("Will use \"%s\" schema" % _green(schema))

        schema_dir = os.path.join(self.ci_dir, "schemas/%s" % schema)
        if not (os.path.exists(schema_dir) and os.path.isdir(schema_dir)):
            raise ValueError("Unknown schema: %s" % schema)

        self.logger.debug("Upload schema files to server")
        _put(os.path.join(schema_dir, "*"), "/etc/snf-deploy/")

        self.logger.debug("Change password in nodes.conf file")
        cmd = """
        sed -i 's/^password =.*/password = {0}/' /etc/snf-deploy/nodes.conf
        """.format(fabric.env.password)
        _run(cmd, False)

        self.logger.debug("Run snf-deploy")
        cmd = """
        snf-deploy keygen --force
        snf-deploy --disable-colors --autoconf all
        """
        _run(cmd, True)

    @_check_fabric
    def unit_test(self):
        """Run Synnefo unit test suite"""
        self.logger.info("Run Synnefo unit test suite")
        component = self.config.get('Unit Tests', 'component')

        self.logger.debug("Install needed packages")
        cmd = """
        pip install -U mock
        pip install -U factory_boy
        """
        _run(cmd, False)

        self.logger.debug("Upload tests.sh file")
        unit_tests_file = os.path.join(self.ci_dir, "tests.sh")
        _put(unit_tests_file, ".")

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
        BurninExitStatus=$?
        log_folder=$(ls -1d /var/log/burnin/* | tail -n1)
        for i in $(ls $log_folder/*/details*); do
            echo -e "\\n\\n"
            echo -e "***** $i\\n"
            cat $i
        done
        exit $BurninExitStatus
        """.format(self.config.get('Burnin', 'cmd_options'))
        _run(cmd, True)

    @_check_fabric
    def fetch_compressed(self, src, dest=None):
        """Create a tarball and fetch it locally"""
        self.logger.debug("Creating tarball of %s" % src)
        basename = os.path.basename(src)
        tar_file = basename + ".tgz"
        cmd = "tar czf %s %s" % (tar_file, src)
        _run(cmd, False)
        if not os.path.exists(dest):
            os.makedirs(dest)

        tmp_dir = tempfile.mkdtemp()
        fabric.get(tar_file, tmp_dir)

        dest_file = os.path.join(tmp_dir, tar_file)
        self._check_hash_sum(dest_file, tar_file)
        self.logger.debug("Untar packages file %s" % dest_file)
        cmd = """
        cd %s
        tar xzf %s
        cp -r %s/* %s
        rm -r %s
        """ % (tmp_dir, tar_file, src, dest, tmp_dir)
        os.system(cmd)
        self.logger.info("Downloaded %s to %s" %
                         (src, _green(dest)))

    @_check_fabric
    def fetch_packages(self, dest=None):
        """Fetch Synnefo packages"""
        if dest is None:
            dest = self.config.get('Global', 'pkgs_dir')
        dest = os.path.abspath(os.path.expanduser(dest))
        if not os.path.exists(dest):
            os.makedirs(dest)
        self.fetch_compressed("synnefo_build-area", dest)
        self.fetch_compressed("webclient_build-area", dest)
        self.logger.info("Downloaded debian packages to %s" %
                         _green(dest))

    def x2go_plugin(self, dest=None):
        """Produce an html page which will use the x2goplugin

        Arguments:
          dest  -- The file where to save the page (String)

        """
        output_str = """
        <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
        <html>
        <head>
        <title>X2Go SynnefoCI Service</title>
        </head>
        <body onload="checkPlugin()">
        <div id="x2goplugin">
            <object
                src="location"
                type="application/x2go"
                name="x2goplugin"
                palette="background"
                height="100%"
                hspace="0"
                vspace="0"
                width="100%"
                x2goconfig="
                    session=X2Go-SynnefoCI-Session
                    server={0}
                    user={1}
                    sshport={2}
                    published=true
                    autologin=true
                ">
            </object>
        </div>
        </body>
        </html>
        """.format(self.read_temp_config('server_ip'),
                   self.read_temp_config('server_user'),
                   self.read_temp_config('server_port'))
        if dest is None:
            dest = self.config.get('Global', 'x2go_plugin_file')

        self.logger.info("Writting x2go plugin html file to %s" % dest)
        fid = open(dest, 'w')
        fid.write(output_str)
        fid.close()


def parse_typed_option(option, value):
    """Parsed typed options (flavors and images)"""
    try:
        [type_, val] = value.strip().split(':')
        if type_ not in ["id", "name"]:
            raise ValueError
        return type_, val
    except ValueError:
        msg = "Invalid %s format. Must be [id|name]:.+" % option
        raise ValueError(msg)
