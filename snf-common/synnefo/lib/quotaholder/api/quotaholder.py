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


from synnefo.lib.commissioning import (CanonifyException, SpecifyException,
                                       Specificator, Null, Integer, Text,
                                       Tuple, ListOf, Dict, Args)

Context             =   Dict(classname='Context', null=True)

class Name(Text):
    def init(self):
        self.opts.update({'regex': "[\w.:@+/]+", 'maxlen':512})
        Text.init(self)

class Nonnegative(Integer):
    def init(self):
        self.opts.update({'minimum': 0})

class Positive(Integer):
    def init(self):
        self.opts.update({'minimum': 1})

Serial              =   Positive(classname='Serial')

ClientKey           =   Name(classname='ClientKey')
Nothing             =   Null(classname='Nothing')

Entity              =   Name(classname='Entity')
Owner               =   Name(classname='Owner')
Key                 =   Text(classname='Key')
NewKey              =   Text(classname='Newkey')
OwnerKey            =   Text(classname='OwnerKey')
Resource            =   Name(classname='Resource')
Policy              =   Name(classname='Policy')

Quantity            =   Integer(classname='Quantity', null=True)
Capacity            =   Nonnegative(classname='Capacity', null=True)
ImportLimit         =   Nonnegative(classname='ImportLimit', null=True)
ExportLimit         =   Nonnegative(classname='ExportLimit', null=True)
Imported            =   Nonnegative(classname='Imported')
Exported            =   Nonnegative(classname='Exported')
Returned            =   Nonnegative(classname='Returned')
Released            =   Nonnegative(classname='Released')
Flags               =   Nonnegative(classname='Flags')
Index               =   Nonnegative(classname='Index')

Timepoint           =   Text(classname='Timepoint', maxlen=24)
Reason              =   Text(   classname   =   'Reason',
                                regex       =   '(ACCEPT|REJECT):.*',
                                maxlen      =   128         )

class QuotaholderAPI(Specificator):

    def create_entity   (
                self,
                context         =   Context,
                create_entity   =   ListOf(Entity, Owner, Key, OwnerKey, nonempty=1)
        ):
        """create_entity description"""
        rejected = ListOf(Index)
        return rejected

    def set_entity_key  (
                self,
                context         =   Context,
                set_entity_key  =   ListOf(Entity, Key, NewKey)
        ):
        """set_entity description"""
        rejected = ListOf(Entity)
        return rejected

    def list_entities   (
                self,
                context         =   Context,
                entity          =   Entity,
                key             =   Key
        ):
        """list_entity description"""
        entities = ListOf(Entity)
        return entities

    def get_entity  (
                self,
                context     =   Context,
                get_entity  =   ListOf(Entity, Key, nonempty=1)
        ):
        """get_entity description"""
        entities = ListOf(Entity, Owner)
        return entities

    def get_limits  (
                self,
                context     =   Context,
                get_limits  =   ListOf(Policy, nonempty=1)
        ):
        """get_limits description"""
        limits = ListOf(Policy, Quantity, Capacity,
                        ImportLimit, ExportLimit)
        return limits

    def set_limits  (
                self,
                context     =   Context,
                set_limits  =   ListOf( Policy, Quantity, Capacity,
                                        ImportLimit, ExportLimit,
                                        nonempty=1 )
        ):
        """set_limits description"""
        rejected = ListOf(Policy)
        return rejected

    def get_holding (
                self,
                context     =   Context,
                get_holding =   ListOf(Entity, Resource, Key)
        ):
        """get_holding description"""
        holdings = ListOf(  Entity, Resource, Policy,
                            Imported, Exported, Returned, Released, Flags   )
        return holdings

    def set_holding (
                self,
                context     =   Context,
                set_holding =   ListOf(Entity, Resource, Key, Policy, Flags)
        ):
        """set_holding description"""
        rejected = ListOf(Entity, Resource, Policy)
        return rejected

    def list_resources  (
                self,
                context     =   Context,
                entity      =   Entity,
                key         =   Key
        ):
        """list_resources description"""
        resources = ListOf(Resource)
        return resources

    def get_quota   (
                self,
                context     =   Context,
                get_quota   =   ListOf(Entity, Resource, Key)
        ):
        """get_quota description"""
        quotas = ListOf(Entity, Resource,
                        Quantity, Capacity,
                        ImportLimit, ExportLimit,
                        Imported, Exported,
                        Returned, Released,
                        Flags)
        return quotas

    def set_quota   (
                self,
                context     =   Context,
                set_quota   =   ListOf( Entity, Resource, Key,
                                        Quantity, Capacity,
                                        ImportLimit, ExportLimit, Flags )
        ):
        """set_quota description"""
        rejected = ListOf(Entity, Resource)
        return rejected

    def issue_commission    (
                self,
                context     =   Context,
                target      =   Entity,
                key         =   Key,
                clientkey   =   ClientKey,
                name        =   Text(default=''),
                provisions  =   ListOf(Entity, Resource, Quantity)
        ):
        """issue_commission description"""
        return Serial

    def accept_commission   (
                self,
                context     =   Context,
                clientkey   =   ClientKey,
                serials     =   ListOf(Serial),
                reason      =   Text(default='ACCEPT')
        ):
        """accept_commission description"""
        return Nothing

    def reject_commission   (
                self,
                context     =   Context,
                clientkey   =   ClientKey,
                serials     =   ListOf(Serial),
                reason      =   Text(default='REJECT')
        ):
        """reject_commission description"""
        return Nothing

    def get_pending_commissions (
                    self,
                    context     =   Context,
                    clientkey   =   ClientKey
        ):
        """get_pending_commissions description"""
        pending = ListOf(Serial)
        return pending

    def resolve_pending_commissions (
                    self,
                    context     =   Context,
                    clientkey   =   ClientKey,
                    max_serial  =   Serial,
                    accept_set  =   ListOf(Serial)
        ):
        """resolve_pending_commissions description"""
        return Nothing

    def release_entity  (
                self,
                context         =   Context,
                release_entity  =   ListOf(Entity, Key, nonempty=1)
        ):
        """relesea_entity description"""
        rejected = ListOf(Entity)
        return rejected

    def get_timeline    (
                self,
                context         =   Context,
                after           =   Timepoint,
                before          =   Timepoint,
                get_timeline    =   ListOf(Entity, Resource, Key)
        ):
        """get_timeline description"""
        timeline = ListOf(Dict(
                            serial                      =   Serial,
                            source                      =   Entity,
                            target                      =   Entity,
                            resource                    =   Resource,
                            name                        =   Name(),
                            quantity                    =   Quantity,
                            source_allocated            =   Quantity,
                            source_allocated_through    =   Quantity,
                            source_inbound              =   Quantity,
                            source_inbound_through      =   Quantity,
                            source_outbound             =   Quantity,
                            source_outbound_through     =   Quantity,
                            target_allocated            =   Quantity,
                            target_allocated_through    =   Quantity,
                            target_inbound              =   Quantity,
                            target_inbound_through      =   Quantity,
                            target_outbound             =   Quantity,
                            target_outbound_through     =   Quantity,
                            issue_time                  =   Timepoint,
                            log_time                    =   Timepoint,
                            reason                      =   Reason,

                            strict  =   True))
        return timeline

