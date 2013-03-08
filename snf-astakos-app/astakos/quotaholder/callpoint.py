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

from astakos.quotaholder.exception import (
    QuotaholderError,
    CorruptedError, InvalidDataError,
    NoStockError, NoCapacityError,
    DuplicateError)

from astakos.quotaholder.commission import (
    Import, Export, Reclaim, Release, Operations)

from astakos.quotaholder.utils.newname import newname
from astakos.quotaholder.api import QH_PRACTICALLY_INFINITE

from django.db.models import Q, Count
from django.db.models import Q
from .models import (Holding,
                     Commission, Provision, ProvisionLog,
                     now,
                     db_get_holding,
                     db_get_commission, db_filter_provision)


class QuotaholderDjangoDBCallpoint(object):

    def _init_holding(self,
                      holder, resource, capacity,
                      imported_min, imported_max, stock_min, stock_max,
                      flags):
        try:
            h = db_get_holding(holder=holder, resource=resource,
                               for_update=True)
        except Holding.DoesNotExist:
            h = Holding(holder=holder, resource=resource)

        h.capacity = capacity
        h.flags = flags
        h.imported_min = imported_min
        h.imported_max = imported_max
        h.stock_min = stock_min
        h.stock_max = stock_max
        h.save()

    def init_holding(self, context=None, init_holding=[]):
        rejected = []
        append = rejected.append

        for idx, sfh in enumerate(init_holding):
            (holder, resource, capacity,
             imported_min, imported_max, stock_min, stock_max,
             flags) = sfh

            self._init_holding(holder, resource, capacity,
                               imported_min, imported_max,
                               stock_min, stock_max,
                               flags)
        if rejected:
            raise QuotaholderError(rejected)
        return rejected

    def reset_holding(self, context=None, reset_holding=[]):
        rejected = []
        append = rejected.append

        for idx, tpl in enumerate(reset_holding):
            (holder, resource,
             imported_min, imported_max, stock_min, stock_max) = tpl

            try:
                h = db_get_holding(holder=holder, resource=resource,
                                   for_update=True)
                h.imported_min = imported_min
                h.imported_max = imported_max
                h.stock_min = stock_min
                h.stock_max = stock_max
                h.save()
            except Holding.DoesNotExist:
                append(idx)
                continue

        if rejected:
            raise QuotaholderError(rejected)
        return rejected

    def _check_pending(self, holder, resource):
        cs = Commission.objects.filter(holder=holder)
        cs = [c for c in cs if c.provisions.filter(resource=resource)]
        as_target = [c.serial for c in cs]

        ps = Provision.objects.filter(holder=holder, resource=resource)
        as_source = [p.serial.serial for p in ps]

        return as_target + as_source

    def release_holding(self, context=None, release_holding=[]):
        rejected = []
        append = rejected.append

        for idx, (holder, resource) in enumerate(release_holding):
            try:
                h = db_get_holding(holder=holder, resource=resource,
                                   for_update=True)
            except Holding.DoesNotExist:
                append(idx)
                continue

            if self._check_pending(holder, resource):
                append(idx)
                continue

            if h.imported_max > 0:
                append(idx)
                continue

            h.delete()

        if rejected:
            raise QuotaholderError(rejected)
        return rejected

    def list_resources(self, context=None, holder=None):
        holdings = Holding.objects.filter(holder=holder)
        resources = [h.resource for h in holdings]
        return resources

    def list_holdings(self, context=None, list_holdings=[]):
        rejected = []
        reject = rejected.append
        holdings_list = []
        append = holdings_list.append

        for holder in list_holdings:
            holdings = list(Holding.objects.filter(holder=holder))
            if not holdings:
                reject(holder)
                continue

            append([(holder, h.resource,
                     h.imported_min, h.imported_max, h.stock_min, h.stock_max)
                    for h in holdings])

        return holdings_list, rejected

    def get_quota(self, context=None, get_quota=[]):
        quotas = []
        append = quotas.append

        holders = set(holder for holder, r in get_quota)
        hs = Holding.objects.filter(holder__in=holders)
        holdings = {}
        for h in hs:
            holdings[(h.holder, h.resource)] = h

        for holder, resource in get_quota:
            try:
                h = holdings[(holder, resource)]
            except:
                continue

            append((h.holder, h.resource, h.capacity,
                    h.imported_min, h.imported_max,
                    h.stock_min, h.stock_max,
                    h.flags))

        return quotas

    def set_quota(self, context=None, set_quota=[]):
        rejected = []
        append = rejected.append

        q_holdings = Q()
        holders = []
        for (holder, resource, _, _) in set_quota:
            holders.append(holder)

        hs = Holding.objects.filter(holder__in=holders).select_for_update()
        holdings = {}
        for h in hs:
            holdings[(h.holder, h.resource)] = h

        for (holder, resource,
             capacity,
             flags) in set_quota:

            try:
                h = holdings[(holder, resource)]
                h.flags = flags
            except KeyError:
                h = Holding(holder=holder, resource=resource,
                            flags=flags)

            h.capacity = capacity
            h.save()
            holdings[(holder, resource)] = h

        if rejected:
            raise QuotaholderError(rejected)
        return rejected

    def add_quota(self,
                  context=None,
                  sub_quota=[], add_quota=[]):
        rejected = []
        append = rejected.append

        sources = sub_quota + add_quota
        q_holdings = Q()
        holders = []
        for (holder, resource, _) in sources:
            holders.append(holder)

        hs = Holding.objects.filter(holder__in=holders).select_for_update()
        holdings = {}
        for h in hs:
            holdings[(h.holder, h.resource)] = h

        for removing, source in [(True, sub_quota), (False, add_quota)]:
            for (holder, resource,
                 capacity,
                 ) in source:

                try:
                    h = holdings[(holder, resource)]
                    current_capacity = h.capacity
                except KeyError:
                    if removing:
                        append((holder, resource))
                        continue

                    h = Holding(holder=holder, resource=resource, flags=0)
                    current_capacity = 0

                h.capacity = (current_capacity - capacity if removing else
                              current_capacity + capacity)

                if h.capacity < 0:
                    append((holder, resource))
                    continue

                h.save()
                holdings[(holder, resource)] = h

        if rejected:
            raise QuotaholderError(rejected)

        return rejected

    def issue_commission(self,
                         context=None,
                         clientkey=None,
                         target=None,
                         name=None,
                         provisions=()):

        create = Commission.objects.create
        commission = create(holder=target, clientkey=clientkey, name=name)
        serial = commission.serial

        operations = Operations()

        try:
            checked = []
            for holder, resource, quantity in provisions:

                if holder == target:
                    m = ("Cannot issue commission from a holder "
                         "to itself (%s)" % (holder,))
                    raise InvalidDataError(m)

                ent_res = holder, resource
                if ent_res in checked:
                    m = "Duplicate provision for %s.%s" % ent_res
                    raise DuplicateError(m)
                checked.append(ent_res)

                # Source
                try:
                    h = (db_get_holding(holder=holder, resource=resource,
                                        for_update=True)
                         if holder is not None
                         else None)
                except Holding.DoesNotExist:
                    m = ("%s has no stock of %s." % (holder, resource))
                    raise NoStockError(m,
                                       holder=holder,
                                       resource=resource,
                                       requested=quantity,
                                       current=0,
                                       limit=0)

                # Target
                try:
                    th = db_get_holding(holder=target, resource=resource,
                                        for_update=True)
                except Holding.DoesNotExist:
                    m = ("There is no capacity "
                         "to allocate into in %s.%s" % (target, resource))
                    raise NoCapacityError(m,
                                          holder=holder,
                                          resource=resource,
                                          requested=quantity,
                                          current=0,
                                          limit=0)

                if quantity >= 0:
                    if h is not None:
                        operations.prepare(Export, h, quantity)
                    operations.prepare(Import, th, quantity)

                else: # release
                    abs_quantity = -quantity

                    if h is not None:
                        operations.prepare(Reclaim, h, abs_quantity)
                    operations.prepare(Release, th, abs_quantity)

                Provision.objects.create(serial=commission,
                                         holder=holder,
                                         resource=resource,
                                         quantity=quantity)

        except QuotaholderError:
            operations.revert()
            raise

        return serial

    def _log_provision(self,
                       commission, s_holding, t_holding,
                       provision, log_time, reason):

        if s_holding is not None:
            s_holder = s_holding.holder
            s_capacity = s_holding.capacity
            s_imported_min = s_holding.imported_min
            s_imported_max = s_holding.imported_max
            s_stock_min = s_holding.stock_min
            s_stock_max = s_holding.stock_max
        else:
            s_holder = None
            s_capacity = None
            s_imported_min = None
            s_imported_max = None
            s_stock_min = None
            s_stock_max = None

        kwargs = {
            'serial':              commission.serial,
            'name':                commission.name,
            'source':              s_holder,
            'target':              t_holding.holder,
            'resource':            provision.resource,
            'source_capacity':     s_capacity,
            'source_imported_min': s_imported_min,
            'source_imported_max': s_imported_max,
            'source_stock_min':    s_stock_min,
            'source_stock_max':    s_stock_max,
            'target_capacity':     t_holding.capacity,
            'target_imported_min': t_holding.imported_min,
            'target_imported_max': t_holding.imported_max,
            'target_stock_min':    t_holding.stock_min,
            'target_stock_max':    t_holding.stock_max,
            'delta_quantity':      provision.quantity,
            'issue_time':          commission.issue_time,
            'log_time':            log_time,
            'reason':              reason,
        }

        ProvisionLog.objects.create(**kwargs)

    def accept_commission(self,
                          context=None, clientkey=None,
                          serials=[], reason=''):
        log_time = now()

        for serial in serials:
            try:
                c = db_get_commission(clientkey=clientkey, serial=serial,
                                      for_update=True)
            except Commission.DoesNotExist:
                return

            t = c.holder

            operations = Operations()

            provisions = db_filter_provision(serial=serial, for_update=True)
            for pv in provisions:
                try:
                    h = (db_get_holding(holder=pv.holder,
                                        resource=pv.resource, for_update=True)
                         if pv.holder is not None
                         else None)
                    th = db_get_holding(holder=t, resource=pv.resource,
                                        for_update=True)
                except Holding.DoesNotExist:
                    m = "Corrupted provision"
                    raise CorruptedError(m)

                quantity = pv.quantity

                if quantity >= 0:
                    if h is not None:
                        operations.finalize(Export, h, quantity)
                    operations.finalize(Import, th, quantity)
                else: # release
                    abs_quantity = -quantity

                    if h is not None:
                        operations.finalize(Reclaim, h, abs_quantity)
                    operations.finalize(Release, th, abs_quantity)

                reason = 'ACCEPT:' + reason[-121:]
                self._log_provision(c, h, th, pv, log_time, reason)
                pv.delete()
            c.delete()

        return

    def reject_commission(self,
                          context=None, clientkey=None,
                          serials=[], reason=''):
        log_time = now()

        for serial in serials:
            try:
                c = db_get_commission(clientkey=clientkey, serial=serial,
                                      for_update=True)
            except Commission.DoesNotExist:
                return

            t = c.holder

            operations = Operations()

            provisions = db_filter_provision(serial=serial, for_update=True)
            for pv in provisions:
                try:
                    h = (db_get_holding(holder=pv.holder,
                                        resource=pv.resource, for_update=True)
                         if pv.holder is not None
                         else None)
                    th = db_get_holding(holder=t, resource=pv.resource,
                                        for_update=True)
                except Holding.DoesNotExist:
                    m = "Corrupted provision"
                    raise CorruptedError(m)

                quantity = pv.quantity

                if quantity >= 0:
                    if h is not None:
                        operations.undo(Export, h, quantity)
                    operations.undo(Import, th, quantity)
                else: # release
                    abs_quantity = -quantity

                    if h is not None:
                        operations.undo(Reclaim, h, abs_quantity)
                    operations.undo(Release, th, abs_quantity)

                reason = 'REJECT:' + reason[-121:]
                self._log_provision(c, h, th, pv, log_time, reason)
                pv.delete()
            c.delete()

        return

    def get_pending_commissions(self, context=None, clientkey=None):
        pending = Commission.objects.filter(clientkey=clientkey)
        pending_list = pending.values_list('serial', flat=True)
        return pending_list

    def resolve_pending_commissions(self,
                                    context=None, clientkey=None,
                                    max_serial=None, accept_set=[]):
        accept_set = set(accept_set)
        pending = self.get_pending_commissions(context=context,
                                               clientkey=clientkey)
        pending = sorted(pending)

        accept = self.accept_commission
        reject = self.reject_commission

        for serial in pending:
            if serial > max_serial:
                break

            if serial in accept_set:
                accept(context=context, clientkey=clientkey, serials=[serial])
            else:
                reject(context=context, clientkey=clientkey, serials=[serial])

        return

    def get_timeline(self, context=None, after="", before="Z", get_timeline=[]):
        holder_set = set()
        e_add = holder_set.add
        resource_set = set()
        r_add = resource_set.add

        for holder, resource in get_timeline:
            if holder not in holder_set:
                e_add(holder)

            r_add((holder, resource))

        chunk_size = 65536
        nr = 0
        timeline = []
        append = timeline.append
        filterlogs = ProvisionLog.objects.filter
        if holder_set:
            q_holder = Q(source__in=holder_set) | Q(target__in=holder_set)
        else:
            q_holder = Q()

        while 1:
            logs = filterlogs(q_holder,
                              issue_time__gt=after,
                              issue_time__lte=before,
                              reason__startswith='ACCEPT:')

            logs = logs.order_by('issue_time')
            #logs = logs.values()
            logs = logs[:chunk_size]
            nr += len(logs)
            if not logs:
                break
            for g in logs:
                if ((g.source, g.resource) not in resource_set
                    or (g.target, g.resource) not in resource_set):
                    continue

                o = {
                    'serial':                   g.serial,
                    'source':                   g.source,
                    'target':                   g.target,
                    'resource':                 g.resource,
                    'name':                     g.name,
                    'quantity':                 g.delta_quantity,
                    'source_allocated':         g.source_allocated(),
                    'source_allocated_through': g.source_allocated_through(),
                    'source_inbound':           g.source_inbound(),
                    'source_inbound_through':   g.source_inbound_through(),
                    'source_outbound':          g.source_outbound(),
                    'source_outbound_through':  g.source_outbound_through(),
                    'target_allocated':         g.target_allocated(),
                    'target_allocated_through': g.target_allocated_through(),
                    'target_inbound':           g.target_inbound(),
                    'target_inbound_through':   g.target_inbound_through(),
                    'target_outbound':          g.target_outbound(),
                    'target_outbound_through':  g.target_outbound_through(),
                    'issue_time':               g.issue_time,
                    'log_time':                 g.log_time,
                    'reason':                   g.reason,
                }

                append(o)

            after = g.issue_time
            if after >= before:
                break

        return timeline


API_Callpoint = QuotaholderDjangoDBCallpoint
