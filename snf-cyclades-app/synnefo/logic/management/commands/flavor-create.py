# Copyright (C) 2010-2017 GRNET S.A.
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
import re

from django.core.management.base import CommandError

from snf_django.management.commands import SynnefoCommand
from snf_django.management.utils import parse_bool
from synnefo.db.models import Flavor, VolumeType

from logging import getLogger


log = getLogger(__name__)


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
        make_option(
            '--public',
            dest='public',
            choices=["True", "False"],
            metavar="True|False",
            default="True",
            help="Mark the flavors as public"),
        make_option(
            "--specs",
            dest="specs",
            help="Comma separated spec key value pairs "
                 "Example --specs key1=value1,key2=value2")
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
        public = parse_bool(options['public'], strict=True)

        for i, r in enumerate(rams):
            value = int(r)
            if value % 4:
                value += 4 - value % 4
                log.warning("Rounding up RAM size: %s -> %s", r, value)

            rams[i] = value

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
                flavors.append((int(cpu), ram, int(disk), volume_type))
            except ValueError:
                raise CommandError("Invalid values")

        for cpu, ram, disk, volume_type in flavors:
            if options["dry_run"]:
                flavor = Flavor(cpu=cpu, ram=ram, disk=disk,
                                volume_type=volume_type, public=public)
                self.stdout.write("Creating flavor '%s'\n" % (flavor.name,))
            else:
                specs = options.get('specs')
                flavor, created = \
                    Flavor.objects.get_or_create(cpu=cpu, ram=ram, disk=disk,
                                                 volume_type=volume_type)
                if created:
                    self.stdout.write("Created flavor '%s'\n" % (flavor.name,))

                    flavor.public = public
                    flavor.save()

                    if specs:
                        spec_regex = re.compile(r'(?P<key>.+?)=(?P<value>.+)$')
                        specs = specs.split(',')
                        for spec in specs:
                            match = spec_regex.match(spec)
                            if match is None:
                                raise CommandError("Incorrect spec format. "
                                                   "Expected <key>=<value>."
                                                   " found: \'%s\'" % spec)
                            k, v = match.group('key'), match.group('value')
                            spec = flavor.specs.create(key=k)
                            spec.value = v
                            spec.save()
                else:
                    self.stdout.write("Flavor '%s' already exists\n"
                                      % flavor.name)
                    if flavor.deleted:
                        msg = "Flavor '%s' is marked as deleted." \
                              " Use 'snf-manage flavor-modify' to" \
                              " restore this flavor\n" \
                              % flavor.name
                        self.stdout.write(msg)
                    elif flavor.public != public:
                        status = 'public' if public else 'private'
                        msg = "Flavor '%s' is not %s." \
                              " Use 'snf-manage flavor-modify' to" \
                              " make this flavor %s\n" \
                              % (flavor.name, status, status)
                        self.stdout.write(msg)

                    if specs:
                        msg = "In order to add/update specs to flavor %s, "\
                              "use 'snf-manage flavor-modify %s "\
                              "--spec-add %s'"\
                              % (flavor.name, flavor.id, specs)
                        self.stdout.write(msg)
