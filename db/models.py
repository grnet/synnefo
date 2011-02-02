# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

import datetime

import vocabs

ganeti_prefix_id = settings.GANETI_PREFIX_ID


class Limit(models.Model):
    description = models.CharField(max_length=45)
    
    class Meta:
        verbose_name = u'User limit'
    
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
    
    def charge_credits(self, cost):
        """Reduce user credits for the specified cost. 
        Returns amount of credits remaining. Negative if the user surpassed his limit."""
        self.credit = self.credit - cost
        rcredit = self.credit
                
        if self.credit < 0:
            self.credit = 0
        
        return rcredit        
    
    def allocate_credits(self):
        """Allocate credits. Add monthly rate to user credit reserve."""
        self.credit = self.credit + self.monthly_rate
        
        # ensure that the user has not more credits than his quota
        if self.credit > self.quota:
            self.credit = self.quota

class UserLimit(models.Model):
    user = models.ForeignKey(OceanUser)
    limit = models.ForeignKey(Limit)
    value = models.IntegerField()
    
    class Meta:
        unique_together = ('user', 'limit')
        verbose_name = u'Enforced limit for user'
    
    def __unicode__(self):
        return u'Limit %s for user %s: %d' % (self.limit, self.user, self.value)


class Flavor(models.Model):
    cpu = models.IntegerField(default=0)
    ram = models.IntegerField(default=0)
    disk = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = u'Virtual machine flavor'
            
    def _get_name(self):
        return u'C%dR%dD%d' % ( self.cpu, self.ram, self.disk )

    name = property(_get_name)

    def __unicode__(self):
        return self.name


class FlavorCostHistory(models.Model):
    cost_active = models.PositiveIntegerField()
    cost_inactive = models.PositiveIntegerField()
    effective_from = models.DateField()
    flavor = models.ForeignKey(Flavor)
    
    class Meta:
        verbose_name = u'Pricing history for flavors'
    
    def __unicode__(self):
        return u'Costs (up, down)=(%d, %d) for %s since %s' % ( cost_active, cost_inactive, flavor.name, effective_from )


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
        verbose_name = u'Virtual machine instance'
        get_latest_by = 'created'
    
    def __unicode__(self):
        return self.name

    def _get_ganeti_id(self):
        """Returns the ganeti id for this VM by prepending ganeti-prefix."""
        return '%s%s' % (ganeti_prefix_id, str(self.id))

    ganeti_id = property(_get_ganeti_id)
    
    def id_from_instance_name(name):
        """ Returns VirtualMachine's Django id, given a ganeti machine name.

        Strips the ganeti prefix atm. Needs a better name!
        """
        return '%s' % (str(name).strip(ganeti_prefix_id))

class VirtualMachineMetadata(models.Model):
    meta_key = models.CharField(max_length=50)
    meta_value = models.CharField(max_length=500)
    vm = models.ForeignKey(VirtualMachine)
    
    class Meta:
        verbose_name = u'Key-value pair of metadata for a VM.'
    
    def __unicode__(self):
        return u'%s, %s for %s' % ( self.key, self.value, self.vm.name )


class AccountingLog(models.Model):
    vm = models.ForeignKey(VirtualMachine)
    date = models.DateTimeField()
    state = models.CharField(choices=vocabs.STATES, max_length=30)
    
    class Meta:
        verbose_name = u'Accounting log'

    def __unicode__(self):
        return u'%s %s %s' % ( self.vm.name, self.date, self.state )


class Image(models.Model):
    name = models.CharField(max_length=255, help_text=_('description'))
    updated = models.DateTimeField(help_text=_("Image update date"))
    created = models.DateTimeField(help_text=_("Image creation date"), default=datetime.datetime.now)
    state = models.CharField(choices=vocabs.STATES, max_length=30)
    description = models.TextField(help_text=_('description'))
    serverid = models.IntegerField(help_text=_('description'))
    vm = models.ForeignKey(VirtualMachine)
    
    class Meta:
        verbose_name = u'Image'

    def __unicode__(self):
        return u'%s' % ( self.name )
