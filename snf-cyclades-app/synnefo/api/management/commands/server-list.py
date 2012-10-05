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

from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from synnefo.api.util import get_image
from synnefo.db.models import VirtualMachine, Backend


class Command(BaseCommand):
    help = "List servers"

    option_list = BaseCommand.option_list + (
        make_option('-c',
            action='store_true',
            dest='csv',
            default=False,
            help="Use pipes to separate values"),
        make_option('--build',
            action='store_true',
            dest='build',
            default=False,
            help="List only servers in the building state"),
        make_option('--non-deleted', action='store_true', dest='non_deleted',
                    default=False,
                    help="List only non-deleted servers"),
        make_option('--backend_id', dest='backend_id',
                    help="List only servers of the specified backend")
        )

    def handle(self, *args, **options):
        if args:
            raise CommandError("Command doesn't accept any arguments")

        if options['backend_id']:
            servers = \
            Backend.objects.get(id=options['backend_id']).virtual_machines
        else:
            servers = VirtualMachine.objects

        if options['non_deleted']:
            servers = servers.filter(deleted=False)
        else:
            servers = servers.all()

        if options['build']:
            servers = servers.filter(operstate='BUILD')

        labels = ('id', 'name', 'owner', 'flavor', 'image', 'state',
                  'backend')
        columns = (3, 12, 20, 11, 12, 9, 40)

        if not options['csv']:
            line = ' '.join(l.rjust(w) for l, w in zip(labels, columns))
            self.stdout.write(line + '\n')
            sep = '-' * len(line)
            self.stdout.write(sep + '\n')

        cache = ImageCache()

        for server in servers:
            id = str(server.id)
            try:
                name = server.name.decode('utf8')
            except UnicodeEncodeError:
                name = server.name
            flavor = server.flavor.name
            try:
                image = cache.get_image(server.imageid, server.userid)['name']
            except:
                image = server.imageid
            fields = (id, name, server.userid, flavor, image, server.operstate,
                      str(server.backend))

            if options['csv']:
                line = '|'.join(fields)
            else:
                line = ' '.join(f.rjust(w) for f, w in zip(fields, columns))

            self.stdout.write(line.encode('utf8') + '\n')


class ImageCache(object):
    def __init__(self):
        self.images = {}

    def get_image(self, imageid, userid):
        if not imageid in self.images:
            self.images[imageid] = get_image(imageid, userid)
        return self.images[imageid]
