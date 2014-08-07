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

import re
import os
import sys
import random
import subprocess
import ipaddr
from snfdeploy import config
from snfdeploy import context
from snfdeploy import constants
from snfdeploy.lib import check_pidfile, create_dir, get_default_route, \
    random_mac, get_netinfo


def runcmd(cmd):
    if config.dry_run:
        print cmd
    else:
        os.system(cmd)


def help():

    print """
Usage: snf-deploy vcluster

  Run the following actions concerning the local virtual cluster:

    - Downloads base image and creates additional disk \
(if --create-extra-disk is passed)
    - Does all the network related actions (bridge, iptables, NAT)
    - Launches dnsmasq for dhcp server on bridge
    - Creates the virtual cluster (with kvm)

    """
    sys.exit(0)


def create_dnsmasq_files(ctx):

    print("Customize dnsmasq..")

    hosts = opts = conf = "\n"
    hostsf = os.path.join(config.dns_dir, "dhcp-hostsfile")
    optsf = os.path.join(config.dns_dir, "dhcp-optsfile")
    conff = os.path.join(config.dns_dir, "conf-file")

    for node in ctx.all_nodes:
        info = config.get_info(node=node)
        if ipaddr.IPAddress(info.ip) not in config.net:
            raise Exception("%s's IP outside vcluster's network." % node)
        # serve ip and name to nodes
        hosts += "%s,%s,%s,2m\n" % (info.mac, info.ip, info.name)

    hosts += "52:54:56:*:*:*,ignore\n"

    opts = """
# Netmask
1,{0}
# Gateway
3,{1}
# Nameservers
6,{2}
""".format(config.net.netmask, config.gateway, constants.EXTERNAL_PUBLIC_DNS)

    conf = """
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
""".format(ctx.ns.ip)

    conf += """
# serve domain and search domain for resolv.conf
domain={5}
interface={0}
dhcp-hostsfile={1}
dhcp-optsfile={2}
dhcp-range={0},{4},static,2m
""".format(config.bridge, hostsf, optsf,
           info.domain, config.net.network, info.domain)

    if config.dry_run:
        print hostsf, hosts
        print optsf, opts
        print conff, conf
    else:
        hostsfile = open(hostsf, "w")
        optsfile = open(optsf, "w")
        conffile = open(conff, "w")

        hostsfile.write(hosts)
        optsfile.write(opts)
        conffile.write(conf)

        hostsfile.close()
        optsfile.close()
        conffile.close()


def cleanup():
    print("Stopping processes..")
    for f in os.listdir(config.run_dir):
        if re.search(".pid$", f):
            check_pidfile(os.path.join(config.run_dir, f))

    create_dir(config.run_dir, True)
    # create_dir(env.cmd, True)

    print("Reseting NAT..")
    cmd = """
    iptables -t nat -D POSTROUTING -s {0} -o {1} -j MASQUERADE
    echo 0 > /proc/sys/net/ipv4/ip_forward
    iptables -D INPUT -i {2} -j ACCEPT
    iptables -D FORWARD -i {2} -j ACCEPT
    iptables -D OUTPUT -o {2} -j ACCEPT
    """.format(config.subnet, get_default_route()[1], config.bridge)
    runcmd(cmd)

    print("Deleting bridge %s.." % config.bridge)
    cmd = """
    ip link show {0} && ip addr del {1}/{2} dev {0}
    sleep 1
    ip link set {0} down
    sleep 1
    brctl delbr {0}
    """.format(config.bridge, config.gateway, config.net.prefixlen)
    runcmd(cmd)


def network():
    print("Creating bridge %s.." % config.bridge)
    print("Add gateway IP %s.." % config.gateway)

    cmd = """
    ! ip link show {0} && brctl addbr {0} && ip link set {0} up
    sleep 1
    ip link set promisc on dev {0}
    ip addr add {1}/{2} dev {0}
    """.format(config.bridge, config.gateway, config.net.prefixlen)
    runcmd(cmd)

    print("Activate NAT..")
    cmd = """
    iptables -t nat -A POSTROUTING -s {0} -o {1} -j MASQUERADE
    echo 1 > /proc/sys/net/ipv4/ip_forward
    iptables -I INPUT 1 -i {2} -j ACCEPT
    iptables -I FORWARD 1 -i {2} -j ACCEPT
    iptables -I OUTPUT 1 -o {2} -j ACCEPT
    """.format(config.subnet, get_default_route()[1], config.bridge)
    runcmd(cmd)


def image():
    disk0 = os.path.join(config.vcluster_dir, "disk0")
    disk1 = os.path.join(config.vcluster_dir, "disk1")

    create_dir(config.vcluster_dir, False)

    env = os.environ.copy()
    env.update({
        "DISK0": disk0,
        "DISK0_SIZE": config.disk0_size,
        "DISK1": disk1,
        "DISK1_SIZE": config.disk1_size,
        })
    cmd = os.path.join(config.lib_dir, "mkimage.sh")

    subprocess.Popen([cmd], env=env)


def cluster(ctx):
    vms = []
    for node in ctx.all_nodes:
        node_info = config.get_info(node=node)
        vnc = _launch_vm(node_info.name, node_info.mac)
        vms.append((node_info, vnc))

    runcmd("reset")
    for vm, port in vms:
        if port:
            vnc = "vncviewer %s:%s" % (get_netinfo()[0],  5900 + port)
        else:
            vnc = "no vnc"
        print "%s: ssh root@%s or %s" % (vm.name, vm.ip, vnc)


def _launch_vm(name, mac):
    check_pidfile("%s/%s.pid" % (config.run_dir, name))

    disk0 = os.path.join(config.vcluster_dir, "disk0")
    disk1 = os.path.join(config.vcluster_dir, "disk1")

    print("Launching cluster node {0}..".format(name))
    os.environ["BRIDGE"] = config.bridge
    if config.vnc:
        random_vnc_port = random.randint(1, 1000)
        graphics = "-vnc :{0}".format(random_vnc_port)
    else:
        random_vnc_port = None
        graphics = "-nographic"

    disks = """ \
-drive file={0},format=raw,if=none,id=drive0,snapshot=on \
-device virtio-blk-pci,drive=drive0,id=virtio-blk-pci.0 \
-drive file={1},format=raw,if=none,id=drive1,snapshot=on \
-device virtio-blk-pci,drive=drive1,id=virtio-blk-pci.1 \
""".format(disk0, disk1)

    ifup = os.path.join(config.lib_dir, "ifup")
    nics = """ \
-netdev tap,id=netdev0,script={0},downscript=no \
-device virtio-net-pci,mac={1},netdev=netdev0,id=virtio-net-pci.0 \
-netdev tap,id=netdev1,script={0},downscript=no \
-device virtio-net-pci,mac={2},netdev=netdev1,id=virtio-net-pci.1 \
-netdev tap,id=netdev2,script={0},downscript=no \
-device virtio-net-pci,mac={3},netdev=netdev2,id=virtio-net-pci.2 \
""".format(ifup, mac, random_mac(), random_mac())

    kernel = """ \
--kernel /boot/vmlinuz-3.2.0-4-amd64 \
--initrd /boot/initrd.img-3.2.0-4-amd64 \
--append "root=/dev/vda1 ro console=ttyS0,38400" \
"""

    cmd = """
/usr/bin/kvm -name {0} -pidfile {1}/{0}.pid -balloon virtio -daemonize \
-monitor unix:{1}/{0}.monitor,server,nowait -usbdevice tablet -boot c \
{2} \
{3} \
-m {4} -smp {5} {6} {7} \
""".format(name, config.run_dir, disks, nics,
           config.mem, config.smp, graphics, kernel)

    runcmd(cmd)

    return random_vnc_port


def dnsmasq():
    check_pidfile(config.run_dir + "/dnsmasq.pid")
    cmd = "dnsmasq --pid-file={0}/dnsmasq.pid --conf-file={1}/conf-file"\
        .format(config.run_dir, config.dns_dir)
    runcmd(cmd)


def launch():
    ctx = context.Context()
    assert len(ctx.clusters) == 1
    assert ctx.all_nodes
    network()
    create_dnsmasq_files(ctx)
    dnsmasq()
    cluster(ctx)
