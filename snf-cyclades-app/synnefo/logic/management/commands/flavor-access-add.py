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

from synnefo.management import common
from synnefo.db.models import FlavorAccess
from snf_django.management.commands import SynnefoCommand
from synnefo.db import transaction


class Command(SynnefoCommand):
    can_import_settings = True

    help = 'Create a new flavor access.'
    option_list = SynnefoCommand.option_list + (
        make_option('--project', dest='project'),
        make_option('--flavor', dest='flavor'),
    )

    @transaction.commit_on_success
    def handle(self, *args, **options):
        write = self.stdout.write
        if len(args) > 0:
            raise CommandError("Command takes no arguments")

        project = options['project']
        flavor_id = options['flavor']

        if not (project and flavor_id):
            raise CommandError("Project and Flavor must be supplied")

        flavor = common.get_resource("flavor", flavor_id, for_update=True)

        flavor_access, created = FlavorAccess.objects\
            .get_or_create(project=project, flavor=flavor)
        if not created:
            msg = "Project has already access to the flavor."
            raise CommandError(msg)

        write('Successfully created flavor-access with id %d.\n'
              % (flavor_access.id))
