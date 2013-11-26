# Copyright 2013 GRNET S.A. All rights reserved.
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


import itertools
import operator
import datetime

from collections import defaultdict  # , OrderedDict
from copy import copy
from django.conf import settings
from django.db.models import Count, Sum

from snf_django.lib.astakos import UserCache
from synnefo.db.models import VirtualMachine, Network, Backend
from synnefo.api.util import get_image
from synnefo.logic import backend as backend_mod


def get_cyclades_stats(backend=None, clusters=True, servers=True,
                       resources=True, networks=True, images=True):
    stats = {"datetime": datetime.datetime.now().strftime("%c")}
    if clusters:
        stats["clusters"] = get_cluster_stats(backend=backend)
    if servers:
        stats["servers"] = get_servers_stats(backend=backend)
    if resources:
        stats["resources"] = get_resources_stats(backend=backend)
    if networks:
        stats["networks"] = get_networks_stats()
    if images:
        stats["images"] = get_images_stats(backend=None)
    return stats


def get_cluster_stats(backend):
    total = Backend.objects.all()
    stats = {"total": total.count(),
             "drained": total.filter(drained=True).count(),
             "offline": total.filter(offline=True).count()}
    return stats


def _get_total_servers(backend=None):
    total_servers = VirtualMachine.objects.all()
    if backend is not None:
        total_servers = total_servers.filter(backend=backend)
    return total_servers


def get_servers_stats(backend=None):
    total_servers = _get_total_servers(backend=backend)
    per_state = total_servers.values("operstate")\
                             .annotate(count=Count("operstate"))
    stats = {"total": 0}
    [stats.setdefault(s[0], 0) for s in VirtualMachine.OPER_STATES]
    for x in per_state:
        stats[x["operstate"]] = x["count"]
        stats["total"] += x["count"]
    return stats


def get_resources_stats(backend=None):
    total_servers = _get_total_servers(backend=backend)
    active_servers = total_servers.filter(deleted=False)

    allocated = {}
    server_count = {}
    for res in ["cpu", "ram", "disk", "disk_template"]:
        server_count[res] = {}
        allocated[res] = 0
        val = "flavor__%s" % res
        results = active_servers.values(val).annotate(count=Count(val))
        for result in results:
            server_count[res][result[val]] = result["count"]
            if res != "disk_template":
                allocated[res] += result["count"]

    resources_stats = get_backend_stats(backend=backend)
    for res in ["cpu", "ram", "disk", "disk_template"]:
        if res not in resources_stats:
            resources_stats[res] = {}
        resources_stats[res]["servers"] = server_count[res]
        resources_stats[res]["allocated"] = allocated[res]

    return resources_stats


def get_images_stats(backend=None):
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


def get_networks_stats():
    total_networks = Network.objects.all()
    stats = {"public_ips": get_ip_stats(),
             "total": 0}
    per_state = total_networks.values("state")\
                              .annotate(count=Count("state"))
    [stats.setdefault(s[0], 0) for s in Network.OPER_STATES]
    for x in per_state:
        stats[x["state"]] = x["count"]
        stats["total"] += x["count"]
    return stats


def group_by_resource(objects, resource):
    stats = {}
    key = operator.attrgetter("flavor."+resource)
    grouped = itertools.groupby(sorted(objects, key=key), key)
    for val, group in grouped:
        stats[val] = len(list(group))
    return stats


def get_ip_stats():
    total, free = 0, 0,
    for network in Network.objects.filter(public=True, deleted=False):
        try:
            net_total, net_free = network.ip_count()
        except AttributeError:
            # TODO: Check that this works..
            pool = network.get_pool(locked=False)
            net_total = pool.pool_size
            net_free = pool.count_available()
        if not network.drained:
            total += net_total
            free += net_free
    return {"total": total,
            "free": free}


def get_backend_stats(backend=None):
    if backend is None:
        backends = Backend.objects.filter(offline=False)
    else:
        if backend.offline:
            return {}
        backends = [backend]
    [backend_mod.update_backend_resources(b) for b in backends]
    resources = {}
    for attr in ("dfree", "dtotal", "mfree", "mtotal", "ctotal"):
        resources[attr] = 0
        for b in backends:
            resources[attr] += getattr(b, attr)

    return {"disk": {"free": resources["dfree"], "total": resources["dtotal"]},
            "ram": {"free": resources["mfree"], "total": resources["mtotal"]},
            "cpu": {"free": resources["ctotal"], "total": resources["ctotal"]},
            "disk_template": {"free": 0, "total": 0}}


class ImageCache(object):
    def __init__(self):
        self.images = {}
        usercache = UserCache(settings.ASTAKOS_BASE_URL,
                              settings.CYCLADES_SERVICE_TOKEN)
        self.system_user_uuid = \
            usercache.get_uuid(settings.SYSTEM_IMAGES_OWNER)

    def get_image(self, imageid, userid):
        if not imageid in self.images:
            try:
                image = get_image(imageid, userid)
                owner = image["owner"]
                owner = "system" if image["owner"] == self.system_user_uuid\
                        else "user"
                self.images[imageid] = owner + ":" + image["name"]
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
        deleted = stats.pop("deleted")
        operstate = stats.pop("operstate")
        state = VirtualMachine.RSAPI_STATE_FROM_OPER_STATE.get(operstate)
        if deleted:
            for key in zero_stats.keys():
                server_stats["DELETED"][key] += stats.get(key, 0)
        elif state:
            for key in zero_stats.keys():
                server_stats[state][key] += stats.get(key, 0)

    #Networks
    net_objects = Network.objects
    networks = net_objects.values("deleted", "state")\
                          .annotate(count=Count("id"))
    zero_stats = {"count": 0}
    network_stats = {}
    for state in Network.RSAPI_STATE_FROM_OPER_STATE.values():
        network_stats[state] = copy(zero_stats)

    for stats in networks:
        deleted = stats.pop("deleted")
        state = stats.pop("state")
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
