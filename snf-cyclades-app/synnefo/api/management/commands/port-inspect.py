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

from synnefo.lib.utils import merge_time
from snf_django.lib.astakos import UserCache
from synnefo.logic.rapi import GanetiApiError
from synnefo.management.common import Omit, convert_api_faults
from synnefo.management import common
from synnefo.settings import (CYCLADES_SERVICE_TOKEN as ASTAKOS_TOKEN,
                              ASTAKOS_BASE_URL)

from synnefo.api.util import get_port
class Command(BaseCommand):
    help = "Inspect a port on DB and Ganeti"
    args = "<port ID>"

    option_list = BaseCommand.option_list + (
        make_option(
            '--jobs',
            action='store_true',
            dest='jobs',
            default=False,
            help="Show non-archived jobs concerning port."),
        make_option(
            '--displayname',
            action='store_true',
            dest='displayname',
            default=False,
            help="Display both uuid and display name"),
    )

    @convert_api_faults
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a port ID")

        port = get_port(args[0], None)

        sep = '-' * 80 + '\n'
        labels =  ['name',  'id', 'device_id', 'network_id',
                   'device_owner', 'mac_address', 'ipv4', 'subnet4',
                   'ipv6', 'subnet6', 'state',
                   'security_groups', 'user_id']

        uuid = port.userid
        security_groups = port.security_groups.values_list('id',
                                                                 flat=True)
        sg_csv = ','.join(map(str, security_groups))

        ipv4 = ''
        ipv6 = ''
        subnet4 = ''
        subnet6 = ''
        for ip in port.ips.all():
            if ip.subnet.ipversion == 4:
                ipv4 = ip.address
                subnet4 = str(ip.subnet.id)
            else:
                ipv6 = ip.address
                subnet6 = str(ip.subnet.id)

        fields = [port.name, str(port.id), str(port.machine.id),
                  str(port.network.id), port.device_owner, port.mac,
                  ipv4, subnet4, ipv6, subnet6, port.state, sg_csv, uuid]

        self.stdout.write(sep)
        self.stdout.write('State of port in DB\n')
        self.stdout.write(sep)
        for l, f in zip(labels, fields):
            if f:
                self.stdout.write(l.ljust(18) + ': ' + f.ljust(20) + '\n')
            else:
                self.stdout.write(l.ljust(18) + ': ' + '\n')

        self.stdout.write('\n')
        '''
        client = vm.get_client()
        try:
            g_vm = client.GetInstance(vm.backend_vm_id)
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
        except GanetiApiError as e:
            if e.code == 404:
                self.stdout.write('Server does not exist in backend %s\n' %
                                  vm.backend.clustername)
            else:
                raise e

        if not options['jobs']:
            return

        self.stdout.write('\n')
        self.stdout.write(sep)
        self.stdout.write('Non-archived jobs concerning Server in Ganeti\n')
        self.stdout.write(sep)
        jobs = client.GetJobs()
        for j in jobs:
            info = client.GetJobStatus(j)
            summary = ' '.join(info['summary'])
            job_is_relevant = summary.startswith("INSTANCE") and\
                (summary.find(vm.backend_vm_id) != -1)
            if job_is_relevant:
                for i in GANETI_JOB_FIELDS:
                    value = info[i]
                    if i.find('_ts') != -1:
                        value = merge_time(value)
                    try:
                        self.stdout.write(i.ljust(14) + ': ' + str(value) +
                                          '\n')
                    except KeyError:
                        pass
                self.stdout.write('\n' + sep)
        # Return the RAPI client to pool
        vm.put_client(client)
        '''
