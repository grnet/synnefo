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

from synnefo.management import common, pprint
from synnefo.logic import backend as backend_mod, reconciliation, utils
from synnefo.db.models import Volume

HELP_MSG = """Import an existing Ganeti disk to Cyclades

Create a Cyclades Volume from an existing Ganeti disk. This command is useful
to handle disks that have been created directly in the Ganeti backend (instead
of being created by Cyclades). The command will not create/delete/modify the
specified disk in the Ganeti backend. Instead, it will create a Volume in
Cyclades DB, and rename the Ganeti disk with the Volume name.

"""


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
            "--server",
            dest="server_id",
            default=None,
            help="The ID of the server that the volume is currently attached"),
        make_option(
            "--disk",
            dest="disk_uuid",
            default=None,
            help="The UUID of the disk to be imported"),
    )

    @common.convert_api_faults
    def handle(self, *args, **options):
        if args:
            raise CommandError("Command doesn't accept any arguments")

        display_name = options.get("name", "")
        display_description = options.get("description", "")

        server_id = options.get("server_id")
        if server_id is None:
            raise CommandError("Please specify the server that the disk is"
                               " currently attached.")

        disk_uuid = options.get("disk_uuid")
        if disk_uuid is None:
            raise CommandError("Please specify the UUID of the Ganeti disk")

        vm = common.get_resource("server", server_id)

        instance_info = backend_mod.get_instance_info(vm)
        instance_disks = reconciliation.disks_from_instance(instance_info)
        try:
            disk = filter(lambda d: d["uuid"] == disk_uuid, instance_disks)[0]
        except IndexError:
            raise CommandError("Instance '%s' does not have a disk with"
                               " UUID '%s" % (vm.id, disk_uuid))

        # Check that the instance disk is not already a Cyclades Volume
        try:
            disk_id = utils.id_from_disk_name(disk["name"])
        except:
            pass
        else:
            raise CommandError("Disk '%s' of instance '%s' is already a"
                               " Cyclades Volume. Volume ID: %s"
                               % (disk_uuid, vm.id, disk_id))

        size = disk["size"] >> 10  # Convert to GB
        index = disk["index"]

        self.stdout.write("Import disk/%s of instance %s, size: %s GB\n"
                          % (index, vm.id, size))

        volume = Volume.objects.create(
            userid=vm.userid,
            disk_template=vm.flavor.disk_template,
            size=size,
            machine_id=vm.id,
            name=display_name,
            description=display_description,
            delete_on_termination=True,
            status="IN_USE",
            index=index)

        self.stdout.write("Created Volume '%s' in DB\n" % volume.id)
        pprint.pprint_volume(volume, stdout=self.stdout)
        self.stdout.write("\n")

        client = vm.get_client()
        jobId = client.ModifyInstance(
            instance=vm.backend_vm_id,
            disks=[("modify", disk["index"],
                    {"name": volume.backend_volume_uuid})])
        (status, error) = backend_mod.wait_for_job(client, jobId)
        vm.put_client(client)
        if status == "success":
            self.stdout.write("Successfully imported disk\n")
        else:
            self.stdout.write("Failed to imported disk:\n %s\n" % error)
