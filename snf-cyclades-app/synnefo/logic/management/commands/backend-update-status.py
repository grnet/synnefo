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
#
from snf_django.management.commands import SynnefoCommand
from synnefo.db.models import Backend
from synnefo.logic import backend as backend_mod


HELP_MSG = """Query Ganeti backends and update the status of backend in DB.

This command updates:
    * the list of the enabled disk-templates
    * the available resources (disk, memory, CPUs)
"""


class Command(SynnefoCommand):
    help = HELP_MSG

    def handle(self, **options):
        for backend in Backend.objects.select_for_update()\
                                      .filter(offline=False):
            backend_mod.update_backend_disk_templates(backend)
            backend_mod.update_backend_resources(backend)
            self.stdout.write("Successfully updated backend '%s'\n" % backend)
