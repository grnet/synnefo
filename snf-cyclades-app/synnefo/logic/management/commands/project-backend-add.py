# Copyright (C) 2010-2016 GRNET S.A.
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
from synnefo.db.models import ProjectBackend
from snf_django.management.commands import SynnefoCommand
from synnefo.db import transaction


class Command(SynnefoCommand):
    can_import_settings = True

    help = 'Create a new project-backend mapping.'
    option_list = SynnefoCommand.option_list + (
        make_option('--project', dest='project'),
        make_option('--backend', dest='backend'),
    )

    @transaction.commit_on_success
    def handle(self, *args, **options):
        write = self.stdout.write
        if len(args) > 0:
            raise CommandError("Command takes no arguments")

        project = options['project']
        backend_id = options['backend']

        if not (project and backend_id):
            raise CommandError("Project and Backend must be supplied")

        backend = common.get_resource("backend", backend_id, for_update=True)

        project_backend, created = ProjectBackend.objects\
            .get_or_create(project=project, backend=backend)
        if not created:
            msg = "Project-Backend mapping already exists."
            raise CommandError(msg)

        write('Successfully created project-backend allocation with id %d.\n'
              % (project_backend.id))
