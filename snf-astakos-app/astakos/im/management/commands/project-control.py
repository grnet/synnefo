# Copyright 2012, 2013 GRNET S.A. All rights reserved.
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

from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from astakos.im.functions import (terminate, suspend, resume, check_expiration,
                                  approve_application, deny_application)
from astakos.im.project_xctx import cmd_project_transaction_context


class Command(BaseCommand):
    help = "Manage projects and applications"

    option_list = BaseCommand.option_list + (
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
                    dest='resume',
                    metavar='<project id>',
                    help="Resume a suspended project"),
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

    def handle(self, *args, **options):

        message = options['message']

        pid = options['terminate']
        if pid is not None:
            self.run_command(terminate, pid)
            return

        pid = options['resume']
        if pid is not None:
            self.run_command(resume, pid)
            return

        pid = options['suspend']
        if pid is not None:
            self.run_command(suspend, pid)
            return

        appid = options['approve']
        if appid is not None:
            self.run_command(approve_application, appid)
            return

        appid = options['deny']
        if appid is not None:
            self.run_command(deny_application, appid, message)
            return

        if options['check_expired']:
            self.expire(execute=False)
            return

        if options['terminate_expired']:
            self.expire(execute=True)

    def run_command(self, func, *args):
        with cmd_project_transaction_context(sync=True) as ctx:
            try:
                func(*args)
            except BaseException as e:
                if ctx:
                    ctx.mark_rollback()
                raise CommandError(e)

    def print_expired(self, projects, execute):
        length = len(projects)
        if length == 0:
            s = 'No expired projects.\n'
        elif length == 1:
            s = '1 expired project:\n'
        else:
            s = '%d expired projects:\n' % (length,)
        self.stdout.write(s)

        if length > 0:
            labels = ('Project', 'Name', 'Status', 'Expiration date')
            columns = (10, 30, 14, 30)

            line = ' '.join(l.rjust(w) for l, w in zip(labels, columns))
            self.stdout.write(line + '\n')
            sep = '-' * len(line)
            self.stdout.write(sep + '\n')

            for project in projects:
                line = ' '.join(f.rjust(w) for f, w in zip(project, columns))
                self.stdout.write(line + '\n')

            if execute:
                self.stdout.write('%d projects have been terminated.\n' % (
                    length,))

    @cmd_project_transaction_context(sync=True)
    def expire(self, execute=False, ctx=None):
        try:
            projects = check_expiration(execute=execute)
            self.print_expired(projects, execute)
        except BaseException as e:
            if ctx:
                ctx.mark_rollback()
            raise CommandError(e)
