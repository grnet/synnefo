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

from snf_django.management.commands import SynnefoCommand
from snf_django.management import utils

from pithos.api.util import get_backend, update_public_meta, is_uuid


class Command(SynnefoCommand):
    args = "<account> <container> <object> or <object uuid>"
    help = """Show file information"""

    option_list = SynnefoCommand.option_list + (
        make_option("--obj-version", dest="obj_version",
                    default=None,
                    help="Show information for a specific file version"),
        make_option("--domain", dest="domain",
                    default='pithos',
                    help="Show file attributes from the specific domain."),
        make_option("--hashmap", dest="hashmap",
                    default=False,
                    action='store_true',
                    help="Display also the object hashmap")
    )

    def handle(self, *args, **options):
        success_status = False
        try:
            b = get_backend()
            b.pre_exec()

            if len(args) == 3:
                account, container, name = args
            elif len(args) == 1:
                if not is_uuid(args[0]):
                    raise CommandError('Invalid UUID')
                try:
                    account, container, name = b.get_uuid(
                        None, args[0], check_permissions=False)
                except NameError:
                    raise CommandError('Unknown UUID')
            else:
                raise CommandError("Invalid number of arguments")

            kv = b.get_object_meta(account, account, container, name,
                                   options['domain'], options['obj_version'])

            if options['obj_version'] is None:
                _, path, permissions = b.get_object_permissions(account,
                                                                account,
                                                                container,
                                                                name)
                if path is not None:
                    kv['permissions'] = path, dict(permissions)

                public = b.get_object_public(account, account, container, name)
                if public is not None:
                    update_public_meta(public, kv)

            if options['hashmap']:
                _, size, kv['hashmap'] = b.get_object_hashmap(
                    account, account, container, name, options['obj_version'])

            utils.pprint_table(self.stdout, [kv.values()], kv.keys(),
                               options["output_format"], vertical=True)

            success_status = True
        except Exception as e:
            raise CommandError(e)
        finally:
            b.post_exec(success_status)
            b.close()
