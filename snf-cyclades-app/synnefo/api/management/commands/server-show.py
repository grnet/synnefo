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

from django.core.management.base import BaseCommand, CommandError
from synnefo.webproject.management.util import format_bool, format_date
from synnefo.management.common import (format_vm_state, get_vm,
                                       get_image)
from synnefo.lib.astakos import UserCache
from synnefo.settings import (CYCLADES_ASTAKOS_SERVICE_TOKEN as ASTAKOS_TOKEN,
                              ASTAKOS_URL)


class Command(BaseCommand):
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

        kv = {
            'id': server.id,
            'name': server.name,
            'owner_uuid': userid,
            'owner_name': UserCache(ASTAKOS_URL, ASTAKOS_TOKEN).get_name(userid),
            'created': format_date(server.created),
            'updated': format_date(server.updated),
            'image': image,
            'host id': server.hostid,
            'flavor': flavor,
            'deleted': format_bool(server.deleted),
            'suspended': format_bool(server.suspended),
            'state': format_vm_state(server),
        }

        for key, val in sorted(kv.items()):
            line = '%s: %s\n' % (key.rjust(16), val)
            self.stdout.write(line.encode('utf8'))
