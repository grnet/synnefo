# Copyright 2012 GRNET S.A. All rights reserved.
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

from django.core.management.base import NoArgsCommand, CommandError

from optparse import make_option

from pithos.api.util import get_backend
from pithos.backends.modular import CLUSTER_NORMAL, DEFAULT_SOURCE
from synnefo.webproject.management import utils
from astakosclient.errors import AstakosClientException

ENTITY_KEY = '1'

backend = get_backend()

class Command(NoArgsCommand):
    help = "List and reset pithos usage"

    option_list = NoArgsCommand.option_list + (
        make_option('--list',
                    dest='list',
                    action="store_true",
                    default=True,
                    help="List usage for all or specified user"),
        make_option('--reset',
                    dest='reset',
                    action="store_true",
                    default=False,
                    help="Reset usage for all or specified users"),
        make_option('--diverging',
                    dest='diverging',
                    action="store_true",
                    default=False,
                    help=("List or reset diverging usages")),
        make_option('--user',
                    dest='users',
                    action='append',
                    metavar='USER_UUID',
                    help=("Specify which users --list or --reset applies."
                          "This option can be repeated several times."
                          "If no user is specified --list or --reset "
                          "will be applied globally.")),
        make_option(
            "--no-headers",
            dest="headers",
            action="store_false",
            default=True,
            help="Do not display headers"),
        make_option(
            "--output-format",
            dest="output_format",
            metavar="[pretty, csv, json]",
            default="pretty",
            choices=["pretty", "csv", "json"],
            help="Select the output format: pretty [the default], tabs"
                 " [tab-separated output], csv [comma-separated output]"),

    )

    def handle_noargs(self, **options):
        try:
            account_nodes = backend.node.node_accounts(options['users'])
            if not account_nodes:
                raise CommandError('No users found.')

            db_usage = {}
            for path, node in account_nodes:
                size = backend.node.node_account_usage(node, CLUSTER_NORMAL)
                db_usage[path] = size or 0

            result = backend.astakosclient.service_get_quotas(
                backend.service_token,
            )

            qh_usage = {}
            resource = 'pithos.diskspace'
            pending_list = []
            for uuid, d in result.iteritems():
                pithos_dict = d.get(DEFAULT_SOURCE, {}).get(resource, {})
                pending = pithos_dict.get('pending', 0)
                if pending != 0:
                    pending_list.append(pending)
                    continue
                qh_usage[uuid] = pithos_dict.get('usage', 0)

            if pending_list:
                self.stdout.write((
                    "There are pending commissions for: %s.\n"
                    "Reconcile commissions and retry"
                    "in order to list/reset their quota.\n"
                ) % pending_list)

            headers = ['uuid', 'usage']
            table = []
            provisions = []
            for uuid in db_usage.keys():
                try:
                    delta = db_usage[uuid] - qh_usage[uuid]
                except KeyError:
                    self.stdout.write('Unknown holder: %s\n' % uuid)
                    continue
                else:
                    if options['diverging'] and delta == 0:
                        continue
                    table.append((uuid, db_usage[uuid]))
                    provisions.append({"holder": uuid,
                                       "source": DEFAULT_SOURCE,
                                       "resource": resource,
                                       "quantity": delta
                    })


            if options['reset']:
                if not provisions:
                    raise CommandError('Nothing to reset')
                request = {}
                request['force'] = True
                request['auto_accept'] = True
                request['provisions'] = provisions
                try:
                    serial = backend.astakosclient.issue_commission(
                        backend.service_token, request
                    )
                except AstakosClientException, e:
                    self.stdout.write(e.details)
                else:
                    backend.commission_serials.insert_many([serial])
            elif options['list'] and table:
                output_format = options["output_format"]
                if output_format != "json" and not options["headers"]:
                    headers = None
                utils.pprint_table(self.stdout, table, headers, output_format)
        finally:
            backend.close()
