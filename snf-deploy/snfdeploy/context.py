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

import sys
import datetime
import ConfigParser
from snfdeploy import constants
from snfdeploy import config
from snfdeploy import status

context = sys.modules[__name__]


class Context(object):

    def __repr__(self):
        ret = "[%s]" % datetime.datetime.now().strftime("%H:%M:%S")
        ret += " [%s %s]" % (self.node_info.ip, self.node_info.name)
        ret += " [%s %s %s %s]" % \
            (self.node, self.role, self.cluster, self.setup)
        return ret

    def __init__(self, node=None, role=None, cluster=None, setup=None):
        if not node:
            node = context.node
        if not role:
            role = context.role
        if not setup:
            setup = context.setup
        if not cluster:
            cluster = context.cluster
        self.node = node
        self.role = role
        self.cluster = cluster
        self.setup = setup
        self.update_info()

    def update(self, node=None, role=None, cluster=None, setup=None):
        if node:
            context.node = self.node = node
        if role:
            context.role = self.role = role
        if cluster:
            context.cluster = self.cluster = cluster
        if setup:
            context.setup = self.setup = setup
        self.update_info()

    def update_info(self):
        self.ns = self._get(constants.NS)
        self.ca = self._get(constants.CA)
        self.nfs = self._get(constants.NFS)
        self.mq = self._get(constants.MQ)
        self.db = self._get(constants.DB)
        self.astakos = self._get(constants.ASTAKOS)
        self.cyclades = self._get(constants.CYCLADES)
        self.admin = self._get(constants.ADMIN)
        self.vnc = self._get(constants.VNC)
        self.pithos = self._get(constants.PITHOS)
        self.stats = self._get(constants.STATS)
        self.cms = self._get(constants.CMS)
        self.router = self._get(constants.ROUTER)
        self.client = self._get(constants.CLIENT)

    def _get(self, role):
        try:
            return config.get_single_node_role_info(self.setup, role)
        except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
            return config.get_node_info(constants.DUMMY_NODE)

    @property
    def node_info(self):
        return config.get_info(node=self.node)

    @property
    def cluster_info(self):
        return config.get_info(cluster=self.cluster)

    @property
    def clusters(self):
        return config.get(self.setup, constants.CLUSTERS)

    @property
    def masters(self):
        return config.get(self.cluster, constants.MASTER)

    @property
    def master(self):
        info = config.get_single_node_role_info(self.cluster, constants.MASTER)
        info.alias = None
        return info

    @property
    def vmcs(self):
        return config.get(self.cluster, constants.VMC)

    @property
    def cluster_nodes(self):
        return list(set(self.masters + self.vmcs))

    @property
    def all_nodes(self):
        return config.find_all_nodes(self.setup)

    @property
    def all_ips(self):
        l = lambda x: config.get_node_info(x).ip
        return [l(n) for n in self.all_nodes]

    def get(self, role):
        try:
            return config.get(self.setup, role)
        except:
            return config.get(self.cluster, role)


def backup():
    context.node_backup = context.node
    context.role_backup = context.role
    context.cluster_backup = context.cluster
    context.setup_backup = context.setup


def restore():
    context.node = context.node_backup
    context.role = context.role_backup
    context.cluster = context.cluster_backup
    context.setup = context.setup_backup


def get_passwd(target):
    if not config.passgen:
        return getattr(config, target)
    return status.get_passwd(context.setup, target)


def update_passwords():
    if config.passgen:
        for p in constants.ALL_PASSWRD_AND_SECRETS:
            passwd = status.get_passwd(context.setup, p)
            setattr(config, p, passwd)
    else:
        print "Using passwords found in configuration files"


def init(args):
    context.node = args.node
    context.role = args.role
    context.cluster = args.cluster
    context.setup = args.setup
    context.method = args.method
    context.component = args.component
    context.target_nodes = args.target_nodes
    context.cmd = args.cmd
    update_passwords()
