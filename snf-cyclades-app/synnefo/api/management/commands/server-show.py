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

from django.core.management.base import CommandError
from snf_django.management.commands import SynnefoCommand
from synnefo.management.common import (format_vm_state, get_vm,
                                       get_image)
from snf_django.lib.astakos import UserCache
from synnefo.settings import (CYCLADES_SERVICE_TOKEN as ASTAKOS_TOKEN,
                              ASTAKOS_BASE_URL)
from synnefo.webproject.management import utils


class Command(SynnefoCommand):
    args = "<server ID>"
    help = "Show server info"

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a server ID")

        server = get_vm(args[0])

        flavor = '%s (%s)' % (server.flavor.id, server.flavor.name)
        userid = server.userid

        imageid = server.imageid
        try:
            image_name = get_image(imageid, userid).get('name')
        except:
            image_name = "None"
        image = '%s (%s)' % (imageid, image_name)

        usercache = UserCache(ASTAKOS_BASE_URL, ASTAKOS_TOKEN)
        kv = {
            'id': server.id,
            'name': server.name,
            'owner_uuid': userid,
            'owner_name': usercache.get_name(userid),
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

        utils.pprint_table(self.stdout, [kv.values()], kv.keys(),
                           options["output_format"], vertical=True)
