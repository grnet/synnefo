
from commissioning import ( QuotaholderAPI,
                            Callpoint, CommissionException,
                            CorruptedError, InvalidDataError,
                            InvalidKeyError, NoEntityError,
                            NoQuantityError, NoCapacityError,
                            ExportLimitError, ImportLimitError)


from commissioning.utils.newname import newname
from django.db.models import Model, BigIntegerField, CharField, ForeignKey, Q
from django.db import transaction, IntegrityError
from .models import (Holder, Entity, Policy, Holding,
                     Commission, Provision, ProvisionLog, now)


class QuotaholderDjangoDBCallpoint(Callpoint):

    api_spec = QuotaholderAPI()

    http_exc_lookup = {
        CorruptedError:   550,
        InvalidDataError: 400,
        InvalidKeyError:  401,
        NoEntityError:    404,
        NoQuantityError:  413,
        NoCapacityError:  413,
    }

    def init_connection(self, connection):
        if connection is not None:
            raise ValueError("Cannot specify connection args with %s" %
                             type(self).__name__)
        pass

    def commit(self):
        transaction.commit()

    def rollback(self):
        transaction.rollback()

    def do_make_call(self, call_name, data):
        call_fn = getattr(self, call_name, None)
        if not call_fn:
            m = "cannot find call '%s'" % (call_name,)
            raise CorruptedError(m)

        return call_fn(**data)

    def create_entity(self, context={}, create_entity=()):
        rejected = []
        append = rejected.append

        for entity, owner, key, ownerkey in create_entity:
            try:
                owner = Entity.objects.get(entity=owner, key=ownerkey)
            except Entity.DoesNotExist:
                append(entity)
                continue

            try:
                e = Entity.objects.get(entity=entity, owner=owner)
                append(entity)
            except Entity.DoesNotExist:
                e = Entity.objects.create(entity=entity,
                                          owner=owner,
                                          key=key)
        return rejected

    def set_entity_key(self, context={}, set_entity_key=()):
        rejected = []
        append = rejected.append

        for entity, key, newkey in set_entity_key:
            try:
                e = Entity.objects.get(entity=entity, key=key)
            except Entity.DoesNotExist:
                append(entity)

            e.key = newkey
            e.save()

        return rejected

    def list_entities(self, context={}, entity=None, key=None):
        try:
            e = Entity.objects.get(entity=entity, key=key)
        except Entity.DoesNotExist:
            m = "Entity '%s' does not exist" % (entity,)
            raise NoEntityError(m)

        children = e.entities.all()
        entities = [e.entity for e in children]
        return entities

    def get_entity(self, context={}, get_entity=()):
        entities = []
        append = entities.append

        for entity, key in get_entity:
            try:
                Entity.objects.get(entity=entity, key=key)
            except Entity.DoesNotExist:
                continue

            append((entity, key))

        return entities

    def get_limits(self, context={}, get_limits=()):
        limits = []
        append = limits.append

        for entity, resource, key in get_limits:
            try:
                h = Holding.objects.get(entity=entity, resource=resource)
            except Policy.DoesNotExist:
                continue

            if h.entity.key != key:
                continue
            p = h.policy
            append((h.entity, h.resource, p.quantity, p.capacity,
                    p.import_limit, p.export_limit, h.flags))

        return limits

    def set_limits(self, context={}, set_limits=()):

        for (   policy, quantity, capacity,
                import_limit, export_limit  ) in set_limits:

                #XXX: create or replace?
                Policy.objects.create(  policy=policy,
                                        quantity=quantity,
                                        capacity=capacity,
                                        import_limit=import_limit,
                                        export_limit=export_limit   )

        return ()

    def get_holding(self, context={}, get_holding=()):
        holdings = []
        append = holdings.append

        for entity, resource, key in get_holding:
            try:
                h = Holding.objects.get(entity=entity, resource=resource)
            except Holding.DoesNotExist:
                continue

            if h.entity.key != key:
                continue

            append((h.entity.entity, h.resource, h.policy,
                    h.imported, h.exported,
                    h.regained, h.released, h.flags))

        return holdings

    def set_holding(self, context={}, set_holding=()):
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
                h = Holding.objects.get(entity=entity, resource=resource)
                h.policy = p
                h.flags = flags
                h.save()
            except Holding.DoesNotExist:
                h = Holding.objects.create( entity=entity, resource=resource,
                                            policy=policy, flags=flags      )

        return rejected

    def list_resources(self, context={}, entity=None, key=None):
        try:
            e = Entity.objects.get()
        except Entity.DoesNotExist:
            m = "No such entity '%s'" % (entity,)
            raise NoEntityError(m)

        if e.key != key:
            m = "Invalid key for entity '%s'" % (entity,)
            raise InvalidKeyError(m)

        holdings = e.holding_set.filter(entity=entity)
        resources = [h.resource for h in holdings]
        return resources

    def get_quota(self, context={}, get_quota=()):
        quotas = []
        append = quotas.append

        for entity, resource, key in get_quota:
            try:
                h = Holding.objects.get(entity=entity, resource=resource)
            except Holding.DoesNotExist:
                continue

            if h.entity.key != key:
                continue

            p = h.policy

            append((h.entity.entity, h.resource, p.quantity, p.capacity,
                    p.import_limit, p.export_limit,
                    h.imported, h.exported,
                    h.regained, h.released,
                    h.flags))

        return quotas

    def set_quota(self, context={}, set_quota=()):
        rejected = []
        append = rejected.append

        for (   entity, resource, key,
                quantity, capacity,
                import_limit, export_limit, flags  ) in set_quota:

                p = None

                try:
                    h = Holding.objects.get(entity=entity, resource=resource)
                    if h.entity.key != key:
                        append((entity, resource))
                        continue
                    p = h.policy

                except Holding.DoesNotExist:
                    try:
                        e = Entity.objects.get(entity=entity)
                    except Entity.DoesNotExist:
                        append((entity, resource))
                        continue

                    if e.key != key:
                        append((entity, resource))
                        continue

                    h = None

                policy = newname('policy_')
                newp = Policy   (
                            policy=policy,
                            quantity=quantity,
                            capacity=capacity,
                            import_limit=import_limit,
                            export_limit=export_limit
                )

                if h is None:
                    h = Holding(entity=e, resource=resource,
                                policy=newp, flags=flags)
                else:
                    h.policy = newp
                    h.flags = flags

                h.save()
                newp.save()

                if p is not None and p.holding_set.count() == 0:
                    p.delete()

        return rejected

    def issue_commission(self,  context     =   {},
                                clientkey   =   None,
                                target      =   None,
                                key         =   None,
                                owner       =   None,
                                ownerkey    =   None,
                                provisions  =   ()  ):

        try:
            t = Entity.objects.get(entity=target)
        except Entity.DoesNotExist:
            create_entity = ((target, owner, key, ownerkey),)
            rejected = self.create_entity(context       =   context,
                                          create_entity =   create_entity)
            if rejected:
                raise NoEntityError("No target entity '%s'" % (target,))

            t = Entity.objects.get(entity=target)
        else:
            if t.key != key:
                m = "Invalid key for target entity '%s'" % (target,)
                raise InvalidKeyError(m)

        create = Commission.objects.create
        commission = create(entity_id=target, clientkey=clientkey)
        serial = commission.serial

        for entity, resource, quantity in provisions:
            release = 0
            if quantity < 0:
                release = 1

            try:
                h = Holding.objects.get(entity=entity, resource=resource)
            except Holding.DoesNotExist:
                m = ("There is not enough quantity "
                     "to allocate from in %s.%s" % (entity, resource))
                raise NoQuantityError(m)

            hp = h.policy

            if (hp.export_limit is not None and
                h.exporting + quantity > hp.export_limit):
                    m = ("Export limit reached for %s.%s" % (entity, resource))
                    raise ExportLimitError(m)

            if hp.quantity is not None:
                available = (+ hp.quantity + h.imported + h.regained
                             - h.exporting - h.releasing)

                if available - quantity < 0:
                    m = ("There is not enough quantity "
                         "to allocate from in %s.%s" % (entity, resource))
                    raise NoQuantityError(m)

            try:
                th = Holding.objects.get(entity=target, resource=resource)
            except Holding.DoesNotExist:
                m = ("There is not enough capacity "
                     "to allocate into in %s.%s" % (target, resource))
                raise NoCapacityError(m)

            tp = th.policy

            if (tp.import_limit is not None and
                th.importing + quantity > tp.import_limit):
                    m = ("Import limit reached for %s.%s" % (target, resource))
                    raise ImportLimitError(m)

            if tp.capacity is not None:
                capacity = (+ tp.capacity + th.exported + th.released
                            - th.importing - th.regaining)

                if capacity - quantity < 0:
                        m = ("There is not enough capacity "
                             "to allocate into in %s.%s" % (target, resource))
                        raise NoCapacityError(m)

            Provision.objects.create(   serial=commission,
                                        entity=t,
                                        resource=resource,
                                        quantity=quantity   )
            if release:
                h.regaining -= quantity
                th.releasing -= quantity
            else:
                h.exporting += quantity
                th.importing += quantity

            h.save()
            th.save()

        return serial

    def _log_provision(self, commission, s_holding, t_holding,
                             provision, log_time, reason):

        source_allocated = s_holding.exported - s_holding.regained
        source_available = (+ s_holding.policy.quantity + s_holding.imported
                            - s_holding.released - source_allocated)
        target_allocated = t_holding.exported - t_holding.regained
        target_available = (+ t_holding.policy.quantity + t_holding.imported
                            - t_holding.released - target_allocated)

        ProvisionLog.objects.create(
                        serial              =   commission.serial,
                        source              =   s_holding.entity.entity,
                        target              =   t_holding.entity.entity,
                        resource            =   provision.resource,
                        source_available    =   source_available,
                        source_allocated    =   source_allocated,
                        target_available    =   target_available,
                        target_allocated    =   target_allocated,
                        delta_quantity      =   provision.quantity,
                        issue_time          =   commission.issue_time,
                        log_time            =   log_time,
                        reason              =   reason)

    def accept_commission(self, context={}, clientkey=None,
                                serials=(), reason=''):
        log_time = now()

        for serial in serials:
            try:
                c = Commission.objects.get(clientkey=clientkey, serial=serial)
            except Commission.DoesNotExist:
                return

            t = c.entity

            provisions = Provision.objects.filter(serial=serial)
            for pv in provisions:
                try:
                    h = Holding.objects.get(entity=pv.entity.entity,
                                            resource=pv.resource    )
                    th = Holding.objects.get(entity=t, resource=pv.resource)
                except Holding.DoesNotExist:
                    m = "Corrupted provision"
                    raise CorruptedError(m)

                quantity = pv.quantity
                release = 0
                if quantity < 0:
                    release = 1

                if release:
                    h.regained -= quantity
                    th.released -= quantity
                else:
                    h.exported += quantity
                    th.imported += quantity

                reason = 'ACCEPT:' + reason[-121:]
                self._log_provision(c, h, th, pv, log_time, reason)
                h.save()
                th.save()
                pv.delete()

        return

    def reject_commission(self, context={}, clientkey=None,
                                serials=(), reason=''):
        log_time = now()

        for serial in serials:
            try:
                c = Commission.objects.get(clientkey=clientkey, serial=serial)
            except Commission.DoesNotExist:
                return

            t = c.entity

            provisions = Provision.objects.filter(serial=serial)
            for pv in provisions:
                try:
                    h = Holding.objects.get(entity=pv.entity.entity,
                                            resource=pv.resource)
                    th = Holding.objects.get(entity=t, resource=pv.resource)
                except Holding.DoesNotExist:
                    m = "Corrupted provision"
                    raise CorruptedError(m)

                quantity = pv.quantity
                release = 0
                if quantity < 0:
                    release = 1

                if release:
                    h.regaining += quantity
                    th.releasing += quantity
                else:
                    h.exporting -= quantity
                    th.importing -= quantity

                source_allocated = h.exported - h.regained
                source_available = (+ h.policy.quantity + h.imported
                        - h.released - source_allocated)
                target_allocated = th.exported - th.regained
                target_available = (+ th.policy.quantity + th.imported
                        - th.released - target_allocated)

                reason = 'REJECT:' + reason[-121:]
                self._log_provision(c, h, th, pv, log_time, reason)
                h.save()
                th.save()
                pv.delete()

        return

    def get_pending_commissions(self, context={}, clientkey=None):
        pending = Commission.objects.filter(clientkey=clientkey)
        return pending

    def resolve_pending_commissions(self,   context={}, clientkey=None,
                                            max_serial=None, accept_set=()  ):
        accept_set = set(accept_set)
        pending = self.get_pending_commissions(clientkey=clientkey)
        pending = sorted(pending)

        accept = self.accept_commission
        reject = self.reject_commission

        for serial in pending:
            if serial > max_serial:
                break

            if serial in accept_set:
                accept(clientkey=clientkey, serial=serial)
            else:
                reject(clientkey=clientkey, serial=serial)

        return

    def release_entity(self, context={}, release_entity=()):
        rejected = []
        append = rejected.append
        for entity, key in release_entity:
            try:
                e = Entity.objects.get(entity=entity, key=key)
            except Entity.DoesNotExist:
                append(entity)
                continue

            if e.entities.count() != 0:
                append(entity)
                continue

            if e.holdings.count() != 0:
                append(entity)
                continue

            e.delete()

        return rejected

    def get_timeline(self, context={}, after="", before="Z", entities=()):
        entity_set = set()
        add = entity_set.add

        for entity, key in entities:
            try:
                e = Entity.objects.get(entity=entity, key=key)
                add(entity)
            except Entity.DoesNotExist:
                continue

        chunk_size = 65536
        nr = 0
        timeline = []
        extend = timeline.extend
        filterlogs = ProvisionLog.objects.filter
        if entity_set:
            q_entity = Q(source__in = entity_set) | Q(target__in = entity_set)
        else:
            q_entity = Q()

        while 1:
            logs = filterlogs(  q_entity,
                                issue_time__gt      =   after,
                                issue_time__lte     =   before,
                                reason__startswith  =   'ACCEPT:'   )

            logs = logs.order_by('issue_time')
            logs = logs.values()
            logs = logs[:chunk_size]
            nr += len(logs)
            if not logs:
                break
            extend(logs)
            after = logs[-1]['issue_time']
            if after >= before:
                break

        return timeline


API_Callpoint = QuotaholderDjangoDBCallpoint

