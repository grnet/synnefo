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
from synnefo.db.models import Flavor


class Command(SynnefoCommand):
    output_transaction = True

    option_list = SynnefoCommand.option_list + (
        make_option("-n", "--dry-run", dest="dry_run", action="store_true"),
    )
    args = "<cpu>[,<cpu>,...] " \
           "<ram>[,<ram>,...] " \
           "<disk>[,<disk>,...] " \
           "<disk template>[,<disk template>,...]"
    help = "Create one or more flavors.\n\nThe flavors that will be created"\
           " are those belonging to the cartesian product of the arguments"

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
            if options["dry_run"]:
                flavor = Flavor(cpu=cpu, ram=ram, disk=disk,
                                disk_template=template)
                self.stdout.write("Creating flavor '%s'\n" % (flavor.name,))
            else:
                flavor, created = \
                    Flavor.objects.get_or_create(cpu=cpu, ram=ram, disk=disk,
                                                 disk_template=template)
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
