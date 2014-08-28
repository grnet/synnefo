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

from astakos.im import transaction
from snf_django.management.commands import SynnefoCommand, CommandError

from astakos.im.auth import fix_superusers


class Command(SynnefoCommand):
    help = "Transform superusers created by syncdb into AstakosUser instances"

    @transaction.commit_on_success
    def handle(self, **options):
        try:
            fixed = fix_superusers()
            count = len(fixed)
            if count != 0:
                self.stderr.write("Fixed %s superuser(s).\n" % count)
            else:
                self.stderr.write("No superuser needed a fix.\n")
        except BaseException, e:
            raise CommandError(e)
