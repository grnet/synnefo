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

from django.core.management.base import CommandError
from optparse import make_option

from pithos.api.util import get_backend
from snf_django.management.commands import SynnefoCommand

import logging

logger = logging.getLogger(__name__)

CLIENTKEY = 'pithos'


class Command(SynnefoCommand):
    help = "Display unresolved commissions and trigger their recovery"

    option_list = SynnefoCommand.option_list + (
        make_option('--fix',
                    dest='fix',
                    action="store_true",
                    default=False,
                    help="Fix unresolved commissions"),
    )

    def handle(self, **options):
        b = get_backend()
        try:
            b.pre_exec()
            pending_commissions = b.astakosclient.get_pending_commissions()

            if pending_commissions:
                self.stdout.write(
                    "Unresolved commissions: %s\n" % pending_commissions
                )
            else:
                self.stdout.write("No unresolved commissions were found\n")
                return

            if options['fix']:
                to_accept = b.commission_serials.lookup(pending_commissions)
                to_reject = list(set(pending_commissions) - set(to_accept))
                response = b.astakosclient.resolve_commissions(
                    accept_serials=to_accept,
                    reject_serials=to_reject
                )
                accepted = response['accepted']
                rejected = response['rejected']
                failed = response['failed']
                self.stdout.write("Accepted commissions: %s\n" % accepted)
                self.stdout.write("Rejected commissions: %s\n" % rejected)
                self.stdout.write("Failed commissions:\n")
                for i in failed:
                    self.stdout.write('%s\n' % i)

                b.commission_serials.delete_many(accepted)
        except Exception, e:
            logger.exception(e)
            b.post_exec(False)
            raise CommandError(e)
        else:
            b.post_exec(True)
        finally:
            b.close()
