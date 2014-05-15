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

from django.db import transaction
from snf_django.management import utils
from snf_django.management.commands import SynnefoCommand, CommandError
from astakos.im.functions import (terminate, suspend, unsuspend,
                                  reinstate, check_expiration,
                                  approve_application, deny_application)


class Command(SynnefoCommand):
    help = "Manage projects and applications"

    option_list = SynnefoCommand.option_list + (
        make_option('--approve',
                    dest='approve',
                    metavar='<application id>',
                    help="Approve a project application"),
        make_option('--deny',
                    dest='deny',
                    metavar='<application id>',
                    help="Deny a project application"),
        make_option('--terminate',
                    dest='terminate',
                    metavar='<project id>',
                    help="Terminate a project"),
        make_option('--suspend',
                    dest='suspend',
                    metavar='<project id>',
                    help="Suspend a project"),
        make_option('--unsuspend',
                    dest='unsuspend',
                    metavar='<project id>',
                    help="Resume a suspended project"),
        make_option('--reinstate',
                    dest='reinstate',
                    metavar='<project id>',
                    help=("Resume a terminated project; this will fail if its "
                          "name has been reserved by another project")),
        make_option('--check-expired',
                    action='store_true',
                    dest='check_expired',
                    default=False,
                    help="Check projects for expiration"),
        make_option('--terminate-expired',
                    action='store_true',
                    dest='terminate_expired',
                    default=False,
                    help="Terminate all expired projects"),
        make_option('--message', '-m',
                    dest='message',
                    metavar='<msg>',
                    help=("Specify reason of action, "
                          "e.g. when denying a project")),
    )

    @transaction.commit_on_success
    def handle(self, *args, **options):

        self.output_format = options["output_format"]
        message = options['message']

        actions = {
            'terminate': terminate,
            'reinstate': reinstate,
            'unsuspend': unsuspend,
            'suspend': suspend,
            'approve': approve_application,
            'deny': lambda a: deny_application(a, reason=message),
            'check_expired': lambda _: self.expire(execute=False),
            'terminate_expired': lambda _: self.expire(execute=True),
        }

        opts = [(key, value)
                for (key, value) in options.items()
                if key in actions and value]

        if len(opts) != 1:
            raise CommandError("Specify exactly one operation.")

        key, value = opts[0]
        action = actions[key]
        try:
            action(value)
        except BaseException as e:
            raise CommandError(e)

    def print_expired(self, projects, execute):
        length = len(projects)
        if length == 0:
            s = 'No expired projects.\n'
            self.stderr.write(s)
            return
        labels = ('Project', 'Name', 'Status', 'Expiration date')
        utils.pprint_table(self.stdout, projects, labels,
                           self.output_format, title="Expired projects")

        if execute:
            self.stderr.write('%d projects have been terminated.\n' %
                              (length,))

    def expire(self, execute=False):
        projects = check_expiration(execute=execute)
        self.print_expired(projects, execute)
