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

from optparse import make_option
from django.core.management.base import CommandError

from snf_django.management.commands import SynnefoCommand
from synnefo.db.models import Backend
from snf_django.management.utils import parse_bool
from synnefo.management import common

HYPERVISORS = [h[0] for h in Backend.HYPERVISORS]


class Command(SynnefoCommand):
    output_transaction = True
    args = "<backend_id>"
    help = "Modify a backend"

    option_list = SynnefoCommand.option_list + (
        make_option('--clustername',
                    dest='clustername',
                    help="Set backend's clustername"),
        make_option('--port',
                    dest='port',
                    help="Set backend's port"),
        make_option('--username',
                    dest='username',
                    help="Set backend'username"),
        make_option('--password',
                    dest='password',
                    help="Set backend's password"),
        make_option('--drained',
                    dest='drained',
                    choices=["True", "False"],
                    metavar="True|False",
                    help="Set the backend as drained to exclude from"
                         " allocation operations"),
        make_option('--hypervisor',
                    dest='hypervisor',
                    default=None,
                    choices=HYPERVISORS,
                    metavar="|".join(HYPERVISORS),
                    help="The hypervisor that the Ganeti backend uses"),
        make_option('--offline',
                    dest='offline',
                    choices=["True", "False"],
                    metavar="True|False",
                    help="Set the backend as offline to not communicate in"
                         " order to avoid delays"),
    )

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a backend ID")

        backend = common.get_resource("backend", args[0], for_update=True)

        # Ensure fields correspondence with options and Backend model
        credentials_changed = False
        fields = ('clustername', 'port', 'username', 'password')
        for field in fields:
            value = options.get(field)
            if value is not None:
                backend.__setattr__(field, value)
                credentials_changed = True

        if credentials_changed:
                # check credentials, if any of them changed!
                common.check_backend_credentials(backend.clustername,
                                                 backend.port,
                                                 backend.username,
                                                 backend.password)
        if options['drained']:
            backend.drained = parse_bool(options['drained'], strict=True)
        if options['offline']:
            backend.offline = parse_bool(options['offline'], strict=True)
        hypervisor = options["hypervisor"]
        if hypervisor:
            backend.hypervisor = hypervisor

        backend.save()
