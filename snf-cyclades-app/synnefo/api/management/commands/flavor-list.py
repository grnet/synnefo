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

from synnefo.webproject.management.commands import ListCommand
from synnefo.db.models import Flavor, VirtualMachine


class Command(ListCommand):
    help = "List available server flavors"

    object_class = Flavor
    deleted_field = "deleted"

    def get_vms(flavor):
        return VirtualMachine.objects.filter(flavor=flavor, deleted=False)\
                                     .count()

    FIELDS = {
        "id": ("id", "Flavor's unique ID"),
        "name": ("name", "Flavor's unique name"),
        "cpu": ("cpu", "Number of CPUs"),
        "ram": ("ram", "Size(MB) of RAM"),
        "disk": ("disk", "Size(GB) of disk"),
        "template": ("disk_template", "Disk template"),
        "vms": (get_vms, "Number of active servers using this flavor")
    }

    fields = ["id", "name", "cpu", "ram", "disk", "template", "vms"]
