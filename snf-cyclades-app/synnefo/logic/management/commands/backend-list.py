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

from synnefo.db.models import Backend
from snf_django.management.commands import ListCommand
from synnefo.api import util


class Command(ListCommand):
    help = "List Ganeti backends"
    object_class = Backend

    def get_vms(backend):
        return backend.virtual_machines.filter(deleted=False).count()

    def get_mem(backend):
        return "%s/%s" % (backend.mfree, backend.mtotal)

    def get_disk(backend):
        return "%s/%s" % (backend.dfree, backend.dtotal)

    def get_ips(backend):
        free_ips = 0
        total_ips = 0
        for network in util.backend_public_networks(backend):
            total, free = network.ip_count()
            total_ips += total
            if not network.drained:
                free_ips += free
        return "%s/%s" % (free_ips, total_ips)

    FIELDS = {
        "id": ("id", "Backend's unique ID"),
        "clustername": ("clustername", "The name of the Ganeti cluster"),
        "port": ("port", ""),
        "username": ("username", "The RAPI user"),
        "drained": ("drained", "Whether backend is marked as drained"),
        "offline": ("offline", "Whether backend if marked as offline"),
        "vms": (get_vms, "Number of VMs that this backend hosts"),
        "ips": (get_ips, "free/total number of public IPs"),
        "mem": (get_mem, "free/total memory (MB)"),
        "disk": (get_mem, "free/total disk (GB)"),
        "hypervisor": ("hypervisor", "The hypervisor the backend is using"),
        "disk_templates": ("disk_templates", "Enabled disk-templates"),
    }

    fields = ["id", "clustername", "port", "username", "drained", "offline",
              "vms", "hypervisor", "ips", "disk_templates"]
