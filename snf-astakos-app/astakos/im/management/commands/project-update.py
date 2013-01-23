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
from astakos.im.functions import terminate, suspend, resume
from astakos.im.project_xctx import project_transaction_context

class Command(BaseCommand):
    args = "<project id>"
    help = "Update project state"

    option_list = BaseCommand.option_list + (
        make_option('--terminate',
                    action='store_true',
                    dest='terminate',
                    default=False,
                    help="Terminate project"),
        make_option('--resume',
                    action='store_true',
                    dest='resume',
                    default=False,
                    help="Resume project"),
        make_option('--suspend',
                    action='store_true',
                    dest='suspend',
                    default=False,
                    help="Suspend project")
    )

    def handle(self, *args, **options):
        if len(args) < 1:
            raise CommandError("Please provide a project id")
        try:
            id = int(args[0])
        except ValueError:
            raise CommandError('Invalid id')
        else:
            if options['terminate']:
                run_command(terminate, id)
            elif options['resume']:
                run_command(resume, id)
            elif options['suspend']:
                run_command(suspend, id)

@project_transaction_context(sync=True)
def run_command(func, id, ctx=None):
    try:
        func(id)
    except BaseException as e:
        if ctx:
            ctx.mark_rollback()
        raise CommandError(e)
