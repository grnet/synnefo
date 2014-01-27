# Copyright 2011-2013 GRNET S.A. All rights reserved.
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
from optparse import make_option
from django.core.management.base import CommandError
from synnefo.volume import snapshots, util
from synnefo.management import common
from snf_django.management.commands import SynnefoCommand


class Command(SynnefoCommand):
    args = "<Snapshot ID>"
    help = "Modify a snapshot"
    option_list = SynnefoCommand.option_list + (
        make_option(
            "--user_id",
            dest="user_id",
            default=None,
            help="UUID of the owner of the snapshot"),
        make_option(
            "--name",
            dest="name",
            default=None,
            help="Update snapshot's name"),
        make_option(
            "--description",
            dest="description",
            default=None,
            help="Update snapshot's description"),
    )

    @common.convert_api_faults
    def handle(self, *args, **options):
        if not args:
            raise CommandError("Please provide a snapshot ID")

        snapshot_id = args[0]
        user_id = self.options["user_id"]
        name = self.options["name"]
        description = self.options["description"]

        snapshot = util.get_snapshot(user_id, snapshot_id)

        snapshots.modify(snapshot, name=name, description=description)
        self.stdout.write("Successfully updated snapshot %s\n"
                          % snapshot)
