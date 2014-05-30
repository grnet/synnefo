#!/usr/bin/python

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

import os
import argparse
import sys
import glob
from fabric.api import hide, settings, execute, show
from snfdeploy import config
from snfdeploy import context
from snfdeploy import status
from snfdeploy import fabfile
from snfdeploy import vcluster
from snfdeploy import constants
from snfdeploy.lib import create_dir


def print_help_msg(cmds):

    if "keygen" in cmds:
        print """
Usage: snf-deploy keygen [--force]

  Generate new ssh keys (both rsa and dsa keypairs)

  """

    elif "vcluster" in cmds:
        print """
Usage: snf-deploy vcluster

  Run the following actions concerning the local virtual cluster:

    - Download base image and create additional disk \
(if --create-extra-disk is passed)
    - Does all the network related actions (bridge, iptables, NAT)
    - Launches dnsmasq for dhcp server on bridge
    - Creates the virtual cluster (with kvm)

  """

    elif "setup" in cmds:
        print """
Usage: setup --node NODE [--role ROLE | --method METHOD --component COMPONENT]

    Setup a specific component on the requested context

      --node      NODE (overriden if --autoconf is passed)
      --role      ROLE (one of the end roles)
      --cluster   CLUSTER (one of the registered cluster)
      --setup     SETUP (one of the registered setups)
      --component COMPONENT (one of the subcomponents)

  """

    elif "run" in cmds:
        print """
Usage: setup --setup SETUP | --target-nodes NODE1,NODE2... --cmd "some cmd"

    Run a specific bash command on the requested nodes

      --target-nodes NODES  Comma separated nodes definded in nodes.conf
      --setup SETUP         Target all nodes in SETUP defined in setups.conf
      --cmd CMD             The bash command to be executed
  """

    else:
        print """
Usage: snf-deploy [-h] [-c CONFDIR] [-t TEMPLATE_DIR] [-s STATE_DIR]
                  [--dry-run] [-v] [-d] [--autoconf] [--mem MEM] [--smp SMP]
                  [--vnc] [--force] [-i SSH_KEY] [--no-key-inject]
                  [--cluster CLUSTER] [--component COMPONENT]
                  [--method METHOD] [--role ROLE] [--node NODE]
                  [--setup SETUP] [--disable-colors]
                  command [cmd]

  The command can be either of:

      packages    Download synnefo packages and stores them locally
      image       Create a debian base image for vcluster
      vcluster    Create a local virtual cluster with KVM, dnsmasq, and NAT
      cleanup     Cleanup the local virtual cluster
      test        Print the configuration
      synnefo     Deploy synnefo on the requested setup
      keygen      Create ssh and ddns keys
      ganeti      Deploy a Ganeti cluster on the requested setup
      ganeti-qa   Deploy a Ganeti QA cluster on the requested cluster
      run         Run a specific bash command on the target nodes
      help        Display a help message for the following command

  """

    sys.exit(0)


def fabcommand(args, actions):
    levels = ["status", "aborts", "warnings", "running",
              "stdout", "stderr", "user", "debug"]

    level_aliases = {
        "output": ["stdout", "stderr"],
        "everything": ["warnings", "running", "user", "output"]
    }

    lhide = level_aliases["everything"]
    lshow = []

    if args.verbose == 1:
        lshow = levels[:3]
        lhide = levels[3:]
    elif args.verbose == 2:
        lshow = levels[:4]
        lhide = levels[4:]
    elif args.verbose >= 3 or args.debug:
        lshow = levels
        lhide = []

#   fabcmd += " --fabfile {4}/fabfile.py \
# setup_env:confdir={0},packages={1},templates={2},cluster_name={3},\
# autoconf={5},disable_colors={6},key_inject={7} \
# ".format(args.confdir, env.packages, env.templates, args.cluster_name,
#          env.lib, args.autoconf, args.disable_colors, args.key_inject)

    with settings(hide(*lhide), show(*lshow)):
        for a in actions:
            fn = getattr(fabfile, a)
            execute(fn)


def get_packages():
    if config.package_url:
        os.system("rm {0}/*.deb".format(config.package_dir))
        os.system("wget -r --level=1 -nH --no-parent --cut-dirs=4 {0} -P {1}"
                  .format(config.package_url, config.package_dir))


def parse_options():
    parser = argparse.ArgumentParser()

    # Directories to load/store config
    parser.add_argument("-c", dest="confdir",
                        default="/etc/snf-deploy",
                        help="Directory to find default configuration")
    parser.add_argument("-t", "--templates-dir", dest="template_dir",
                        default=None,
                        help="Directory to find templates. Overrides"
                             " the one found in the deploy.conf file")
    parser.add_argument("-s", "--state-dir", dest="state_dir",
                        default=None,
                        help="Directory to store current state. Overrides"
                             " the one found in the deploy.conf")
    parser.add_argument("--dry-run", dest="dry_run",
                        default=False, action="store_true",
                        help="Do not execute or write anything.")
    parser.add_argument("-v", dest="verbose",
                        default=0, action="count",
                        help="Increase verbosity.")
    parser.add_argument("-d", dest="debug",
                        default=False, action="store_true",
                        help="Debug mode")
    parser.add_argument("--autoconf", dest="autoconf",
                        default=False, action="store_true",
                        help="In case of all in one auto conf setup")

    # virtual cluster related options
    parser.add_argument("--mem", dest="mem",
                        default=2024,
                        help="Memory for every virtual node")
    parser.add_argument("--smp", dest="smp",
                        default=1,
                        help="Virtual CPUs for every virtual node")
    parser.add_argument("--vnc", dest="vnc",
                        default=False, action="store_true",
                        help="Whether virtual nodes will have a vnc "
                             "console or not")
    parser.add_argument("--force", dest="force",
                        default=False, action="store_true",
                        help="Force things (creation of key pairs"
                             " do not abort execution if something fails")

    parser.add_argument("-i", "--ssh-key", dest="ssh_key",
                        default=None,
                        help="Path of an existing ssh key to use")

    parser.add_argument("--no-key-inject", dest="key_inject",
                        default=True, action="store_false",
                        help="Whether to inject ssh key pairs to hosts")

    parser.add_argument("--pass-gen", dest="passgen",
                        default=False, action="store_true",
                        help="Whether to create random passwords")

    # backend related options
    parser.add_argument("--cluster", dest="cluster",
                        default=constants.DEFAULT_CLUSTER,
                        help="The cluster name in ganeti.conf")

    # options related to custom setup
    parser.add_argument("--component", dest="component",
                        default=None,
                        help="The component class")

    parser.add_argument("--method", dest="method",
                        default=None,
                        help="The component method")

    parser.add_argument("--role", dest="role",
                        default=None,
                        help="The target node's role")

    parser.add_argument("--node", dest="node",
                        default=constants.DEFAULT_NODE,
                        help="The target node")

    parser.add_argument("--setup", dest="setup",
                        default=constants.DEFAULT_SETUP,
                        help="The target setup")

    parser.add_argument("--cmd", dest="cmd",
                        default="date",
                        help="The command to run on target nodes")

    parser.add_argument("--target-nodes", dest="target_nodes",
                        default=None,
                        help="The target nodes to run cmd")

    # available commands
    parser.add_argument("command", type=str,
                        choices=["packages", "vcluster", "cleanup", "image",
                                 "setup", "test", "synnefo", "keygen",
                                 "ganeti", "ganeti-qa", "help", "run"],
                        help="Run on of the supported deployment commands")

    # available actions for the run command
    parser.add_argument("cmds", type=str, nargs="*",
                        help="Specific commands to display help for")

    # disable colors in terminal
    parser.add_argument("--disable-colors", dest="disable_colors",
                        default=False, action="store_true",
                        help="Disable colors in terminal")

    return parser.parse_args()


def get_actions(*args):
    actions = {
        "ganeti": [
            "setup_ganeti"
        ],
        "ganeti-qa": [
            "setup_qa",
        ],
        "synnefo": [
            "setup_synnefo",
        ],
        "setup": [
            "setup",
        ],
        "run": [
            "run",
        ],

    }

    ret = []
    for x in args:
        ret += actions[x]

    return ret


def must_create_keys():
    """Check if the ssh keys already exist

    """
    d = os.path.join(config.template_dir, "root/.ssh")
    auth_keys_exists = os.path.exists(os.path.join(d, "authorized_keys"))
    dsa_exists = os.path.exists(os.path.join(d, "id_dsa"))
    dsa_pub_exists = os.path.exists(os.path.join(d, "id_dsa.pub"))
    rsa_exists = os.path.exists(os.path.join(d, "id_rsa"))
    rsa_pub_exists = os.path.exists(os.path.join(d, "id_rsa.pub"))
    # If any of the above doesn't exist return True
    return not (dsa_exists and dsa_pub_exists
                and rsa_exists and rsa_pub_exists
                and auth_keys_exists)


def do_create_keys():
    d = os.path.join(config.template_dir, "root/.ssh")
    # Create dir if it does not exist
    if not os.path.exists(d):
        os.makedirs(d)
    a = os.path.join(d, "authorized_keys")
    # Delete old keys
    for filename in os.listdir(d):
        os.remove(os.path.join(d, filename))
    # Generate new keys
    for t in ("dsa", "rsa"):
        f = os.path.join(d, "id_" + t)
        cmd = 'ssh-keygen -q -t {0} -f {1} -N ""'.format(t, f)
        os.system(cmd)
        cmd = 'cat {0}.pub >> {1}'.format(f, a)
        os.system(cmd)


def must_create_ddns_keys():
    d = os.path.join(config.template_dir, "root/ddns")
    # Create dir if it does not exist
    if not os.path.exists(d):
        os.makedirs(d)
    key_exists = glob.glob(os.path.join(d, "Kddns*key"))
    private_exists = glob.glob(os.path.join(d, "Kddns*private"))
    bind_key_exists = os.path.exists(os.path.join(d, "ddns.key"))
    return not (key_exists and private_exists and bind_key_exists)


def find_ddns_key_files():
    d = os.path.join(config.template_dir, "root/ddns")
    keys = glob.glob(os.path.join(d, "Kddns*"))
    # Here we must have a key!
    return map(os.path.basename, keys)


def do_create_ddns_keys():
    d = os.path.join(config.template_dir, "root/ddns")
    if not os.path.exists(d):
        os.mkdir(d)
    for filename in os.listdir(d):
        os.remove(os.path.join(d, filename))
    cmd = """
dnssec-keygen -a HMAC-MD5 -b 128 -K {0} -r /dev/urandom -n USER DDNS_UPDATE
key=$(cat {0}/Kddns_update*.key | awk '{{ print $7 }}')
cat > {0}/ddns.key <<EOF
key DDNS_UPDATE {{
        algorithm HMAC-MD5.SIG-ALG.REG.INT;
        secret "$key";
}};
EOF
""".format(d)
    os.system(cmd)


def main():
    args = parse_options()

    config.init(args)
    status.init()
    context.init(args)

    create_dir(config.run_dir, False)
    create_dir(config.dns_dir, False)

    # Check if there are keys to use
    if args.command == "keygen":
        if must_create_keys() or args.force:
            do_create_keys()
        else:
            print "ssh keys found. To re-create them use --force"
        if must_create_ddns_keys() or args.force:
            do_create_ddns_keys()
        else:
            print "ddns keys found. To re-create them use --force"
        return 0
    else:
        if ((args.key_inject and not args.ssh_key and
             must_create_keys()) or must_create_ddns_keys()):
            print "No ssh/ddns keys to use. Run `snf-deploy keygen' first."
            return 1
        config.ddns_keys = find_ddns_key_files()
        config.ddns_private_key = "/root/ddns/" + config.ddns_keys[0]

    if args.command == "test":
        config.print_config()
        return 0

    if args.command == "image":
        vcluster.image()
        return 0

    if args.command == "cleanup":
        vcluster.cleanup()
        return 0

    if args.command == "packages":
        create_dir(config.package_dir, True)
        get_packages()
        return 0

    if args.command == "vcluster":
        status.reset()
        vcluster.cleanup()
        vcluster.launch()
        return 0

    if args.command == "help":
        print_help_msg(args.cmds)
        return 0

    actions = get_actions(args.command)
    fabcommand(args, actions)

    return 0

if __name__ == "__main__":
    sys.exit(main())
