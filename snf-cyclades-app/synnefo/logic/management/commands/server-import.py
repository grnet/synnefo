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

from django.core.management.base import CommandError
from synnefo.management import common

from synnefo.db.models import VirtualMachine, Network, Flavor, VolumeType
from synnefo.logic.utils import id_from_network_name, id_from_instance_name
from synnefo.logic.backend import wait_for_job, connect_to_network
from snf_django.management.commands import SynnefoCommand
from synnefo.logic.rapi import GanetiApiError
from synnefo.logic import servers
from synnefo import quotas


HELP_MSG = """

Import an existing Ganeti instance into Synnefo, with the attributes specified
by the command line options. In order to be imported, the instance will be
turned off, renamed and then turned on again.

Importing an instance will fail, if the instance has NICs that are connected to
a network not belonging to Synnefo. You can either manually modify the instance
or use --new-nics option, that will remove all old NICs, and create a new one
connected to a public network of Synnefo.

"""


class Command(SynnefoCommand):
    help = "Import an existing Ganeti VM into Synnefo." + HELP_MSG
    args = "<ganeti_instance_name>"
    output_transaction = True

    option_list = SynnefoCommand.option_list + (
        make_option(
            "--backend-id",
            dest="backend_id",
            help="Unique identifier of the Ganeti backend that"
                 " hosts the VM. Use snf-manage backend-list to"
                 " find out available backends."),
        make_option(
            "--user-id",
            dest="user_id",
            help="Unique identifier of the owner of the server"),
        make_option(
            "--image-id",
            dest="image_id",
            default=None,
            help="Unique identifier of the image."
                 " Use snf-manage image-list to find out"
                 " available images."),
        make_option(
            "--flavor-id",
            dest="flavor_id",
            help="Unique identifier of the flavor"
                 " Use snf-manage flavor-list to find out"
                 " available flavors."),
        make_option(
            "--new-nics",
            dest='new_nics',
            default=False,
            action="store_true",
            help="Remove old NICs of instance, and create"
                 " a new NIC connected to a public network of"
                 " Synnefo.")
    )

    REQUIRED = ("user-id", "backend-id", "image-id", "flavor-id")

    def handle(self, *args, **options):
        if len(args) < 1:
            raise CommandError("Please specify a Ganeti instance")

        instance_name = args[0]

        try:
            id_from_instance_name(instance_name)
            raise CommandError("%s is already a synnefo instance")
        except:
            pass

        user_id = options['user_id']
        backend_id = options['backend_id']
        image_id = options['image_id']
        flavor_id = options['flavor_id']
        new_public_nic = options['new_nics']

        for field in self.REQUIRED:
            if not locals()[field.replace("-", "_")]:
                raise CommandError(field + " is mandatory")

        import_server(instance_name, backend_id, flavor_id, image_id, user_id,
                      new_public_nic, self.stderr)


def import_server(instance_name, backend_id, flavor_id, image_id, user_id,
                  new_public_nic, stream):
    flavor = common.get_resource("flavor", flavor_id)
    backend = common.get_resource("backend", backend_id)

    backend_client = backend.get_client()

    try:
        instance = backend_client.GetInstance(instance_name)
    except GanetiApiError as e:
        if e.code == 404:
            raise CommandError("Instance %s does not exist in backend %s"
                               % (instance_name, backend))
        else:
            raise CommandError("Unexpected error: %s" % e)

    if not new_public_nic:
        check_instance_nics(instance, stream)

    shutdown_instance(instance, backend_client, stream=stream)

    # Create the VM in DB
    stream.write("Creating VM entry in DB\n")
    vm = VirtualMachine.objects.create(name=instance_name,
                                       backend=backend,
                                       userid=user_id,
                                       imageid=image_id,
                                       flavor=flavor)

    quotas.issue_and_accept_commission(vm)

    if new_public_nic:
        remove_instance_nics(instance, backend_client,
                             stream=stream)

    # Rename instance
    rename_instance(instance_name, vm.backend_vm_id, backend_client,
                    stream)

    if new_public_nic:
        ports = servers.create_instance_ports(user_id)
        stream.write("Adding new NICs to server")
        [servers.associate_port_with_machine(port, vm)
         for port in ports]
        [connect_to_network(vm, port) for port in ports]

    # Startup instance
    startup_instance(vm.backend_vm_id, backend_client, stream=stream)

    backend.put_client(backend_client)
    return


def flavor_from_instance(instance, flavor, stream):
    beparams = instance['beparams']
    disk_sizes = instance['disk.sizes']
    if len(disk_sizes) != 1:
        stream.write("Instance has more than one disk.\n")

    disk = disk_sizes[0]
    disk_template = instance['disk_template']
    cpu = beparams['vcpus']
    ram = beparams['memory']

    try:
        volume_type = VolumeType.objects.get(disk_template=disk_template)
    except VolumeType.DoesNotExist:
        raise CommandError("Cannot find volume type with '%s' disk template."
                           % disk_template)
    return Flavor.objects.get_or_create(disk=disk,
                                        volume_type=volume_type,
                                        cpu=cpu, ram=ram)


def check_instance_nics(instance, stream):
    instance_name = instance['name']
    networks = instance['nic.networks.names']
    stream.write(str(networks) + "\n")
    try:
        networks = map(id_from_network_name, networks)
    except Network.InvalidBackendIdError:
        raise CommandError("Instance %s has NICs that do not belong to a"
                           " network belonging to synnefo. Either manually"
                           " modify the instance NICs or specify --new-nics"
                           " to clear the old NICs and create a new NIC to"
                           " a public network of synnefo." % instance_name)


def remove_instance_nics(instance, backend_client, stream):
    instance_name = instance['name']
    ips = instance['nic.ips']
    nic_indexes = xrange(0, len(ips))
    op = map(lambda x: ('remove', x, {}), nic_indexes)
    stream.write("Removing instance nics\n")
    op.reverse()
    jobid = backend_client.ModifyInstance(instance_name, nics=op)
    (status, error) = wait_for_job(backend_client, jobid)
    if status != 'success':
        raise CommandError("Cannot remove instance NICs: %s" % error)


def add_public_nic(instance_name, nic, backend_client, stream):
    stream.write("Adding public NIC %s\n" % nic)
    jobid = backend_client.ModifyInstance(instance_name, nics=[('add', nic)])
    (status, error) = wait_for_job(backend_client, jobid)
    if status != 'success':
        raise CommandError("Cannot rename instance: %s" % error)


def shutdown_instance(instance, backend_client, stream):
    instance_name = instance['name']
    if instance['status'] != 'ADMIN_down':
        stream.write("Instance is not down. Shutting down instance...\n")
        jobid = backend_client.ShutdownInstance(instance_name)
        (status, error) = wait_for_job(backend_client, jobid)
        if status != 'success':
            raise CommandError("Cannot shutdown instance: %s" % error)


def rename_instance(old_name, new_name, backend_client, stream):
    stream.write("Renaming instance to %s\n" % new_name)

    jobid = backend_client.RenameInstance(old_name, new_name,
                                          ip_check=False, name_check=False)
    (status, error) = wait_for_job(backend_client, jobid)
    if status != 'success':
        raise CommandError("Cannot rename instance: %s" % error)


def startup_instance(name, backend_client, stream):
    stream.write("Starting instance %s\n" % name)
    jobid = backend_client.StartupInstance(name)
    (status, error) = wait_for_job(backend_client, jobid)
    if status != 'success':
        raise CommandError("Cannot rename instance: %s" % error)
