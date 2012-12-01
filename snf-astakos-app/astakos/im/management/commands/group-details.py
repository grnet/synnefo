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

from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import models

from astakos.im.models import AstakosGroup

class Command(BaseCommand):
    args = "<group name>"
    help = "Show group info"

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a group name")

        group = AstakosGroup.objects
        name_or_id = args[0].decode('utf8')
        try:
            if name_or_id.isdigit():
                group = group.get(id=int(name_or_id))
            else:
                group = group.get(name=name_or_id)
        except AstakosGroup.DoesNotExist:
            field = 'id' if name_or_id.isdigit() else 'name'
            msg = "Unknown user with %s '%s'" % (field, name_or_id)
            raise CommandError(msg)
        
        attrs = (
            'id',
            'name',
            'kind',
            'homepage', 
            'desc',
            'owners',
            'is_enabled',
            'max_participants',
            'moderation_enabled',
            'creation_date',
            'issue_date',
            'expiration_date',
            'approval_date',
            'members',
            'approved_members',
            'quota',
            'permissions'
        )

        for attr in attrs:
            val = getattr(group, attr)
            if isinstance(val, defaultdict):
                val = dict(val)
            if isinstance(val, models.Manager):
                val = val.all()
            line = '%s: %s\n' % (attr.rjust(22), val)
            self.stdout.write(line.encode('utf8'))
        self.stdout.write('\n')