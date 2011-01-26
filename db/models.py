# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8

from django.db import models
from django.contrib.auth.models import User
import vocabs

class Limit(models.Model):
    description = models.CharField(max_length=45)
    
    class Meta:
        verbose_name = u'Available limits for users'
    
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
    
    class Meta:
        verbose_name = u'Ocean User'
    
    def __unicode__(self):
        return self.name


class UserLimit(models.Model):
    user = models.ForeignKey(OceanUser)
    limit = models.ForeignKey(Limit)
    value = models.IntegerField()
    
    class Meta:
        unique_together = ('user', 'limit')
        verbose_name = u'Enforced limits for each user'
    
    def __unicode__(self):
        return u'Limit %s for user %s: %d' % (self.limit, self.user, self.value)


class Flavor(models.Model):
    cpu = models.IntegerField(default=0)
    ram = models.IntegerField(default=0)
    disk = models.IntegerField(default=0)
    cost_active = models.PositiveIntegerField()
    cost_inactive = models.PositiveIntegerField()
    
    class Meta:
        verbose_name = u'Virtual Machine flavors'
    
    def _get_name(self):
        return u'c%dr%dd%d' % ( self.cpu, self.ram, self.disk )

    name = property(_get_name)

    def __unicode__(self):
        return self.name


class VirtualMachine(models.Model):
    name = models.CharField(max_length=255)
    created = models.DateTimeField()
    state = models.CharField(choices=vocabs.STATES, max_length=30)
    charged = models.DateTimeField()
    imageid = models.IntegerField()
    hostid = models.CharField(max_length=100)
    server_label = models.CharField(max_length=100)
    image_version = models.CharField(max_length=100)
    ipfour = models.IPAddressField()
    ipsix = models.CharField(max_length=100)
    owner = models.ForeignKey(OceanUser)
    flavor = models.ForeignKey(Flavor)
    
    class Meta:
        verbose_name = u'Virtual machine instances'
        get_latest_by = 'created'
    
    def __unicode__(self):
        return self.name


class VirtualMachineMetadata(models.Model):
    meta_key = models.CharField(max_length=50)
    meta_value = models.CharField(max_length=500)
    vm = models.ForeignKey(VirtualMachine)
    
    class Meta:
        verbose_name = u'Metadata for virtual machine instances'
    
    def __unicode__(self):
        return u'%s, %s for %s' % ( self.key, self.value, self.vm.name )


class AccountingLog(models.Model):
    vm = models.ForeignKey(VirtualMachine)
    date = models.DateTimeField()
    state = models.CharField(choices=vocabs.STATES, max_length=30)
    
    class Meta:
        verbose_name = u'Charging log'

	def __unicode__(self):
		return u'%s %s %s' % ( self.vm.name, self.date, self.state )
