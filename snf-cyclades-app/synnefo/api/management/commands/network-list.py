# Copyright 2012-2013 GRNET S.A. All rights reserved.
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

from snf_django.management.commands import ListCommand
from synnefo.db.models import Network
from synnefo.settings import (CYCLADES_SERVICE_TOKEN as ASTAKOS_TOKEN,
                              ASTAKOS_BASE_URL)

from logging import getLogger
log = getLogger(__name__)


class Command(ListCommand):
    help = "List networks"

    option_list = ListCommand.option_list + (
        make_option(
            '--public',
            action='store_true',
            dest='public',
            default=False,
            help="List only public networks"),
        make_option(
            '--ipv6',
            action='store_true',
            dest='ipv6',
            default=False,
            help="Include IPv6 information"),
    )

    object_class = Network
    deleted_field = "deleted"
    user_uuid_field = "userid"
    astakos_url = ASTAKOS_BASE_URL
    astakos_token = ASTAKOS_TOKEN

    def get_machines(network):
        return network.machines.filter(deleted=False).count()

    def get_backends(network):
        return network.backend_networks.values_list("backend_id", flat=True)

    def get_subnet_ipv4(network):
        return _get_subnet_field(network, "cidr", 4)

    def get_subnet_ipv6(network):
        return _get_subnet_field(network, "cidr", 6)

    def get_gateway_ipv4(network):
        return _get_subnet_field(network, "gateway", 4)

    def get_gateway_ipv6(network):
        return _get_subnet_field(network, "gateway", 6)

    def get_subnets(network):
        return network.subnets.values_list('id', flat=True)

    FIELDS = {
        "id": ("id", "The ID of the network"),
        "name": ("name", "The name of the network"),
        "user.uuid": ("userid", "The UUID of the network's owner"),
        "public": ("public", "Whether network is public or private"),
        "flavor": ("flavor", "The network's flavor"),
        "state": ("state", "The network's state"),
        "subnets": (get_subnets, "The IDs of the associated subnets"),
        "subnet.ipv4":  (get_subnet_ipv4, "The IPv4 subnet of the network"),
        "gateway.ipv4": (get_gateway_ipv4, "The IPv4 gateway of the network"),
        "subnet.ipv6":  (get_subnet_ipv6, "The IPv6 subnet of the network"),
        "gateway.ipv6":  (get_gateway_ipv6, "The IPv6 gateway of the network"),
        "created": ("created", "The date the network was created"),
        "updated": ("updated", "The date the network was updated"),
        "deleted": ("deleted", "Whether the network is deleted or not"),
        "mode": ("mode", "The mode of the network"),
        "link": ("link", "The link of the network"),
        "mac_prefix": ("mac_prefix", "The network's MAC prefix"),
        "drained": ("drained", "Whether network is drained or not"),
        "vms": (get_machines, "Number of connected servers"),
        "backends": (get_backends, "IDs of Ganeti backends that the network is"
                                   " connected to"),
        "floating_ip_pool": ("floating_ip_pool",
                             "Whether the network is a floating IP pool"),
    }

    fields = ["id", "name", "user.uuid", "state", "public", "subnet.ipv4",
              "gateway.ipv4", "link", "mac_prefix",  "drained",
              "floating_ip_pool"]

    def handle_args(self, *args, **options):
        if options["public"]:
            self.filters["public"] = True
        if options["ipv6"]:
            self.fields.extend(["subnet.ipv6", "gateway.ipv6"])


def _get_subnet_field(network, field, version=4):
    for subnet in network.subnets.all():
        if subnet.ipversion == version:
            return getattr(subnet, field)
    return None
