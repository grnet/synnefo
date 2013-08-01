#!/usr/bin/python

import json
import time
import ipaddr
import os
import signal
import ConfigParser
import sys
import re
import random
import subprocess
import shutil
import imp
import tempfile
from snfdeploy import massedit



class Host(object):
    def __init__(self, hostname, ip, mac, domain):
        self.hostname = hostname
        self.ip = ip
        self.mac = mac
        self.domain = domain

    @property
    def fqdn(self):
        return self.hostname + "." + self.domain

    @property
    def arecord(self):
        return self.hostname + " IN A " + self.ip + "\n"

    @property
    def ptrrecord(self):
        return ".".join(raddr(self.ip)) + " IN PTR " + self.fqdn + ".\n"


class Alias(Host):
    def __init__(self, host, alias):
        super(Alias, self).__init__(host.hostname, host.ip, host.mac, host.domain)
        self.alias = alias

    @property
    def cnamerecord(self):
        return self.alias + " IN CNAME " + self.hostname + "." + self.domain + ".\n"

    @property
    def fqdn(self):
        return self.alias + "." + self.domain


class Env(object):

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
        self.hostnames = [self.node2hostname[n] for n in self.nodes.split(",")]
        self.ips = [self.node2ip[n] for n in self.nodes.split(",")]
        self.cluster_hostnames = [self.node2hostname[n] for n in self.cluster_nodes.split(",")]
        self.cluster_ips = [self.node2ip[n] for n in self.cluster_nodes.split(",")]

        self.net = ipaddr.IPNetwork(self.subnet)

        self.nodes_info = {}
        self.hosts_info = {}
        self.ips_info = {}
        for node in self.nodes.split(","):
            host =  Host(self.node2hostname[node],
                         self.node2ip[node],
                         self.node2mac[node], self.domain)

            self.nodes_info[node] = host
            self.hosts_info[host.hostname] = host
            self.ips_info[host.ip] = host

        self.cluster = Host(self.cluster_name, self.cluster_ip, None, self.domain)
        self.master = self.nodes_info[self.master_node]

        self.roles = {}
        for role, node in conf.get_section("synnefo", "roles"):
            self.roles[role] = Alias(self.nodes_info[node], role)
            setattr(self, role, self.roles[role])

class Conf(object):

    files = {
      "nodes": ["network", "info"],
      "deploy": ["dirs", "packages"],
      "vcluster": ["cluster", "image"],
      "synnefo": ["cred", "synnefo", "roles"],
      "packages": ["debian", "ganeti", "synnefo", "other"],
      "ganeti": [],
    }

    def __init__(self, confdir, cluster_name):
        self.confdir = confdir
        self.files["ganeti"] = [cluster_name]
        for f in self.files.keys():
            setattr(self, f, self.read_config(f))

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

    def _configure(self, args):
        for f, sections in self.files.iteritems():
            for s in sections:
                for k, v in self.get_section(f, s):
                    if getattr(args, k, None):
                        self.set(f, s, k, getattr(args, k))

    @classmethod
    def configure(cls, confdir="/etc/snf-deploy",
                  cluster_name="ganeti1", args=None, autoconf=False):

        conf = cls(confdir, cluster_name)
        if args:
            conf._configure(args)
        if autoconf:
            conf.autoconf()

        return conf

    def autoconf(self):
        #domain = get_domain()
        #if domain:
        #    self.nodes.set("network", "domain", get_domain())
        self.nodes.set("network", "subnet", "/".join(get_netinfo()))
        self.nodes.set("network", "gateway", get_default_route()[0])
        self.nodes.set("hostnames", "node1", get_hostname())
        self.nodes.set("ips", "node1", get_netinfo()[0])
        self.nodes.set("info", "nodes", "node1")
        self.nodes.set("info", "public_iface", get_default_route()[1])


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

    def disable(self):
        self.HEADER = ''
        self.OKBLUE = ''
        self.OKGREEN = ''
        self.WARNING = ''
        self.FAIL = ''
        self.ENDC = ''


def debug(host, msg):

    print bcolors.HEADER + host + \
          bcolors.OKBLUE + ": " + msg + bcolors.ENDC


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


def randomMAC():
    mac = [ 0x52, 0x54, 0x56,
        random.randint(0x00, 0xff),
        random.randint(0x00, 0xff),
        random.randint(0x00, 0xff) ]
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
    s = subprocess.Popen(['ip', 'addr', 'show', 'dev', pdev], stdout=subprocess.PIPE)
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
    return list(reversed(addr.replace("/","-").split(".")))
