
from commissioning import ( QuotaholderAPI,
                            Callpoint, CommissionException,
                            CorruptedError, InvalidDataError,
                            InvalidKeyError, NoEntityError,
                            NoQuantityError, NoCapacityError    )


from django.db.models import Model, BigIntegerField, CharField, ForeignKey
from django.db import transaction
from .models import Holder, Entity, Policy, Holding, Commission, Provision


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

    @classmethod
    def http_exception(cls, exc):
        if not isinstance(exc, CommissionException):
            raise exc

        body = str(exc.args)
        status = cls.http_exc_lookup.get(type(exc), 400)
        return status, body

    def create_entity(self, context={}, create_entity=()):
        rejected = []
        append = rejected.append

        for entity, owner, key, ownerkey in create_entity:
            try:
                owner = Entity.objects.get(entity=owner, key=ownerkey)
            except Entity.DoesNotExist:
                append(entity)

            Entity.objects.create(entity=entity, owner=owner, key=key)

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

            append((h.entity, h.resource, h.policy,
                    h.imported, h.exported, h.flags))

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

        holdings = e.holdings.filter(entity=entity)
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
                    h.imported, h.exported, h.flags))

        return quotas

    def set_quota(self, context={}, set_quota=()):
        rejected = []
        append = rejected.append

        for (   entity, resource, key,
                quantity, capacity,
                import_limit, export_limit, flags  ) in set_quota:

                try:
                    h = Holding.objects.get(entity=entity, resource=resource)
                    if h.entity.key != key:
                        append((entity, resource))
                        continue
                except Holding.DoesNotExist:
                    append(entity, resource)

                p = h.policy
                policy = newname()
                newp = Policy.objects.create    (
                            policy=policy,
                            quantity=quantity,
                            capacity=capacity,
                            import_limit=import_limit,
                            export_limit=export_limit
                )

                h.policy = newp
                h.save()

                if p.holdings.count() == 0:
                    p.delete()

        return rejected

    def issue_commission(self,  context={}, clientkey=None,
                                target=None, key=None,
                                owner=None, ownerkey=None,
                                provisions=()               ):

        try:
            t = Entity.objects.get(entity=target)
        except Entity.DoesNotExist:
            create_entity = ((entity, owner, key, ownerkey),)
            rejected = self.create_entity(  context=context,
                                            create_entity=create_entity )
            if rejected:
                raise NoEntityError("No target entity '%s'" % (target,))

            t = Entity.objects.get(entity=target)
        else:
            if t.key != key:
                m = "Invalid key for target entity '%s'" % (target,)
                raise InvalidKeyError(m)

        commission = Commission.objects.create( entity=target,
                                                clientkey=clientkey )
        serial = commission.serial

        for entity, resource, quantity in provisions:
            try:
                h = Holding.objects.get(entity=entity, resource=resource)
            except Holding.DoesNotExist:
                m = ("There is not enough quantity "
                     "to allocate from in %s.%s" % (entity, resource))
                raise NoQuantityError(m)

            hp = h.policy

            if h.importing - h.exported + hp.quantity - quantity < 0:
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

            if (    th.exported - th.importing - tp.quantity
                    + tp.capacity - quantity                ) < 0:

                    m = ("There is not enough capacity "
                         "to allocate into in %s.%s" % (target, resource))
                    raise NoCapacityError(m)

            Provision.objects.create(   serial=serial,
                                        entity=entity,
                                        resource=resource,
                                        quantity=quantity   )

            h.exporting += quantity
            th.importing += quantity

            h.save()
            th.save()

        return serial

    def accept_commission(self, context={}, clientkey=None, serial=None):
        try:
            c = Commission.objects.get(clientkey=clientkey, serial=serial)
        except Commission.DoesNotExist:
            return

        t = c.entity

        provisions = Provision.objects.filter(  clientkey=clientkey,
                                                serial=serial       )
        for pv in provisions:
            pv.entity,
            pv.resource
            try:
                h = Holding.objects.get(entity=pv.entity.entity,
                                        resource=pv.resource    )
                th = Holding.objects.get(entity=t, resource=pv.resource)
            except Holding.DoesNotExist:
                m = "Corrupted provision"
                raise CorruptedError(m)

            h.exported += pv.quantity
            th.imported += pv.quantity
            h.save()
            th.save()
            pv.delete()

        return

    def reject_commission(self, context={}, clientkey=None, serial=None):
        try:
            c = Commission.objects.get(clientkey=clientkey, serial=serial)
        except Commission.DoesNotExist:
            return

        t = c.entity

        provisions = Provision.objects.filter(  clientkey=clientkey,
                                                serial=serial       )
        for pv in provisions:
            pv.entity,
            pv.resource
            try:
                h = Holding.objects.get(entity=pv.entity.entity,
                                        resource=pv.resource    )
                th = Holding.objects.get(entity=t, resource=pv.resource)
            except Holding.DoesNotExist:
                m = "Corrupted provision"
                raise CorruptedError(m)

            h.exporting -= pv.quantity
            th.importing -= pv.quantity
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

API_Callpoint = QuotaholderDjangoDBCallpoint
