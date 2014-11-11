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
from synnefo.management.common import get_resource
from snf_django.management.utils import parse_bool


from logging import getLogger
log = getLogger(__name__)


class Command(SynnefoCommand):
    args = "<flavor_id>"
    help = "Modify a flavor"

    option_list = SynnefoCommand.option_list + (
        make_option(
            "--deleted",
            dest="deleted",
            metavar="True|False",
            choices=["True", "False"],
            default=None,
            help="Mark/unmark a flavor as deleted"),
        make_option(
            "--allow-create",
            dest="allow_create",
            metavar="True|False",
            choices=["True", "False"],
            default=None,
            help="Set if users can create servers with this flavor"),
    )

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a flavor ID")

        flavor = get_resource("flavor", args[0], for_update=True)

        deleted = options['deleted']

        if deleted:
            deleted = parse_bool(deleted)
            log.info("Marking flavor %s as deleted=%s", flavor, deleted)
            flavor.deleted = deleted
            flavor.save()

        allow_create = options['allow_create']
        if allow_create:
            allow_create = parse_bool(allow_create)
            log.info("Marking flavor %s as allow_create=%s", flavor,
                     allow_create)
            flavor.allow_create = allow_create
            flavor.save()
