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

from synnefo.db.models import IPAddress
from snf_django.management.commands import ListCommand
from synnefo.settings import CYCLADES_SERVICE_TOKEN, ASTAKOS_BASE_URL
from logging import getLogger
log = getLogger(__name__)


class Command(ListCommand):
    help = "List Floating IPs"
    object_class = IPAddress
    deleted_field = "deleted"
    user_uuid_field = "userid"
    astakos_url = ASTAKOS_BASE_URL
    astakos_token = CYCLADES_SERVICE_TOKEN
    filters = {'floating_ip': True}

    def get_machine(ip):
        try:
            return ip.nic.machine_id
        except AttributeError:
            return None

    FIELDS = {
        "id": ("id", "Floating IP UUID"),
        "user.uuid": ("userid", "The UUID of the server's owner"),
        "address": ("address", "IP Address"),
        "pool": ("network", "Floating IP Pool (network)"),
        "machine": (get_machine, "VM using this Floating IP"),
        "created": ("created", "Datetime this IP was reserved"),
        "deleted": ("deleted", "If the floating IP is deleted"),
    }

    fields = ["id", "address", "pool", "user.uuid", "machine", "created"]
