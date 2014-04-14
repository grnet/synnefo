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

from django.utils import simplejson as json

from pithos.api.settings import pithos_services
from synnefo.lib.services import filter_public
from snf_django.management.commands import SynnefoCommand


class Command(SynnefoCommand):
    help = "Export Pithos services in JSON format."

    def handle(self, *args, **options):
        output = json.dumps(filter_public(pithos_services), indent=4)
        self.stdout.write(output + "\n")
