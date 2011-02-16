# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

import datetime

backend_prefix_id = settings.BACKEND_PREFIX_ID

class Limit(models.Model):
    description = models.CharField(max_length=45)
    
    class Meta:
        verbose_name = u'User limit'
    
    def __unicode__(self):
        return self.description


class SynnefoUser(models.Model):
    name = models.CharField(max_length=255)
    credit = models.IntegerField()
    quota = models.IntegerField()
    created = models.DateField()
    monthly_rate = models.IntegerField()
    user = models.ForeignKey(User)
    limits = models.ManyToManyField(Limit, through='UserLimit')
    violations = models.IntegerField()
    max_violations = models.IntegerField(default=3)
    
    class Meta:
        verbose_name = u'Synnefo User'
    
    def __unicode__(self):
        return self.name
    
    def charge_credits(self, cost, start, end):
        """Reduce user credits for specified duration. 
        Returns amount of credits remaining. Negative if the user surpassed his limit."""
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
        if self.credit > self.quota:
            self.credit = self.quota


class Image(models.Model):
    # This is WIP, FIXME
    IMAGE_STATES = (
                ('ACTIVE', 'Active'),
                ('SAVING', 'Saving'),
                ('DELETED', 'Deleted')
    )

    name = models.CharField(max_length=255, help_text=_('description'))
    updated = models.DateTimeField(help_text=_("Image update date"))
    created = models.DateTimeField(help_text=_("Image creation date"), default=datetime.datetime.now())
    state = models.CharField(choices=IMAGE_STATES, max_length=30)
    description = models.TextField(help_text=_('description'))
    owner = models.ForeignKey(SynnefoUser,blank=True, null=True)
    #FIXME: ImageMetadata, as in VirtualMachineMetadata
    #       "os" contained in metadata. Newly created Server inherits value of "os" metadata key from Image.
    #       The Web UI uses the value of "os" to determine the icon to use.

    class Meta:
        verbose_name = u'Image'

    def __unicode__(self):
        return u'%s' % (self.name)

    def get_vmid(self):
        """Returns first Virtual Machine's id, if any"""
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


class UserLimit(models.Model):
    user = models.ForeignKey(SynnefoUser)
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
        """Returns flavor name"""
        return u'C%dR%dD%d' % (self.cpu, self.ram, self.disk)

    def _get_cost_inactive(self):
        self._update_costs()
        return self._cost_inactive

    def _get_cost_active(self):
        self._update_costs()
        return self._cost_active
    
    def _update_costs(self):
        # if _cost_active is not defined, then define it!
        if '_cost_active' not in dir(self):
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
        fch_list = FlavorCostHistory.objects.filter(flavor=self).order_by('effective_from')
        
        return fch_list            


class FlavorCostHistory(models.Model):
    cost_active = models.PositiveIntegerField()
    cost_inactive = models.PositiveIntegerField()
    effective_from = models.DateField()
    flavor = models.ForeignKey(Flavor)
    
    class Meta:
        verbose_name = u'Pricing history for flavors'
    
    def __unicode__(self):
        return u'Costs (up, down)=(%d, %d) for %s since %s' % (self.cost_active, self.cost_inactive, flavor.name, self.effective_from)
        
    @staticmethod
    def find_cost(fch_list, dat):
        rdate = fch_list[0]

        for fc in fch_list:
            if dat > fc.effective_from:
                rdate = fc
        
        return rdate


class VirtualMachine(models.Model):
    ACTIONS = (
       ('CREATE', 'Create VM'),
       ('START', 'Start VM'),
       ('STOP', 'Shutdown VM'),
       ('SUSPEND', 'Admin Suspend VM'),
       ('REBOOT', 'Reboot VM'),
       ('DESTROY', 'Destroy VM')
    )

    OPER_STATES = (
        ('BUILD', 'Queued for creation'),
        ('ERROR', 'Creation failed'),
        ('STOPPED', 'Stopped'),
        ('STARTED', 'Started'),
        ('DESTROYED', 'Destroyed')
    )

    BACKEND_OPCODES = (
        ('OP_INSTANCE_CREATE', 'Create Instance'),
        ('OP_INSTANCE_REMOVE', 'Remove Instance'),
        ('OP_INSTANCE_STARTUP', 'Startup Instance'),
        ('OP_INSTANCE_SHUTDOWN', 'Shutdown Instance'),
        ('OP_INSTANCE_REBOOT', 'Reboot Instance')
    )

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

    RSAPI_STATE_FROM_OPER_STATE = {
        "BUILD": "BUILD",
        "ERROR": "ERROR",
        "STOPPED": "STOPPED",
        "STARTED": "ACTIVE",
        "DESTROYED": "DELETED"
    }

    name = models.CharField(max_length=255)
    created = models.DateTimeField(help_text=_('VM creation date'), default=datetime.datetime.now())
    charged = models.DateTimeField()
    # Use string reference to avoid circular ForeignKey def.
    # FIXME: "sourceimage" works, "image" causes validation errors. See "related_name" in the Django docs.
    sourceimage = models.ForeignKey(Image, null=False) 
    hostid = models.CharField(max_length=100)
    description = models.TextField(help_text=_('description'))
    ipfour = models.IPAddressField()
    ipsix = models.CharField(max_length=100)
    flavor = models.ForeignKey(Flavor)
    suspended = models.BooleanField('Administratively Suspended')

    # VM State [volatile data]
    updated = models.DateTimeField(null=True)
    action = models.CharField(choices=ACTIONS, max_length=30, null=True)
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
            self.__action = action
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
            self.updated = datetime.datetime.now()
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

        # FIXME: Should be implemented in a pre-save signal handler.
        self.updated = datetime.datetime.now()
        self.save()

    def start_action(self, action):
        """Update the state of a VM when a new action is initiated."""
        if not action in [x[0] for x in VirtualMachine.ACTIONS]:
            raise VirtualMachine.InvalidActionError(action)

        self._action = action
        self._backendjobid = None
        self._backendopcode = None
        self._backendlogmsg = None
        self.updated = datetime.datetime.now()
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


class VirtualMachineGroup(models.Model):
    "Groups of VM's for SynnefoUsers"
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(SynnefoUser)
    machines = models.ManyToManyField(VirtualMachine)
    created = models.DateTimeField(help_text=_("Group creation date"), default=datetime.datetime.now())

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

