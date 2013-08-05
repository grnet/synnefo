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
from snf_django.management.commands import ListCommand

from optparse import make_option
from astakos.quotaholder_app.models import Commission
import datetime


class Command(ListCommand):
    help = "List pending commissions"

    option_list = ListCommand.option_list + (
        make_option('--overdue',
                    help="Specify overdue time in seconds"),
    )

    object_class = Commission

    FIELDS = {
        'serial': ('serial', ('Commission serial')),
        'name': ('name', 'Commission name'),
        'clientkey': (
            'clientkey',
            'Key of the client (service) that issued the commission'),
        'issue time': ('issue_datetime', 'Commission issue time'),
    }

    fields = ['serial', 'name', 'clientkey', 'issue time']

    def handle_args(self, *args, **options):
        overdue = options['overdue']
        if overdue is not None:
            try:
                overdue = int(overdue)
            except ValueError:
                raise CommandError("Expecting an integer.")

            delta = datetime.timedelta(0, overdue)
            until = datetime.datetime.now() - delta
            self.filters["issue_datetime__lt"] = until
