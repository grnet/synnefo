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
import re

from django.core.management.base import CommandError

from snf_django.management.commands import SynnefoCommand
from synnefo.management.common import get_resource
from snf_django.management.utils import parse_bool
from synnefo.db import transaction


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
        make_option(
            '--public',
            dest='public',
            choices=["True", "False"],
            metavar="True|False",
            default=None,
            help="Mark the flavor as public"),
        make_option(
            '--spec-add',
            dest='spec_add',
            metavar="<key1>=<value1>,<key2>=<value2>,...",
            help="Add or update key value pair specs to a flavor"),
        make_option(
            '--spec-delete',
            metavar="<key1>,<key2>,...",
            help="Delete a list of specs from the flavor")

    )

    @transaction.commit_on_success
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a flavor ID")

        flavor = get_resource("flavor", args[0], for_update=True)

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
                spec, _ = flavor.specs.get_or_create(key=k)
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
                spec = flavor.specs.filter(key=key)
                if not spec:
                    raise CommandError("Spec with key \'%s\' does not exist" %
                                       key)
                spec.delete()

        deleted = options.get('deleted')
        if deleted:
            deleted = parse_bool(deleted)
            log.info("Marking flavor %s as deleted=%s", flavor, deleted)
            flavor.deleted = deleted

        public = options.get('public')
        if public:
            public = parse_bool(public, strict=True)
            log.info("Marking flavor %s as public=%s", flavor, public)
            flavor.public = public

        allow_create = options.get('allow_create')
        if allow_create:
            allow_create = parse_bool(allow_create)
            log.info("Marking flavor %s as allow_create=%s", flavor,
                     allow_create)
            flavor.allow_create = allow_create

        if deleted is not None or public is not None\
           or allow_create is not None:
            flavor.save()
