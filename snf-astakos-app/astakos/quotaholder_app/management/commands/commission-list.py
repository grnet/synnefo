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

from snf_django.management.commands import ListCommand, CommandError

from optparse import make_option
from astakos.quotaholder_app.models import Commission
import datetime


class Command(ListCommand):
    help = "List pending commissions"

    option_list = ListCommand.option_list + (
        make_option('--overdue',
                    help="Specify overdue time in seconds"),
    )

    object_class = Commission

    FIELDS = {
        'serial': ('serial', ('Commission serial')),
        'name': ('name', 'Commission name'),
        'clientkey': (
            'clientkey',
            'Key of the client (service) that issued the commission'),
        'issue time': ('issue_datetime', 'Commission issue time'),
    }

    fields = ['serial', 'name', 'clientkey', 'issue time']

    def handle_args(self, *args, **options):
        overdue = options['overdue']
        if overdue is not None:
            try:
                overdue = int(overdue)
            except ValueError:
                raise CommandError("Expecting an integer.")

            delta = datetime.timedelta(0, overdue)
            until = datetime.datetime.now() - delta
            self.filters["issue_datetime__lt"] = until
