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
    NoQuantityError, NoCapacityError,
    DuplicateError)

from astakos.quotaholder.utils.newname import newname
from astakos.quotaholder.api import QH_PRACTICALLY_INFINITE

from django.db.models import Q, Count
from django.db.models import Q
from .models import (Policy, Holding,
                     Commission, Provision, ProvisionLog,
                     now,
                     db_get_holding, db_get_policy,
                     db_get_commission, db_filter_provision)


class QuotaholderDjangoDBCallpoint(object):

    def get_limits(self, context=None, get_limits=[]):
        limits = []
        append = limits.append

        for policy in get_limits:
            try:
                p = Policy.objects.get(policy=policy)
            except Policy.DoesNotExist:
                continue

            append((policy, p.quantity, p.capacity))

        return limits

    def set_limits(self, context=None, set_limits=[]):

        for (policy, quantity, capacity) in set_limits:

            try:
                policy = db_get_policy(policy=policy, for_update=True)
            except Policy.DoesNotExist:
                Policy.objects.create(policy=policy,
                                      quantity=quantity,
                                      capacity=capacity,
                                      )
            else:
                policy.quantity = quantity
                policy.capacity = capacity
                policy.save()

        return ()

    def get_holding(self, context=None, get_holding=[]):
        holdings = []
        append = holdings.append

        for holder, resource in get_holding:
            try:
                h = Holding.objects.get(holder=holder, resource=resource)
            except Holding.DoesNotExist:
                continue

            append((h.holder, h.resource, h.policy.policy,
                    h.imported, h.exported,
                    h.returned, h.released, h.flags))

        return holdings

    def set_holding(self, context=None, set_holding=[]):
        rejected = []
        append = rejected.append

        for holder, resource, policy, flags in set_holding:
            try:
                p = Policy.objects.get(policy=policy)
            except Policy.DoesNotExist:
                append((holder, resource, policy))
                continue

            try:
                h = db_get_holding(holder=holder, resource=resource,
                                   for_update=True)
                h.policy = p
                h.flags = flags
                h.save()
            except Holding.DoesNotExist:
                h = Holding.objects.create(holder=holder, resource=resource,
                                           policy=p, flags=flags)

        if rejected:
            raise QuotaholderError(rejected)
        return rejected

    def _init_holding(self,
                      holder, resource, policy,
                      imported, exported, returned, released,
                      flags):
        try:
            h = db_get_holding(holder=holder, resource=resource,
                               for_update=True)
        except Holding.DoesNotExist:
            h = Holding(holder=holder, resource=resource)

        h.policy = policy
        h.flags = flags
        h.imported = imported
        h.importing = imported
        h.exported = exported
        h.exporting = exported
        h.returned = returned
        h.returning = returned
        h.released = released
        h.releasing = released
        h.save()

    def init_holding(self, context=None, init_holding=[]):
        rejected = []
        append = rejected.append

        for idx, sfh in enumerate(init_holding):
            (holder, resource, policy,
             imported, exported, returned, released,
             flags) = sfh

            try:
                p = Policy.objects.get(policy=policy)
            except Policy.DoesNotExist:
                append(idx)
                continue

            self._init_holding(holder, resource, p,
                               imported, exported,
                               returned, released,
                               flags)
        if rejected:
            raise QuotaholderError(rejected)
        return rejected

    def reset_holding(self, context=None, reset_holding=[]):
        rejected = []
        append = rejected.append

        for idx, tpl in enumerate(reset_holding):
            (holder, resource,
             imported, exported, returned, released) = tpl

            try:
                h = db_get_holding(holder=holder, resource=resource,
                                   for_update=True)
                h.imported = imported
                h.importing = imported
                h.exported = exported
                h.exporting = exported
                h.returned = returned
                h.returning = returned
                h.released = released
                h.releasing = released
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

    def _actual_quantity(self, holding):
        hp = holding.policy
        return hp.quantity + (holding.imported + holding.returned -
                              holding.exported - holding.released)

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

            q = self._actual_quantity(h)
            if q > 0:
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
                     h.imported, h.exported, h.returned, h.released)
                    for h in holdings])

        return holdings_list, rejected

    def get_quota(self, context=None, get_quota=[]):
        quotas = []
        append = quotas.append

        holders = set(holder for holder, r in get_quota)
        hs = Holding.objects.select_related().filter(holder__in=holders)
        holdings = {}
        for h in hs:
            holdings[(h.holder, h.resource)] = h

        for holder, resource in get_quota:
            try:
                h = holdings[(holder, resource)]
            except:
                continue

            p = h.policy

            append((h.holder, h.resource, p.quantity, p.capacity,
                    h.imported, h.exported,
                    h.returned, h.released,
                    h.flags))

        return quotas

    def set_quota(self, context=None, set_quota=[]):
        rejected = []
        append = rejected.append

        q_holdings = Q()
        holders = []
        for (holder, resource, _, _, _) in set_quota:
            holders.append(holder)

        hs = Holding.objects.filter(holder__in=holders).select_for_update()
        holdings = {}
        for h in hs:
            holdings[(h.holder, h.resource)] = h

        old_policies = []

        for (holder, resource,
             quantity, capacity,
             flags) in set_quota:

            policy = newname('policy_')
            newp = Policy(policy=policy,
                          quantity=quantity,
                          capacity=capacity,
                          )

            try:
                h = holdings[(holder, resource)]
                old_policies.append(h.policy_id)
                h.policy = newp
                h.flags = flags
            except KeyError:
                h = Holding(holder=holder, resource=resource,
                            policy=newp, flags=flags)

            # the order is intentionally reversed so that it
            # would break if we are not within a transaction.
            # Has helped before.
            h.save()
            newp.save()
            holdings[(holder, resource)] = h

        objs = Policy.objects.annotate(refs=Count('holding'))
        objs.filter(policy__in=old_policies, refs=0).delete()

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
        for (holder, resource, _, _) in sources:
            holders.append(holder)

        hs = Holding.objects.filter(holder__in=holders).select_for_update()
        holdings = {}
        for h in hs:
            holdings[(h.holder, h.resource)] = h

        pids = [h.policy_id for h in hs]
        policies = Policy.objects.in_bulk(pids)

        old_policies = []

        for removing, source in [(True, sub_quota), (False, add_quota)]:
            for (holder, resource,
                 quantity, capacity,
                 ) in source:

                try:
                    h = holdings[(holder, resource)]
                    old_policies.append(h.policy_id)
                    try:
                        p = policies[h.policy_id]
                    except KeyError:
                        raise AssertionError("no policy %s" % h.policy_id)
                except KeyError:
                    if removing:
                        append((holder, resource))
                        continue

                    h = Holding(holder=holder, resource=resource, flags=0)
                    p = None

                policy = newname('policy_')
                newp = Policy(policy=policy)

                newp.quantity = _add(p.quantity if p else 0, quantity,
                                     invert=removing)
                newp.capacity = _add(p.capacity if p else 0, capacity,
                                     invert=removing)

                if _isneg(newp.capacity):
                    append((holder, resource))
                    continue

                h.policy = newp

                # the order is intentionally reversed so that it
                # would break if we are not within a transaction.
                # Has helped before.
                h.save()
                newp.save()
                policies[policy] = newp
                holdings[(holder, resource)] = h

        objs = Policy.objects.annotate(refs=Count('holding'))
        objs.filter(policy__in=old_policies, refs=0).delete()

        if rejected:
            raise QuotaholderError(rejected)

        return rejected

    def issue_commission(self,
                         context=None,
                         clientkey=None,
                         target=None,
                         name=None,
                         provisions=[]):

        create = Commission.objects.create
        commission = create(holder=target, clientkey=clientkey, name=name)
        serial = commission.serial

        checked = []
        for holder, resource, quantity in provisions:

            if holder == target:
                m = "Cannot issue commission from an holder to itself (%s)" % (
                    holder,)
                raise InvalidDataError(m)

            ent_res = holder, resource
            if ent_res in checked:
                m = "Duplicate provision for %s.%s" % ent_res
                raise DuplicateError(m)
            checked.append(ent_res)

            release = 0
            if quantity < 0:
                release = 1

            # Source limits checks
            try:
                h = db_get_holding(holder=holder, resource=resource,
                                   for_update=True)
            except Holding.DoesNotExist:
                m = ("There is no quantity "
                     "to allocate from in %s.%s" % (holder, resource))
                raise NoQuantityError(m,
                                      source=holder, target=target,
                                      resource=resource, requested=quantity,
                                      current=0, limit=0)

            hp = h.policy

            if not release:
                limit = hp.quantity + h.imported - h.releasing
                unavailable = h.exporting - h.returned
                available = limit - unavailable

                if quantity > available:
                    m = ("There is not enough quantity "
                         "to allocate from in %s.%s" % (holder, resource))
                    raise NoQuantityError(m,
                                          source=holder,
                                          target=target,
                                          resource=resource,
                                          requested=quantity,
                                          current=unavailable,
                                          limit=limit)
            else:
                current = (+ h.importing + h.returning
                           - h.exported - h.returned)
                limit = hp.capacity
                if current - quantity > limit:
                    m = ("There is not enough capacity "
                         "to release to in %s.%s" % (holder, resource))
                    raise NoQuantityError(m,
                                          source=holder,
                                          target=target,
                                          resource=resource,
                                          requested=quantity,
                                          current=current,
                                          limit=limit)

            # Target limits checks
            try:
                th = db_get_holding(holder=target, resource=resource,
                                    for_update=True)
            except Holding.DoesNotExist:
                m = ("There is no capacity "
                     "to allocate into in %s.%s" % (target, resource))
                raise NoCapacityError(m,
                                      source=holder,
                                      target=target,
                                      resource=resource,
                                      requested=quantity,
                                      current=0,
                                      limit=0)

            tp = th.policy

            if not release:
                limit = tp.quantity + tp.capacity
                current = (+ th.importing + th.returning + tp.quantity
                           - th.exported - th.released)

                if current + quantity > limit:
                    m = ("There is not enough capacity "
                         "to allocate into in %s.%s" % (target, resource))
                    raise NoCapacityError(m,
                                          source=holder,
                                          target=target,
                                          resource=resource,
                                          requested=quantity,
                                          current=current,
                                          limit=limit)
            else:
                limit = tp.quantity + th.imported - th.releasing
                unavailable = th.exporting - th.returned
                available = limit - unavailable

                if available + quantity < 0:
                    m = ("There is not enough quantity "
                         "to release from in %s.%s" % (target, resource))
                    raise NoCapacityError(m,
                                          source=holder,
                                          target=target,
                                          resource=resource,
                                          requested=quantity,
                                          current=unavailable,
                                          limit=limit)

            Provision.objects.create(serial=commission,
                                     holder=holder,
                                     resource=resource,
                                     quantity=quantity)
            if release:
                h.returning -= quantity
                th.releasing -= quantity
            else:
                h.exporting += quantity
                th.importing += quantity

            h.save()
            th.save()

        return serial

    def _log_provision(self,
                       commission, s_holding, t_holding,
                       provision, log_time, reason):

        s_holder = s_holding.holder
        s_policy = s_holding.policy
        t_holder = t_holding.holder
        t_policy = t_holding.policy

        kwargs = {
            'serial':              commission.serial,
            'name':                commission.name,
            'source':              s_holder,
            'target':              t_holder,
            'resource':            provision.resource,
            'source_quantity':     s_policy.quantity,
            'source_capacity':     s_policy.capacity,
            'source_imported':     s_holding.imported,
            'source_exported':     s_holding.exported,
            'source_returned':     s_holding.returned,
            'source_released':     s_holding.released,
            'target_quantity':     t_policy.quantity,
            'target_capacity':     t_policy.capacity,
            'target_imported':     t_holding.imported,
            'target_exported':     t_holding.exported,
            'target_returned':     t_holding.returned,
            'target_released':     t_holding.released,
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

            provisions = db_filter_provision(serial=serial, for_update=True)
            for pv in provisions:
                try:
                    h = db_get_holding(holder=pv.holder,
                                       resource=pv.resource, for_update=True)
                    th = db_get_holding(holder=t, resource=pv.resource,
                                        for_update=True)
                except Holding.DoesNotExist:
                    m = "Corrupted provision"
                    raise CorruptedError(m)

                quantity = pv.quantity
                release = 0
                if quantity < 0:
                    release = 1

                if release:
                    h.returned -= quantity
                    th.released -= quantity
                else:
                    h.exported += quantity
                    th.imported += quantity

                reason = 'ACCEPT:' + reason[-121:]
                self._log_provision(c, h, th, pv, log_time, reason)
                h.save()
                th.save()
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

            provisions = db_filter_provision(serial=serial, for_update=True)
            for pv in provisions:
                try:
                    h = db_get_holding(holder=pv.holder,
                                       resource=pv.resource, for_update=True)
                    th = db_get_holding(holder=t, resource=pv.resource,
                                        for_update=True)
                except Holding.DoesNotExist:
                    m = "Corrupted provision"
                    raise CorruptedError(m)

                quantity = pv.quantity
                release = 0
                if quantity < 0:
                    release = 1

                if release:
                    h.returning += quantity
                    th.releasing += quantity
                else:
                    h.exporting -= quantity
                    th.importing -= quantity

                reason = 'REJECT:' + reason[-121:]
                self._log_provision(c, h, th, pv, log_time, reason)
                h.save()
                th.save()
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


def _add(x, y, invert=False):
    return x + y if not invert else x - y


def _isneg(x):
    return x < 0


API_Callpoint = QuotaholderDjangoDBCallpoint
