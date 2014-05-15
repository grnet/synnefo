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

import time
import os
import sys
import re
import random
from snfdeploy import config
from snfdeploy import context
from snfdeploy.lib import check_pidfile, create_dir, get_default_route, \
    random_mac


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
    out = config.dns_dir

    hostsfile = open(out + "/dhcp-hostsfile", "w")
    optsfile = open(out + "/dhcp-optsfile", "w")
    conffile = open(out + "/conf-file", "w")

    for node in ctx.nodes:
        info = config.get_info(node=node)
        # serve ip and name to nodes
        hostsfile.write("%s,%s,%s,2m\n" % (info.mac, info.ip, info.name))

    hostsfile.write("52:54:56:*:*:*,ignore\n")

    # Netmask
    optsfile.write("1,%s\n" % config.net.netmask)
    # Gateway
    optsfile.write("3,%s\n" % config.gateway)
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
""".format(ctx.ns.ip)

    dnsconf += """
# serve domain and search domain for resolv.conf
domain={5}
interface={0}
dhcp-hostsfile={1}
dhcp-optsfile={2}
dhcp-range={0},{4},static,2m
""".format(config.bridge, hostsfile.name, optsfile.name,
           info.domain, config.net.network, info.domain)

    conffile.write(dnsconf)

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
    os.system(cmd)

    print("Deleting bridge %s.." % config.bridge)
    cmd = """
    ip link show {0} && ip addr del {1}/{2} dev {0}
    sleep 1
    ip link set {0} down
    sleep 1
    brctl delbr {0}
    """.format(config.bridge, config.gateway, config.net.prefixlen)
    os.system(cmd)


def network():
    print("Creating bridge %s.." % config.bridge)
    print("Add gateway IP %s.." % config.gateway)

    cmd = """
    ! ip link show {0} && brctl addbr {0} && ip link set {0} up
    sleep 1
    ip link set promisc on dev {0}
    ip addr add {1}/{2} dev {0}
    """.format(config.bridge, config.gateway, config.net.prefixlen)
    os.system(cmd)

    print("Activate NAT..")
    cmd = """
    iptables -t nat -A POSTROUTING -s {0} -o {1} -j MASQUERADE
    echo 1 > /proc/sys/net/ipv4/ip_forward
    iptables -I INPUT 1 -i {2} -j ACCEPT
    iptables -I FORWARD 1 -i {2} -j ACCEPT
    iptables -I OUTPUT 1 -o {2} -j ACCEPT
    """.format(config.subnet, get_default_route()[1], config.bridge)
    os.system(cmd)


def image():
    # FIXME: Create a clean wheezy image and use it for vcluster
    if config.os == "ubuntu":
        url = config.ubuntu_image_url
    else:
        url = config.squeeze_image_url

    disk0 = "{0}/{1}.disk0".format(config.image_dir, config.os)
    disk1 = "{0}/{1}.disk1".format(config.image_dir, config.os)

    if url and not os.path.exists(disk0):
        cmd = "wget {0} -O {1}".format(url, disk0)
        os.system(cmd)

    if config.create_extra_disk and not os.path.exists(disk1):
        if config.lvg:
            cmd = """
lvcreate -L30G -n{0}.disk1 {1}
""".format(config.os, config.lvg)
            os.system(cmd)
            cmd = """
ln -s /dev/{0}/{1}.disk1 {2}
""".format(config.lvg, config.os, disk1)
            os.system(cmd)
        else:
            cmd = "dd if=/dev/zero of={0} bs=10M count=3000".format(disk1)
            os.system(cmd)


def cluster(ctx):
    for node in ctx.nodes:
        node_info = config.get_info(node=node)
        _launch_vm(node_info.name, node_info.mac)

    # TODO: check if the cluster is up and running instead of sleeping 30 secs
    time.sleep(30)
    os.system("reset")


def _launch_vm(name, mac):
    check_pidfile("%s/%s.pid" % (config.run_dir, name))

    print("Launching cluster node {0}..".format(name))
    os.environ["BRIDGE"] = config.bridge
    if config.vnc:
        graphics = "-vnc :{0}".format(random.randint(1, 1000))
    else:
        graphics = "-nographic"

    disks = """ \
-drive file={0}/{1}.disk0,format=raw,if=none,id=drive0,snapshot=on \
-device virtio-blk-pci,drive=drive0,id=virtio-blk-pci.0 \
""".format(config.image_dir, config.os)

    if config.create_extra_disk:
        disks += """ \
-drive file={0}/{1}.disk1,format=raw,if=none,id=drive1,snapshot=on \
-device virtio-blk-pci,drive=drive1,id=virtio-blk-pci.1 \
""".format(config.image_dir, config.os)

    ifup = config.lib_dir + "/ifup"
    nics = """ \
-netdev tap,id=netdev0,script={0},downscript=no \
-device virtio-net-pci,mac={1},netdev=netdev0,id=virtio-net-pci.0 \
-netdev tap,id=netdev1,script={0},downscript=no \
-device virtio-net-pci,mac={2},netdev=netdev1,id=virtio-net-pci.1 \
-netdev tap,id=netdev2,script={0},downscript=no \
-device virtio-net-pci,mac={3},netdev=netdev2,id=virtio-net-pci.2 \
""".format(ifup, mac, random_mac(), random_mac())

    cmd = """
/usr/bin/kvm -name {0} -pidfile {1}/{0}.pid -balloon virtio -daemonize \
-monitor unix:{1}/{0}.monitor,server,nowait -usbdevice tablet -boot c \
{2} \
{3} \
-m {4} -smp {5} {6} \
""".format(name, config.run_dir, disks, nics, config.mem, config.smp, graphics)
    print cmd
    os.system(cmd)


def dnsmasq():
    check_pidfile(config.run_dir + "/dnsmasq.pid")
    cmd = "dnsmasq --pid-file={0}/dnsmasq.pid --conf-file={1}/conf-file"\
        .format(config.run_dir, config.dns_dir)
    os.system(cmd)


def launch():
    ctx = context.Context()
    assert len(ctx.clusters) == 1
    assert ctx.cluster
    assert ctx.nodes
    image()
    network()
    create_dnsmasq_files(ctx)
    dnsmasq()
    cluster(ctx)
