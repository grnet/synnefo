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

from itertools import product
from optparse import make_option

from django.core.management.base import CommandError

from snf_django.management.commands import SynnefoCommand
from synnefo.db.models import Flavor, VolumeType


HELP_MSG = """Create one or more flavors.

Create one or more flavors (virtual hardware templates) that define the
compute, memory and storage capacity of virtual servers. The flavors that will
be created are those belonging to the cartesian product of the arguments.

To create a flavor you must specify the following arguments:
    * cpu: Number of virtual CPUs.
    * ram: Size of virtual RAM (MB).
    * disk: Size of virtual disk (GB).
    * volume_type_id: ID of the volyme type defining the volume's disk
                      template.
"""


class Command(SynnefoCommand):
    output_transaction = True
    help = HELP_MSG

    option_list = SynnefoCommand.option_list + (
        make_option("-n", "--dry-run", dest="dry_run", action="store_true"),
    )
    args = "<cpu>[,<cpu>,...] " \
           "<ram>[,<ram>,...] " \
           "<disk>[,<disk>,...] " \
           "<volume_type_id>[,<volume_type_id>,...]"

    def handle(self, *args, **options):
        if len(args) != 4:
            raise CommandError("Invalid number of arguments")

        cpus = args[0].split(',')
        rams = args[1].split(',')
        disks = args[2].split(',')

        volume_types = []
        volume_type_ids = args[3].split(',')
        for vol_t_id in volume_type_ids:
            try:
                vol_t_id = int(vol_t_id)
                volume_types.append(VolumeType.objects.get(id=vol_t_id,
                                                           deleted=False))
            except ValueError:
                raise CommandError("Invalid volume type ID: '%s'" % vol_t_id)
            except (VolumeType.DoesNotExist, ValueError):
                raise CommandError("Volume type with ID '%s' does not exist."
                                   " Use 'snf-manage volume-type-list' to find"
                                   " out available volume types." % vol_t_id)

        flavors = []
        for cpu, ram, disk, volume_type in product(cpus, rams, disks,
                                                   volume_types):
            try:
                flavors.append((int(cpu), int(ram), int(disk), volume_type))
            except ValueError:
                raise CommandError("Invalid values")

        for cpu, ram, disk, volume_type in flavors:
            if options["dry_run"]:
                flavor = Flavor(cpu=cpu, ram=ram, disk=disk,
                                volume_type=volume_type)
                self.stdout.write("Creating flavor '%s'\n" % (flavor.name,))
            else:
                flavor, created = \
                    Flavor.objects.get_or_create(cpu=cpu, ram=ram, disk=disk,
                                                 volume_type=volume_type)
                if created:
                    self.stdout.write("Created flavor '%s'\n" % (flavor.name,))
                else:
                    self.stdout.write("Flavor '%s' already exists\n"
                                      % flavor.name)
                    if flavor.deleted:
                        msg = "Flavor '%s' is marked as deleted." \
                              " Use 'snf-manage flavor-modify' to" \
                              " restore this flavor\n" \
                              % flavor.name
                        self.stdout.write(msg)
