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
    InvalidKeyError, NoEntityError,
    NoQuantityError, NoCapacityError,
    ExportLimitError, ImportLimitError,
    DuplicateError)

from astakos.quotaholder.utils.newname import newname
from astakos.quotaholder.api import QH_PRACTICALLY_INFINITE

from django.db.models import Q, Count
from .models import (Entity, Policy, Holding,
                     Commission, Provision, ProvisionLog, CallSerial,
                     now,
                     db_get_entity, db_get_holding, db_get_policy,
                     db_get_commission, db_filter_provision, db_get_callserial)


class QuotaholderDjangoDBCallpoint(object):

    def create_entity(self, context=None, create_entity=()):
        rejected = []
        append = rejected.append

        for idx, (entity, owner, key, ownerkey) in enumerate(create_entity):
            try:
                owner = Entity.objects.get(entity=owner, key=ownerkey)
            except Entity.DoesNotExist:
                append(idx)
                continue

            try:
                e = Entity.objects.get(entity=entity)
                append(idx)
            except Entity.DoesNotExist:
                e = Entity.objects.create(entity=entity,
                                          owner=owner,
                                          key=key)

        if rejected:
            raise QuotaholderError(rejected)
        return rejected

    def set_entity_key(self, context=None, set_entity_key=()):
        rejected = []
        append = rejected.append

        for entity, key, newkey in set_entity_key:
            try:
                e = db_get_entity(entity=entity, key=key, for_update=True)
            except Entity.DoesNotExist:
                append(entity)
                continue

            e.key = newkey
            e.save()

        if rejected:
            raise QuotaholderError(rejected)
        return rejected

    def list_entities(self, context=None, entity=None, key=None):
        try:
            e = Entity.objects.get(entity=entity, key=key)
        except Entity.DoesNotExist:
            m = "Entity '%s' does not exist" % (entity,)
            raise NoEntityError(m)

        children = e.entities.all()
        entities = [e.entity for e in children]
        return entities

    def get_entity(self, context=None, get_entity=()):
        entities = []
        append = entities.append

        names = [entity for entity, key in get_entity]
        es = Entity.objects.select_related(depth=1).filter(entity__in=names)
        data = {}
        for e in es:
            data[e.entity] = e

        for entity, key in get_entity:
            e = data.get(entity, None)
            if e is None or e.key != key:
                continue
            append((entity, e.owner.entity))

        return entities

    def get_limits(self, context=None, get_limits=()):
        limits = []
        append = limits.append

        for policy in get_limits:
            try:
                p = Policy.objects.get(policy=policy)
            except Policy.DoesNotExist:
                continue

            append((policy, p.quantity, p.capacity,
                    p.import_limit, p.export_limit))

        return limits

    def set_limits(self, context=None, set_limits=()):

        for (policy, quantity, capacity,
             import_limit, export_limit) in set_limits:

            try:
                policy = db_get_policy(policy=policy, for_update=True)
            except Policy.DoesNotExist:
                Policy.objects.create(policy=policy,
                                      quantity=quantity,
                                      capacity=capacity,
                                      import_limit=import_limit,
                                      export_limit=export_limit)
            else:
                policy.quantity = quantity
                policy.capacity = capacity
                policy.export_limit = export_limit
                policy.import_limit = import_limit
                policy.save()

        return ()

    def get_holding(self, context=None, get_holding=()):
        holdings = []
        append = holdings.append

        for entity, resource, key in get_holding:
            try:
                h = Holding.objects.get(entity=entity, resource=resource)
            except Holding.DoesNotExist:
                continue

            if h.entity.key != key:
                continue

            append((h.entity.entity, h.resource, h.policy.policy,
                    h.imported, h.exported,
                    h.returned, h.released, h.flags))

        return holdings

    def set_holding(self, context=None, set_holding=()):
        rejected = []
        append = rejected.append

        for entity, resource, key, policy, flags in set_holding:
            try:
                e = Entity.objects.get(entity=entity, key=key)
            except Entity.DoesNotExist:
                append((entity, resource, policy))
                continue

            if e.key != key:
                append((entity, resource, policy))
                continue

            try:
                p = Policy.objects.get(policy=policy)
            except Policy.DoesNotExist:
                append((entity, resource, policy))
                continue

            try:
                h = db_get_holding(entity=entity, resource=resource,
                                   for_update=True)
                h.policy = p
                h.flags = flags
                h.save()
            except Holding.DoesNotExist:
                h = Holding.objects.create(entity=e, resource=resource,
                                           policy=p, flags=flags)

        if rejected:
            raise QuotaholderError(rejected)
        return rejected

    def _init_holding(self,
                      entity, resource, policy,
                      imported, exported, returned, released,
                      flags):
        try:
            h = db_get_holding(entity=entity, resource=resource,
                               for_update=True)
        except Holding.DoesNotExist:
            h = Holding(entity=entity, resource=resource)

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

    def init_holding(self, context=None, init_holding=()):
        rejected = []
        append = rejected.append

        for idx, sfh in enumerate(init_holding):
            (entity, resource, key, policy,
             imported, exported, returned, released,
             flags) = sfh
            try:
                e = Entity.objects.get(entity=entity, key=key)
            except Entity.DoesNotExist:
                append(idx)
                continue

            if e.key != key:
                append(idx)
                continue

            try:
                p = Policy.objects.get(policy=policy)
            except Policy.DoesNotExist:
                append(idx)
                continue

            self._init_holding(e, resource, p,
                               imported, exported,
                               returned, released,
                               flags)
        if rejected:
            raise QuotaholderError(rejected)
        return rejected

    def reset_holding(self, context=None, reset_holding=()):
        rejected = []
        append = rejected.append

        for idx, tpl in enumerate(reset_holding):
            (entity, resource, key,
             imported, exported, returned, released) = tpl
            try:
                e = Entity.objects.get(entity=entity, key=key)
            except Entity.DoesNotExist:
                append(idx)
                continue

            try:
                h = db_get_holding(entity=entity, resource=resource,
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

    def _check_pending(self, entity, resource):
        cs = Commission.objects.filter(entity=entity)
        cs = [c for c in cs if c.provisions.filter(resource=resource)]
        as_target = [c.serial for c in cs]

        ps = Provision.objects.filter(entity=entity, resource=resource)
        as_source = [p.serial.serial for p in ps]

        return as_target + as_source

    def _actual_quantity(self, holding):
        hp = holding.policy
        return hp.quantity + (holding.imported + holding.returned -
                              holding.exported - holding.released)

    def _new_policy_name(self):
        return newname('policy_')

    def _increase_resource(self, entity, resource, amount):
        try:
            h = db_get_holding(entity=entity, resource=resource,
                               for_update=True)
        except Holding.DoesNotExist:
            h = Holding(entity=entity, resource=resource)
            p = Policy.objects.create(policy=self._new_policy_name(),
                                      quantity=0,
                                      capacity=QH_PRACTICALLY_INFINITE,
                                      import_limit=QH_PRACTICALLY_INFINITE,
                                      export_limit=QH_PRACTICALLY_INFINITE)
            h.policy = p
        h.imported += amount
        h.save()

    def release_holding(self, context=None, release_holding=()):
        rejected = []
        append = rejected.append

        for idx, (entity, resource, key) in enumerate(release_holding):
            try:
                h = db_get_holding(entity=entity, resource=resource,
                                   for_update=True)
            except Holding.DoesNotExist:
                append(idx)
                continue

            if h.entity.key != key:
                append(idx)
                continue

            if self._check_pending(entity, resource):
                append(idx)
                continue

            q = self._actual_quantity(h)
            if q > 0:
                owner = h.entity.owner
                self._increase_resource(owner, resource, q)

            h.delete()

        if rejected:
            raise QuotaholderError(rejected)
        return rejected

    def list_resources(self, context=None, entity=None, key=None):
        try:
            e = Entity.objects.get(entity=entity)
        except Entity.DoesNotExist:
            m = "No such entity '%s'" % (entity,)
            raise NoEntityError(m)

        if e.key != key:
            m = "Invalid key for entity '%s'" % (entity,)
            raise InvalidKeyError(m)

        holdings = e.holding_set.filter(entity=entity)
        resources = [h.resource for h in holdings]
        return resources

    def list_holdings(self, context=None, list_holdings=()):
        rejected = []
        reject = rejected.append
        holdings_list = []
        append = holdings_list.append

        for entity, key in list_holdings:
            try:
                e = Entity.objects.get(entity=entity)
                if e.key != key:
                    raise Entity.DoesNotExist("wrong key")
            except Entity.DoesNotExist:
                reject(entity)
                continue

            holdings = e.holding_set.filter(entity=entity)
            append([[entity, h.resource,
                     h.imported, h.exported, h.returned, h.released]
                    for h in holdings])

        return holdings_list, rejected

    def get_quota(self, context=None, get_quota=()):
        quotas = []
        append = quotas.append

        entities = set(e for e, r, k in get_quota)
        hs = Holding.objects.select_related().filter(entity__in=entities)
        holdings = {}
        for h in hs:
            holdings[(h.entity_id, h.resource)] = h

        for entity, resource, key in get_quota:
            try:
                h = holdings[(entity, resource)]
            except:
                continue

            if h.entity.key != key:
                continue

            p = h.policy

            append((h.entity.entity, h.resource, p.quantity, p.capacity,
                    p.import_limit, p.export_limit,
                    h.imported, h.exported,
                    h.returned, h.released,
                    h.flags))

        return quotas

    def set_quota(self, context=None, set_quota=()):
        rejected = []
        append = rejected.append

        q_holdings = Q()
        entities = []
        for (entity, resource, key, _, _, _, _, _) in set_quota:
            entities.append(entity)

        hs = Holding.objects.filter(entity__in=entities).select_for_update()
        holdings = {}
        for h in hs:
            holdings[(h.entity_id, h.resource)] = h

        entities = Entity.objects.in_bulk(entities)

        old_policies = []

        for (entity, resource, key,
             quantity, capacity,
             import_limit, export_limit, flags) in set_quota:

            e = entities.get(entity, None)
            if e is None or e.key != key:
                append((entity, resource))
                continue

            policy = newname('policy_')
            newp = Policy(policy=policy,
                          quantity=quantity,
                          capacity=capacity,
                          import_limit=import_limit,
                          export_limit=export_limit)

            try:
                h = holdings[(entity, resource)]
                old_policies.append(h.policy_id)
                h.policy = newp
                h.flags = flags
            except KeyError:
                h = Holding(entity=e, resource=resource,
                            policy=newp, flags=flags)

            # the order is intentionally reversed so that it
            # would break if we are not within a transaction.
            # Has helped before.
            h.save()
            newp.save()
            holdings[(entity, resource)] = h

        objs = Policy.objects.annotate(refs=Count('holding'))
        objs.filter(policy__in=old_policies, refs=0).delete()

        if rejected:
            raise QuotaholderError(rejected)
        return rejected

    def add_quota(self,
                  context=None, clientkey=None, serial=None,
                  sub_quota=(), add_quota=()):
        rejected = []
        append = rejected.append

        if serial is not None:
            if clientkey is None:
                all_pairs = [(q[0], q[1]) for q in sub_quota + add_quota]
                raise QuotaholderError(all_pairs)
            try:
                cs = CallSerial.objects.get(serial=serial, clientkey=clientkey)
                all_pairs = [(q[0], q[1]) for q in sub_quota + add_quota]
                raise QuotaholderError(all_pairs)
            except CallSerial.DoesNotExist:
                pass

        sources = sub_quota + add_quota
        q_holdings = Q()
        entities = []
        for (entity, resource, key, _, _, _, _) in sources:
            entities.append(entity)

        hs = Holding.objects.filter(entity__in=entities).select_for_update()
        holdings = {}
        for h in hs:
            holdings[(h.entity_id, h.resource)] = h

        entities = Entity.objects.in_bulk(entities)

        pids = [h.policy_id for h in hs]
        policies = Policy.objects.in_bulk(pids)

        old_policies = []

        for removing, source in [(True, sub_quota), (False, add_quota)]:
            for (entity, resource, key,
                 quantity, capacity,
                 import_limit, export_limit) in source:

                e = entities.get(entity, None)
                if e is None or e.key != key:
                    append((entity, resource))
                    continue

                try:
                    h = holdings[(entity, resource)]
                    old_policies.append(h.policy_id)
                    try:
                        p = policies[h.policy_id]
                    except KeyError:
                        raise AssertionError("no policy %s" % h.policy_id)
                except KeyError:
                    if removing:
                        append((entity, resource))
                        continue
                    h = Holding(entity=e, resource=resource, flags=0)
                    p = None

                policy = newname('policy_')
                newp = Policy(policy=policy)

                newp.quantity = _add(p.quantity if p else 0, quantity,
                                     invert=removing)
                newp.capacity = _add(p.capacity if p else 0, capacity,
                                     invert=removing)
                newp.import_limit = _add(p.import_limit if p else 0,
                                         import_limit, invert=removing)
                newp.export_limit = _add(p.export_limit if p else 0,
                                         export_limit, invert=removing)

                new_values = [newp.capacity,
                              newp.import_limit, newp.export_limit]
                if any(map(_isneg, new_values)):
                    append((entity, resource))
                    continue

                h.policy = newp

                # the order is intentionally reversed so that it
                # would break if we are not within a transaction.
                # Has helped before.
                h.save()
                newp.save()
                policies[policy] = newp
                holdings[(entity, resource)] = h

        objs = Policy.objects.annotate(refs=Count('holding'))
        objs.filter(policy__in=old_policies, refs=0).delete()

        if rejected:
            raise QuotaholderError(rejected)

        if serial is not None and clientkey is not None:
            CallSerial.objects.create(serial=serial, clientkey=clientkey)
        return rejected

    def ack_serials(self, context=None, clientkey=None, serials=()):
        if clientkey is None:
            return

        for serial in serials:
            try:
                c = db_get_callserial(clientkey=clientkey,
                                      serial=serial,
                                      for_update=True)
                c.delete()
            except CallSerial.DoesNotExist:
                pass
        return

    def query_serials(self, context=None, clientkey=None, serials=()):
        result = []
        append = result.append

        if clientkey is None:
            return result

        if not serials:
            cs = CallSerial.objects.filter(clientkey=clientkey)
            return [c.serial for c in cs]

        for serial in serials:
            try:
                db_get_callserial(clientkey=clientkey, serial=serial)
                append(serial)
            except CallSerial.DoesNotExist:
                pass

        return result

    def issue_commission(self,
                         context=None,
                         clientkey=None,
                         target=None,
                         key=None,
                         name=None,
                         provisions=()):

        try:
            t = Entity.objects.get(entity=target)
        except Entity.DoesNotExist:
            m = "No target entity '%s'" % (target,)
            raise NoEntityError(m)
        else:
            if t.key != key:
                m = "Invalid key for target entity '%s'" % (target,)
                raise InvalidKeyError(m)

        create = Commission.objects.create
        commission = create(entity_id=target, clientkey=clientkey, name=name)
        serial = commission.serial

        checked = []
        for entity, resource, quantity in provisions:

            if entity == target:
                m = "Cannot issue commission from an entity to itself (%s)" % (
                    entity,)
                raise InvalidDataError(m)

            ent_res = entity, resource
            if ent_res in checked:
                m = "Duplicate provision for %s.%s" % ent_res
                raise DuplicateError(m)
            checked.append(ent_res)

            try:
                e = Entity.objects.get(entity=entity)
            except Entity.DoesNotExist:
                m = "No source entity '%s'" % (entity,)
                raise NoEntityError(m)

            release = 0
            if quantity < 0:
                release = 1

            # Source limits checks
            try:
                h = db_get_holding(entity=entity, resource=resource,
                                   for_update=True)
            except Holding.DoesNotExist:
                m = ("There is no quantity "
                     "to allocate from in %s.%s" % (entity, resource))
                raise NoQuantityError(m,
                                      source=entity, target=target,
                                      resource=resource, requested=quantity,
                                      current=0, limit=0)

            hp = h.policy

            if not release:
                current = h.exporting
                limit = hp.export_limit
                if current + quantity > limit:
                    m = ("Export limit reached for %s.%s" % (entity, resource))
                    raise ExportLimitError(m,
                                           source=entity,
                                           target=target,
                                           resource=resource,
                                           requested=quantity,
                                           current=current,
                                           limit=limit)

                limit = hp.quantity + h.imported - h.releasing
                unavailable = h.exporting - h.returned
                available = limit - unavailable

                if quantity > available:
                    m = ("There is not enough quantity "
                         "to allocate from in %s.%s" % (entity, resource))
                    raise NoQuantityError(m,
                                          source=entity,
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
                         "to release to in %s.%s" % (entity, resource))
                    raise NoQuantityError(m,
                                          source=entity,
                                          target=target,
                                          resource=resource,
                                          requested=quantity,
                                          current=current,
                                          limit=limit)

            # Target limits checks
            try:
                th = db_get_holding(entity=target, resource=resource,
                                    for_update=True)
            except Holding.DoesNotExist:
                m = ("There is no capacity "
                     "to allocate into in %s.%s" % (target, resource))
                raise NoCapacityError(m,
                                      source=entity,
                                      target=target,
                                      resource=resource,
                                      requested=quantity,
                                      current=0,
                                      limit=0)

            tp = th.policy

            if not release:
                limit = tp.import_limit
                current = th.importing
                if current + quantity > limit:
                    m = ("Import limit reached for %s.%s" % (target, resource))
                    raise ImportLimitError(m,
                                           source=entity,
                                           target=target,
                                           resource=resource,
                                           requested=quantity,
                                           current=current,
                                           limit=limit)

                limit = tp.quantity + tp.capacity
                current = (+ th.importing + th.returning + tp.quantity
                           - th.exported - th.released)

                if current + quantity > limit:
                    m = ("There is not enough capacity "
                         "to allocate into in %s.%s" % (target, resource))
                    raise NoCapacityError(m,
                                          source=entity,
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
                                          source=entity,
                                          target=target,
                                          resource=resource,
                                          requested=quantity,
                                          current=unavailable,
                                          limit=limit)

            Provision.objects.create(serial=commission,
                                     entity=e,
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

        s_entity = s_holding.entity
        s_policy = s_holding.policy
        t_entity = t_holding.entity
        t_policy = t_holding.policy

        kwargs = {
            'serial':              commission.serial,
            'name':                commission.name,
            'source':              s_entity.entity,
            'target':              t_entity.entity,
            'resource':            provision.resource,
            'source_quantity':     s_policy.quantity,
            'source_capacity':     s_policy.capacity,
            'source_import_limit': s_policy.import_limit,
            'source_export_limit': s_policy.export_limit,
            'source_imported':     s_holding.imported,
            'source_exported':     s_holding.exported,
            'source_returned':     s_holding.returned,
            'source_released':     s_holding.released,
            'target_quantity':     t_policy.quantity,
            'target_capacity':     t_policy.capacity,
            'target_import_limit': t_policy.import_limit,
            'target_export_limit': t_policy.export_limit,
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
                          serials=(), reason=''):
        log_time = now()

        for serial in serials:
            try:
                c = db_get_commission(clientkey=clientkey, serial=serial,
                                      for_update=True)
            except Commission.DoesNotExist:
                return

            t = c.entity

            provisions = db_filter_provision(serial=serial, for_update=True)
            for pv in provisions:
                try:
                    h = db_get_holding(entity=pv.entity.entity,
                                       resource=pv.resource, for_update=True)
                    th = db_get_holding(entity=t, resource=pv.resource,
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
                          serials=(), reason=''):
        log_time = now()

        for serial in serials:
            try:
                c = db_get_commission(clientkey=clientkey, serial=serial,
                                      for_update=True)
            except Commission.DoesNotExist:
                return

            t = c.entity

            provisions = db_filter_provision(serial=serial, for_update=True)
            for pv in provisions:
                try:
                    h = db_get_holding(entity=pv.entity.entity,
                                       resource=pv.resource, for_update=True)
                    th = db_get_holding(entity=t, resource=pv.resource,
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
                                    max_serial=None, accept_set=()):
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

    def release_entity(self, context=None, release_entity=()):
        rejected = []
        append = rejected.append
        for entity, key in release_entity:
            try:
                e = db_get_entity(entity=entity, key=key, for_update=True)
            except Entity.DoesNotExist:
                append(entity)
                continue

            if e.entities.count() != 0:
                append(entity)
                continue

            if e.holding_set.count() != 0:
                append(entity)
                continue

            e.delete()

        if rejected:
            raise QuotaholderError(rejected)
        return rejected

    def get_timeline(self, context=None, after="", before="Z", get_timeline=()):
        entity_set = set()
        e_add = entity_set.add
        resource_set = set()
        r_add = resource_set.add

        for entity, resource, key in get_timeline:
            if entity not in entity_set:
                try:
                    e = Entity.objects.get(entity=entity, key=key)
                    e_add(entity)
                except Entity.DoesNotExist:
                    continue

            r_add((entity, resource))

        chunk_size = 65536
        nr = 0
        timeline = []
        append = timeline.append
        filterlogs = ProvisionLog.objects.filter
        if entity_set:
            q_entity = Q(source__in=entity_set) | Q(target__in=entity_set)
        else:
            q_entity = Q()

        while 1:
            logs = filterlogs(q_entity,
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
