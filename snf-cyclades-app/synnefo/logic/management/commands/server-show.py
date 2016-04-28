# Copyright (C) 2010-2015 GRNET S.A. and individual contributors
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

from django.core.management.base import CommandError
from snf_django.management.commands import SynnefoCommand
from synnefo.management.common import (format_vm_state, get_resource,
                                       get_image)
from snf_django.lib.astakos import UserCache
from synnefo.settings import (CYCLADES_SERVICE_TOKEN as ASTAKOS_TOKEN,
                              ASTAKOS_AUTH_URL)
from snf_django.management import utils


class Command(SynnefoCommand):
    args = "<server_id>"
    help = "Show server info"

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a server ID")

        server = get_resource("server", args[0])

        flavor = '%s (%s)' % (server.flavor.id, server.flavor.name)
        userid = server.userid

        imageid = server.imageid
        try:
            image_name = get_image(imageid, userid).get('name')
        except:
            image_name = "None"
        image = '%s (%s)' % (imageid, image_name)

        usercache = UserCache(ASTAKOS_AUTH_URL, ASTAKOS_TOKEN)
        kv = {
            'id': server.id,
            'name': server.name,
            'owner_uuid': userid,
            'owner_name': usercache.get_name(userid),
            'project': server.project,
            'shared_to_project': server.shared_to_project,
            'created': utils.format_date(server.created),
            'updated': utils.format_date(server.updated),
            'image': image,
            'host id': server.hostid,
            'flavor': flavor,
            'deleted': utils.format_bool(server.deleted),
            'suspended': utils.format_bool(server.suspended),
            'state': format_vm_state(server),
            'task': server.task,
            'task_job_id': server.task_job_id,
        }

        self.pprint_table([kv.values()], kv.keys(), options["output_format"],
                          vertical=True)
