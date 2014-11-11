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


from django.core.management import call_command
from django.utils.importlib import import_module
from django.conf import settings

from astakos.im.models import SessionCatalog
from snf_django.management.commands import SynnefoCommand


class Command(SynnefoCommand):
    help = "Cleanup sessions and session catalog"

    def handle(self, **options):
        self.stderr.write('Cleanup sessions ...\n')
        call_command('cleanup')

        self.stderr.write('Cleanup session catalog ...\n')
        engine = import_module(settings.SESSION_ENGINE)
        store = engine.SessionStore()
        tbd = (entry for entry in SessionCatalog.objects.all()
               if not store.exists(entry.session_key))
        for entry in tbd:
            entry.delete()
