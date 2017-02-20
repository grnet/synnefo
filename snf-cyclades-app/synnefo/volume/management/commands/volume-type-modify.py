# Copyright (C) 2010-2017 GRNET S.A.
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
from synnefo.db import transaction

from snf_django.management.commands import SynnefoCommand
from synnefo.management.common import get_resource
from snf_django.management.utils import parse_bool

import re

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
        make_option(
            "--spec-add",
            dest="spec_add",
            metavar="<key1>=<value1>,<key2>=<value2>,...",
            help="Add or update key value pair specs to a volume type"
        ),
        make_option(
            "--spec-delete",
            dest="spec_delete",
            metavar="<key1>,<key2>,...",
            help="Delete a list of specs from a volume type"
        )
    )

    @transaction.commit_on_success
    def handle(self, *args, **options):

        if len(args) != 1:
            raise CommandError("Please provide a volume type ID")

        vtype = get_resource("volume-type", args[0], for_update=True)

        # Keep a list with spec keys that are added. If one of these keys
        # appears in the list to be deleted, we should raise an error
        added_keys = []
        spec_add = options.get('spec_add')
        if spec_add:
            spec_regex = re.compile(r'^(?P<key>.+?)=(?P<value>.+)$')

            specs = spec_add.split(',')
            for spec in specs:
                match = spec_regex.match(spec)
                if match is None:
                    raise CommandError("Incorrect spec format. Expected: "
                                       " <key>=<value> ,found: \'%s\' " % spec)
                k, v = match.group('key'), match.group('value')
                spec, _ = vtype.specs.get_or_create(key=k)
                spec.value = v
                spec.save()
                added_keys.append(k)

        spec_delete = options.get('spec_delete')
        if spec_delete:
            spec_keys = spec_delete.split(',')
            for key in spec_keys:
                if key in added_keys:
                    raise CommandError("Cannot add and delete key %s at the "
                                       "same time. If that was the intended "
                                       "action, consider adding first and then"
                                       " deleting it" % key)
                spec = vtype.specs.filter(key=key)
                if not spec:
                    raise CommandError("Spec with key \'%s\' does not exist" %
                                       key)
                spec.delete()

        deleted = options['deleted']
        if deleted:
            deleted = parse_bool(deleted)
            self.stdout.write("Marking volume type '%s' and all related"
                              " flavors as deleted=%s\n" % (vtype.id, deleted))
            vtype.deleted = deleted
            vtype.save()
            vtype.flavors.update(deleted=deleted)
