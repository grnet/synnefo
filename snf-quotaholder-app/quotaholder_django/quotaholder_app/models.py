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


from synnefo.lib.commissioning import CorruptedError

from django.db.models import Model, BigIntegerField, CharField, ForeignKey
from django.db import transaction


class Holder(Model):

    attribute   =   CharField(max_length=4096, primary_key=True)
    intval      =   BigIntegerField()
    strval      =   CharField(max_length=4096)


def alloc_serial(nr=1):
    if nr < 0:
        m = "Can only receive a positive argument, not %d" % (nr,)
        raise CorruptedError(m)

    try:
        holder = Holder.objects.get(attribute='serial')
    except Holder.DoesNotExist:
        holder = Holder(attribute='serial', intval=1)

    serial = holder.intval
    holder.intval += nr
    holder.save()

    return serial


class Entity(Model):

    entity      =   CharField(max_length=4096, primary_key=True)
    owner       =   ForeignKey('self', to_field='entity',
                               related_name='entities')
    key         =   CharField(max_length=4096, null=False)


class Policy(Model):

    policy          =   CharField(max_length=4096, primary_key=True)
    quantity        =   BigIntegerField(null=True, default=None)
    capacity        =   BigIntegerField(null=True,  default=None)
    import_limit    =   BigIntegerField(null=True,  default=None)
    export_limit    =   BigIntegerField(null=True,  default=None)


class Holding(Model):

    entity      =   ForeignKey(Entity, to_field='entity')
    resource    =   CharField(max_length=4096, null=False)

    policy      =   ForeignKey(Policy, to_field='policy')
    flags       =   BigIntegerField(null=False, default=0)

    imported    =   BigIntegerField(null=False, default=0)
    importing   =   BigIntegerField(null=False, default=0)
    exported    =   BigIntegerField(null=False, default=0)
    exporting   =   BigIntegerField(null=False, default=0)
    returned    =   BigIntegerField(null=False, default=0)
    returning   =   BigIntegerField(null=False, default=0)
    released    =   BigIntegerField(null=False, default=0)
    releasing   =   BigIntegerField(null=False, default=0)

    class Meta:
        unique_together = (('entity', 'resource'),)


from datetime import datetime

def now():
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:24]


class Commission(Model):

    serial      =   BigIntegerField(primary_key=True, default=alloc_serial)
    entity      =   ForeignKey(Entity, to_field='entity')
    name        =   CharField(max_length=4096, null=True)
    clientkey   =   CharField(max_length=4096, null=False)
    issue_time  =   CharField(max_length=24, default=now)


class Provision(Model):

    serial      =   ForeignKey( Commission,
                                to_field='serial',
                                related_name='provisions'   )

    entity      =   ForeignKey(Entity, to_field='entity')
    resource    =   CharField(max_length=4096, null=False)
    quantity    =   BigIntegerField(null=False)


class ProvisionLog(Model):

    serial              =   BigIntegerField()
    source              =   CharField(max_length=4096)
    target              =   CharField(max_length=4096)
    name                =   CharField(max_length=4096)
    issue_time          =   CharField(max_length=4096)
    log_time            =   CharField(max_length=4096)
    resource            =   CharField(max_length=4096)
    source_quantity     =   BigIntegerField(null=True)
    source_capacity     =   BigIntegerField(null=True)
    source_import_limit =   BigIntegerField(null=True)
    source_export_limit =   BigIntegerField(null=True)
    source_imported     =   BigIntegerField(null=False)
    source_exported     =   BigIntegerField(null=False)
    source_returned     =   BigIntegerField(null=False)
    source_released     =   BigIntegerField(null=False)
    target_quantity     =   BigIntegerField(null=True)
    target_capacity     =   BigIntegerField(null=True)
    target_import_limit =   BigIntegerField(null=True)
    target_export_limit =   BigIntegerField(null=True)
    target_imported     =   BigIntegerField(null=False)
    target_exported     =   BigIntegerField(null=False)
    target_returned     =   BigIntegerField(null=False)
    target_released     =   BigIntegerField(null=False)
    delta_quantity      =   BigIntegerField(null=False)
    reason              =   CharField(max_length=4096)


    def source_allocated_through(self):
        return self.source_imported - self.source_released

    def source_allocated(self):
        return (+ self.source_allocated_through()
                - self.source_exported
                + self.source_returned)

    def source_inbound_through(self):
        return self.source_imported

    def source_inbound(self):
        return self.source_inbound_through() + self.source_returned

    def source_outbound_through(self):
        return self.source_released

    def source_outbound(self):
        return self.source_outbound_through() + self.source_exported

    def target_allocated_through(self):
        return self.target_imported - self.target_released

    def target_allocated(self):
        return (+ self.target_allocated_through()
                - self.target_exported
                + self.target_returned)

    def target_inbound_through(self):
        return self.target_imported

    def target_inbound(self):
        return self.target_inbound_through() + self.target_returned

    def target_outbound_through(self):
        return self.target_released

    def target_outbound(self):
        return self.target_outbound_through() + self.target_exported

