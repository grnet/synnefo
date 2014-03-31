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
from synnefo.management import common, pprint
from synnefo.volume import volumes

HELP_MSG = """Create a new volume."""


class Command(SynnefoCommand):
    help = HELP_MSG

    option_list = SynnefoCommand.option_list + (
        make_option(
            "--name",
            dest="name",
            default=None,
            help="Display name of the volume."),
        make_option(
            "--description",
            dest="description",
            default=None,
            help="Display description of the volume."),
        make_option(
            "--owner",
            dest="user_id",
            default=None,
            help="UUID of the owner of the volume."),
        make_option(
            "-s", "--size",
            dest="size",
            default=None,
            help="Size of the new volume in GB"),
        make_option(
            "--server",
            dest="server_id",
            default=None,
            help="The ID of the server that the volume will be connected to."),
        make_option(
            "--wait",
            dest="wait",
            default="True",
            choices=["True", "False"],
            metavar="True|False",
            help="Wait for Ganeti jobs to complete."),
    )

    @common.convert_api_faults
    def handle(self, *args, **options):
        if args:
            raise CommandError("Command doesn't accept any arguments")

        size = options.get("size")
        user_id = options.get("user_id")
        server_id = options.get("server_id")
        wait = parse_bool(options["wait"])

        display_name = options.get("name", "")
        display_description = options.get("description", "")

        if size is None:
            raise CommandError("Please specify the size of the volume")

        if server_id is None:
            raise CommandError("Please specify the server to attach the"
                               " volume.")

        vm = common.get_resource("server", server_id, for_update=True)

        if user_id is None:
            user_id = vm.userid

        source_image_id = source_volume_id = source_snapshot_id = None
        volume = volumes.create(user_id, size, server_id,
                                name=display_name,
                                description=display_description,
                                source_image_id=source_image_id,
                                source_snapshot_id=source_snapshot_id,
                                source_volume_id=source_volume_id,
                                metadata={})

        self.stdout.write("Created volume '%s' in DB:\n" % volume.id)

        pprint.pprint_volume(volume, stdout=self.stdout)
        self.stdout.write("\n")
        if volume.machine is not None:
            volume.machine.task_job_id = volume.backendjobid
            common.wait_server_task(volume.machine, wait, stdout=self.stdout)
