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

from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from synnefo.management import common

from synnefo.logic import subnets

HELP_MSG = """

Update a subnet without authenticating the user. Only the name of a subnet can
be updated.
"""


class Command(BaseCommand):
    help = "Update a Subnet." + HELP_MSG

    option_list = BaseCommand.option_list + (
        make_option("--name", dest="name",
                    help="The new subnet name."),
    )

    @common.convert_api_faults
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Command accepts only the subnet ID as an"
                               " argument. Use snf-manage subnet-modify --help"
                               " for more info.")

        subnet_id = args[0]
        name = options["name"]

        if not name:
            raise CommandError("--name is mandatory")

        subnet = common.get_subnet(subnet_id)
        user_id = common.get_network(subnet.network.id).userid

        subnets.update_subnet(sub_id=subnet_id,
                              name=name,
                              user_id=user_id)
