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

from synnefo.db.models import Network


class Command(BaseCommand):
    args = "<network id>"
    help = "Modify a network"

    option_list = BaseCommand.option_list + (
        make_option('--name',
            dest='name',
            metavar='NAME',
            help="Set network's name"),
        make_option('--owner',
            dest='owner',
            metavar='USER_ID',
            help="Set network's owner"),
        make_option('--subnet',
            dest='subnet',
            help="Set network's subnet"),
        make_option('--gateway',
            dest='gateway',
            help="Set network's gateway"),
        make_option('--subnet6',
            dest='subnet6',
            help="Set network's IPv6 subnet"),
        make_option('--gateway6',
            dest='gateway6',
            help="Set network's IPv6 gateway"),
        make_option('--dhcp',
            dest='dhcp',
            help="Set if network will use nfdhcp"),
        make_option('--state',
            dest='state',
            metavar='STATE',
            help="Set network's state")
    )

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a network ID")

        try:
            network_id = int(args[0])
            network = Network.objects.get(id=network_id)
        except (ValueError, Network.DoesNotExist):
            raise CommandError("Invalid network id")

        name = options.get('name')
        if name is not None:
            network.name = name

        owner = options.get('owner')
        if owner is not None:
            network.userid = owner

        subnet = options.get('subnet')
        if subnet is not None:
            network.subnet = subnet

        gateway = options.get('gateway')
        if gateway is not None:
            network.gateway = gateway

        subnet6 = options.get('subnet6')
        if subnet6 is not None:
            network.subnet6 = subnet6

        gateway6 = options.get('gateway6')
        if gateway6 is not None:
            network.gateway6 = gateway6

        dhcp = options.get('dhcp')
        if dhcp is not None:
            network.dhcp = dhcp

        state = options.get('state')
        if state is not None:
            allowed = [x[0] for x in Network.OPER_STATES]
            if state not in allowed:
                msg = "Invalid state, must be one of %s" % ', '.join(allowed)
                raise CommandError(msg)
            network.state = state

        network.save()
