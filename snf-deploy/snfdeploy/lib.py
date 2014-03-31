#!/usr/bin/python

# Copyright (C) 2013, 2014 GRNET S.A. All rights reserved.
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
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A. OR
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

import time
import ipaddr
import os
import signal
import ConfigParser
import sys
import re
import random
import subprocess
import imp


HEADER = '\033[95m'
OKBLUE = '\033[94m'
OKGREEN = '\033[92m'
WARNING = '\033[93m'
FAIL = '\033[91m'
ENDC = '\033[0m'


def disable_color():
    global HEADER
    global OKBLUE
    global OKGREEN
    global WARNING
    global FAIL
    global ENDC

    HEADER = ''
    OKBLUE = ''
    OKGREEN = ''
    WARNING = ''
    FAIL = ''
    ENDC = ''


if not sys.stdout.isatty():
    disable_color()


class Host(object):
    def __init__(self, hostname, ip, mac, domain, os, passwd):
        self.hostname = hostname
        self.ip = ip
        self.mac = mac
        self.domain = domain
        self.os = os
        self.passwd = passwd

    @property
    def fqdn(self):
        return self.hostname + "." + self.domain

    @property
    def arecord(self):
        return self.fqdn + " 300 A " + self.ip

    @property
    def ptrrecord(self):
        return ".".join(raddr(self.ip)) + ".in-addr.arpa 300 PTR " + self.fqdn

    @property
    def cnamerecord(self):
        return ""


class Alias(Host):
    def __init__(self, host, alias):
        super(Alias, self).__init__(host.hostname, host.ip, host.mac,
                                    host.domain, host.os, host.passwd)
        self.alias = alias

    @property
    def cnamerecord(self):
        return self.fqdn + " 300 CNAME " + self.hostname + "." + self.domain

    @property
    def ptrrecord(self):
        return ""

    @property
    def arecord(self):
        return ""

    @property
    def fqdn(self):
        return self.alias + "." + self.domain


class Env(object):

    def update_packages(self, os):
        for section in self.conf.files[os]:
            self.evaluate(os, section)

    def evaluate(self, filename, section):
        for k, v in self.conf.get_section(filename, section):
            setattr(self, k, v)

    def __init__(self, conf):
        self.conf = conf
        for f, sections in conf.files.iteritems():
            for s in sections:
                self.evaluate(f, s)

        self.node2hostname = dict(conf.get_section("nodes", "hostnames"))
        self.node2ip = dict(conf.get_section("nodes", "ips"))
        self.node2mac = dict(conf.get_section("nodes", "macs"))
        self.node2os = dict(conf.get_section("nodes", "os"))
        self.node2passwd = dict(conf.get_section("nodes", "passwords"))

        self.hostnames = [self.node2hostname[n]
                          for n in self.nodes.split(",")]

        self.ips = [self.node2ip[n]
                    for n in self.nodes.split(",")]

        self.net = ipaddr.IPNetwork(self.subnet)

        self.nodes_info = {}
        self.hosts_info = {}
        self.ips_info = {}
        for node in self.nodes.split(","):
            host = Host(self.node2hostname[node],
                        self.node2ip[node],
                        self.node2mac[node], self.domain, self.node2os[node],
                        self.node2passwd[node])

            self.nodes_info[node] = host
            self.hosts_info[host.hostname] = host
            self.ips_info[host.ip] = host

        self.cluster = Host(self.cluster_name, self.cluster_ip, None,
                            self.domain, None, None)

        # This is needed because "".split(",") -> ['']
        if self.cluster_nodes:
            self.cluster_nodes = self.cluster_nodes.split(",")
        else:
            self.cluster_nodes = []

        self.cluster_hostnames = [self.node2hostname[n]
                                  for n in self.cluster_nodes]

        self.cluster_ips = [self.node2ip[n]
                            for n in self.cluster_nodes]

        self.master = self.nodes_info[self.master_node]

        self.roles_info = {}
        for role, node in conf.get_section("synnefo", "roles"):
            self.roles_info[role] = Alias(self.nodes_info[node], role)
            setattr(self, role, self.roles_info[role])

        self.astakos = self.accounts
        # This is the nodes that get nfs mount points
        self.mount = self.ips[:]
        self.mount.remove(self.pithos.ip)


class Status(object):
    STATUSES = [
        "check",
        "prepare",
        "install",
        "restart",
        "initialize",
        "test",
        "ok",
        ]

    def create_section(self, ip):
        try:
            section = self.config.items(ip, True)
        except ConfigParser.NoSectionError:
            self.config.add_section(ip)

    def __init__(self, env):
        self.config = ConfigParser.ConfigParser()
        self.config.optionxform = str
        self.statusfile = os.path.join(env.state, "snf_deploy_status")
        self.config.read(self.statusfile)

    def check_status(self, ip, component_class):
        try:
            return self.config.get(ip, component_class.__name__, True)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return None

    def update_status(self, ip, component_class, status):
        self.create_section(ip)
        self.config.set(ip, component_class.__name__, status)

    def write_status(self):
        with open(self.statusfile, 'wb') as configfile:
            self.config.write(configfile)


class Conf(object):

    files = {
        "nodes": ["network", "info"],
        "deploy": ["dirs", "packages", "keys", "options"],
        "vcluster": ["cluster", "image", "network"],
        "synnefo": ["cred", "synnefo", "roles"],
        "wheezy": ["debian", "ganeti", "synnefo", "other", "archip"],
    }
    confdir = "/etc/snf-deploy"

    def get_ganeti(self, cluster_name):
        self.files["ganeti"] = [cluster_name]

    def __init__(self, args):
        self.confdir = args.confdir
        self.get_ganeti(args.cluster_name)
        for f in self.files.keys():
            setattr(self, f, self.read_config(f))
        for f, sections in self.files.iteritems():
            for s in sections:
                for k, v in self.get_section(f, s):
                    if getattr(args, k, None):
                        self.set(f, s, k, getattr(args, k))
        # Override conf file settings if
        # --templates-dir and --state-dir args are passed
        if args.templatesdir:
            self.deploy.set("dirs", "templates", args.templatesdir)
        if args.statedir:
            self.deploy.set("dirs", "state", args.statedir)
        if args.autoconf:
            self.autoconf()

    def autoconf(self):
        #domain = get_domain()
        #if domain:
        #    self.nodes.set("network", "domain", get_domain())
        # self.nodes.set("network", "subnet", "/".join(get_netinfo()))
        # self.nodes.set("network", "gateway", get_default_route()[0])
        self.nodes.set("hostnames", "node1", get_hostname())
        self.nodes.set("ips", "node1", get_netinfo()[0])
        self.nodes.set("info", "nodes", "node1")
        self.nodes.set("info", "public_iface", get_default_route()[1])

    def read_config(self, f):
        config = ConfigParser.ConfigParser()
        config.optionxform = str
        filename = os.path.join(self.confdir, f) + ".conf"
        config.read(filename)
        return config

    def set(self, conf, section, option, value):
        c = getattr(self, conf)
        c.set(section, option, value)

    def get(self, conf, section, option):
        c = getattr(self, conf)
        return c.get(section, option, True)

    def get_section(self, conf, section):
        c = getattr(self, conf)
        return c.items(section, True)

    def print_config(self):
        for f in self.files.keys():
            getattr(self, f).write(sys.stdout)


def debug(host, msg, info=""):

    print " ".join([HEADER, host, OKBLUE, msg, OKGREEN, info, ENDC])


def check_pidfile(pidfile):
    print("Checking pidfile " + pidfile)
    try:
        f = open(pidfile, "r")
        pid = f.readline()
        os.kill(int(pid), signal.SIGKILL)
        f.close()
        os.remove(pidfile)
        time.sleep(5)
    except:
        pass


def random_mac():
    mac = [0x52, 0x54, 0x56,
           random.randint(0x00, 0xff),
           random.randint(0x00, 0xff),
           random.randint(0x00, 0xff)]
    return ':'.join(map(lambda x: "%02x" % x, mac))


def create_dir(d, clean=False):
    os.system("mkdir -p " + d)
    if clean:
        try:
            os.system("rm -f %s/*" % d)
        except:
            pass


def get_netinfo():
    _, pdev = get_default_route()
    r = re.compile(".*inet (\S+)/(\S+).*")
    s = subprocess.Popen(['ip', 'addr', 'show', 'dev', pdev],
                         stdout=subprocess.PIPE)

    for line in s.stdout.readlines():
        match = r.search(line)
        if match:
            ip, size = match.groups()
            break

    return ip, size


def get_hostname():
    s = subprocess.Popen(['hostname', '-s'], stdout=subprocess.PIPE)
    return s.stdout.readline().strip()


def get_domain():
    s = subprocess.Popen(['hostname', '-d'], stdout=subprocess.PIPE)
    return s.stdout.readline().strip()


def get_default_route():
    r = re.compile("default via (\S+) dev (\S+)")
    s = subprocess.Popen(['ip', 'route'], stdout=subprocess.PIPE)
    for line in s.stdout.readlines():
        match = r.search(line)
        if match:
            gw, dev = match.groups()
            break

    return (gw, dev)


def import_conf_file(filename, directory):
    return imp.load_module(filename, *imp.find_module(filename, [directory]))


def raddr(addr):
    return list(reversed(addr.replace("/", "-").split(".")))
