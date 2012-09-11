
from commissioning import ( Callpoint, Controller,
                            Physical, CommissionException,
                            CorruptedError, InvalidDataError,
                            InvalidKeyError, NoEntityError,
                            NoQuantityError, NoCapacityError    )


from django.db.models import Model, BigIntegerField, CharField, ForeignKey
from django.db import transaction


class Holder(Model):

    attribute   =   CharField(max_length=72, primary_key=True)
    intval      =   BigIntegerField()
    strval      =   CharField(max_length=72)


def alloc_serial(nr=1):
    if nr < 0:
        m = "Can only receive a positive argument, not %d" % (nr,)
        raise CorruptedError(m)

    try:
        holder = Holder.objects.get(attribute='serial')
    except Holder.DoesNotExist:
        holder = Holder(attribute='serial', inval=1)

    serial = holder.serial
    holder.serial += nr
    holder.save()

    return serial


class Entity(Model):

    entity      =   CharField(max_length=72, primary_key=True)
    owner       =   ForeignKey('self', to_field='entity',
                               related_name='entities')
    key         =   CharField(max_length=72, null=False)


class Policy(Model):

    policy          =   CharField(max_length=72, primary_key=True)
    quantity        =   BigIntegerField(null=False, default=0)
    capacity        =   BigIntegerField(null=False, default=0)
    import_limit    =   BigIntegerField(null=False, default=0)
    export_limit    =   BigIntegerField(null=False, default=0)


class Holding(Model):

    entity      =   ForeignKey(Entity, to_field='entity')
    resource    =   CharField(max_length=72, null=False)

    policy      =   ForeignKey(Policy, to_field='policy')
    flags       =   BigIntegerField(null=False, default=0)

    imported    =   BigIntegerField(null=False, default=0)
    importing   =   BigIntegerField(null=False, default=0)
    exported    =   BigIntegerField(null=False, default=0)
    exporting   =   BigIntegerField(null=False, default=0)
    regained    =   BigIntegerField(null=False, default=0)
    regaining   =   BigIntegerField(null=False, default=0)
    released    =   BigIntegerField(null=False, default=0)
    releasing   =   BigIntegerField(null=False, default=0)

    class Meta:
        unique_together = (('entity', 'resource'),)


from datetime import datetime

def now():
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:24]


class Commission(Model):

    serial      =   BigIntegerField(primary_key=True, default=alloc_serial)
    entity      =   ForeignKey(Entity, to_field='entity')
    clientkey   =   CharField(max_length=72, null=False)
    issue_time  =   CharField(max_length=24, default=now)


class Provision(Model):

    serial      =   ForeignKey( Commission,
                                to_field='serial',
                                related_name='provisions'   )

    entity      =   ForeignKey(Entity, to_field='entity')
    resource    =   CharField(max_length=72, null=False)
    quantity    =   BigIntegerField(null=False)


class ProvisionLog(Model):

    serial              =   BigIntegerField(primary_key=True)
    source              =   CharField(max_length=72)
    target              =   CharField(max_length=72)
    issue_time          =   CharField(max_length=24)
    log_time            =   CharField(max_length=24)
    resource            =   CharField(max_length=72)
    source_available    =   BigIntegerField()
    source_allocated    =   BigIntegerField()
    target_available    =   BigIntegerField()
    target_allocated    =   BigIntegerField()
    delta_quantity      =   BigIntegerField()
    reason              =   CharField(max_length=128)

