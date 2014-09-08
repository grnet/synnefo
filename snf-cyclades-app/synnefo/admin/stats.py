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


import datetime

from collections import defaultdict  # , OrderedDict
from copy import copy
from django.conf import settings
from django.db import connection
from django.db.models import Count, Sum

from snf_django.lib.astakos import UserCache
from synnefo.plankton.backend import PlanktonBackend
from synnefo.db.models import (VirtualMachine, Network, Backend, VolumeType,
                               pooled_rapi_client, Flavor)


def get_cyclades_stats(backend=None, clusters=True, servers=True,
                       ip_pools=True, networks=True, images=True):
    stats = {"datetime": datetime.datetime.now().strftime("%c")}
    if clusters:
        stats["clusters"] = get_cluster_stats(backend=backend)
    if servers:
        stats["servers"] = get_server_stats(backend=backend)
    if ip_pools:
        stats["ip_pools"] = get_ip_pool_stats()
    if networks:
        stats["networks"] = get_network_stats()
    if images:
        stats["images"] = get_image_stats(backend=None)
    return stats


def _get_cluster_stats(bend):
    """Get information about a Ganeti cluster and all of it's nodes."""
    bend_vms = bend.virtual_machines.filter(deleted=False)
    vm_stats = bend_vms.aggregate(Sum("flavor__cpu"),
                                  Sum("flavor__ram"),
                                  Sum("flavor__disk"))
    cluster_info = {
        "drained": bend.drained,
        "offline": bend.offline,
        "hypervisor": bend.hypervisor,
        "disk_templates": bend.disk_templates,
        "virtual_servers": bend_vms.count(),
        "virtual_cpu": (vm_stats["flavor__cpu__sum"] or 0),
        "virtual_ram": (vm_stats["flavor__ram__sum"] or 0) << 20,
        "virtual_disk": (vm_stats["flavor__disk__sum"] or 0) << 30,
        "nodes": {},
    }
    nodes = []
    if not bend.offline:
        with pooled_rapi_client(bend) as c:
            nodes = c.GetNodes(bulk=True)
    for node in nodes:
        _node_stats = {
            "drained": node["drained"],
            "offline": node["offline"],
            "vm_capable": node["vm_capable"],
            "instances": node["pinst_cnt"],
            "cpu": (node["ctotal"] or 0),
            "ram": {
                "total": (node["mtotal"] or 0) << 20,
                "free": (node["mfree"] or 0) << 20
            },
            "disk": {
                "total": (node["dtotal"] or 0) << 20,
                "free": (node["dfree"] or 0) << 20
            },
        }
        cluster_info["nodes"][node["name"]] = _node_stats
    return bend.clustername, cluster_info


def get_cluster_stats(backend=None):
    """Get statistics about all Ganeti clusters."""
    if backend is None:
        backends = Backend.objects.all()
    else:
        backends = [backend]
    return dict([_get_cluster_stats(bend) for bend in backends])


def _get_total_servers(backend=None):
    total_servers = VirtualMachine.objects.all()
    if backend is not None:
        total_servers = total_servers.filter(backend=backend)
    return total_servers


def get_server_stats(backend=None):
    servers = VirtualMachine.objects.select_related("flavor__volume_type")\
                                    .filter(deleted=False)
    if backend is not None:
        servers = servers.filter(backend=backend)
    disk_templates = \
        VolumeType.objects.values_list("disk_template", flat=True).distinct()

    # Initialize stats
    server_stats = defaultdict(dict)
    for state in ["started", "stopped", "error"]:
        server_stats[state]["count"] = 0
        server_stats[state]["cpu"] = defaultdict(int)
        server_stats[state]["ram"] = defaultdict(int)
        server_stats[state]["disk"] = \
            dict([(disk_t, defaultdict(int)) for disk_t in disk_templates])

    for s in servers:
        if s.operstate in ["STARTED", "BUILD"]:
            state = "started"
        elif s.operstate == "ERROR":
            state = "error"
        else:
            state = "stopped"

        flavor = s.flavor
        disk_template = flavor.volume_type.disk_template
        server_stats[state]["count"] += 1
        server_stats[state]["cpu"][flavor.cpu] += 1
        server_stats[state]["ram"][flavor.ram << 20] += 1
        server_stats[state]["disk"][disk_template][flavor.disk << 30] += 1

    return server_stats


def get_network_stats():
    """Get statistics about Cycldades Networks."""
    network_stats = defaultdict(dict)
    for flavor in Network.FLAVORS.keys():
        network_stats[flavor] = defaultdict(int)
        network_stats[flavor]["active"] = 0
        network_stats[flavor]["error"] = 0

    networks = Network.objects.filter(deleted=False)
    for net in networks:
        state = "error" if net.state == "ERROR" else "active"
        network_stats[net.flavor][state] += 1

    return network_stats


def get_ip_pool_stats():
    """Get statistics about floating IPs."""
    ip_stats = {}
    for status in ["drained", "active"]:
        ip_stats[status] = {
            "count": 0,
            "total": 0,
            "free": 0,
        }
    ip_pools = Network.objects.filter(deleted=False, floating_ip_pool=True)
    for ip_pool in ip_pools:
        status = "drained" if ip_pool.drained else "active"
        total, free = ip_pool.ip_count()
        ip_stats[status]["count"] += 1
        ip_stats[status]["total"] += total
        ip_stats[status]["free"] += free
    return ip_stats


IMAGES_QUERY = """
SELECT is_system, osfamily, os, count(vm.id)
FROM db_virtualmachine as vm LEFT OUTER JOIN db_image as img
ON img.uuid = vm.imageid AND img.version = vm.image_version
WHERE vm.deleted=false
GROUP BY is_system, osfamily, os
"""

def get_image_stats(backend=None):
    cursor = connection.cursor()
    cursor.execute(IMAGES_QUERY)
    images = cursor.fetchall()
    images_stats = {}
    for image in images:
        owner = "system" if image[0] else "user"
        osfamily = image[1] or "unknown"
        os = image[2] or "unknown"
        images_stats["%s:%s:%s" % (owner, osfamily, os)] = image[3]
    return images_stats


class ImageCache(object):
    def __init__(self):
        self.images = {}
        usercache = UserCache(settings.ASTAKOS_AUTH_URL,
                              settings.CYCLADES_SERVICE_TOKEN)
        self.system_user_uuid = \
            usercache.get_uuid(settings.SYSTEM_IMAGES_OWNER)

    def get_image(self, imageid, userid):
        if imageid not in self.images:
            try:
                with PlanktonBackend(userid) as ib:
                    image = ib.get_image(imageid)
                properties = image.get("properties")
                os = properties.get("os",
                                    properties.get("osfamily", "unknown"))
                owner = image["owner"]
                owner = "system" if image["owner"] == self.system_user_uuid\
                        else "user"
                self.images[imageid] = owner + ":" + os
            except Exception:
                self.images[imageid] = "unknown:unknown"

        return self.images[imageid]


def get_public_stats():
    # VirtualMachines
    vm_objects = VirtualMachine.objects
    servers = vm_objects.values("deleted", "operstate")\
                        .annotate(count=Count("id"),
                                  cpu=Sum("flavor__cpu"),
                                  ram=Sum("flavor__ram"),
                                  disk=Sum("flavor__disk"))
    zero_stats = {"count": 0, "cpu": 0, "ram": 0, "disk": 0}
    server_stats = {}
    for state in VirtualMachine.RSAPI_STATE_FROM_OPER_STATE.values():
        server_stats[state] = copy(zero_stats)

    for stats in servers:
        deleted = stats.get("deleted")
        operstate = stats.get("operstate")
        state = VirtualMachine.RSAPI_STATE_FROM_OPER_STATE.get(operstate)
        if deleted:
            for key in zero_stats.keys():
                server_stats["DELETED"][key] += (stats.get(key, 0) or 0)
        elif state:
            for key in zero_stats.keys():
                server_stats[state][key] += (stats.get(key, 0) or 0)

    # Networks
    net_objects = Network.objects
    networks = net_objects.values("deleted", "state")\
                          .annotate(count=Count("id"))
    zero_stats = {"count": 0}
    network_stats = {}
    for state in Network.RSAPI_STATE_FROM_OPER_STATE.values():
        network_stats[state] = copy(zero_stats)

    for stats in networks:
        deleted = stats.get("deleted")
        state = stats.get("state")
        state = Network.RSAPI_STATE_FROM_OPER_STATE.get(state)
        if deleted:
            for key in zero_stats.keys():
                network_stats["DELETED"][key] += stats.get(key, 0)
        elif state:
            for key in zero_stats.keys():
                network_stats[state][key] += stats.get(key, 0)

    statistics = {"servers": server_stats,
                  "networks": network_stats}
    return statistics


if __name__ == "__main__":
    import json
    print json.dumps(get_cyclades_stats())
