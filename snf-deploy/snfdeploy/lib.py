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
import signal
import sys
import re
import random
import subprocess
import imp
import ast
import string

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


def evaluate(some_object, **kwargs):
    for k, v in kwargs.items():
        setattr(some_object, k, v)


def getlist(value):
    return list(filter(None, (x.strip() for x in value.splitlines())))


def getbool(value):
    return ast.literal_eval(value)


class FQDN(object):
    def __init__(self, alias=None, **kwargs):
        self.alias = alias
        evaluate(self, **kwargs)
        self.hostname = self.name

    @property
    def fqdn(self):
        return self.name + "." + self.domain

    @property
    def arecord(self):
        return self.fqdn + " 300 A " + self.ip

    @property
    def ptrrecord(self):
        return ".".join(raddr(self.ip)) + ".in-addr.arpa 300 PTR " + self.fqdn

    @property
    def cnamerecord(self):
        if self.cname:
            return self.cname + " 300 CNAME " + self.fqdn
        else:
            return ""

    @property
    def cname(self):
        if self.alias:
            return self.alias + "." + self.domain
        else:
            return ""


def debug(*args):

    print " ".join([
        HEADER, args[0],
        OKBLUE, args[1],
        OKGREEN, args[2],
        ENDC])


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


def create_passwd(length):
    char_set = string.ascii_uppercase + string.digits + string.ascii_lowercase
    return ''.join(random.sample(char_set, length))
