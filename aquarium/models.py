# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8

from django.db import models
from django.contrib.auth.models import User

class Limit(models.Model):
    description = models.CharField(max_length=45)

    def __unicode__(self):
        return self.description

class OceanUser(models.Model):
    name = models.CharField(max_length=255)
    credit = models.IntegerField()
    quota = models.IntegerField()
    created = models.DateField()
    monthly_rate = models.IntegerField()
    user = models.ForeignKey(User, unique=True)    
    limits = models.ManyToManyField(Limit, through='UserLimit')

    def __unicode__(self):
        return self.name

class UserLimit(models.Model):
    user = models.ForeignKey(OceanUser)
    limit = models.ForeignKey(Limit)
    value = models.IntegerField()

    class Meta:
        unique_together = ('user', 'limit')

    def __unicode__(self):
        return u'Limit %s for user %s: %d' % (self.limit, self.user, self.value)


class Flavor(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.CharField(max_length=1000)
    cost_active = models.PositiveIntegerField()
    cost_inactive = models.PositiveIntegerField()

    def __unicode__(self):
        return self.name

class VirtualMachine(models.Model):
    STATES = (
            (0, 'VM_STOPPED'),
            (1, 'VM_RUNNING'),
            (2, 'VM_PAUSED'),
            (3, 'VM_INTERNAL'),
            # FIXME
    )

    name = models.CharField(max_length=255)
    created = models.DateTimeField()
    state = models.IntegerField(choices=STATES, default=0)
    started = models.DateTimeField()
    vmid = models.IntegerField()
    imageid = models.IntegerField()
    hostid = models.CharField(max_length=100)
    server_label = models.CharField(max_length=100)
    image_version = models.CharField(max_length=100)
    owner = models.ForeignKey(OceanUser)
    flavor = models.ForeignKey(Flavor)

    class Meta:
        verbose_name = u'Virtual machine'
        get_latest_by = 'created'

    def __unicode__(self):
        return self.name

class VirtualMachineAddress(models.Model):
    ipfour = models.CharField(max_length=15)
    ipsix = models.CharField(max_length=100)
    public = models.BooleanField()
    vmachine = models.ForeignKey(VirtualMachine)
	
    class Meta:
        verbose_name = u'Virtual Machine Network Address'
        
    def __unicode__(self):
        return u'%s address for vm named' % ( self.ipfour, self.vm_id.name )

class ChargingLog(models.Model):
    vm = models.ForeignKey(VirtualMachine)
    date = models.DateTimeField()
    credit = models.IntegerField()
    message = models.CharField(max_length=1000)

    class Meta:
        verbose_name = u'Charging log'
