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
from snf_django.management.commands import SynnefoCommand, CommandError

from snf_django.management.utils import parse_bool
from synnefo.management.common import convert_api_faults
from synnefo.management import pprint, common
from synnefo.volume import volumes


class Command(SynnefoCommand):
    help = "Modify a volume"
    args = "<volume ID>"

    option_list = SynnefoCommand.option_list + (
        make_option(
            '--name',
            dest='name',
            help="Modify a volume's display name"),
        make_option(
            '--description',
            dest='description',
            help="Modify a volume's display description"),
        make_option(
            '--delete-on-termination',
            dest='delete_on_termination',
            default="True",
            choices=["True", "False"],
            metavar="True|False",
            help="Set whether volume will be preserved when the server"
                 " the volume is attached will be deleted"),
    )

    @convert_api_faults
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a volume ID")

        volume = common.get_resource("volume", args[0], for_update=True)

        name = options.get("name")
        description = options.get("description")
        delete_on_termination = options.get("delete_on_termination")
        if delete_on_termination is not None:
            delete_on_termination = parse_bool(delete_on_termination)

        volume = volumes.update(volume, name, description,
                                delete_on_termination)

        pprint.pprint_volume(volume, stdout=self.stdout)
        self.stdout.write('\n\n')
