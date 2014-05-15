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

from django.db.models import (Model, BigIntegerField, CharField, DateTimeField,
                              ForeignKey, AutoField)


class Holding(Model):

    holder = CharField(max_length=4096, db_index=True)
    source = CharField(max_length=4096, null=True)
    resource = CharField(max_length=4096, null=False)

    limit = BigIntegerField()
    usage_min = BigIntegerField(default=0)
    usage_max = BigIntegerField(default=0)

    class Meta:
        unique_together = (('holder', 'source', 'resource'),)


class Commission(Model):

    serial = AutoField(primary_key=True)
    name = CharField(max_length=4096, default="")
    clientkey = CharField(max_length=4096, null=False)
    issue_datetime = DateTimeField()


class Provision(Model):

    serial = ForeignKey(Commission,
                        to_field='serial',
                        related_name='provisions')
    holder = CharField(max_length=4096, db_index=True)
    source = CharField(max_length=4096, null=True)
    resource = CharField(max_length=4096, null=False)

    quantity = BigIntegerField()

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
    limit = BigIntegerField()
    usage_min = BigIntegerField()
    usage_max = BigIntegerField()
    delta_quantity = BigIntegerField()
    reason = CharField(max_length=4096)
