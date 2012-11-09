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

from itertools import product

from django.core.management.base import BaseCommand, CommandError

from synnefo.db.models import Flavor


class Command(BaseCommand):
    output_transaction = True
    args = "<cpu>[,<cpu>,...] " \
           "<ram>[,<ram>,...] " \
           "<disk>[,<disk>,...] " \
           "<disk template>[,<disk template>,...]"
    help = "Create one or more flavors.\n\nThe flavors that will be created are"\
           " those belonging to the cartesian product of the arguments"\

    def handle(self, *args, **options):
        if len(args) != 4:
            raise CommandError("Invalid number of arguments")

        cpus = args[0].split(',')
        rams = args[1].split(',')
        disks = args[2].split(',')
        templates = args[3].split(',')

        flavors = []
        for cpu, ram, disk, template in product(cpus, rams, disks, templates):
            try:
                flavors.append((int(cpu), int(ram), int(disk), template))
            except ValueError:
                raise CommandError("Invalid values")

        for cpu, ram, disk, template in flavors:
            flavor = Flavor.objects.create(cpu=cpu, ram=ram, disk=disk,
                                           disk_template=template)
            self.stdout.write("Created flavor %s\n" % (flavor.name,))
