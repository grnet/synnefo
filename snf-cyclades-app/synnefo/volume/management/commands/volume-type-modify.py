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
from django.db import transaction

from snf_django.management.commands import SynnefoCommand
from synnefo.management.common import get_resource
from snf_django.management.utils import parse_bool


from logging import getLogger
log = getLogger(__name__)


class Command(SynnefoCommand):
    args = "<volume_type_id>"
    help = "Modify a Volume Type"

    option_list = SynnefoCommand.option_list + (
        make_option(
            "--deleted",
            dest="deleted",
            metavar="True|False",
            choices=["True", "False"],
            default=None,
            help="Mark/unmark a volume type as deleted. Deleted volume types"
                 " cannot be used for creation of new volumes. All related"
                 " flavors will also be updated."),
    )

    @transaction.commit_on_success
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a volume type ID")

        vtype = get_resource("volume-type", args[0], for_update=True)

        deleted = options['deleted']

        if deleted:
            deleted = parse_bool(deleted)
            self.stdout.write("Marking volume type '%s' and all related"
                              " flavors as deleted=%s\n" % (vtype.id, deleted))
            vtype.deleted = deleted
            vtype.save()
            vtype.flavors.update(deleted=deleted)
