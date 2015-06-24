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

import ConfigParser
import sys
import os
import ipaddr
from snfdeploy.lib import evaluate, get_hostname, get_netinfo, \
    get_default_route, getlist, getbool, disable_color, FQDN


config = sys.modules[__name__]

CONF_FILES = [
    "nodes", "setups",
    "synnefo", "ganeti",
    "packages", "deploy", "vcluster",
    ]


def _autoconf():
    return {
        "name": get_hostname(),
        "ip": get_netinfo()[0],
        "public_iface": get_default_route()[1],
        }


def _read_config(f):
    cfg = ConfigParser.ConfigParser()
    cfg.optionxform = str
    filename = os.path.join(config.confdir, f) + ".conf"
    cfg.read(filename)
    return cfg


def get(setup_or_cluster, role):
    assert setup_or_cluster and role
    value = config.setups.get(setup_or_cluster, role)
    return getlist(value)


def get_info(cluster=None, node=None):
    if cluster:
        return get_cluster_info(cluster)
    if node:
        return get_node_info(node)


def get_single_node_role_info(setup, role):
    assert setup and role
    nodes = get(setup, role)
    assert len(nodes) == 1
    info = get_node_info(nodes[0])
    info.alias = role
    return info


def get_package(package, os="debian"):
    try:
        return config.packages.get(os, package)
    except ConfigParser.NoOptionError:
        return None


def print_config():
    for f in CONF_FILES:
        getattr(config, f).write(sys.stdout)


def get_cluster_info(cluster):
    options = dict(config.ganeti.items(cluster))
    info = FQDN(**options)
    return info


def _get_node_info(node):
    info = dict(config.nodes.items(node))
    if config.autoconf:
        info.update(_autoconf())
    info.update({
        "node": node
        })
    return info


def get_node_info(node):
    info = _get_node_info(node)
    return FQDN(**info)


def find_all_nodes(setup):
    ret = []
    for op in config.setups.options(setup):
        for tgt in get(setup, op):
            if config.nodes.has_section(tgt):
                ret.append(tgt)
            elif config.ganeti.has_section(tgt):
                ret += find_all_nodes(tgt)

    return list(set(ret))


def init(args):
    config.confdir = args.confdir
    config.autoconf = args.autoconf
    # Import all .conf files
    for f in CONF_FILES:
        setattr(config, f, _read_config(f))

    # This is done here in order to have easy access
    # to configuration options
    evaluate(config, **config.deploy.defaults())
    evaluate(config, **config.vcluster.defaults())
    evaluate(config, **config.synnefo.defaults())

    # Override conf file settings if
    # --templates-dir and --state-dir args are passed
    if args.template_dir:
        config.template_dir = args.template_dir
    if args.state_dir:
        config.state_dir = args.state_dir

    config.dry_run = args.dry_run
    config.force = args.force
    config.ssh_key = args.ssh_key
    config.mem = args.mem
    config.vnc = args.vnc
    config.smp = args.smp
    config.passgen = args.passgen

    config.jsonfile = "/tmp/service.json"
    config.ganeti_dir = os.path.join(config.shared_dir, "ganeti")
    config.images_dir = os.path.join(config.shared_dir, "images")
    config.archip_dir = os.path.join(config.shared_dir, "archip")
    config.src_dir = os.path.join(config.shared_dir, "src")

    # debian_base_url is given in config
    # Here we set some config vars that will be frequently used
    config.debian_base_name = "debian_base.diskdump"
    config.debian_base_image = os.path.join(config.images_dir,
                                            config.debian_base_name)

    if args.disable_colors:
        disable_color()

    config.testing_vm = getbool(config.testing_vm)
    config.use_local_packages = getbool(config.use_local_packages)

    config.net = ipaddr.IPNetwork(config.subnet)
    config.all_nodes = config.nodes.sections()
    config.all_ips = [get_node_info(node).ip
                      for node in config.all_nodes]
