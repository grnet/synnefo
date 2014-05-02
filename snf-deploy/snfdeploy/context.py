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
from snfdeploy import constants
from snfdeploy import config

context = sys.modules[__name__]


class Context(object):

    def __repr__(self):
        ret = "[%s %s] " % (self.node_info.ip, self.node_info.name)
        ret += "[%s %s %s %s]" % \
            (self.node, self.role, self.setup, self.cluster)
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
            self.node = node
        if role:
            self.role = role
        if cluster:
            self.cluster = cluster
        if setup:
            self.setup = setup
        self.update_info()

    def update_info(self):
        self.ns = self.get(constants.NS)
        self.nfs = self.get(constants.NFS)
        self.mq = self.get(constants.MQ)
        self.db = self.get(constants.DB)
        self.astakos = self.get(constants.ASTAKOS)
        self.cyclades = self.get(constants.CYCLADES)
        self.pithos = self.get(constants.PITHOS)
        self.stats = self.get(constants.STATS)
        self.cms = self.get(constants.CMS)
        self.router = self.get(constants.ROUTER)
        self.client = self.get(constants.CLIENT)

    def get(self, role):
        return config.get_single_node_role_info(self.setup, role)

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
    def nodes(self):
        return list(set(self.masters + self.vmcs))


def get(role):
    return config.get(context.setup, role)


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


def init(args):
    context.node = args.node
    context.role = args.role
    context.cluster = args.cluster
    context.setup = args.setup
