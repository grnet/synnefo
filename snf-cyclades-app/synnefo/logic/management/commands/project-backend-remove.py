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

from snf_django.management.commands import SynnefoCommand
from synnefo.management import common
from synnefo.db.models import ProjectBackend
from synnefo.db import transaction


class Command(SynnefoCommand):
    help = "Remove a project-backend mapping."
    args = "<project_backend_id>"
    option_list = SynnefoCommand.option_list + (
        make_option('--project', dest='project'),
        make_option('--backend', dest='backend'),
    )

    @transaction.commit_on_success
    def handle(self, *args, **options):
        write = self.stdout.write
        project = options['project']
        backend_id = options['backend']

        if len(args) < 1 and not project and not backend_id:
            raise CommandError("Please provide a project-backend ID or a "
                               "PROJECT or BACKEND")

        if len(args) > 0:
            project_backend = common.get_resource("project-backend", args[0])
            project_backend.delete()
            write('Successfully removed project-backend mapping.\n')
        else:
            project_backends = ProjectBackend.objects
            if backend_id:
                backend = common.get_resource("backend", backend_id)
                project_backends = project_backends.filter(backend=backend)
            if project:
                project_backends = project_backends.filter(project=project)

            project_backends.delete()
            write('Successfully removed project-backend mappings.\n')
