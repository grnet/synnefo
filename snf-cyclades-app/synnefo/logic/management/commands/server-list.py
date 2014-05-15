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

from optparse import make_option
from functools import partial

from snf_django.management.commands import ListCommand
from synnefo.db.models import VirtualMachine
from synnefo.management.common import get_resource
from synnefo.api.util import get_image
from synnefo.settings import (CYCLADES_SERVICE_TOKEN as ASTAKOS_TOKEN,
                              ASTAKOS_AUTH_URL)
from logging import getLogger
log = getLogger(__name__)


class Command(ListCommand):
    help = "List servers"

    option_list = ListCommand.option_list + (
        make_option(
            '--suspended',
            action='store_true',
            dest='suspended',
            default=False,
            help="List only suspended servers"),
        make_option(
            '--backend-id',
            dest='backend_id',
            help="List only servers of the specified backend"),
        make_option(
            "--build",
            action="store_true",
            dest="build",
            default=False,
            help="List only servers in the building state"),
        make_option(
            "--image-name",
            action="store_true",
            dest="image_name",
            default=False,
            help="Display image name instead of image ID"),
    )

    object_class = VirtualMachine
    deleted_field = "deleted"
    user_uuid_field = "userid"
    astakos_auth_url = ASTAKOS_AUTH_URL
    astakos_token = ASTAKOS_TOKEN
    select_related = ["flavor.volume_type"]

    def get_ips(version, vm):
        ips = []
        for nic in vm.nics.all():
            for ip in nic.ips.all():
                if ip.subnet.ipversion == version:
                    ips.append(ip.address)
        return ips

    def format_vm_state(vm):
        if vm.operstate == "BUILD":
            return "BUILD(" + str(vm.buildpercentage) + "%)"
        else:
            return vm.operstate

    FIELDS = {
        "id": ("id", "ID of the server"),
        "name": ("name", "Name of the server"),
        "user.uuid": ("userid", "The UUID of the server's owner"),
        "flavor": ("flavor.name", "The name of the server's flavor"),
        "backend": ("backend", "The Ganeti backend that hosts the VM"),
        "image.id": ("imageid", "The ID of the server's image"),
        "image.name": ("image", "The name of the server's image"),
        "state": (format_vm_state, "The current state of the server"),
        "ipv4": (partial(get_ips, 4),
                 "The IPv4 addresses of the server"),
        "ipv6": (partial(get_ips, 6),
                 "The IPv6 addresses of the server"),
        "created": ("created", "The date the server was created"),
        "deleted": ("deleted", "Whether the server is deleted or not"),
        "suspended": ("suspended", "Whether the server is administratively"
                      " suspended"),
        "project": ("project", "The project UUID"),
    }

    fields = ["id", "name", "user.uuid", "state", "flavor", "image.id",
              "backend"]

    def handle_args(self, *args, **options):
        if options["suspended"]:
            self.filters["suspended"] = True

        if options["backend_id"]:
            backend = get_resource("backend", options["backend_id"])
            self.filters["backend"] = backend.id

        if options["build"]:
            self.filters["operstate"] = "BUILD"

        if options["image_name"]:
            self.fields = ["image.name" if x == "image.id" else x
                           for x in self.fields]

        if "ipv4" in self.fields or "ipv6" in self.fields:
            self.prefetch_related.append("nics__ips__subnet")

    def handle_db_objects(self, rows, *args, **kwargs):
        if "image.name" in self.fields:
            icache = ImageCache()
            for vm in rows:
                vm.image = icache.get_image(vm.imageid, vm.userid)


class ImageCache(object):
    def __init__(self):
        self.images = {}

    def get_image(self, imageid, userid):
        if not imageid in self.images:
            try:
                self.images[imageid] = get_image(imageid, userid)['name']
            except Exception as e:
                log.warning("Error getting image name from imageid %s: %s",
                            imageid, e)
                self.images[imageid] = imageid

        return self.images[imageid]
