# Copyright 2012, 2013 GRNET S.A. All rights reserved.
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

from datetime import datetime
from snf_django.lib.db.fields import intDecimalField

from django.db.models import (Model, BigIntegerField, CharField,
                              ForeignKey, AutoField)
from django.db import transaction
from snf_django.lib.db.managers import ForUpdateManager


class Holding(Model):

    holder = CharField(max_length=4096, db_index=True)
    source = CharField(max_length=4096, null=True)
    resource = CharField(max_length=4096, null=False)

    limit = intDecimalField()
    imported_min = intDecimalField(default=0)
    imported_max = intDecimalField(default=0)

    objects = ForUpdateManager()

    class Meta:
        unique_together = (('holder', 'source', 'resource'),)


def now():
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:24]


class Commission(Model):

    serial = AutoField(primary_key=True)
    name = CharField(max_length=4096, default="")
    clientkey = CharField(max_length=4096, null=False)
    issue_time = CharField(max_length=24)

    objects = ForUpdateManager()


class Provision(Model):

    serial = ForeignKey(Commission,
                        to_field='serial',
                        related_name='provisions')
    holder = CharField(max_length=4096, db_index=True)
    source = CharField(max_length=4096, null=True)
    resource = CharField(max_length=4096, null=False)

    quantity = intDecimalField()

    objects = ForUpdateManager()

    def todict(self):
        return {'holder':   self.holder,
                'source':   self.source,
                'resource': self.resource,
                'quantity': self.quantity,
                }

    def holding_key(self):
        return (self.holder, self.source, self.resource)


class ProvisionLog(Model):

    serial = BigIntegerField()
    name = CharField(max_length=4096)
    issue_time = CharField(max_length=4096)
    log_time = CharField(max_length=4096)
    holder = CharField(max_length=4096)
    source = CharField(max_length=4096, null=True)
    resource = CharField(max_length=4096)
    limit = intDecimalField()
    imported_min = intDecimalField()
    imported_max = intDecimalField()
    delta_quantity = intDecimalField()
    reason = CharField(max_length=4096)

    objects = ForUpdateManager()
