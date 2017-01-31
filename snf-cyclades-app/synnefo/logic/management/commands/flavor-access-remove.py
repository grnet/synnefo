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
#

from optparse import make_option
from django.core.management.base import CommandError

from snf_django.management.commands import SynnefoCommand
from synnefo.management import common
from synnefo.db.models import FlavorAccess
from synnefo.db import transaction


class Command(SynnefoCommand):
    help = "Remove a flavor access."
    args = "<flavor_access_id>"
    option_list = SynnefoCommand.option_list + (
        make_option('--project', dest='project'),
        make_option('--flavor', dest='flavor'),
    )

    @transaction.commit_on_success
    def handle(self, *args, **options):
        write = self.stdout.write
        project = options['project']
        flavor_id = options['flavor']

        if len(args) < 1 and not project and not flavor_id:
            raise CommandError("Please provide a flavor-access ID or a "
                               "PROJECT or a FLAVOR")

        if len(args) > 0:
            flavor_access = common.get_resource("flavor-access", args[0],
                                                for_update=True)
            flavor_access.delete()
            write('Successfully removed flavor-access.\n')
        else:
            flavor_accesses = FlavorAccess.objects
            if flavor_id:
                flavor = common.get_resource("flavor", flavor_id,
                                             for_update=True)
                flavor_accesses = flavor_accesses.filter(flavor=flavor)
            if project:
                flavor_accesses = flavor_accesses.filter(project=project)

            flavor_accesses.delete()
            write('Successfully removed flavor-accesses.\n')
