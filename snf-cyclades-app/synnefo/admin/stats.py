# Copyright 2013-2014 GRNET S.A. All rights reserved.
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
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
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


import datetime

from collections import defaultdict  # , OrderedDict
from copy import copy
from django.conf import settings
from django.db.models import Count, Sum

from snf_django.lib.astakos import UserCache
from synnefo.db.models import (VirtualMachine, Network, Backend,
                               pooled_rapi_client, Flavor)
from synnefo.plankton.utils import image_backend


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
            "cpu": node["ctotal"],
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
    servers = VirtualMachine.objects.select_related("flavor")\
                                    .filter(deleted=False)
    if backend is not None:
        servers = servers.filter(backend=backend)
    disk_templates = Flavor.objects.values_list("disk_template", flat=True)\
                                   .distinct()

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
        disk_template = flavor.disk_template
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


def get_image_stats(backend=None):
    total_servers = _get_total_servers(backend=backend)
    active_servers = total_servers.filter(deleted=False)

    active_servers_images = active_servers.values("imageid", "userid")\
                                          .annotate(number=Count("imageid"))

    image_cache = ImageCache()
    image_stats = defaultdict(int)
    for result in active_servers_images:
        imageid = image_cache.get_image(result["imageid"], result["userid"])
        image_stats[imageid] += result["number"]
    return dict(image_stats)


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
                with image_backend(userid) as ib:
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
