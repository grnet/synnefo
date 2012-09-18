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


from datetime import datetime
from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from synnefo.api.util import get_image
from synnefo.lib.utils import merge_time
from synnefo.db.models import VirtualMachine
from synnefo.util.rapi import GanetiApiError


# Fields to print from a gnt-instance info
GANETI_INSTANCE_FIELDS = ('name', 'oper_state', 'admin_state', 'status',
                          'pnode', 'snode', 'network_port', 'disk_template',
                          'disk_usage', 'oper_ram', 'oper_vcpus', 'mtime',
                          'nic.ips', 'nic.macs', 'nic.networks', 'nic.modes')

# Fields to print from a gnt-job info
GANETI_JOB_FIELDS = ('id', 'status', 'summary', 'opresult', 'opstatus',
                     'oplog', 'start_ts', 'end_ts')


class Command(BaseCommand):
    help = "Inspect a server on DB and Ganeti"

    option_list = BaseCommand.option_list + (
        make_option('--jobs', action='store_true',
                    dest='jobs', default=False,
                    help="Show non-archived jobs concerning server."
            ),
    )

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a server ID")

        try:
            vm_id = int(args[0])
        except ValueError:
            raise CommandError("Invalid server ID")

        try:
            vm = VirtualMachine.objects.get(id=vm_id)
        except VirtualMachine.DoesNotExist:
            raise CommandError("Server not found in DB")

        try:
            image = get_image(vm.imageid, vm.userid)['name']
        except:
            image = vm.imageid

        sep = '-' * 80 + '\n'
        labels = ('name', 'owner', 'flavor', 'image', 'state', 'backend',
                  'deleted', 'action', 'backendjobid', 'backendopcodoe',
                  'backendjobstatus', 'backend_time')
        fields = (vm.name, vm.userid, vm.flavor.name, image, vm.operstate,
                  str(vm.backend), str(vm.deleted), str(vm.action),
                  str(vm.backendjobid), str(vm.backendopcode),
                  str(vm.backendjobstatus), str(vm.backendtime))

        self.stdout.write(sep)
        self.stdout.write('State of Server in DB\n')
        self.stdout.write(sep)
        for l, f in zip(labels, fields):
            self.stdout.write(l.ljust(18) + ': ' + f.ljust(20) + '\n')
        self.stdout.write('\n')
        for nic in vm.nics.all():
            self.stdout.write("nic/%d: IPv4: %s, MAC: %s, IPv6:%s,  Network: %s\n"\
                              % (nic.index, nic.ipv4, nic.mac, nic.ipv6,  nic.network))

        client = vm.backend.client
        try:
            g_vm = client.GetInstance(vm.backend_vm_id)
        except GanetiApiError as e:
            if e.code == 404:
                self.stdout.write('Server does not exist in backend %s\n' %
                                  vm.backend.clustername)
                return
            else:
                raise e

        self.stdout.write('\n')
        self.stdout.write(sep)
        self.stdout.write('State of Server in Ganeti\n')
        self.stdout.write(sep)
        for i in GANETI_INSTANCE_FIELDS:
            try:
                value = g_vm[i]
                if i.find('time') != -1:
                    value = datetime.fromtimestamp(value)
                self.stdout.write(i.ljust(14) + ': ' + str(value) + '\n')
            except KeyError:
                pass

        if not options['jobs']:
            return

        self.stdout.write('\n')
        self.stdout.write(sep)
        self.stdout.write('Non-archived jobs concering Server in Ganeti\n')
        self.stdout.write(sep)
        jobs = client.GetJobs()
        for j in jobs:
            info = client.GetJobStatus(j)
            summary = ' '.join(info['summary'])
            if summary.startswith("INSTANCE") and \
               summary.find(vm.backend_vm_id) != -1:
                for i in GANETI_JOB_FIELDS:
                    value = info[i]
                    if i.find('_ts') != -1:
                        value = merge_time(value)
                    try:
                        self.stdout.write(i.ljust(14) + ': ' + str(value) +\
                                          '\n')
                    except KeyError:
                        pass
                self.stdout.write('\n' + sep)
