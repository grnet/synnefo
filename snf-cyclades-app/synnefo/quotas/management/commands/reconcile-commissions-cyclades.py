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

from snf_django.management.commands import SynnefoCommand
from synnefo import quotas


class Command(SynnefoCommand):
    help = "Detect and resolve pending commissions to Quotaholder"
    output_transaction = True
    option_list = SynnefoCommand.option_list + (
        make_option("--fix", dest="fix",
                    action='store_true',
                    default=False,
                    help="Fix pending commissions"
                    ),
    )

    def handle(self, *args, **options):
        fix = options['fix']

        accepted, rejected = quotas.resolve_pending_commissions()

        if accepted:
            self.stdout.write("Pending accepted commissions:\n %s\n"
                              % list_to_string(accepted))

        if rejected:
            self.stdout.write("Pending rejected commissions:\n %s\n"
                              % list_to_string(rejected))

        if fix and (accepted or rejected):
            self.stdout.write("Fixing pending commissions..\n")
            quotas.reconcile_resolve_commissions(accept=accepted,
                                                 reject=rejected,
                                                 strict=False)


def list_to_string(l):
    return ",".join([str(x) for x in l])
