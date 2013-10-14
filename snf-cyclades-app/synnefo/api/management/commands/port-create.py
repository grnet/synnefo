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

from django.core.management.base import BaseCommand, CommandError
from synnefo.management.common import get_backend, convert_api_faults
from snf_django.management.utils import parse_bool

from synnefo.db.models import Network, NetworkInterface, SecurityGroup
from synnefo.api import util
from synnefo.logic import ports


class Command(BaseCommand):
    can_import_settings = True
    output_transaction = True

    help = "Create a new port"

    option_list = BaseCommand.option_list + (
        make_option(
            '--name',
            dest='name',
            default=None,
            help="Name of port"),
        make_option(
            '--owner',
            dest='owner',
            default=None,
            help="The owner of the port"),
        make_option(
            '--network',
            dest='network',
            default=None,
            help='The network to attach the port to'),
        make_option(
            '--device',
            dest='device_id',
            default=None,
            help='The VM id the port will be connected to'),
        make_option(
            '--security-groups',
            dest='security-groups',
            default=None,
            help='Security Groups associated with the port'),
    )

    @convert_api_faults
    def handle(self, *args, **options):
        if args:
            raise CommandError("Command doesn't accept any arguments")

        name = options['name']
        network = options['network']
        device = options['device_id']
        #assume giving security groups comma separated
        security_groups = options['security-groups']
        userid = options["owner"]

        if not name:
            name=""

        if not network:
            raise CommandError("network is required")
        if not device:
            raise CommandError("device is required")
        if not userid:
            raise CommandError("owner is required")

        #get the network
        network = util.get_network(network, userid, non_deleted=True)

        #get the vm
        vm = util.get_vm(device, userid)

        #validate security groups
        sg_list = []
        if security_groups:
            security_groups = security_groups.split(",")
            for gid in security_groups:
                sg = util.get_security_group(int(gid))
                sg_list.append(sg)

        new_port = ports.create(userid, network, vm, security_groups=sg_list)
        self.stdout.write("Created port '%s' in DB.\n" % new_port)
