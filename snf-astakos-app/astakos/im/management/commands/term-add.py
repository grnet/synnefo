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

from os.path import abspath
from snf_django.management.commands import SynnefoCommand, CommandError
from astakos.im import transaction
from astakos.im.models import ApprovalTerms, AstakosUser


class Command(SynnefoCommand):
    args = "<location>"
    help = "Insert approval terms"

    @transaction.commit_on_success
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Invalid number of arguments")

        location = abspath(args[0].decode('utf8'))
        try:
            open(location, 'r')
        except IOError:
            raise CommandError("Invalid location")

        terms = ApprovalTerms(location=location)
        terms.save()
        AstakosUser.objects.select_for_update().\
            filter(has_signed_terms=True).\
            update(has_signed_terms=False, date_signed_terms=None)

        msg = "Created term id %d" % (terms.id,)
        self.stdout.write(msg + '\n')
