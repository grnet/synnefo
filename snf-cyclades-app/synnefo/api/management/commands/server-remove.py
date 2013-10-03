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
from synnefo.management.common import get_vm, convert_api_faults
from synnefo.logic import servers, backend as backend_mod
from snf_django.management.utils import parse_bool


class Command(BaseCommand):
    args = "<server ID>"
    help = "Remove a server by deleting the instance from the Ganeti backend."

    option_list = BaseCommand.option_list + (
        make_option(
            '--wait',
            dest='wait',
            default="True",
            choices=["True", "False"],
            metavar="True|False",
            help="Wait for Ganeti job to complete."),
    )

    @convert_api_faults
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a server ID")

        server = get_vm(args[0])

        self.stdout.write("Trying to remove server '%s' from backend '%s'\n" %
                          (server.backend_vm_id, server.backend))

        servers.destroy(server)
        jobID = server.task_job_id

        self.stdout.write("Issued OP_INSTANCE_REMOVE with id: %s\n" % jobID)

        wait = parse_bool(options["wait"])
        if wait:
            self.stdout.write("Waiting for job to complete...\n")
            client = server.get_client()
            status, error = backend_mod.wait_for_job(client, jobID)
            if status == "success":
                self.stdout.write("Job '%s' completed successfully.\n" % jobID)
            else:
                self.stdout.write("Job '%s' failed: %s\n" % (jobID, error))
