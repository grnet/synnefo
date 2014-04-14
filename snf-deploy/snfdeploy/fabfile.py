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
from fabric.api import hide, env, settings, local, roles, execute
from fabric.operations import run, put, get
import fabric
import re
import os
import shutil
import tempfile
import ast
from snfdeploy.lib import debug, Conf, Env, disable_color
from snfdeploy.utils import *
from snfdeploy import massedit
# Allow referring to components with their name, e.g. Cyclades, Pithos, etc.
from snfdeploy.components import *
# Use only in setup() so that we getattr(components, XX) to get
# the actual class from the user provided name
# (snf-deploy run setup --component XX)
from snfdeploy import components


def setup_env(args, localenv):
    """Setup environment"""
    print("Loading configuration for synnefo...")

    env.env = localenv

    env.target_node = args.node
    env.target_component = args.component
    env.target_method = args.method
    env.target_role = args.role
    env.dry_run = args.dry_run
    env.local = args.autoconf
    env.key_inject = args.key_inject
    env.password = env.env.password
    env.user = env.env.user
    env.shell = "/bin/bash -c"
    env.key_filename = args.ssh_key
    env.jsonfile = "/tmp/service.json"
    env.force = args.force

    if args.disable_colors:
        disable_color()

    env.roledefs = {
        "accounts": [env.env.accounts.ip],
        "cyclades": [env.env.cyclades.ip],
        "pithos": [env.env.pithos.ip],
        "cms": [env.env.cms.ip],
        "mq": [env.env.mq.ip],
        "db": [env.env.db.ip],
        "ns": [env.env.ns.ip],
        "client": [env.env.client.ip],
        "stats": [env.env.stats.ip],
        "nfs": [env.env.nfs.ip],
    }

    env.enable_lvm = False
    env.enable_drbd = False
    if ast.literal_eval(env.env.create_extra_disk) and env.env.extra_disk:
        env.enable_lvm = True
        env.enable_drbd = True

    env.roledefs.update({
        "ganeti": env.env.cluster_ips,
        "master": [env.env.master.ip],
    })


#
#
# Those methods retrieve info from existing installation and update env
#
#
@roles("db")
def update_env_with_user_info():
    user_email = env.env.user_email
    result = RunComponentMethod(DB, "get_user_info_from_db")
    r = re.compile(r"(\d+)[ |]*(\S+)[ |]*(\S+)[ |]*" + user_email, re.M)
    match = r.search(result)
    if env.dry_run:
        env.user_id, env.user_auth_token, env.user_uuid = \
            ("dummy_uid", "dummy_user_auth_token", "dummy_user_uuid")
    else:
        env.user_id, env.user_auth_token, env.user_uuid = match.groups()


@roles("accounts")
def update_env_with_service_info(service="pithos"):
    result = RunComponentMethod(Astakos, "get_services")
    r = re.compile(r"(\d+)[ ]*%s[ ]*(\S+)" % service, re.M)
    match = r.search(result)
    if env.dry_run:
        env.service_id, env.service_token = \
            ("dummy_service_id", "dummy_service_token")
    else:
        env.service_id, env.service_token = match.groups()


@roles("cyclades")
def update_env_with_backend_info():
    cluster_name = env.env.cluster.fqdn
    result = RunComponentMethod(Cyclades, "list_backends")
    r = re.compile(r"(\d+)[ ]*%s.*" % cluster_name, re.M)
    match = r.search(result)
    if env.dry_run:
        env.backend_id = "dummy_backend_id"
    else:
        env.backend_id, = match.groups()


#
#
# Those methods act on components after their basic setup
#
#
@roles("cyclades")
def add_ganeti_backend():
    RunComponentMethod(Cyclades, "add_backend")
    execute(update_env_with_backend_info)
    RunComponentMethod(Cyclades, "undrain_backend")


@roles("accounts")
def add_synnefo_user():
    RunComponentMethod(Astakos, "add_user")


@roles("accounts")
def activate_user():
    execute(update_env_with_user_info)
    RunComponentMethod(Astakos, "activate_user")


@roles("accounts")
def import_service():
    f = env.jsonfile
    PutToComponent(Astakos, f + ".local", f)
    RunComponentMethod(Astakos, "import_service")


@roles("ns")
def update_ns_for_node(node_info):
    RunComponentMethod(NS, "update_ns_for_node", node_info)


@roles("nfs")
def update_exports_for_node(node_info):
    RunComponentMethod(NFS, "update_exports", node_info)


@roles("master")
def add_ganeti_node(node_info):
    RunComponentMethod(Master, "add_node", node_info)


@roles("db")
def allow_db_access(node_info):
    RunComponentMethod(DB, "allow_access_in_db", node_info, "all", "trust")


@roles("accounts")
def set_default_quota():
    RunComponentMethod(Astakos, "set_default_quota")


@roles("cyclades")
def add_public_networks():
    RunComponentMethod(Cyclades, "add_network")
    if ast.literal_eval(env.env.testing_vm):
        RunComponentMethod(Cyclades, "add_network6")


@roles("client")
def add_image():
    RunComponentMethod(Kamaki, "fetch_image")
    RunComponentMethod(Kamaki, "upload_image")
    RunComponentMethod(Kamaki, "register_image")


#
#
# Those methods do the basic setup of a synnefo role
#
#
@roles("ns")
def setup_ns_role():
    SetupSynnefoRole("ns")


@roles("nfs")
def setup_nfs_role():
    SetupSynnefoRole("nfs")


@roles("db")
def setup_db_role():
    SetupSynnefoRole("db")
    if ast.literal_eval(env.env.testing_vm):
        RunComponentMethod(DB, "make_db_fast")


@roles("mq")
def setup_mq_role():
    SetupSynnefoRole("mq")


@roles("accounts")
def setup_astakos_role():
    node_info = get_node_info(env.host)
    execute(allow_db_access, node_info)
    SetupSynnefoRole("astakos")
    RunComponentMethod(Astakos, "export_service")
    f = env.jsonfile
    GetFromComponent(Astakos, f, f + ".local")
    execute(import_service)


@roles("pithos")
def setup_pithos_role():
    node_info = get_node_info(env.host)
    execute(allow_db_access, node_info)
    execute(update_env_with_service_info, "pithos")
    SetupSynnefoRole("pithos")
    RunComponentMethod(Pithos, "export_service")
    f = env.jsonfile
    GetFromComponent(Pithos, f, f + ".local")
    execute(import_service)


@roles("cyclades")
def setup_cyclades_role():
    node_info = get_node_info(env.host)
    execute(allow_db_access, node_info)
    execute(update_env_with_service_info, "cyclades")
    SetupSynnefoRole("cyclades")
    RunComponentMethod(Cyclades, "export_service")
    f = env.jsonfile
    GetFromComponent(Cyclades, f, f + ".local")
    execute(import_service)


@roles("cms")
def setup_cms_role():
    SetupSynnefoRole("cms")


@roles("ganeti")
def setup_ganeti_role():
    if not env.host:
        return
    node_info = get_node_info(env.host)
    execute(update_exports_for_node, node_info)
    SetupSynnefoRole("ganeti")
    execute(add_ganeti_node, node_info)
    #FIXME: prepare_lvm ????


@roles("master")
def setup_master_role():
    node_info = get_node_info(env.host)
    execute(update_exports_for_node, node_info)
    execute(update_ns_for_node, env.env.cluster)
    SetupSynnefoRole("master")


@roles("stats")
def setup_stats_role():
    SetupSynnefoRole("stats")


@roles("client")
def setup_client_role():
    execute(update_env_with_user_info)
    SetupSynnefoRole("client")


def setup():
    node_info = get_node_info(env.target_node)
    if not node_info:
        debug("setup", "Please give a valid node identifier")
        return
    execute(update_ns_for_node, node_info)
    env.host = env.host_string = node_info.ip
    if env.target_role:
        SetupSynnefoRole(env.target_role)
        return
    if not env.target_component:
        debug("setup", "Please give a valid Component")
        return
    component_class = getattr(components, env.target_component)
    if not env.target_method:
        debug("setup", "Please give a valid Component method")
        return
    RunComponentMethod(component_class, env.target_method)
