# Copyright 2012 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of GRNET S.A.
#

from snf_django.management.commands import SynnefoCommand, CommandError
from optparse import make_option

from synnefo.management import common
from synnefo.plankton.backend import PlanktonBackend
from snf_django.management import utils


class Command(SynnefoCommand):
    args = "<snapshot_id>"
    help = "Display available information about a snapshot"
    option_list = SynnefoCommand.option_list + (
        make_option(
            '--user-id',
            dest='userid',
            default=None,
            help="The UUID of the owner of the snapshot. Required"
                 "if snapshot is not public"),
    )

    @common.convert_api_faults
    def handle(self, *args, **options):

        if len(args) != 1:
            raise CommandError("Please provide a snapshot ID")

        snapshot_id = args[0]
        userid = options["userid"]

        with PlanktonBackend(userid) as backend:
            snapshot = backend.get_snapshot(userid, snapshot_id)
        utils.pprint_table(out=self.stdout, table=[snapshot.values()],
                           headers=snapshot.keys(), vertical=True)
