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

import os

from optparse import make_option
from collections import namedtuple

from django.core.management.base import BaseCommand, CommandError

from astakos.im.models import AstakosUser

AddResourceArgs = namedtuple('AddQuotaArgs', ('resource',
                                              'quantity',
                                              'capacity',
                                              'import_limit',
                                              'export_limit'))

class Command(BaseCommand):
    help = "Import account quota policies"

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError('Invalid number of arguments')
 
        location = os.path.abspath(args[0])
        try:
            f = open(location, 'r')
        except IOError, e:
            raise CommandError(e)

        for line in f.readlines():
            try:
                t = line.rstrip('\n').split(' ')
                user = t[0]
                args = AddResourceArgs(*t[1:])
            except(IndexError, TypeError):
                self.stdout.write('Invalid line format: %s:\n' % t)
                continue
            else:
                try:
                    user = AstakosUser.objects.get(uuid=user)
                except AstakosUser.DoesNotExist:
                    self.stdout.write('Not found user having uuid: %s\n' % user)
                    continue
                else:
                    try:
                        user.add_resource_policy(*args)
                    except Exception, e:
                        self.stdout.write('Failed to policy: %s\n' % e)
                        continue
            finally:
                f.close()
