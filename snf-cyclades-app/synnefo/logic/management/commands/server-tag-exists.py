# Copyright (C) 2010-2017 GRNET S.A. and individual contributors
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

import sys
from optparse import make_option
from snf_django.lib.api import Credentials
from django.core.management.base import CommandError
from snf_django.management.commands import SynnefoCommand
from synnefo.management.common import get_resource
from synnefo.api.util import (COMPUTE_API_TAG_NAMESPACES as tag_namespaces,
                              make_tag)
from synnefo.logic import servers


class Command(SynnefoCommand):
    args = "<server_id> <tag>"
    help = "Check whether a server tag exists"

    def handle(self, *args, **options):
        if len(args) != 2:
            raise CommandError("Please provide a server ID and a tag")

        credentials = Credentials("snf-manage", is_admin=True)
        server_id = args[0]
        server = get_resource("server", server_id)

        tag = args[1]
        header = ['tag', 'status', 'namespace']
        table = []

        for namespace in tag_namespaces:
            tag_db = make_tag(tag, namespace)
            db_tag = servers.check_tag_exists(server_id, credentials, tag_db)
            if db_tag:
                table.append([tag.encode('utf-8'), db_tag.status, namespace])

        if table:
            self.pprint_table(table, header, options["output_format"])
