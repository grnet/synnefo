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


from snf_django.management.commands import ListCommand
from synnefo.db.models import IPAddressLog
from optparse import make_option

from logging import getLogger
log = getLogger(__name__)


class Command(ListCommand):
    help = "Information about a floating IP"

    option_list = ListCommand.option_list + (
        make_option(
            '--address',
            dest='address',
            help="Get logs about a specif IP"),
        make_option(
            '--server',
            dest='server',
            help="Get logs about a specif server"),
    )

    object_class = IPAddressLog
    order_by = "allocated_at"

    FIELDS = {
        "address": ("address", "The IP address"),
        "server": ("server_id", "The the server connected to"),
        "network": ("network_id", "The id of the network"),
        "allocated_at": ("allocated_at", "Datetime IP allocated to server"),
        "released_at": ("released_at", "Datetime IP released from server"),
        "active": ("active", "Whether IP still allocated to server"),
    }

    fields = ["address", "server", "network", "allocated_at", "released_at"]

    def handle_args(self, *args, **options):
        if options["address"]:
            self.filters["address"] = options["address"]
        if options["server"]:
            self.filters["server_id"] = options["server"]
