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

from importlib import import_module
import time
from multiprocessing import Process
from optparse import make_option

from django.core.management.base import CommandError

from synnefo.management import common
from synnefo.logic import servers
from synnefo.db.models import Backend, VirtualMachine
server_create_mod = import_module("synnefo.logic.management.commands.server-create")


HELP_MSG = """

Sync helper VMs in all Ganeti backends. If a Ganeti backend does not have a
helper VM with a user-provided flavor, image and password, then a new one will
be created and will be set immediately in STOPPED state.
"""


class Command(server_create_mod.Command):
    help = "Sync helper vms." + HELP_MSG
    umask = 0o007

    def __init__(self, *args, **kwargs):
        self.option_list = filter(self.is_valid_option, self.option_list) + (
            make_option("--parallel", dest="parallel", default=False,
                        action="store_true",
                        help="Use a seperate process for each backend."),
            make_option("--copies", dest="copies", default=1, type="int",
                        help="Specify how many helper VMs will be created"
                        " in each backend.")
        )
        super(Command, self).__init__(*args, **kwargs)

    def is_valid_option(self, option):
        dest = option.dest
        if (dest == "connections" or dest == "volumes" or
                dest == "floating_ip_ids" or dest == "helper_vm"):
            return False
        return True

    def get_helper_vms(self, backend):
        return backend.virtual_machines.filter(helper=True, deleted=False)

    def add_default_options(self, options):
        """Add default options for server-create.

        Using `is_valid_option`, we have filtered out some options that do not
        make sense for this action. Yet, these options are needed by the
        `server-create` action. Thus, we must add some sane defaults for these
        options.
        """
        options['connections'] = None
        options['volumes'] = []
        options['floating_ip_ids'] = None
        options['helper_vm'] = True

    def wait_building_server(self, vm, period=1):
        common.wait_server_task(vm, True, self.stdout)
        while vm.task:
            time.sleep(period)
            # We need to reload the VM from the DB, as the task field has
            # changed.
            vm = VirtualMachine.objects.get(id=vm.id)
        return vm

    @common.convert_api_faults
    def handle(self, *args, **options):
        self.add_default_options(options)

        flavor_id = options['flavor_id']
        if not flavor_id:
            raise CommandError("flavor is mandatory")

        # Get the disk template of the helper servers.
        flavor = common.get_resource("flavor", flavor_id)
        disk_template = flavor.volume_type.template

        # Check if we will operate on all online backends or just for a
        # specified one.
        backend_id = options['backend_id']
        if backend_id:
            backend = Backend.objects.get(id=backend_id)
            if disk_template in backend.disk_templates:
                backends = [backend]
            else:
                raise CommandError("backend %s cannot host servers with disk"
                                   " template %s.\nAvailable templates are: %s"
                                   % (backend.clustername, disk_template,
                                      backend.disk_templates))
        else:
            backends = Backend.objects.filter(
                offline=False, disk_templates__contains=disk_template)

        # Check if we will create VMs in parallel
        parallel = options['parallel']
        del options['parallel']

        # Construct a name that will be used for all helper VMs, if the user
        # has not given any.
        if not options['name']:
            options['name'] = "Helper VM"

        # Do the syncing
        if parallel:
            ps = [Process(target=self.sync_servers, args=(backend, options))
                  for backend in backends]
            map(lambda p: p.start(), ps)
            map(lambda p: p.join(), ps)

        else:
            for backend in backends:
                self.sync_servers(backend, options)

    def sync_servers(self, backend, options):
        print "Backend %s: Syncing helper servers" % backend.clustername
        self.create_servers(backend, options)
        self.stop_servers(backend, options)
        print "Backend %s: Syncing completed" % backend.clustername

    def create_server(self, options):
        super(Command, self).handle(**options)

    def create_servers(self, backend, options):
        """Create helper VMs in the specified backend."""
        options['backend_id'] = backend.id

        # Find out how many VMs we need to create for that backend
        helper_vms = self.get_helper_vms(backend).count()

        # Create the remaining VMs in the backend
        copies = options["copies"]
        for i in range(helper_vms, copies):
            print ("Backend %s: Creating new helper server (%s/%s)" %
                   (backend.clustername, i + 1, copies))
            self.create_server(options)

    def stop_server(self, vm, wait):
        """Stop a helper VM.

        First, we need to wait for the server to finish building. Then, we can
        send a shutdown job to Ganeti and optionally wait once more.
        """
        vm = self.wait_building_server(vm)
        servers.stop(vm)
        common.wait_server_task(vm, wait, self.stdout)

    def stop_servers(self, backend, options):
        """Stop all helper VMs in the specified backend."""
        wait = options['wait']
        helper_vms = self.get_helper_vms(backend).exclude(operstate="STOPPED")

        # Send "shutdown" to all helper VMs
        for i, vm in enumerate(helper_vms):
            print ("Backend %s: Stopping helper server %s" %
                   (backend.clustername, vm.id))
            self.stop_server(vm, wait)
