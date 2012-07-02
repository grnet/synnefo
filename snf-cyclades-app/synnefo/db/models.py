# Copyright 2011-2012 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of GRNET S.A.

from django.conf import settings
from django.db import models


class Flavor(models.Model):
    cpu = models.IntegerField('Number of CPUs', default=0)
    ram = models.IntegerField('RAM size in MiB', default=0)
    disk = models.IntegerField('Disk size in GiB', default=0)
    disk_template = models.CharField('Disk template', max_length=32,
            default=settings.DEFAULT_GANETI_DISK_TEMPLATE)
    deleted = models.BooleanField('Deleted', default=False)

    class Meta:
        verbose_name = u'Virtual machine flavor'
        unique_together = ('cpu', 'ram', 'disk', 'disk_template')

    @property
    def name(self):
        """Returns flavor name (generated)"""
        return u'C%dR%dD%d' % (self.cpu, self.ram, self.disk)

    def __unicode__(self):
        return self.name


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
        ('OP_INSTANCE_REINSTALL', 'Reinstall Instance'),
        ('OP_INSTANCE_ACTIVATE_DISKS', 'Activate Disks'),
        ('OP_INSTANCE_DEACTIVATE_DISKS', 'Deactivate Disks'),
        ('OP_INSTANCE_REPLACE_DISKS', 'Replace Disks'),
        ('OP_INSTANCE_MIGRATE', 'Migrate Instance'),
        ('OP_INSTANCE_CONSOLE', 'Get Instance Console'),
        ('OP_INSTANCE_RECREATE_DISKS', 'Recreate Disks'),
        ('OP_INSTANCE_FAILOVER', 'Failover Instance')
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
    # IMPORTANT: Make sure all keys have a corresponding
    # entry in BACKEND_OPCODES if you update this field, see #1035, #1111.
    OPER_STATE_FROM_OPCODE = {
        'OP_INSTANCE_CREATE': 'STARTED',
        'OP_INSTANCE_REMOVE': 'DESTROYED',
        'OP_INSTANCE_STARTUP': 'STARTED',
        'OP_INSTANCE_SHUTDOWN': 'STOPPED',
        'OP_INSTANCE_REBOOT': 'STARTED',
        'OP_INSTANCE_SET_PARAMS': None,
        'OP_INSTANCE_QUERY_DATA': None,
        'OP_INSTANCE_REINSTALL' : None,
        'OP_INSTANCE_ACTIVATE_DISKS' : None,
        'OP_INSTANCE_DEACTIVATE_DISKS': None,
        'OP_INSTANCE_REPLACE_DISKS' : None,
        'OP_INSTANCE_MIGRATE': None,
        'OP_INSTANCE_CONSOLE': None,
        'OP_INSTANCE_RECREATE_DISKS': None,
        'OP_INSTANCE_FAILOVER': None
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
    userid = models.CharField('User ID of the owner', max_length=100)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    imageid = models.CharField(max_length=100, null=False)
    hostid = models.CharField(max_length=100)
    flavor = models.ForeignKey(Flavor)
    deleted = models.BooleanField('Deleted', default=False)
    suspended = models.BooleanField('Administratively Suspended',
                                    default=False)

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
    backendopcode = models.CharField(choices=BACKEND_OPCODES, max_length=30,
            null=True)
    backendjobstatus = models.CharField(choices=BACKEND_STATUSES,
            max_length=30, null=True)
    backendlogmsg = models.TextField(null=True)
    buildpercentage = models.IntegerField(default=0)

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
            return repr('<opcode: %s, status: %s>' % (self.opcode,
                    self.status))

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

    @property
    def backend_id(self):
        """Returns the backend id for this VM by prepending backend-prefix."""
        if not self.id:
            raise VirtualMachine.InvalidBackendIdError("self.id is None")
        return '%s%s' % (settings.BACKEND_PREFIX_ID, self.id)

    class Meta:
        verbose_name = u'Virtual machine instance'
        get_latest_by = 'created'

    def __unicode__(self):
        return self.name


class VirtualMachineMetadata(models.Model):
    meta_key = models.CharField(max_length=50)
    meta_value = models.CharField(max_length=500)
    vm = models.ForeignKey(VirtualMachine, related_name='metadata')

    class Meta:
        unique_together = (('meta_key', 'vm'),)
        verbose_name = u'Key-value pair of metadata for a VM.'

    def __unicode__(self):
        return u'%s: %s' % (self.meta_key, self.meta_value)


class Network(models.Model):
    NETWORK_STATES = (
        ('ACTIVE', 'Active'),
        ('DELETED', 'Deleted')
    )

    name = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    userid = models.CharField('User ID of the owner', max_length=100,
                              null=True)
    state = models.CharField(choices=NETWORK_STATES, max_length=30)
    public = models.BooleanField(default=False)
    link = models.ForeignKey('NetworkLink', related_name='+')
    machines = models.ManyToManyField(VirtualMachine,
                                      through='NetworkInterface')

    def __unicode__(self):
        return self.name


class NetworkInterface(models.Model):
    FIREWALL_PROFILES = (
        ('ENABLED', 'Enabled'),
        ('DISABLED', 'Disabled'),
        ('PROTECTED', 'Protected')
    )

    machine = models.ForeignKey(VirtualMachine, related_name='nics')
    network = models.ForeignKey(Network, related_name='nics')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    index = models.IntegerField(null=True)
    mac = models.CharField(max_length=17, null=True)
    ipv4 = models.CharField(max_length=15, null=True)
    ipv6 = models.CharField(max_length=100, null=True)
    firewall_profile = models.CharField(choices=FIREWALL_PROFILES,
                                        max_length=30, null=True)

    def __unicode__(self):
        return '%s@%s' % (self.machine.name, self.network.name)


class NetworkLink(models.Model):
    network = models.ForeignKey(Network, null=True, related_name='+')
    index = models.IntegerField()
    name = models.CharField(max_length=255)
    available = models.BooleanField(default=True)

    def __unicode__(self):
        return self.name

    class NotAvailable(Exception):
        pass

