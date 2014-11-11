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

from optparse import make_option

from django.core.management.base import CommandError

from snf_django.management.commands import SynnefoCommand
from synnefo.management import common

from synnefo.logic import subnets

HELP_MSG = """

Update a subnet without authenticating the user. Only the name of a subnet can
be updated.
"""


class Command(SynnefoCommand):
    help = "Update a Subnet." + HELP_MSG
    args = "<subnet_id>"
    option_list = SynnefoCommand.option_list + (
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

        subnet = common.get_resource("subnet", subnet_id, for_update=True)
        user_id = common.get_resource("network", subnet.network.id).userid

        subnets.update_subnet(sub_id=subnet_id,
                              name=name,
                              user_id=user_id)
