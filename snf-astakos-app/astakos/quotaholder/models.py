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


from synnefo.lib.db.intdecimalfield import intDecimalField

from django.db.models import (Model, BigIntegerField, CharField,
                              ForeignKey, AutoField)
from django.db import transaction
from synnefo.lib.db.managers import ForUpdateManager

class Policy(Model):

    policy          =   CharField(max_length=4096, primary_key=True)
    quantity        =   intDecimalField()
    capacity        =   intDecimalField()
    import_limit    =   intDecimalField()
    export_limit    =   intDecimalField()

    objects     =   ForUpdateManager()

class Holding(Model):

    holder      =   CharField(max_length=4096, db_index=True)
    resource    =   CharField(max_length=4096, null=False)

    policy      =   ForeignKey(Policy, to_field='policy')
    flags       =   BigIntegerField(null=False, default=0)

    imported    =   intDecimalField(default=0)
    importing   =   intDecimalField(default=0)
    exported    =   intDecimalField(default=0)
    exporting   =   intDecimalField(default=0)
    returned    =   intDecimalField(default=0)
    returning   =   intDecimalField(default=0)
    released    =   intDecimalField(default=0)
    releasing   =   intDecimalField(default=0)

    objects     =   ForUpdateManager()

    class Meta:
        unique_together = (('holder', 'resource'),)


from datetime import datetime

def now():
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:24]


class Commission(Model):

    serial      =   AutoField(primary_key=True)
    holder      =   CharField(max_length=4096, db_index=True)
    name        =   CharField(max_length=4096, null=True)
    clientkey   =   CharField(max_length=4096, null=False)
    issue_time  =   CharField(max_length=24, default=now)

    objects     =   ForUpdateManager()

class Provision(Model):

    serial      =   ForeignKey( Commission,
                                to_field='serial',
                                related_name='provisions'   )

    holder      =   CharField(max_length=4096, db_index=True)
    resource    =   CharField(max_length=4096, null=False)
    quantity    =   intDecimalField()

    objects     =   ForUpdateManager()

class ProvisionLog(Model):

    serial              =   BigIntegerField()
    source              =   CharField(max_length=4096)
    target              =   CharField(max_length=4096)
    name                =   CharField(max_length=4096)
    issue_time          =   CharField(max_length=4096)
    log_time            =   CharField(max_length=4096)
    resource            =   CharField(max_length=4096)
    source_quantity     =   intDecimalField()
    source_capacity     =   intDecimalField()
    source_import_limit =   intDecimalField()
    source_export_limit =   intDecimalField()
    source_imported     =   intDecimalField()
    source_exported     =   intDecimalField()
    source_returned     =   intDecimalField()
    source_released     =   intDecimalField()
    target_quantity     =   intDecimalField()
    target_capacity     =   intDecimalField()
    target_import_limit =   intDecimalField()
    target_export_limit =   intDecimalField()
    target_imported     =   intDecimalField()
    target_exported     =   intDecimalField()
    target_returned     =   intDecimalField()
    target_released     =   intDecimalField()
    delta_quantity      =   intDecimalField()
    reason              =   CharField(max_length=4096)

    objects     =   ForUpdateManager()

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

class CallSerial(Model):

    serial      =   BigIntegerField(null=False)
    clientkey   =   CharField(max_length=4096, null=False)

    objects     =   ForUpdateManager()

    class Meta:
        unique_together = (('serial', 'clientkey'),)


def _get(*args, **kwargs):
    model = args[0]
    args = args[1:]
    o = model.objects

    for_update = kwargs.pop('for_update', False)
    f = o.get_for_update if for_update else o.get
    return f(*args, **kwargs)


def _filter(*args, **kwargs):
    model = args[0]
    args = args[1:]
    o = model.objects

    for_update = kwargs.pop('for_update', False)
    q = o.filter(*args, **kwargs)
    q = q.select_for_update() if for_update else q
    return q


def db_get_holding(*args, **kwargs):
    return _get(Holding, *args, **kwargs)

def db_get_policy(*args, **kwargs):
    return _get(Policy, *args, **kwargs)

def db_get_commission(*args, **kwargs):
    return _get(Commission, *args, **kwargs)

def db_get_callserial(*args, **kwargs):
    return _get(CallSerial, *args, **kwargs)

def db_filter_provision(*args, **kwargs):
    return _filter(Provision, *args, **kwargs)
