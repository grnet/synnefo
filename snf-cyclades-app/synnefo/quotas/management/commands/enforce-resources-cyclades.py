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

import string
from optparse import make_option
from django.db import transaction

from synnefo.lib.ordereddict import OrderedDict
from synnefo.quotas import util
from synnefo.quotas import enforce
from synnefo.quotas import errors
from snf_django.management.commands import SynnefoCommand, CommandError
from snf_django.management.utils import pprint_table


DEFAULT_RESOURCES = ["cyclades.cpu",
                     "cyclades.ram",
                     "cyclades.floating_ip",
                     ]


class Command(SynnefoCommand):
    help = """Check and fix quota violations for Cyclades resources.
    """
    option_list = SynnefoCommand.option_list + (
        make_option("--max-operations",
                    help="Limit operations per backend."),
        make_option("--users", dest="users",
                    help=("Enforce resources only for the specified list "
                          "of users, e.g uuid1,uuid2")),
        make_option("--exclude-users",
                    help=("Exclude list of users from resource enforcement")),
        make_option("--resources",
                    help="Specify resources to check, default: %s" %
                    ",".join(DEFAULT_RESOURCES)),
        make_option("--fix",
                    default=False,
                    action="store_true",
                    help="Fix violations"),
        make_option("--force",
                    default=False,
                    action="store_true",
                    help=("Confirm actions that may permanently "
                          "remove a vm")),
        make_option("--shutdown-timeout",
                    help="Force vm shutdown after given seconds."),
    )

    def confirm(self):
        self.stdout.write("Confirm? [y/N] ")
        try:
            response = raw_input()
        except EOFError:
            response = "ABORT"
        if string.lower(response) not in ['y', 'yes']:
            self.stderr.write("Aborted.\n")
            exit()

    def get_handlers(self, resources):
        def rem(v):
            try:
                resources.remove(v)
                return True
            except ValueError:
                return False

        if resources is None:
            resources = list(DEFAULT_RESOURCES)
        else:
            resources = resources.split(",")

        handlers = [h for h in enforce.RESOURCE_HANDLING if rem(h[0])]
        if resources:
            m = "No such resource '%s'" % resources[0]
            raise CommandError(m)
        return handlers

    @transaction.commit_on_success
    def handle(self, *args, **options):
        write = self.stderr.write
        fix = options["fix"]
        force = options["force"]
        maxops = options["max_operations"]
        if maxops is not None:
            try:
                maxops = int(maxops)
            except ValueError:
                m = "Expected integer max operations."
                raise CommandError(m)

        shutdown_timeout = options["shutdown_timeout"]
        if shutdown_timeout is not None:
            try:
                shutdown_timeout = int(shutdown_timeout)
            except ValueError:
                m = "Expected integer shutdown timeout."
                raise CommandError(m)

        users = options['users']
        if users is not None:
            users = users.split(',')

        excluded = options['exclude_users']
        excluded = set(excluded.split(',') if excluded is not None else [])

        handlers = self.get_handlers(options["resources"])
        try:
            qh_holdings = util.get_qh_users_holdings(users)
        except errors.AstakosClientException as e:
            raise CommandError(e)

        qh_holdings = sorted(qh_holdings.items())
        resources = set(h[0] for h in handlers)
        dangerous = bool(resources.difference(DEFAULT_RESOURCES))

        opts = {"shutdown_timeout": shutdown_timeout}
        actions = {}
        overlimit = []
        viol_id = 0
        for resource, handle_resource, resource_type in handlers:
            if resource_type not in actions:
                actions[resource_type] = OrderedDict()
            actual_resources = enforce.get_actual_resources(resource_type,
                                                            users)
            for user, user_quota in qh_holdings:
                if user in excluded:
                    continue
                for source, source_quota in user_quota.iteritems():
                    try:
                        qh = util.transform_quotas(source_quota)
                        qh_value, qh_limit, qh_pending = qh[resource]
                    except KeyError:
                        write("Resource '%s' does not exist in Quotaholder"
                              " for user '%s' and source '%s'!\n" %
                              (resource, user, source))
                        continue
                    if qh_pending:
                        write("Pending commission for user '%s', source '%s', "
                              "resource '%s'. Skipping\n" %
                              (user, source, resource))
                        continue
                    diff = qh_value - qh_limit
                    if diff > 0:
                        viol_id += 1
                        overlimit.append((viol_id, user, source, resource,
                                          qh_limit, qh_value))
                        relevant_resources = actual_resources[user]
                        handle_resource(viol_id, resource, relevant_resources,
                                        diff, actions)

        if not overlimit:
            write("No violations.\n")
            return

        headers = ("#", "User", "Source", "Resource", "Limit", "Usage")
        pprint_table(self.stdout, overlimit, headers,
                     options["output_format"], title="Violations")

        if any(actions.values()):
            self.stdout.write("\n")
            if fix:
                if dangerous and not force:
                    write("You are enforcing resources that may permanently "
                          "remove a vm.\n")
                    self.confirm()
                write("Applying actions. Please wait...\n")
            title = "Applied Actions" if fix else "Suggested Actions"
            log = enforce.perform_actions(actions, maxops=maxops, fix=fix,
                                          options=opts)
            headers = ("Type", "ID", "State", "Backend", "Action", "Violation")
            if fix:
                headers += ("Result",)
            pprint_table(self.stdout, log, headers,
                         options["output_format"], title=title)
