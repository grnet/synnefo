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
from synnefo.volume import volumes
from synnefo.management import common
from snf_django.management.utils import parse_bool
from snf_django.management.commands import RemoveCommand


class Command(RemoveCommand):
    can_import_settings = True
    args = "<Volume ID> [<Volume ID> ...]"
    help = "Remove a volume from the Database and from the VM attached to"
    option_list = RemoveCommand.option_list + (
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
        if not args:
            raise CommandError("Please provide a volume ID")

        force = options['force']
        message = "volumes" if len(args) > 1 else "volume"
        self.confirm_deletion(force, message, args)

        for volume_id in args:
            self.stdout.write("\n")
            try:
                volume = common.get_resource("volume", volume_id,
                                             for_update=True)
                volumes.delete(volume)

                wait = parse_bool(options["wait"])
                if volume.machine is not None:
                    volume.machine.task_job_id = volume.backendjobid
                    common.wait_server_task(volume.machine, wait,
                                            stdout=self.stdout)
                else:
                    self.stdout.write("Successfully removed volume %s\n"
                                      % volume)
            except CommandError as e:
                self.stdout.write("Error -- %s\n" % e.message)
