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

from django.db import transaction
from django.core.management.base import BaseCommand, CommandError
from synnefo.management.common import get_vm, get_flavor, convert_api_faults
from synnefo.webproject.management.utils import parse_bool
from synnefo.logic import servers, backend as backend_mod


class Command(BaseCommand):
    args = "<server ID>"
    help = "Modify a server."

    option_list = BaseCommand.option_list + (
        make_option(
            '--name',
            dest='name',
            metavar='NAME',
            help="Rename server"),
        make_option(
            '--owner',
            dest='owner',
            metavar='USER_UUID',
            help="Change ownership of server. Value must be a user UUID"),
        make_option(
            "--suspended",
            dest="suspended",
            default=None,
            choices=["True", "False"],
            metavar="True|False",
            help="Mark a server as suspended/non-suspended."),
        make_option(
            "--flavor",
            dest="flavor",
            metavar="FLAVOR_ID",
            help="Resize a server by modifying its flavor. The new flavor"
                 " must have the same disk size and disk template."),
    )

    @transaction.commit_on_success
    @convert_api_faults
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a server ID")

        server = get_vm(args[0])

        new_name = options.get("name", None)
        if new_name is not None:
            old_name = server.name
            server = servers.rename(server, new_name)
            self.stdout.write("Renamed server '%s' from '%s' to '%s'\n" %
                              (server, old_name, new_name))

        suspended = options.get("suspended", None)
        if suspended is not None:
            suspended = parse_bool(suspended)
            server.suspended = suspended
            server.save()
            self.stdout.write("Set server '%s' as suspended=%s\n" %
                              (server, suspended))

        new_owner = options.get('owner')
        if new_owner is not None:
            if "@" in new_owner:
                raise CommandError("Invalid owner UUID.")
            old_owner = server.userid
            server.userid = new_owner
            server.save()
            msg = "Changed the owner of server '%s' from '%s' to '%s'.\n"
            self.stdout.write(msg % (server, old_owner, new_owner))

        new_flavor_id = options.get("flavor")
        if new_flavor_id is not None:
            new_flavor = get_flavor(new_flavor_id)
            old_flavor = server.flavor
            msg = "Resizing server '%s' from flavor '%s' to '%s'.\n"
            self.stdout.write(msg % (server, old_flavor, new_flavor))
            server = servers.resize(server, new_flavor)
            jobID = server.task_job_id
            msg = "Issued job '%s'. Waiting to complete...\n"
            self.stdout.write(msg % jobID)
            client = server.get_client()
            status, error = backend_mod.wait_for_job(client, jobID)
            if status == "success":
                self.stdout.write("Job finished successfully.\n")
            else:
                self.stdout.write("Job failed! Error: %s\n" % error)
