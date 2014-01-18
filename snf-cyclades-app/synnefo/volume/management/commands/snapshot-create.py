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

from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from synnefo.management import common
#from snf_django.management.utils import parse_bool
from synnefo.volume import snapshots


class Command(BaseCommand):
    args = "<volume ID>"
    help = "Create a snapshot from the specified volume"

    option_list = BaseCommand.option_list + (
        make_option(
            '--wait',
            dest='wait',
            default="True",
            choices=["True", "False"],
            metavar="True|False",
            help="Wait for Ganeti job to complete."),
        make_option(
            "--name",
            dest="name",
            default=None,
            help="Display name of the snapshot"),
        make_option(
            "--description",
            dest="description",
            default=None,
            help="Display description of the snapshot"),
    )

    @common.convert_api_faults
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a volume ID")

        volume = common.get_volume(args[0])

        name = options.get("name")
        if name is None:
            raise CommandError("'name' option is required")

        description = options.get("description")
        if description is None:
            description = "Snapshot of Volume '%s" % volume.id

        snapshot = snapshots.create(volume.userid,
                                    volume,
                                    name=name,
                                    description=description,
                                    metadata={})

        msg = ("Created snapshot of volume '%s' with ID %s\n"
               % (volume.id, snapshot["id"]))
        self.stdout.write(msg)
