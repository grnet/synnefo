# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

import datetime

backend_prefix_id = settings.BACKEND_PREFIX_ID

class SynnefoUser(models.Model):
    name = models.CharField('Synnefo Username', max_length=255)
    credit = models.IntegerField('Credit Balance')
    created = models.DateTimeField('Time of creation', auto_now_add=True)
    updated = models.DateTimeField('Time of last update', auto_now=True)
    user = models.ForeignKey(User)
    violations = models.IntegerField()
    
    class Meta:
        verbose_name = u'Synnefo User'
    
    def __unicode__(self):
        return self.name
    
    def charge_credits(self, cost, start, end):
        """Reduce user credits for specified duration.
        
        Returns amount of credits remaining. Negative if the user has surpassed his limit.
        
        """
        td = end - start
        sec = float(td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / float(10**6)
        
        total_hours = float(sec) / float(60.0*60.0)
        total_cost = float(cost)*total_hours
        
        self.credit = self.credit - round(total_cost)
        
        if self.credit < 0:
            self.violations = self.violations + 1
        else:
            self.violations = 0
                
        return self.credit
    
    def allocate_credits(self):
        """Allocate credits. Add monthly rate to user credit reserve."""
        self.credit = self.credit + self.monthly_rate
        
        # ensure that the user has not more credits than his quota
        limit_quota = self.credit_quota
                
        if self.credit > limit_quota:
            self.credit = limit_quota

    def get_limit(self, limit_name):
        """Returns the limit value for the specified limit"""
        limit_objs = Limit.objects.filter(name=limit_name, user=self)
        
        if len(limit_objs) == 1:
            return limit_objs[0].value
        
        return 0
        
    def _get_credit_quota(self):
        """Internal getter function for credit quota"""
        return self.get_limit('QUOTA_CREDIT')
        
    credit_quota = property(_get_credit_quota)
    
    def _get_monthly_rate(self):
        """Internal getter function for monthly credit issue rate"""
        return self.get_limit('MONTHLY_RATE')
        
    monthly_rate = property(_get_monthly_rate)
    
    def _get_max_violations(self):
        """Internal getter function for maximum number of violations"""
        return self.get_limit('MAX_VIOLATIONS')
        
    max_violations = property(_get_max_violations)


class Image(models.Model):
    # This is WIP, FIXME
    IMAGE_STATES = (
        ('ACTIVE', 'Active'),
        ('SAVING', 'Saving'),
        ('DELETED', 'Deleted')
    )

    name = models.CharField(max_length=255, help_text=_('description'))
    state = models.CharField(choices=IMAGE_STATES, max_length=30)
    description = models.TextField(help_text=_('description'))
    owner = models.ForeignKey(SynnefoUser,blank=True, null=True)
    created = models.DateTimeField('Time of creation', auto_now_add=True)
    updated = models.DateTimeField('Time of last update', auto_now=True)
    sourcevm = models.ForeignKey("VirtualMachine", null=True)

    class Meta:
        verbose_name = u'Image'

    def __unicode__(self):
        return u'%s' % (self.name)

    def get_vmid(self):
        """Returns first Virtual Machine's id, if any
           an Image might be the ForeignKey to one or many VirtualMachines
           we want the vm that created the Image (the first one)
        """
        if self.virtualmachine_set.all():
            return self.virtualmachine_set.all()[0].id
        else:
            return ''

    vm_id = property(get_vmid)


class ImageMetadata(models.Model):
    meta_key = models.CharField(max_length=50)
    meta_value = models.CharField(max_length=500)
    image = models.ForeignKey(Image)
    
    class Meta:
        verbose_name = u'Key-value pair of metadata for an Image.'
    
    def __unicode__(self):
        return u'%s, %s for %s' % (self.meta_key, self.meta_value, self.image.name)


class Limit(models.Model):
    LIMITS = (
        ('QUOTA_CREDIT', 'Maximum number of credits per user'),
        ('MAX_VIOLATIONS', 'Maximum number of credit violation per user'),
        ('MONTHLY_RATE', 'Monthly credit issue rate')
    )
    user = models.ForeignKey(SynnefoUser)
    name = models.CharField(choices=LIMITS, max_length=30, null=False)
    value = models.IntegerField()
    
    class Meta:
        verbose_name = u'Enforced limit for user'
    
    def __unicode__(self):
        return u'Limit %s for user %s: %d' % (self.limit, self.user, self.value)


class Flavor(models.Model):
    cpu = models.IntegerField(default=0, unique=False)
    ram = models.IntegerField(default=0, unique=False)
    disk = models.IntegerField(default=0, unique=False)
    
    class Meta:
        verbose_name = u'Virtual machine flavor'
        unique_together = ("cpu","ram","disk")
            
    def _get_name(self):
        """Returns flavor name (generated)"""
        return u'C%dR%dD%d' % (self.cpu, self.ram, self.disk)

    def _get_cost_inactive(self):
        """Returns the inactive cost for a Flavor (usually only disk usage counts)"""
        self._update_costs()
        return self._cost_inactive

    def _get_cost_active(self):
        """Returns the active cost for a Flavor"""
        self._update_costs()
        return self._cost_active
    
    def _update_costs(self):
        """Update the internal cost_active, cost_inactive variables"""
        if not hasattr(self, '_cost_active'):
            fch_list = FlavorCostHistory.objects.filter(flavor=self).order_by('-effective_from')
            if len(fch_list) > 0:
                fch = fch_list[0]
                self._cost_active = fch.cost_active
                self._cost_inactive = fch.cost_inactive
            else:
                self._cost_active = 0
                self._cost_inactive = 0

    name = property(_get_name)
    cost_active = property(_get_cost_active)
    cost_inactive = property(_get_cost_inactive)

    def __unicode__(self):
        return self.name
    
    def get_price_list(self):
        """Returns the price catalog for this Flavor"""
        fch_list = FlavorCostHistory.objects.filter(flavor=self).order_by('effective_from')
        
        return fch_list
        
    def find_cost(self, the_date):
        """Returns costs (FlavorCostHistory instance) for the specified date (the_date)"""
        rdate = None
        fch_list = self.get_price_list()
        
        for fc in fch_list:
            if the_date > fc.effective_from:
                rdate = fc
            else:
                break
        
        return rdate


class FlavorCostHistory(models.Model):
    cost_active = models.PositiveIntegerField()
    cost_inactive = models.PositiveIntegerField()
    effective_from = models.DateField()
    flavor = models.ForeignKey(Flavor)
    
    class Meta:
        verbose_name = u'Pricing history for flavors'
    
    def __unicode__(self):
        return u'Costs (up, down)=(%d, %d) for %s since %s' % (self.cost_active, self.cost_inactive, flavor.name, self.effective_from)


class VirtualMachine(models.Model):
    # The list of possible actions for a VM
    ACTIONS = (
       ('CREATE', 'Create VM'),
       ('START', 'Start VM'),
       ('STOP', 'Shutdown VM'),
       ('SUSPEND', 'Admin Suspend VM'),
       ('REBOOT', 'Reboot VM'),
       ('DESTROY', 'Destroy VM')
    )
    # The internal operating state of a VM
    OPER_STATES = (
        ('BUILD', 'Queued for creation'),
        ('ERROR', 'Creation failed'),
        ('STOPPED', 'Stopped'),
        ('STARTED', 'Started'),
        ('DESTROYED', 'Destroyed')
    )
    # The list of possible operations on the backend
    BACKEND_OPCODES = (
        ('OP_INSTANCE_CREATE', 'Create Instance'),
        ('OP_INSTANCE_REMOVE', 'Remove Instance'),
        ('OP_INSTANCE_STARTUP', 'Startup Instance'),
        ('OP_INSTANCE_SHUTDOWN', 'Shutdown Instance'),
        ('OP_INSTANCE_REBOOT', 'Reboot Instance')
    )
    # A backend job may be in one of the following possible states
    BACKEND_STATUSES = (
        ('queued', 'request queued'),
        ('waiting', 'request waiting for locks'),
        ('canceling', 'request being canceled'),
        ('running', 'request running'),
        ('canceled', 'request canceled'),
        ('success', 'request completed successfully'),
        ('error', 'request returned error')
    )

    # The operating state of a VM,
    # upon the successful completion of a backend operation.
    OPER_STATE_FROM_OPCODE = {
        'OP_INSTANCE_CREATE': 'STARTED',
        'OP_INSTANCE_REMOVE': 'DESTROYED',
        'OP_INSTANCE_STARTUP': 'STARTED',
        'OP_INSTANCE_SHUTDOWN': 'STOPPED',
        'OP_INSTANCE_REBOOT': 'STARTED'
    }

    # This dictionary contains the correspondence between
    # internal operating states and Server States as defined
    # by the Rackspace API.
    RSAPI_STATE_FROM_OPER_STATE = {
        "BUILD": "BUILD",
        "ERROR": "ERROR",
        "STOPPED": "STOPPED",
        "STARTED": "ACTIVE",
        "DESTROYED": "DELETED"
    }

    name = models.CharField(max_length=255)
    owner = models.ForeignKey(SynnefoUser,blank=True, null=True)
    created = models.DateTimeField('Time of creation', auto_now_add=True)
    updated = models.DateTimeField('Time of last update', auto_now=True)
    charged = models.DateTimeField('Time of last charge', default=datetime.datetime.now())
    # Use string reference to avoid circular ForeignKey def.
    # FIXME: "sourceimage" works, "image" causes validation errors. See "related_name" in the Django docs.
    sourceimage = models.ForeignKey("Image", null=False) 
    hostid = models.CharField(max_length=100)
    description = models.TextField(help_text=_('description'))
    ipfour = models.IPAddressField()
    ipsix = models.CharField(max_length=100)
    flavor = models.ForeignKey(Flavor)
    suspended = models.BooleanField('Administratively Suspended')

    # VM State 
    # The following fields are volatile data, in the sense
    # that they need not be persistent in the DB, but rather
    # get generated at runtime by quering Ganeti and applying
    # updates received from Ganeti.
    #
    # They belong to a separate caching layer, in the long run.
    # [vkoukis] after discussion with [faidon].
    _action = models.CharField(choices=ACTIONS, max_length=30, null=True)
    _operstate = models.CharField(choices=OPER_STATES, max_length=30, null=True)
    _backendjobid = models.PositiveIntegerField(null=True)
    _backendopcode = models.CharField(choices=BACKEND_OPCODES, max_length=30, null=True)
    _backendjobstatus = models.CharField(choices=BACKEND_STATUSES, max_length=30, null=True)
    _backendlogmsg = models.TextField(null=True)

    # Error classes
    class InvalidBackendIdError(Exception):
         def __init__(self, value):
            self.value = value
         def __str__(self):
            return repr(self.value)

    class InvalidBackendMsgError(Exception):
         def __init__(self, opcode, status):
            self.opcode = opcode
            self.status = status
         def __str__(self):
            return repr("<opcode: %s, status: %s>" % (str(self.opcode), str(self.status)))

    class InvalidActionError(Exception):
         def __init__(self, action):
            self._action = action
         def __str__(self):
            return repr(str(self._action))

    @staticmethod
    def id_from_instance_name(name):
        """Returns VirtualMachine's Django id, given a ganeti machine name.

        Strips the ganeti prefix atm. Needs a better name!
        
        """
        if not str(name).startswith(backend_prefix_id):
            raise VirtualMachine.InvalidBackendIdError(str(name))
        ns = str(name).lstrip(backend_prefix_id)
        if not ns.isdigit():
            raise VirtualMachine.InvalidBackendIdError(str(name))
        return int(ns)

    def __init__(self, *args, **kw):
        """Initialize state for just created VM instances."""
        super(VirtualMachine, self).__init__(*args, **kw)
        # Before this instance gets save()d
        if not self.pk: 
            self._action = None
            self._operstate = "BUILD"
            self._backendjobid = None
            self._backendjobstatus = None
            self._backendopcode = None
            self._backendlogmsg = None

    def process_backend_msg(self, jobid, opcode, status, logmsg):
        """Process a job progress notification from the backend.

        Process an incoming message from the backend (currently Ganeti).
        Job notifications with a terminating status (sucess, error, or canceled),
        also update the operating state of the VM.

        """
        if (opcode not in [x[0] for x in VirtualMachine.BACKEND_OPCODES] or
           status not in [x[0] for x in VirtualMachine.BACKEND_STATUSES]):
            raise VirtualMachine.InvalidBackendMsgError(opcode, status)

        self._backendjobid = jobid
        self._backendjobstatus = status
        self._backendopcode = opcode
        self._backendlogmsg = logmsg

        # Notifications of success change the operating state
        if status == 'success':
            self._operstate = VirtualMachine.OPER_STATE_FROM_OPCODE[opcode]
        # Special cases OP_INSTANCE_CREATE fails --> ERROR
        if status in ('canceled', 'error') and opcode == 'OP_INSTANCE_CREATE':
            self._operstate = 'ERROR'
        # Any other notification of failure leaves the operating state unchanged

        self.save()

    def start_action(self, action):
        """Update the state of a VM when a new action is initiated."""
        if not action in [x[0] for x in VirtualMachine.ACTIONS]:
            raise VirtualMachine.InvalidActionError(action)

        self._action = action
        self._backendjobid = None
        self._backendopcode = None
        self._backendlogmsg = None
        
        self.save()

    # FIXME: Perhaps move somewhere else, outside the model?
    def _get_rsapi_state(self):
        try:
            return VirtualMachine.RSAPI_STATE_FROM_OPER_STATE[self._operstate]
        except KeyError:
            return "UNKNOWN"

    rsapi_state = property(_get_rsapi_state)

    def _get_backend_id(self):
        """Returns the backend id for this VM by prepending backend-prefix."""
        return '%s%s' % (backend_prefix_id, str(self.id))

    backend_id = property(_get_backend_id)

    class Meta:
        verbose_name = u'Virtual machine instance'
        get_latest_by = 'created'
    
    def __unicode__(self):
        return self.name

    def get_accounting_logs(self):
        """Returns all AcountingLog records after the charged field"""
        acc_logs = AccountingLog.objects.filter(date__gte=self.charged, vm=self)
        if len(acc_logs) == 0:
            return []
            
        return acc_logs


class VirtualMachineGroup(models.Model):
    """Groups of VMs for SynnefoUsers"""
    name = models.CharField(max_length=255)
    created = models.DateTimeField('Time of creation', auto_now_add=True)
    updated = models.DateTimeField('Time of last update', auto_now=True)
    owner = models.ForeignKey(SynnefoUser)
    machines = models.ManyToManyField(VirtualMachine)

    class Meta:
        verbose_name = u'Virtual Machine Group'
        verbose_name_plural = 'Virtual Machine Groups'
        ordering = ['name']
    
    def __unicode__(self):
        return self.name


class VirtualMachineMetadata(models.Model):
    meta_key = models.CharField(max_length=50)
    meta_value = models.CharField(max_length=500)
    vm = models.ForeignKey(VirtualMachine)
    
    class Meta:
        verbose_name = u'Key-value pair of metadata for a VM.'
    
    def __unicode__(self):
        return u'%s, %s for %s' % (self.meta_key, self.meta_value, self.vm.name)


class AccountingLog(models.Model):
    vm = models.ForeignKey(VirtualMachine)
    date = models.DateTimeField()
    state = models.CharField(choices=VirtualMachine.OPER_STATES, max_length=30)
    
    class Meta:
        verbose_name = u'Accounting log'

    def __unicode__(self):
        return u'%s - %s - %s' % (self.vm.name, str(self.date), self.state)
    
    @staticmethod   
    def get_log_entries(vm_obj, date_from):
        """Returns log entries for the specified vm after a date"""
        entries = AccountingLog.objects.filter(vm=vm_obj).filter(date__gte=date_from).order_by('-date')
    
        return entries


class Disk(models.Model):
    name = models.CharField(max_length=255)
    created = models.DateTimeField('Time of creation', auto_now_add=True)
    updated = models.DateTimeField('Time of last update', auto_now=True)
    size = models.PositiveIntegerField('Disk size in GBs')
    vm = models.ForeignKey(VirtualMachine, blank=True, null=True)
    owner = models.ForeignKey(SynnefoUser, blank=True, null=True)  

    class Meta:
        verbose_name = u'Disk instance'

    def __unicode__(self):
        return self.name
