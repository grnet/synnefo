# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8

from django.conf import settings
from django.db import models

import datetime

class SynnefoUser(models.Model):

    #TODO: Amend this when we have groups
    ACCOUNT_TYPE = (
        ('STUDENT', 'Student'),
        ('PROFESSOR', 'Professor')
    )

    name = models.CharField('Synnefo Username', max_length=255, default='')
    realname = models.CharField('Real Name', max_length=255, default='')
    uniq = models.CharField('External Unique ID', max_length=255,null=True)
    credit = models.IntegerField('Credit Balance')
    auth_token = models.CharField('Authentication Token', max_length=32, null=True)
    auth_token_created = models.DateTimeField('Time of auth token creation', auto_now_add=True)
    type = models.CharField('Current Image State', choices=ACCOUNT_TYPE, max_length=30)
    created = models.DateTimeField('Time of creation', auto_now_add=True)
    updated = models.DateTimeField('Time of last update', auto_now=True)

    class Meta:
        verbose_name = u'Synnefo User'

    def __unicode__(self):
        return self.name

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
    
    def _get_min_credits(self):
        """Internal getter function for maximum number of violations"""
        return self.get_limit('MIN_CREDITS')
        
    min_credits = property(_get_min_credits)


class Image(models.Model):
    # This is WIP, FIXME
    IMAGE_STATES = (
        ('ACTIVE', 'Active'),
        ('SAVING', 'Saving'),
        ('DELETED', 'Deleted')
    )

    name = models.CharField('Image name', max_length=255)
    state = models.CharField('Current Image State', choices=IMAGE_STATES, max_length=30)
    owner = models.ForeignKey(SynnefoUser, blank=True, null=True)
    created = models.DateTimeField('Time of creation', auto_now_add=True)
    updated = models.DateTimeField('Time of last update', auto_now=True)
    sourcevm = models.ForeignKey("VirtualMachine", null=True)

    class Meta:
        verbose_name = u'Image'

    def __unicode__(self):
        return u'%s' % ( self.name, )


class ImageMetadata(models.Model):
    meta_key = models.CharField('Image metadata key name', max_length=50)
    meta_value = models.CharField('Image metadata value', max_length=500)
    image = models.ForeignKey(Image)
    
    class Meta:
        verbose_name = u'Key-value pair of Image metadata.'
    
    def __unicode__(self):
        return u'%s, %s for %s' % (self.meta_key, self.meta_value, self.image.name)


class Limit(models.Model):
    LIMITS = (
        ('QUOTA_CREDIT', 'Maximum amount of credits per user'),
        ('MIN_CREDITS', 'Minimum amount of credits per user'),
        ('MONTHLY_RATE', 'Monthly credit issue rate')
    )
    user = models.ForeignKey(SynnefoUser)
    name = models.CharField('Limit key name', choices=LIMITS, max_length=30, null=False)
    value = models.IntegerField('Limit current value')
    
    class Meta:
        verbose_name = u'Enforced limit for user'
    
    def __unicode__(self):
        return u'Limit %s for user %s: %d' % (self.value, self.user, self.value)


class Flavor(models.Model):
    cpu = models.IntegerField('Number of CPUs', default=0)
    ram = models.IntegerField('Size of RAM', default=0)             # Size in MiB
    disk = models.IntegerField('Size of Disk space', default=0)     # Size in GiB
    
    class Meta:
        verbose_name = u'Virtual machine flavor'
        unique_together = ("cpu","ram","disk")
            
    def _get_name(self):
        """Returns flavor name (generated)"""
        return u'C%dR%dD%d' % (self.cpu, self.ram, self.disk)

    def _current_cost(self, active):
        """Returns active/inactive cost value

        set active = True to get active cost and False for the inactive.

        """
        fch_list = FlavorCost.objects.filter(flavor=self).order_by('-effective_from')
        if len(fch_list) > 0:
            if active:
                return fch_list[0].cost_active
            else:
                return fch_list[0].cost_inactive

        return 0

    def _current_cost_active(self):
        """Returns current active cost (property method)"""
        return self._current_cost(True)

    def _current_cost_inactive(self):
        """Returns current inactive cost (property method)"""
        return self._current_cost(False)

    name = property(_get_name)
    current_cost_active = property(_current_cost_active)
    current_cost_inactive = property(_current_cost_inactive)

    def __unicode__(self):
        return self.name


class FlavorCost(models.Model):
    cost_active = models.PositiveIntegerField('Active Cost')
    cost_inactive = models.PositiveIntegerField('Inactive Cost')
    effective_from = models.DateTimeField()
    flavor = models.ForeignKey(Flavor)
    
    class Meta:
        verbose_name = u'Pricing history for flavors'
    
    def __unicode__(self):
        return u'Costs (up, down)=(%d, %d) for %s since %s' % (int(self.cost_active), int(self.cost_inactive), self.flavor.name, self.effective_from)


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
        ('OP_INSTANCE_REBOOT', 'Reboot Instance'),

        # These are listed here for completeness,
        # and are ignored for the time being
        ('OP_INSTANCE_SET_PARAMS', 'Set Instance Parameters'),
        ('OP_INSTANCE_QUERY_DATA', 'Query Instance Data'),
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
        'OP_INSTANCE_REBOOT': 'STARTED',
        'OP_INSTANCE_SET_PARAMS': None,
        'OP_INSTANCE_QUERY_DATA': None
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

    name = models.CharField('Virtual Machine Name', max_length=255)
    owner = models.ForeignKey(SynnefoUser)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    charged = models.DateTimeField(default=datetime.datetime.now())
    sourceimage = models.ForeignKey("Image", null=False) 
    hostid = models.CharField(max_length=100)
    flavor = models.ForeignKey(Flavor)
    deleted = models.BooleanField('Deleted', default=False)
    suspended = models.BooleanField('Administratively Suspended', default=False)

    # VM State 
    # The following fields are volatile data, in the sense
    # that they need not be persistent in the DB, but rather
    # get generated at runtime by quering Ganeti and applying
    # updates received from Ganeti.
    
    # In the future they could be moved to a separate caching layer
    # and removed from the database.
    # [vkoukis] after discussion with [faidon].
    action = models.CharField(choices=ACTIONS, max_length=30, null=True)
    operstate = models.CharField(choices=OPER_STATES, max_length=30, null=True)
    backendjobid = models.PositiveIntegerField(null=True)
    backendopcode = models.CharField(choices=BACKEND_OPCODES, max_length=30, null=True)
    backendjobstatus = models.CharField(choices=BACKEND_STATUSES, max_length=30, null=True)
    backendlogmsg = models.TextField(null=True)

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
    
    class DeletedError(Exception):
        pass
    
    class BuildingError(Exception):
        pass
    
    def __init__(self, *args, **kw):
        """Initialize state for just created VM instances."""
        super(VirtualMachine, self).__init__(*args, **kw)
        # This gets called BEFORE an instance gets save()d for
        # the first time.
        if not self.pk: 
            self.action = None
            self.backendjobid = None
            self.backendjobstatus = None
            self.backendopcode = None
            self.backendlogmsg = None
            self.operstate = 'BUILD'

    def _get_backend_id(self):
        """Returns the backend id for this VM by prepending backend-prefix."""
        if not self.id:
            raise VirtualMachine.InvalidBackendIdError("self.id is None")
        return '%s%s' % (settings.BACKEND_PREFIX_ID, str(self.id))

    backend_id = property(_get_backend_id)

    class Meta:
        verbose_name = u'Virtual machine instance'
        get_latest_by = 'created'
    
    def __unicode__(self):
        return self.name


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


class Debit(models.Model):
    when = models.DateTimeField()
    user = models.ForeignKey(SynnefoUser)
    vm = models.ForeignKey(VirtualMachine)
    description = models.TextField()
    
    class Meta:
        verbose_name = u'Accounting log'

    def __unicode__(self):
        return u'%s - %s - %s - %s' % ( self.user.id, self.vm.name, str(self.when), self.description)


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


class Network(models.Model):
    NETWORK_STATES = (
        ('ACTIVE', 'Active'),
        ('DELETED', 'Deleted')
    )
    
    name = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(SynnefoUser, null=True)
    state = models.CharField(choices=NETWORK_STATES, max_length=30)
    public = models.BooleanField(default=False)
    machines = models.ManyToManyField(VirtualMachine, through='NetworkInterface')
    
    def __unicode__(self):
        return self.name


class NetworkInterface(models.Model):
    FIREWALL_PROFILES = (
        ('ENABLED', 'Enabled'),
        ('DISABLED', 'Disabled')
    )
    
    machine = models.ForeignKey(VirtualMachine, related_name='nics')
    network = models.ForeignKey(Network, related_name='nics')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    index = models.IntegerField(null=True)
    mac = models.CharField(max_length=17, null=True)
    ipv4 = models.CharField(max_length=15, null=True)
    ipv6 = models.CharField(max_length=100, null=True)
    firewall_profile = models.CharField(choices=FIREWALL_PROFILES, max_length=30, null=True)


class NetworkLink(models.Model):
    network = models.OneToOneField(Network, null=True, related_name='link')
    index = models.IntegerField()
    name = models.CharField(max_length=255)
    available = models.BooleanField(default=True)
