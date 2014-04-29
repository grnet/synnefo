# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
            volume_type=vm.flavor.volume_type,
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
