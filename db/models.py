# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8

from django.conf import settings
from django.db import models
from django.db import transaction

import datetime

backend_prefix_id = settings.BACKEND_PREFIX_ID

class SynnefoUser(models.Model):
    name = models.CharField('Synnefo Username', max_length=255)
    credit = models.IntegerField('Credit Balance')
    created = models.DateTimeField('Time of creation', auto_now_add=True)
    updated = models.DateTimeField('Time of last update', auto_now=True)
    #
    # We do not rely on Django's user authentication mechanism.
    # Hence, no references to the User model.
    # [vkoukis], after discussion with [faidon].
    # user = models.ForeignKey(User)
    
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

    @transaction.commit_on_success
    def debit_account(self, amount, vm, description):
        """Charges the user with the specified amount of credits for a vm (resource)"""
        date_now = datetime.datetime.now()
        self.credit = self.credit - amount
        self.save()

        # then write the debit entry
        debit = Debit()

        debit.user = self
        debit.vm = vm
        debit.when = date_now
        debit.description = description

        debit.save()

    def credit_account(self, amount, creditor, description):
        """No clue :)"""
        return


class Image(models.Model):
    # This is WIP, FIXME
    IMAGE_STATES = (
        ('ACTIVE', 'Active'),
        ('SAVING', 'Saving'),
        ('DELETED', 'Deleted')
    )

    name = models.CharField('Image name', max_length=255)
    state = models.CharField('Current Image State', choices=IMAGE_STATES, max_length=30)
    description = models.TextField('General description')
    size = models.PositiveIntegerField('Image size in MBs')
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
    ram = models.IntegerField('Size of RAM', default=0)
    disk = models.IntegerField('Size of Disk space', default=0)
    
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

    def _get_costs(self, start_datetime, end_datetime, active):
        """Return a list with FlavorCost objects for the specified duration"""
        def between(enh_fc, a_date):
            """Checks if a date is between a FlavorCost duration"""
            if enh_fc.effective_from <= a_date and enh_fc.effective_to is None:
                return True

            return enh_fc.effective_from <= a_date and enh_fc.effective_to >= a_date

        def calculate_cost(start_date, end_date, cost):
            """Calculate the total cost for the specified duration"""
            td = end_date - start_date
            sec = float(td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / float(10**6)
            total_hours = float(sec) / float(60.0*60.0)
            total_cost = float(cost)*total_hours

            return round(total_cost)

        # Get the related FlavorCost objects, sorted.
        price_list = FlavorCost.objects.filter(flavor=self).order_by('effective_from')

        # add the extra field FlavorCost.effective_to
        for idx in range(0, len(price_list)):
            if idx + 1 == len(price_list):
                price_list[idx].effective_to = None
            else:
                price_list[idx].effective_to = price_list[idx + 1].effective_from

        price_result = []
        found_start = False

        # Find the affected FlavorCost, according to the
        # dates, and put them in price_result
        for p in price_list:
            if between(p, start_datetime):
                found_start = True
                p.effective_from = start_datetime
            if between(p, end_datetime):
                p.effective_to = end_datetime
                price_result.append(p)
                break
            if found_start:
                price_result.append(p)

        results = []

        # Create the list and the result tuples
        for p in price_result:
            if active:
                cost = p.cost_active
            else:
                cost = p.cost_inactive

            results.append( ( p.effective_from, calculate_cost(p.effective_from, p.effective_to, cost)) )

        return results

    def get_cost_active(self, start_datetime, end_datetime):
        """Returns a list with the active costs for the specified duration"""
        return self._get_costs(start_datetime, end_datetime, True)

    def get_cost_inactive(self, start_datetime, end_datetime):
        """Returns a list with the inactive costs for the specified duration"""
        return self._get_costs(start_datetime, end_datetime, False)


class FlavorCost(models.Model):
    cost_active = models.PositiveIntegerField('Active Cost')
    cost_inactive = models.PositiveIntegerField('Inactive Cost')
    effective_from = models.DateTimeField()
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

    name = models.CharField('Virtual Machine Name', max_length=255)
    owner = models.ForeignKey(SynnefoUser)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    charged = models.DateTimeField(default=datetime.datetime.now())
    sourceimage = models.ForeignKey("Image", null=False) 
    hostid = models.CharField(max_length=100)
    description = models.TextField()
    ipfour = models.IPAddressField()
    ipsix = models.CharField(max_length=100)
    flavor = models.ForeignKey(Flavor)
    deleted = models.BooleanField('Deleted', default=False)
    suspended = models.BooleanField('Administratively Suspended', default=False)

    # VM State 
    # The following fields are volatile data, in the sense
    # that they need not be persistent in the DB, but rather
    # get generated at runtime by quering Ganeti and applying
    # updates received from Ganeti.
    #
    # In the future they could be moved to a separate caching layer
    # and removed from the database.
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
        # This gets called BEFORE an instance gets save()d for
        # the first time.
        if not self.pk: 
            self._action = None
            self._backendjobid = None
            self._backendjobstatus = None
            self._backendopcode = None
            self._backendlogmsg = None
            # Do not use _update_state() for this, 
            # as this may cause save() to get called in __init__(),
            # breaking VirtualMachine.object.create() among other things.
            self._operstate = 'BUILD'

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
            self._update_state(VirtualMachine.OPER_STATE_FROM_OPCODE[opcode])
        # Special cases OP_INSTANCE_CREATE fails --> ERROR
        if status in ('canceled', 'error') and opcode == 'OP_INSTANCE_CREATE':
            self._update_state('ERROR')
        # Any other notification of failure leaves the operating state unchanged

        self.save()

    def start_action(self, action):
        """Update the state of a VM when a new action is initiated."""
        if not action in [x[0] for x in VirtualMachine.ACTIONS]:
            raise VirtualMachine.InvalidActionError(action)

        # No actions to deleted and no actions beside destroy to suspended vms
        if self.deleted or (self.suspended and action not in ["START", "DESTROY"]):
            raise VirtualMachine.InvalidActionError(action)

        self._action = action
        self._backendjobid = None
        self._backendopcode = None
        self._backendlogmsg = None

        # Update the relevant flags if the VM is being suspended or destroyed
        if action == "DESTROY":
            self.deleted = True
        elif action == "SUSPEND":
            self.suspended = True
        elif action == "START":
            self.suspended = False
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

    def _update_state(self, new_operstate):
        """Wrapper around updates of the _operstate field

        Currently calls the charge() method when necessary.

        """

        # Call charge() unconditionally before any change of
        # internal state.
        self.charge()
        self._operstate = new_operstate

    @transaction.commit_on_success
    def charge(self):
        """Charges the owner of this VM.
        
        Charges the owner of a VM for the period
        from vm.charged to datetime.now(), based on the
        current operating state.
        
        """
        charged_states = ('STARTED', 'STOPPED')
       
        start_datetime = self.charged
        self.charged = datetime.datetime.now()

        # Only charge for a specific set of states
        if self._operstate not in charged_states:
            self.save()
            return

        cost_list = []

        # remember, we charge only for Started and Stopped
        if self._operstate == 'STARTED':
            cost_list = self.flavor.get_cost_active(start_datetime, self.charged)
        elif self._operstate == 'STOPPED':
            cost_list = self.flavor.get_cost_inactive(start_datetime, self.charged)

        # find the total vost
        total_cost = sum([x[1] for x in cost_list])

        # add the debit entry
        description = "Server = %d, charge = %d for state: %s" % (self.id, total_cost, self._operstate)
        self.owner.debit_account(total_cost, self, description)
        
        self.save()


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
