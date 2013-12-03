# Copyright 2013 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

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
                _, kv['hashmap'] = b.get_object_hashmap(account, account,
                                                        container, name,
                                                        options['obj_version'])

            utils.pprint_table(self.stdout, [kv.values()], kv.keys(),
                               options["output_format"], vertical=True)

            success_status = True
        except Exception, e:
            raise CommandError(e)
        finally:
            b.post_exec(success_status)
            b.close()
