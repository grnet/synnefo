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

#from optparse import make_option

from synnefo.db import transaction
from django.core.management.base import CommandError
from snf_django.management.commands import RemoveCommand
from synnefo.management import common
from synnefo.logic import ips


class Command(RemoveCommand):
    args = "<floating_ip_id> [<floating_ip_id> ...]"
    help = "Release a floating IP"

    @common.convert_api_faults
    @transaction.commit_on_success
    def handle(self, *args, **options):
        if not args:
            raise CommandError("Please provide a floating-ip ID")

        force = options['force']
        message = "floating IPs" if len(args) > 1 else "floating IP"
        self.confirm_deletion(force, message, args)

        for floating_ip_id in args:
            self.stdout.write("\n")
            try:
                floating_ip = common.get_resource("floating-ip",
                                                  floating_ip_id,
                                                  for_update=True)
                ips.delete_floating_ip(floating_ip)
                self.stdout.write("Deleted floating IP '%s'.\n" %
                                  floating_ip_id)
            except CommandError as e:
                self.stdout.write("Error -- %s\n" % e.message)
