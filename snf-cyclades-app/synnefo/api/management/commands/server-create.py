# Copyright 2012 GRNET S.A. All rights reserved.
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

from django.core.management.base import BaseCommand, CommandError

from synnefo.db.models import VirtualMachine, Backend, Flavor
from synnefo.logic.backend import create_instance
from synnefo.logic.backend_allocator import BackendAllocator
from synnefo.api.util import get_image, allocate_public_address
from synnefo.api.faults import ItemNotFound

HELP_MSG = """

Create a new VM without authenticating the user or checking the resource
limits of the user. Also the allocator can be bypassed by specifing a
backend-id.
"""


class Command(BaseCommand):
    help = "Create a new VM." + HELP_MSG

    output_transaction = True

    option_list = BaseCommand.option_list + (
            make_option("--backend-id", dest="backend_id",
                        help="Unique identifier of the Ganeti backend."
                             " Use snf-manage backend-list to find out"
                             " available backends."),
            make_option("--name", dest="name",
                        help="An arbitrary string for naming the server"),
            make_option("--user-id", dest="user_id",
                        help="Unique identifier of the owner of the server"),
            make_option("--image-id", dest="image_id",
                        help="Unique identifier of the image."
                             " Use snf-manage image-list to find out"
                             " available images."),
            make_option("--flavor-id", dest="flavor_id",
                        help="Unique identifier of the flavor"
                             " Use snf-manage flavor-list to find out"
                             " available flavors."),
            make_option("--password", dest="password",
                        help="Password for the new server")
        )

    def handle(self, *args, **options):
        if args:
            raise CommandError("Command doesn't accept any arguments")

        name = options['name']
        user_id = options['user_id']
        backend_id = options['backend_id']
        image_id = options['image_id']
        flavor_id = options['flavor_id']
        password = options['password']

        if not name:
            raise CommandError("name is mandatory")
        if not user_id:
            raise CommandError("user-id is mandatory")
        if not password:
            raise CommandError("password is mandatory")

        # Get Flavor
        if flavor_id:
            try:
                flavor_id = int(flavor_id)
                flavor = Flavor.objects.get(id=flavor_id)
            except ValueError:
                raise CommandError("Invalid flavor-id")
            except Flavor.DoesNotExist:
                raise CommandError("Flavor not found")
        else:
            raise CommandError("flavor-id is mandatory")

        # Get Image
        if image_id:
            try:
                img = get_image(image_id, user_id)
            except ItemNotFound:
                raise CommandError("Image not found")

            properties = img.get('properties', {})
            image = {}
            image['backend_id'] = img['location']
            image['format'] = img['disk_format']
            image['metadata'] = dict((key.upper(), val) \
                                     for key, val in properties.items())
        else:
            raise CommandError("image-id is mandatory")

        # Get Backend
        if backend_id:
            try:
                backend_id = int(backend_id)
                backend = Backend.objects.get(id=backend_id)
            except (ValueError, Backend.DoesNotExist):
                raise CommandError("Invalid Backend ID")
        else:
            ballocator = BackendAllocator()
            backend = ballocator.allocate(user_id, flavor)
            if not backend:
                raise CommandError("Can not allocate VM")

        # Get Public address
        (network, address) = allocate_public_address(backend)
        if address is None:
            raise CommandError("Can not allocate a public address."\
                               " No available public network.")
        nic = {'ip': address, 'network': network.backend_id}

        # Create the VM in DB
        vm = VirtualMachine.objects.create(name=name,
                                           backend=backend,
                                           userid=user_id,
                                           imageid=image_id,
                                           flavor=flavor)

        # Create the instance in Backend
        jobID = create_instance(vm, nic, flavor, image, password, [])

        self.stdout.write("Creating VM %s with IP %s in Backend %s. JobID: %s\n" % \
                          (vm, address, backend, jobID))
