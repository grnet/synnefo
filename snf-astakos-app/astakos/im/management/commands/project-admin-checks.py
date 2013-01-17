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

from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from astakos.im.functions import check_expiration

@transaction.commit_manually
class Command(BaseCommand):
    help = "Perform administration checks on projects"

    option_list = BaseCommand.option_list + (
        make_option('--expire',
                    action='store_true',
                    dest='expire',
                    default=False,
                    help="Check projects for expiration"),
        make_option('--execute',
                    action='store_true',
                    dest='execute',
                    default=False,
                    help="Perform the actual operation"),
    )


    def print_expired(self, projects, execute):
        length = len(projects)
        if length == 0:
            s = 'No expired projects.\n'
        elif length == 1:
            s = '1 expired project:\n'
        else:
            s = '%d expired projects:\n' %(length,)
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
                self.stdout.write(line.encode('utf8') + '\n')

            if execute:
                self.stdout.write('%d projects have been terminated.\n' %(length,))

    def handle(self, *args, **options):

        execute = options['execute']

        try:
            if options['expire']:
                projects = check_expiration(execute=execute)
                self.print_expired(projects, execute)
        except BaseException as e:
            transaction.rollback()
            raise CommandError(e)
        else:
            transaction.commit()
