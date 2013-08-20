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

from optparse import make_option

from snf_django.management.commands import ListCommand
from synnefo.db.models import VirtualMachine
from synnefo.management.common import get_backend
from synnefo.api.util import get_image
from synnefo.settings import (CYCLADES_SERVICE_TOKEN as ASTAKOS_TOKEN,
                              ASTAKOS_BASE_URL)
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
    astakos_url = ASTAKOS_BASE_URL
    astakos_token = ASTAKOS_TOKEN

    def get_public_ip(vm):
        try:
            return vm.nics.all()[0].ipv4
        except IndexError:
            return None

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
        "ip": (get_public_ip, "The public IP of the server"),
        "created": ("created", "The date the server was created"),
        "deleted": ("deleted", "Whether the server is deleted or not"),
        "suspended": ("suspended", "Whether the server is administratively"
                      " suspended"),
    }

    fields = ["id", "name", "user.uuid", "state", "flavor", "image.id",
              "backend"]

    def handle_args(self, *args, **options):
        if options["suspended"]:
            self.filters["suspended"] = True

        if options["backend_id"]:
            backend = get_backend(options["backend_id"])
            self.filters["backend"] = backend.id

        if options["build"]:
            self.filters["operstate"] = "BUILD"

        if options["image_name"]:
            self.fields = ["image.name" if x == "image.id" else x
                           for x in self.fields]

    def handle_db_objects(self, rows, *args, **kwargs):
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
