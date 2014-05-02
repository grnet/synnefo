# Too many lines in module pylint: disable-msg=C0302
# Too many arguments (7/5) pylint: disable-msg=R0913

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

"""
Fabric file for snf-deploy

"""

from __future__ import with_statement
from fabric.api import env, execute, parallel
from snfdeploy import context
from snfdeploy import constants
from snfdeploy import roles


def setup_env(args):
    env.component = args.component
    env.method = args.method
    env.ctx = context.Context()


@parallel
def setup_vmc():
    env.ctx.update(node=env.host)
    VMC = roles.get(constants.VMC, env.ctx)
    VMC.setup()


def setup_master():
    env.ctx.update(node=env.host)
    _setup_role(constants.MASTER)


@parallel
def setup_cluster():
    env.ctx.update(cluster=env.host)
    execute(setup_master, hosts=env.ctx.masters)
    execute(setup_vmc, hosts=env.ctx.vmcs)


def _setup_role(role):
    env.ctx.update(node=env.host)
    ROLE = roles.get(role, env.ctx)
    ROLE.setup()


def setup_role(role):
    execute(_setup_role, role, hosts=context.get(role))


def setup_synnefo():
    setup_role(constants.NS)
    setup_role(constants.NFS)
    setup_role(constants.DB)
    setup_role(constants.MQ)

    setup_role(constants.ASTAKOS)
    setup_role(constants.PITHOS)
    setup_role(constants.CYCLADES)
    setup_role(constants.CMS)

    execute(setup_cluster, hosts=env.ctx.clusters)

    setup_role(constants.STATS)
    setup_role(constants.CLIENT)


def setup_ganeti():
    setup_role(constants.NS)
    setup_role(constants.NFS)
    execute(setup_cluster, hosts=env.ctx.clusters)


def _setup_qa():
    env.ctx.update(cluster=env.host)
    setup_role(constants.NS)
    setup_role(constants.NFS)
    setup_cluster()
    setup_role(constants.DEV)


def setup_qa():
    execute(_setup_qa, hosts=env.ctx.clusters)


def setup():
    if env.component:
        target = env.component
    else:
        target = env.ctx.role
    C = roles.get(target, env.ctx)
    if env.method:
        fn = getattr(C, env.method)
        fn()
    else:
        C.setup()
