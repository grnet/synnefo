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

from astakos.im.models import AuthProviderPolicyProfile as Profile
from synnefo.lib.ordereddict import OrderedDict
from snf_django.management.commands import SynnefoCommand, CommandError
from snf_django.management import utils


class Command(SynnefoCommand):
    args = "<profile_name>"
    help = "Show authentication provider profile details"

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please profile name")

        try:
            profile = Profile.objects.get(name=args[0])
        except Profile.DoesNotExist:
            raise CommandError("Profile does not exist")

        kv = OrderedDict(
            [
                ('id', profile.id),
                ('is active', str(profile.active)),
                ('name', profile.name),
                ('is exclusive', profile.is_exclusive),
                ('policies', profile.policies),
                ('groups', profile.groups.all()),
                ('users', profile.users.all())
            ])

        utils.pprint_table(self.stdout, [kv.values()], kv.keys(),
                           options["output_format"], vertical=True)
