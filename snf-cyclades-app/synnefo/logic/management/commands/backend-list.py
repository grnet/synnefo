# Copyright 2012-2013 GRNET S.A. All rights reserved.
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
