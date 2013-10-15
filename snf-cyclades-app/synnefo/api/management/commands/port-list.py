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
from synnefo.db.models import NetworkInterface
from synnefo.settings import (CYCLADES_SERVICE_TOKEN as ASTAKOS_TOKEN,
                              ASTAKOS_BASE_URL)

from logging import getLogger
log = getLogger(__name__)


class Command(ListCommand):
    help = "List ports"


    object_class = NetworkInterface
    user_uuid_field = "userid"
    astakos_url = ASTAKOS_BASE_URL
    astakos_token = ASTAKOS_TOKEN

    def get_fixed_ips(ip):

        def labels((a, b)):
            return str({"subnet": b, "ip_address": str(a) })

        lista = ip.get_ip_addresses_subnets()
        lista = map(labels, lista)
        return " ".join(lista)

    FIELDS = {
        "id": ("id", "The ID of the port"),
        "name": ("name", "The name of the port"),
        "user.uuid": ("userid", "The UUID of the port's owner"),
        "mac_address": ("mac", "The MAC address of the port"),
        "device_id": ("machine.id", "The vm's id the port is conncted to"),
        "status": ("status", "The port's status"),
        "device_owner": ("device_owner", "The owner of the port (vm/router)"),
        "network": ("network.id", "The network's ID the port is\
                        connected to"),
        "created": ("created", "The date the port was created"),
        "updated": ("updated", "The date the port was updated"),
        "fixed_ips": (get_fixed_ips, "The ips and subnets associated with\
                                     the port"),
    }

    fields = ["id", "name", "user.uuid", "mac_address", "network",
               "device_id", "fixed_ips"]
