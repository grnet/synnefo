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
    NoCapacityError,
    DuplicateError)

from astakos.quotaholder.commission import (
    Import, Release, Operations)

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
                      holder, resource, limit,
                      imported_min, imported_max,
                      flags):
        try:
            h = db_get_holding(holder=holder, resource=resource,
                               for_update=True)
        except Holding.DoesNotExist:
            h = Holding(holder=holder, resource=resource)

        h.limit = limit
        h.flags = flags
        h.imported_min = imported_min
        h.imported_max = imported_max
        h.save()

    def init_holding(self, context=None, init_holding=[]):
        rejected = []
        append = rejected.append

        for idx, sfh in enumerate(init_holding):
            (holder, resource, limit,
             imported_min, imported_max,
             flags) = sfh

            self._init_holding(holder, resource, limit,
                               imported_min, imported_max,
                               flags)
        if rejected:
            raise QuotaholderError(rejected)
        return rejected

    def reset_holding(self, context=None, reset_holding=[]):
        rejected = []
        append = rejected.append

        for idx, tpl in enumerate(reset_holding):
            (holder, source, resource,
             imported_min, imported_max) = tpl

            try:
                h = db_get_holding(holder=holder,
                                   source=source,
                                   resource=resource,
                                   for_update=True)
                h.imported_min = imported_min
                h.imported_max = imported_max
                h.save()
            except Holding.DoesNotExist:
                append(idx)
                continue

        if rejected:
            raise QuotaholderError(rejected)
        return rejected

    def _check_pending(self, holding):
        ps = Provision.objects.filter(holding=holding)
        return ps.count()

    def release_holding(self, context=None, release_holding=[]):
        rejected = []
        append = rejected.append

        for idx, (holder, source, resource) in enumerate(release_holding):
            try:
                h = db_get_holding(holder=holder,
                                   source=source,
                                   resource=resource,
                                   for_update=True)
            except Holding.DoesNotExist:
                append(idx)
                continue

            if self._check_pending(h):
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

            append([(holder, h.source, h.resource,
                     h.imported_min, h.imported_max)
                    for h in holdings])

        return holdings_list, rejected

    def get_holder_quota(self, holders=None, sources=None, resources=None):
        holdings = Holding.objects.filter(holder__in=holders)

        if sources is not None:
            holdings = holdings.filter(source__in=sources)

        if resources is not None:
            holdings = holdings.filter(resource__in=resources)

        quotas = {}
        for holding in holdings:
            key = (holding.holder, holding.source, holding.resource)
            value = (holding.limit, holding.imported_min, holding.imported_max)
            quotas[key] = value

        return quotas

    def get_quota(self, context=None, get_quota=[]):
        quotas = []
        append = quotas.append

        holders = set(holder for holder, r in get_quota)
        hs = Holding.objects.filter(holder__in=holders)
        holdings = {}
        for h in hs:
            holdings[(h.holder, h.source, h.resource)] = h

        for holder, source, resource in get_quota:
            try:
                h = holdings[(holder, source, resource)]
            except:
                continue

            append((h.holder, h.source, h.resource, h.limit,
                    h.imported_min, h.imported_max,
                    h.flags))

        return quotas

    def set_holder_quota(self, quotas):
        holders = quotas.keys()
        hs = Holding.objects.filter(holder__in=holders).select_for_update()
        holdings = {}
        for h in hs:
            holdings[(h.holder, h.source, h.resource)] = h

        for holder, holder_quota in quotas.iteritems():
            for source, source_quota in holder_quota.iteritems():
                for resource, limit in source_quota.iteritems():
                    try:
                        h = holdings[(holder, source, resource)]
                    except KeyError:
                        h = Holding(holder=holder,
                                    source=source,
                                    resource=resource)

                    h.limit = limit
                    h.save()

    def set_quota(self, context=None, set_quota=[]):
        rejected = []
        append = rejected.append

        q_holdings = Q()
        holders = []
        for (holder, source, resource, _, _) in set_quota:
            holders.append(holder)

        hs = Holding.objects.filter(holder__in=holders).select_for_update()
        holdings = {}
        for h in hs:
            holdings[(h.holder, h.source, h.resource)] = h

        for (holder, source, resource,
             limit,
             flags) in set_quota:

            try:
                h = holdings[(holder, source, resource)]
                h.flags = flags
            except KeyError:
                h = Holding(holder=holder,
                            source=source,
                            resource=resource,
                            flags=flags)

            h.limit = limit
            h.save()
            holdings[(holder, source, resource)] = h

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
                 limit,
                 ) in source:

                try:
                    h = holdings[(holder, resource)]
                    current_limit = h.limit
                except KeyError:
                    if removing:
                        append((holder, resource))
                        continue

                    h = Holding(holder=holder, resource=resource, flags=0)
                    current_limit = 0

                h.limit = (current_limit - limit if removing else
                           current_limit + limit)

                if h.limit < 0:
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
                         name=None,
                         provisions=()):

        if name is None:
            name = ""
        create = Commission.objects.create
        commission = create(clientkey=clientkey, name=name)
        serial = commission.serial

        operations = Operations()

        try:
            checked = []
            for holder, source, resource, quantity in provisions:

                if holder == source:
                    m = ("Cannot issue commission from a holder "
                         "to itself (%s)" % (holder,))
                    raise InvalidDataError(m)

                ent_res = holder, resource
                if ent_res in checked:
                    m = "Duplicate provision for %s.%s" % ent_res
                    raise DuplicateError(m)
                checked.append(ent_res)

                # Target
                try:
                    th = db_get_holding(holder=holder,
                                        resource=resource,
                                        source=source,
                                        for_update=True)
                except Holding.DoesNotExist:
                    m = ("There is no capacity "
                         "to allocate into in %s.%s" % (holder, resource))
                    raise NoCapacityError(m,
                                          holder=holder,
                                          resource=resource,
                                          requested=quantity,
                                          current=0,
                                          limit=0)

                if quantity >= 0:
                    operations.prepare(Import, th, quantity)

                else: # release
                    abs_quantity = -quantity
                    operations.prepare(Release, th, abs_quantity)

                Provision.objects.create(serial=commission,
                                         holding=th,
                                         quantity=quantity)

        except QuotaholderError:
            operations.revert()
            raise

        return serial

    def _log_provision(self,
                       commission, provision, log_time, reason):

        holding = provision.holding

        kwargs = {
            'serial':              commission.serial,
            'name':                commission.name,
            'holder':              holding.holder,
            'source':              holding.source,
            'resource':            holding.resource,
            'limit':               holding.limit,
            'imported_min':        holding.imported_min,
            'imported_max':        holding.imported_max,
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

            operations = Operations()

            provisions = db_filter_provision(serial=serial, for_update=True)
            for pv in provisions:
                try:
                    th = db_get_holding(id=pv.holding_id,
                                        for_update=True)
                except Holding.DoesNotExist:
                    m = "Corrupted provision"
                    raise CorruptedError(m)

                quantity = pv.quantity

                if quantity >= 0:
                    operations.finalize(Import, th, quantity)
                else: # release
                    abs_quantity = -quantity
                    operations.finalize(Release, th, abs_quantity)

                reason = 'ACCEPT:' + reason[-121:]
                self._log_provision(c, pv, log_time, reason)
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

            operations = Operations()

            provisions = db_filter_provision(serial=serial, for_update=True)
            for pv in provisions:
                try:
                    th = db_get_holding(id=pv.holding_id,
                                        for_update=True)
                except Holding.DoesNotExist:
                    m = "Corrupted provision"
                    raise CorruptedError(m)

                quantity = pv.quantity

                if quantity >= 0:
                    operations.undo(Import, th, quantity)
                else: # release
                    abs_quantity = -quantity
                    operations.undo(Release, th, abs_quantity)

                reason = 'REJECT:' + reason[-121:]
                self._log_provision(c, pv, log_time, reason)
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
