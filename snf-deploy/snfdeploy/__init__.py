import json
import time
import ipaddr
import os
import signal
import time
import ConfigParser
import argparse
import sys
import re
import random
import subprocess
import imp
import ast
from snfdeploy.lib import *

def print_available_actions(command):

  if command == "keygen":
    print """
Usage: snf-deploy keygen [--force]

  Generate new ssh keys (both rsa and dsa keypairs)

  """

  if command == "vcluster":
    print """
Usage: snf-deploy vcluster

  Run the following actions concerning the local virtual cluster:

    - Download base image and create additional disk (if --create-extra-disk is passed)
    - Does all the network related actions (bridge, iptables, NAT)
    - Launches dnsmasq for dhcp server on bridge
    - Creates the virtual cluster (with kvm)

  """

  if command == "prepare":
    print """
Usage: snf-deploy prepare

  Run the following actions concerning deployment preparation:

    - Setup an internal Domain Name Server
    - Tweak hosts and add ssh keys
    - Check network setup
    - Setup apt repository and apt-get update
    - Setup the nfs server and clients among all nodes

  """

  if command == "backend":
    print """
Usage: snf-deploy backend [update]

  Run the following actions concerning a ganeti backend:

    - Create and add a backend to cyclades
    - Does all the net-infra specific actions in backend nodes
      (create/connect bridges, iptables..)
    - Does all the storage-infra specific actions in backend nodes
      depending on the --extra-disk option (create VG, enable lvm/drbd storage..)

    or

    - Update packages in an already registered backend in cyclades.

  """

  if command == "run":
    print """
Usage: snf-deploy run <action> [<action>...]

  Run any of the following fabric commands:


    Setup commands:        Init commands:                Admin commands:
      setup_apache           add_pools                     activate_user
      setup_apt              add_rapi_user                 add_backend
      setup_astakos          add_nodes                     add_image_locally
      setup_cms              astakos_loaddata              add_network
      setup_common           astakos_register_components   add_ns
      setup_cyclades         cms_loaddata                  add_user
      setup_db               cyclades_loaddata             connect_bridges
      setup_ganeti           enable_drbd                   create_bridges
      setup_gtools           init_cluster                  create_vlans
      setup_gunicorn         setup_nfs_clients             destroy_db
      setup_hosts            setup_nfs_server              get_auth_token_from_db
      setup_image_helper     update_ns_for_ganeti          get_service_details
      setup_image_host                                     gnt_instance_add
      setup_iptables                                       gnt_network_add
      setup_kamaki         Test commands:                  register_image
      setup_lvm              test                          restart_services
      setup_mq                                             setup_drbd_dparams
      setup_net_infra
      setup_network
      setup_ns
      setup_pithos
      setup_pithos_dir
      setup_router
      setup_vncauthproxy
      setup_webproject

  """

  sys.exit(1)


def create_dnsmasq_files(args, env):

  print("Customize dnsmasq..")
  out = env.dns

  hostsfile = open(out + "/dhcp-hostsfile", "w")
  optsfile = open(out + "/dhcp-optsfile", "w")
  conffile = open(out + "/conf-file", "w")

  for node, info in env.nodes_info.iteritems():
    # serve ip and hostname to nodes
    hostsfile.write("%s,%s,%s,2m\n" % (info.mac, info.ip, info.hostname))

  hostsfile.write("52:54:56:*:*:*,ignore\n")

  # Netmask
  optsfile.write("1,%s\n" % env.net.netmask)
  # Gateway
  optsfile.write("3,%s\n" % env.gateway)
  # Namesevers
  optsfile.write("6,%s\n" % "8.8.8.8")

  dnsconf = """
user=dnsmasq
bogus-priv
no-poll
no-negcache
leasefile-ro
bind-interfaces
except-interface=lo
dhcp-fqdn
no-resolv
# disable DNS
port=0
""".format(env.ns.ip)

  dnsconf += """
# serve domain and search domain for resolv.conf
domain={5}
interface={0}
dhcp-hostsfile={1}
dhcp-optsfile={2}
dhcp-range={0},{4},static,2m
""".format(env.bridge, hostsfile.name, optsfile.name,
           env.domain, env.net.network, env.domain)

  conffile.write(dnsconf)

  hostsfile.close()
  optsfile.close()
  conffile.close()


def cleanup(args, env):
  print("Cleaning up bridge, NAT, resolv.conf...")

  for f in os.listdir(env.run):
    if re.search(".pid$", f):
      check_pidfile(os.path.join(env.run, f))

  create_dir(env.run, True)
  # create_dir(env.cmd, True)
  cmd = """
  iptables -t nat -D POSTROUTING -s {0} -o {1} -j MASQUERADE
  echo 0 > /proc/sys/net/ipv4/ip_forward
  iptables -D INPUT -i {2} -j ACCEPT
  iptables -D FORWARD -i {2} -j ACCEPT
  iptables -D OUTPUT -o {2} -j ACCEPT
  """.format(env.subnet, get_default_route()[1], env.bridge)
  os.system(cmd)

  cmd = """
  ip link show {0} && ip addr del {1}/{2} dev {0}
  sleep 1
  ip link set {0} down
  sleep 1
  brctl delbr {0}
  """.format(env.bridge, env.gateway, env.net.prefixlen)
  os.system(cmd)


def network(args, env):
  print("Create bridge..Add gateway IP..Activate NAT..Append NS options to resolv.conf")

  cmd = """
  ! ip link show {0} && brctl addbr {0} && ip link set {0} up
  sleep 1
  ip link set promisc on dev {0}
  ip addr add {1}/{2} dev {0}
  """.format(env.bridge, env.gateway, env.net.prefixlen)
  os.system(cmd)

  cmd = """
  iptables -t nat -A POSTROUTING -s {0} -o {1} -j MASQUERADE
  echo 1 > /proc/sys/net/ipv4/ip_forward
  iptables -I INPUT 1 -i {2} -j ACCEPT
  iptables -I FORWARD 1 -i {2} -j ACCEPT
  iptables -I OUTPUT 1 -o {2} -j ACCEPT
  """.format(env.subnet, get_default_route()[1], env.bridge)
  os.system(cmd)


def image(args, env):
  if env.os == "ubuntu":
    url = env.ubuntu_image_url
  else:
    url = env.squeeze_image_url

  disk0 = "{0}/{1}.disk0".format(env.images, env.os)
  disk1 = "{0}/{1}.disk1".format(env.images, env.os)

  if url and not os.path.exists(disk0):
    cmd = "wget {0} -O {1}".format(url, disk0)
    os.system(cmd)

  if ast.literal_eval(env.create_extra_disk) and not os.path.exists(disk1):
    if env.lvg:
      cmd = "lvcreate -L30G -n{0}.disk1 {1}".format(env.os, env.lvg)
      os.system(cmd)
      cmd = "ln -s /dev/{0}/{1}.disk1 {2}".format(env.lvg, env.os, disk1)
      os.system(cmd)
    else:
      cmd = "dd if=/dev/zero of={0} bs=10M count=3000".format(disk1)
      os.system(cmd)


def fabcommand(args, env, actions, nodes=[]):
  levels = ["status", "aborts", "warnings", "running",
            "stdout", "stderr", "user", "debug"]

  level_aliases = {
    "output": ["stdout", "stderr"],
    "everything": ["warnings", "running", "user", "output"]
    }

  hide = ",".join(level_aliases["everything"])
  show = None

  if args.verbose == 1:
    show = ",".join(levels[:3])
    hide = ",".join(levels[3:])
  elif args.verbose == 2:
    show = ",".join(levels[:4])
    hide = ",".join(levels[4:])
  elif args.verbose >= 3 or args.debug:
    show = ",".join(levels)
    hide = None

  if args.ssh_key:
    fabcmd = "fab -i %s " % args.ssh_key
  else:
    fabcmd = "fab "

  fabcmd += " --fabfile {4}/fabfile.py \
setup_env:confdir={0},packages={1},templates={2},cluster_name={3},\
autoconf={5},disable_colors={6},key_inject={7} \
".format(args.confdir, env.packages, env.templates, args.cluster_name,
         env.lib, args.autoconf, args.disable_colors, args.key_inject)

  if nodes:
    hosts = [env.nodes_info[n].hostname for n in nodes]
    actions = [a + ':hosts="%s"' % ";".join(hosts) for a in actions]

  extra = " ".join(actions)

  fabcmd += extra

  if show:
    fabcmd += " --show %s " % show
  if hide:
    fabcmd += " --hide %s " % hide

  # print("snf-deploy run " + " ".join(actions) + " -vvv")
  print(fabcmd)

  if not args.dry_run:
    ret = os.system(fabcmd)
    if ret != 0:
        status = "exit with status %s" % ret
        sys.exit(status)


def cluster(args, env):
  for hostname, mac in env.node2mac.iteritems():
    launch_vm(args, env, hostname, mac)

  time.sleep(30)
  os.system("reset")


def launch_vm(args, env, hostname, mac):
  check_pidfile("%s/%s.pid" % (env.run, hostname))

  print("Launching cluster node {0}..".format(hostname))
  os.environ["BRIDGE"] = env.bridge
  if args.vnc:
    graphics = "-vnc :{0}".format(random.randint(1, 1000))
  else:
    graphics = "-nographic"

  disks = """ \
-drive file={0}/{1}.disk0,format=raw,if=none,id=drive0,snapshot=on \
-device virtio-blk-pci,drive=drive0,id=virtio-blk-pci.0 \
  """.format(env.images, env.os)

  if ast.literal_eval(env.create_extra_disk):
    disks += """ \
-drive file={0}/{1}.disk1,format=raw,if=none,id=drive1,snapshot=on \
-device virtio-blk-pci,drive=drive1,id=virtio-blk-pci.1 \
  """.format(env.images, env.os)


  ifup = env.lib + "/ifup"
  nics = """ \
-netdev tap,id=netdev0,script={0},downscript=no \
-device virtio-net-pci,mac={1},netdev=netdev0,id=virtio-net-pci.0 \
-netdev tap,id=netdev1,script={0},downscript=no \
-device virtio-net-pci,mac={2},netdev=netdev1,id=virtio-net-pci.1 \
-netdev tap,id=netdev2,script={0},downscript=no \
-device virtio-net-pci,mac={3},netdev=netdev2,id=virtio-net-pci.2 \
  """.format(ifup, mac, randomMAC(), randomMAC())

  cmd = """
/usr/bin/kvm -name {0} -pidfile {1}/{0}.pid -balloon virtio -daemonize \
-monitor unix:{1}/{0}.monitor,server,nowait -usbdevice tablet -boot c \
{2} \
{3} \
-m {4} -smp {5} {6} \
  """.format(hostname, env.run, disks, nics, args.mem, args.smp, graphics)
  print cmd
  os.system(cmd)


def dnsmasq(args, env):
  check_pidfile(env.run + "/dnsmasq.pid")
  cmd = "dnsmasq --pid-file={0}/dnsmasq.pid --conf-file={1}/conf-file".format(env.run, env.dns)
  os.system(cmd)


def get_packages(args, env):
  if env.package_url:
    os.system("rm {0}/*.deb".format(env.packages))
    os.system("wget -r --level=1 -nH --no-parent --cut-dirs=4 {0} -P {1}".format(env.package_url, env.packages))


def parse_options():
  parser = argparse.ArgumentParser()

  # Directories to load/store config
  parser.add_argument("-c", dest="confdir",
                      default="/etc/snf-deploy",
                      help="Directory to find default configuration")
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
                      help="Memory for every virutal node")
  parser.add_argument("--smp", dest="smp",
                      default=1,
                      help="Virtual CPUs for every virtual node")
  parser.add_argument("--vnc", dest="vnc",
                      default=False, action="store_true",
                      help="Wheter virtual nodes will have a vnc console or not")
  parser.add_argument("--force", dest="force",
                      default=False, action="store_true",
                      help="Force the creation of new ssh key pairs")

  parser.add_argument("-i", "--ssh-key", dest="ssh_key",
                      default=None,
                      help="Path of an existing ssh key to use")

  parser.add_argument("--no-key-inject", dest="key_inject",
                      default=True, action="store_false",
                      help="Whether to inject ssh key pairs to hosts")

  # backend related options
  parser.add_argument("--cluster-name", dest="cluster_name",
                      default="ganeti1",
                      help="The cluster name in ganeti.conf")

  # backend related options
  parser.add_argument("--cluster-node", dest="cluster_node",
                      default=None,
                      help="The node to add to the existing cluster")

  # available commands
  parser.add_argument("command", type=str,
                      choices=["packages", "vcluster", "prepare",
                               "synnefo", "backend", "ganeti",
                               "run", "cleanup", "test",
                               "all", "add", "keygen"],
                      help="Run on of the supported deployment commands")

  # available actions for the run command
  parser.add_argument("actions", type=str, nargs="*",
                      help="Run one or more of the supported subcommands")

  # disable colors in terminal
  parser.add_argument("--disable-colors", dest="disable_colors", default=False,
                      action="store_true", help="Disable colors in terminal")

  return parser.parse_args()


def get_actions(*args):
    actions = {
      # prepare actions
      "ns":  ["setup_ns", "setup_resolv_conf"],
      "hosts": ["setup_hosts", "add_keys"],
      "check": ["check_dhcp", "check_dns", "check_connectivity", "check_ssh"],
      "apt": ["apt_get_update", "setup_apt"],
      "nfs": ["setup_nfs_server", "setup_nfs_clients"],
      "prepare":  [
        "setup_hosts", "add_keys",
        "setup_ns", "setup_resolv_conf",
        "check_dhcp", "check_dns", "check_connectivity", "check_ssh",
        "apt_get_update", "setup_apt",
        "setup_nfs_server", "setup_nfs_clients"
        ],
      # synnefo actions
      "synnefo": [
        "setup_mq", "setup_db",
        "setup_astakos",
        #TODO: astakos-quota fails if no user is added.
        #      add_user fails if no groups found
        "astakos_loaddata", "add_user", "activate_user",
        "astakos_register_components",
        "setup_cms", "cms_loaddata",
        "setup_pithos",
        "setup_vncauthproxy",
        "setup_cyclades", "cyclades_loaddata", "add_pools",
        "export_services", "import_services",
        "setup_kamaki", "upload_image", "register_image",
        "setup_burnin"
        ],
      "supdate": [
        "apt_get_update", "setup_astakos",
        "setup_cms", "setup_pithos", "setup_cyclades"
        ],
      # backend actions
      "backend": [
        "setup_hosts",
        "update_ns_for_ganeti",
        "setup_ganeti", "init_cluster",
        "add_rapi_user", "add_nodes",
        "setup_image_host", "setup_image_helper",
        "setup_network",
        "setup_gtools", "add_backend", "add_network",
        "setup_lvm", "enable_lvm",
        "enable_drbd", "setup_drbd_dparams",
        "setup_net_infra", "setup_iptables", "setup_router",
        ],
      "bstorage": [
        "setup_lvm", "enable_lvm",
        "enable_drbd", "setup_drbd_dparams"
        ],
      "bnetwork": ["setup_net_infra", "setup_iptables", "setup_router"],
      "bupdate": [
        "apt_get_update", "setup_ganeti", "setup_image_host", "setup_image_helper",
        "setup_network", "setup_gtools"
        ],
      # ganeti actions
      "ganeti": [
        "update_ns_for_ganeti",
        "setup_ganeti", "init_cluster", "add_nodes",
        "setup_image_host", "setup_image_helper", "add_image_locally",
        "debootstrap", "setup_net_infra",
        "setup_lvm", "enable_lvm", "enable_drbd", "setup_drbd_dparams",
        ],
      "gupdate": ["setup_apt", "setup_ganeti"],
      "gdestroy": ["destroy_cluster"],
      }

    ret = []
    for x in args:
      ret += actions[x]

    return ret


def must_create_keys(force, env):
    """Check if we need to create ssh keys

    If force is true we are going to overide the old keys.
    Else if there are already generated keys to use, don't create new ones.

    """
    if force:
        return True
    d = os.path.join(env.templates, "root/.ssh")
    auth_keys_exists = os.path.exists(os.path.join(d, "authorized_keys"))
    dsa_exists = os.path.exists(os.path.join(d, "id_dsa"))
    dsa_pub_exists = os.path.exists(os.path.join(d, "id_dsa.pub"))
    rsa_exists = os.path.exists(os.path.join(d, "id_rsa"))
    rsa_pub_exists = os.path.exists(os.path.join(d, "id_rsa.pub"))
    # If any of the above doesn't exist return True
    return not (dsa_exists and dsa_pub_exists
                and rsa_exists and rsa_pub_exists
                and auth_keys_exists)


def do_create_keys(args, env):
  d = os.path.join(env.templates, "root/.ssh")
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

def add_node(args, env):
    actions = [
      "update_ns_for_node:" + args.cluster_node,
      ]
    fabcommand(args, env, actions)
    actions = [
      "setup_resolv_conf",
      "apt_get_update",
      "setup_apt",
      "setup_hosts",
      "add_keys",
      ]
    fabcommand(args, env, actions, [args.cluster_node])

    actions = get_actions("check")
    fabcommand(args, env, actions)

    actions = [
      "setup_nfs_clients",
      "setup_ganeti",
      "setup_image_host", "setup_image_helper", "setup_network", "setup_gtools",
      ]
    fabcommand(args, env, actions, [args.cluster_node])

    actions = [
      "add_node:" + args.cluster_node,
      ]
    fabcommand(args, env, actions)

    actions = [
      "setup_lvm", "enable_drbd",
      "setup_net_infra", "setup_iptables",
      ]
    fabcommand(args, env, actions, [args.cluster_node])

def main():
  args = parse_options()

  conf = Conf.configure(args.confdir, args.cluster_name, args, args.autoconf)
  env = Env(conf)

  create_dir(env.run, False)
  create_dir(env.dns, False)

  # Check if there are keys to use
  if args.command == "keygen":
    if must_create_keys(args.force, env):
      do_create_keys(args, env)
      return 0
    else:
      print "Keys already existed.. aborting"
      return 1
  else:
    if (args.key_inject and (args.ssh_key is None)
        and must_create_keys(False, env)):
      print "No ssh keys to use. Run `snf-deploy keygen' first."
      return 1

  if args.command == "test":
    conf.print_config()

  if args.command == "cleanup":
    cleanup(args, env)

  if args.command == "packages":
    create_dir(env.packages, True)
    get_packages(args, env)

  if args.command == "vcluster":
    image(args, env)
    network(args, env)
    create_dnsmasq_files(args, env)
    dnsmasq(args, env)
    cluster(args, env)

  if args.command == "prepare":
    actions = get_actions("prepare")
    fabcommand(args, env, actions)

  if args.command == "synnefo":
    actions = get_actions("synnefo")
    fabcommand(args, env, actions)

  if args.command == "backend":
    actions = get_actions("backend")
    fabcommand(args, env, actions)

  if args.command == "ganeti":
    actions = get_actions("ganeti")
    fabcommand(args, env, actions)




  if args.command == "all":
    actions = get_actions("prepare", "synnefo", "backend")
    fabcommand(args, env, actions)

  if args.command == "add":
    if args.cluster_node:
      add_node(args, env)
    else:
      actions = get_actions("backend")
      fabcommand(args, env, actions)


  if args.command == "run":
    if not args.actions:
      print_available_actions(args.command)
    else:
      fabcommand(args, env, args.actions)


if __name__ == "__main__":
  sys.exit(main())
