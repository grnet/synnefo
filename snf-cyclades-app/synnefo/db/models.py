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

import datetime

from copy import deepcopy
from django.conf import settings
from django.db import models

import utils
from contextlib import contextmanager
from hashlib import sha1
from snf_django.lib.api import faults
from django.conf import settings as snf_settings
from aes_encrypt import encrypt_db_charfield, decrypt_db_charfield

from synnefo.db import pools, fields

from synnefo.logic.rapi_pool import (get_rapi_client,
                                     put_rapi_client)

import logging
log = logging.getLogger(__name__)


class Flavor(models.Model):
    cpu = models.IntegerField('Number of CPUs', default=0)
    ram = models.IntegerField('RAM size in MiB', default=0)
    disk = models.IntegerField('Disk size in GiB', default=0)
    disk_template = models.CharField('Disk template', max_length=32)
    deleted = models.BooleanField('Deleted', default=False)

    class Meta:
        verbose_name = u'Virtual machine flavor'
        unique_together = ('cpu', 'ram', 'disk', 'disk_template')

    @property
    def name(self):
        """Returns flavor name (generated)"""
        return u'C%dR%dD%d%s' % (self.cpu, self.ram, self.disk,
                                 self.disk_template)

    def __unicode__(self):
        return "<%s:%s>" % (str(self.id), self.name)


class Backend(models.Model):
    clustername = models.CharField('Cluster Name', max_length=128, unique=True)
    port = models.PositiveIntegerField('Port', default=5080)
    username = models.CharField('Username', max_length=64, blank=True,
                                null=True)
    password_hash = models.CharField('Password', max_length=128, blank=True,
                                     null=True)
    # Sha1 is up to 40 characters long
    hash = models.CharField('Hash', max_length=40, editable=False, null=False)
    # Unique index of the Backend, used for the mac-prefixes of the
    # BackendNetworks
    index = models.PositiveIntegerField('Index', null=False, unique=True,
                                        default=0)
    drained = models.BooleanField('Drained', default=False, null=False)
    offline = models.BooleanField('Offline', default=False, null=False)
    # Type of hypervisor
    hypervisor = models.CharField('Hypervisor', max_length=32, default="kvm",
                                  null=False)
    disk_templates = fields.SeparatedValuesField("Disk Templates", null=True)
    # Last refresh of backend resources
    updated = models.DateTimeField(auto_now_add=True)
    # Backend resources
    mfree = models.PositiveIntegerField('Free Memory', default=0, null=False)
    mtotal = models.PositiveIntegerField('Total Memory', default=0, null=False)
    dfree = models.PositiveIntegerField('Free Disk', default=0, null=False)
    dtotal = models.PositiveIntegerField('Total Disk', default=0, null=False)
    pinst_cnt = models.PositiveIntegerField('Primary Instances', default=0,
                                            null=False)
    ctotal = models.PositiveIntegerField('Total number of logical processors',
                                         default=0, null=False)

    HYPERVISORS = (
        ("kvm", "Linux KVM hypervisor"),
        ("xen-pvm", "Xen PVM hypervisor"),
        ("xen-hvm", "Xen KVM hypervisor"),
    )

    class Meta:
        verbose_name = u'Backend'
        ordering = ["clustername"]

    def __unicode__(self):
        return self.clustername + "(id=" + str(self.id) + ")"

    @property
    def backend_id(self):
        return self.id

    def get_client(self):
        """Get or create a client. """
        if self.offline:
            raise faults.ServiceUnavailable
        return get_rapi_client(self.id, self.hash,
                               self.clustername,
                               self.port,
                               self.username,
                               self.password)

    @staticmethod
    def put_client(client):
            put_rapi_client(client)

    def create_hash(self):
        """Create a hash for this backend. """
        sha = sha1('%s%s%s%s' %
                   (self.clustername, self.port, self.username, self.password))
        return sha.hexdigest()

    @property
    def password(self):
        return decrypt_db_charfield(self.password_hash)

    @password.setter
    def password(self, value):
        self.password_hash = encrypt_db_charfield(value)

    def save(self, *args, **kwargs):
        # Create a new hash each time a Backend is saved
        old_hash = self.hash
        self.hash = self.create_hash()
        super(Backend, self).save(*args, **kwargs)
        if self.hash != old_hash:
            # Populate the new hash to the new instances
            self.virtual_machines.filter(deleted=False)\
                                 .update(backend_hash=self.hash)

    def __init__(self, *args, **kwargs):
        super(Backend, self).__init__(*args, **kwargs)
        if not self.pk:
            # Generate a unique index for the Backend
            indexes = Backend.objects.all().values_list('index', flat=True)
            try:
                first_free = [x for x in xrange(0, 16) if x not in indexes][0]
                self.index = first_free
            except IndexError:
                raise Exception("Can not create more than 16 backends")

    def use_hotplug(self):
        return self.hypervisor == "kvm" and snf_settings.GANETI_USE_HOTPLUG

    def get_create_params(self):
        params = deepcopy(snf_settings.GANETI_CREATEINSTANCE_KWARGS)
        params["hvparams"] = params.get("hvparams", {})\
                                   .get(self.hypervisor, {})
        return params


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


class QuotaHolderSerial(models.Model):
    """Model representing a serial for a Quotaholder Commission.

    serial:   The serial that Quotaholder assigned to this commission
    pending:  Whether it has been decided to accept or reject this commission
    accept:   If pending is False, this attribute indicates whether to accept
              or reject this commission
    resolved: Whether this commission has been accepted or rejected to
              Quotaholder.

    """
    serial = models.BigIntegerField(null=False, primary_key=True,
                                    db_index=True)
    pending = models.BooleanField(default=True, db_index=True)
    accept = models.BooleanField(default=False)
    resolved = models.BooleanField(default=False)

    class Meta:
        verbose_name = u'Quota Serial'
        ordering = ["serial"]

    def __unicode__(self):
        return u"<serial: %s>" % self.serial


class VirtualMachine(models.Model):
    # The list of possible actions for a VM
    ACTIONS = (
        ('CREATE', 'Create VM'),
        ('START', 'Start VM'),
        ('STOP', 'Shutdown VM'),
        ('SUSPEND', 'Admin Suspend VM'),
        ('REBOOT', 'Reboot VM'),
        ('DESTROY', 'Destroy VM'),
        ('RESIZE', 'Resize a VM'),
        ('ADDFLOATINGIP', 'Add floating IP to VM'),
        ('REMOVEFLOATINGIP', 'Add floating IP to VM'),
    )

    # The internal operating state of a VM
    OPER_STATES = (
        ('BUILD', 'Queued for creation'),
        ('ERROR', 'Creation failed'),
        ('STOPPED', 'Stopped'),
        ('STARTED', 'Started'),
        ('DESTROYED', 'Destroyed'),
        ('RESIZE', 'Resizing')
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
        'OP_INSTANCE_REINSTALL': None,
        'OP_INSTANCE_ACTIVATE_DISKS': None,
        'OP_INSTANCE_DEACTIVATE_DISKS': None,
        'OP_INSTANCE_REPLACE_DISKS': None,
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
        'RESIZE': 'RESIZE',
        'DESTROYED': 'DELETED',
    }

    name = models.CharField('Virtual Machine Name', max_length=255)
    userid = models.CharField('User ID of the owner', max_length=100,
                              db_index=True, null=False)
    backend = models.ForeignKey(Backend, null=True,
                                related_name="virtual_machines",
                                on_delete=models.PROTECT)
    backend_hash = models.CharField(max_length=128, null=True, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    imageid = models.CharField(max_length=100, null=False)
    hostid = models.CharField(max_length=100)
    flavor = models.ForeignKey(Flavor)
    deleted = models.BooleanField('Deleted', default=False, db_index=True)
    suspended = models.BooleanField('Administratively Suspended',
                                    default=False)
    serial = models.ForeignKey(QuotaHolderSerial,
                               related_name='virtual_machine', null=True)

    # VM State
    # The following fields are volatile data, in the sense
    # that they need not be persistent in the DB, but rather
    # get generated at runtime by quering Ganeti and applying
    # updates received from Ganeti.

    # In the future they could be moved to a separate caching layer
    # and removed from the database.
    # [vkoukis] after discussion with [faidon].
    action = models.CharField(choices=ACTIONS, max_length=30, null=True,
                              default=None)
    operstate = models.CharField(choices=OPER_STATES, max_length=30,
                                 null=False, default="BUILD")
    backendjobid = models.PositiveIntegerField(null=True)
    backendopcode = models.CharField(choices=BACKEND_OPCODES, max_length=30,
                                     null=True)
    backendjobstatus = models.CharField(choices=BACKEND_STATUSES,
                                        max_length=30, null=True)
    backendlogmsg = models.TextField(null=True)
    buildpercentage = models.IntegerField(default=0)
    backendtime = models.DateTimeField(default=datetime.datetime.min)

    # Latest action and corresponding Ganeti job ID, for actions issued
    # by the API
    task = models.CharField(max_length=64, null=True)
    task_job_id = models.BigIntegerField(null=True)

    def get_client(self):
        if self.backend:
            return self.backend.get_client()
        else:
            raise faults.ServiceUnavailable

    def get_last_diagnostic(self, **filters):
        try:
            return self.diagnostics.filter()[0]
        except IndexError:
            return None

    @staticmethod
    def put_client(client):
            put_rapi_client(client)

    def save(self, *args, **kwargs):
        # Store hash for first time saved vm
        if (self.id is None or self.backend_hash == '') and self.backend:
            self.backend_hash = self.backend.hash
        super(VirtualMachine, self).save(*args, **kwargs)

    @property
    def backend_vm_id(self):
        """Returns the backend id for this VM by prepending backend-prefix."""
        if not self.id:
            raise VirtualMachine.InvalidBackendIdError("self.id is None")
        return "%s%s" % (settings.BACKEND_PREFIX_ID, str(self.id))

    class Meta:
        verbose_name = u'Virtual machine instance'
        get_latest_by = 'created'

    def __unicode__(self):
        return "<vm: %s>" % str(self.id)

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
    OPER_STATES = (
        ('PENDING', 'Pending'),  # Unused because of lazy networks
        ('ACTIVE', 'Active'),
        ('DELETED', 'Deleted'),
        ('ERROR', 'Error')
    )

    ACTIONS = (
        ('CREATE', 'Create Network'),
        ('DESTROY', 'Destroy Network'),
        ('ADD', 'Add server to Network'),
        ('REMOVE', 'Remove server from Network'),
    )

    RSAPI_STATE_FROM_OPER_STATE = {
        'PENDING': 'PENDING',
        'ACTIVE': 'ACTIVE',
        'DELETED': 'DELETED',
        'ERROR': 'ERROR'
    }

    FLAVORS = {
        'CUSTOM': {
            'mode': 'bridged',
            'link': settings.DEFAULT_BRIDGE,
            'mac_prefix': settings.DEFAULT_MAC_PREFIX,
            'tags': None,
            'desc': "Basic flavor used for a bridged network",
        },
        'IP_LESS_ROUTED': {
            'mode': 'routed',
            'link': settings.DEFAULT_ROUTING_TABLE,
            'mac_prefix': settings.DEFAULT_MAC_PREFIX,
            'tags': 'ip-less-routed',
            'desc': "Flavor used for an IP-less routed network using"
                    " Proxy ARP",
        },
        'MAC_FILTERED': {
            'mode': 'bridged',
            'link': settings.DEFAULT_MAC_FILTERED_BRIDGE,
            'mac_prefix': 'pool',
            'tags': 'private-filtered',
            'desc': "Flavor used for bridged networks that offer isolation"
                    " via filtering packets based on their src "
                    " MAC (ebtables)",
        },
        'PHYSICAL_VLAN': {
            'mode': 'bridged',
            'link': 'pool',
            'mac_prefix': settings.DEFAULT_MAC_PREFIX,
            'tags': 'physical-vlan',
            'desc': "Flavor used for bridged network that offer isolation"
                    " via dedicated physical vlan",
        },
    }

    name = models.CharField('Network Name', max_length=128)
    userid = models.CharField('User ID of the owner', max_length=128,
                              null=True, db_index=True)
    # subnet will be null for IPv6 only networks
    subnet = models.CharField('Subnet', max_length=32, null=True)
    # subnet6 will be null for IPv4 only networks
    subnet6 = models.CharField('IPv6 Subnet', max_length=64, null=True)
    gateway = models.CharField('Gateway', max_length=32, null=True)
    gateway6 = models.CharField('IPv6 Gateway', max_length=64, null=True)
    dhcp = models.BooleanField('DHCP', default=True)
    flavor = models.CharField('Flavor', max_length=32, null=False)
    mode = models.CharField('Network Mode', max_length=16, null=True)
    link = models.CharField('Network Link', max_length=32, null=True)
    mac_prefix = models.CharField('MAC Prefix', max_length=32, null=False)
    tags = models.CharField('Network Tags', max_length=128, null=True)
    public = models.BooleanField(default=False, db_index=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField('Deleted', default=False, db_index=True)
    state = models.CharField(choices=OPER_STATES, max_length=32,
                             default='PENDING')
    machines = models.ManyToManyField(VirtualMachine,
                                      through='NetworkInterface')
    action = models.CharField(choices=ACTIONS, max_length=32, null=True,
                              default=None)
    drained = models.BooleanField("Drained", default=False, null=False)
    floating_ip_pool = models.BooleanField('Floating IP Pool', null=False,
                                           default=False)
    pool = models.OneToOneField('IPPoolTable', related_name='network',
                                default=lambda: IPPoolTable.objects.create(
                                                            available_map='',
                                                            reserved_map='',
                                                            size=0),
                                null=True)
    serial = models.ForeignKey(QuotaHolderSerial, related_name='network',
                               null=True)

    def __unicode__(self):
        return "<Network: %s>" % str(self.id)

    @property
    def backend_id(self):
        """Return the backend id by prepending backend-prefix."""
        if not self.id:
            raise Network.InvalidBackendIdError("self.id is None")
        return "%snet-%s" % (settings.BACKEND_PREFIX_ID, str(self.id))

    @property
    def backend_tag(self):
        """Return the network tag to be used in backend

        """
        if self.tags:
            return self.tags.split(',')
        else:
            return []

    def create_backend_network(self, backend=None):
        """Create corresponding BackendNetwork entries."""

        backends = [backend] if backend else\
            Backend.objects.filter(offline=False)
        for backend in backends:
            backend_exists =\
                BackendNetwork.objects.filter(backend=backend, network=self)\
                                      .exists()
            if not backend_exists:
                BackendNetwork.objects.create(backend=backend, network=self)

    def get_pool(self, with_lock=True):
        if not self.pool_id:
            self.pool = IPPoolTable.objects.create(available_map='',
                                                   reserved_map='',
                                                   size=0)
            self.save()
        objects = IPPoolTable.objects
        if with_lock:
            objects = objects.select_for_update()
        return objects.get(id=self.pool_id).pool

    def reserve_address(self, address):
        pool = self.get_pool()
        pool.reserve(address)
        pool.save()

    def release_address(self, address):
        pool = self.get_pool()
        pool.put(address)
        pool.save()

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
            return repr('<opcode: %s, status: %s>'
                        % (self.opcode, self.status))

    class InvalidActionError(Exception):
        def __init__(self, action):
            self._action = action

        def __str__(self):
            return repr(str(self._action))


class BackendNetwork(models.Model):
    OPER_STATES = (
        ('PENDING', 'Pending'),
        ('ACTIVE', 'Active'),
        ('DELETED', 'Deleted'),
        ('ERROR', 'Error')
    )

    # The list of possible operations on the backend
    BACKEND_OPCODES = (
        ('OP_NETWORK_ADD', 'Create Network'),
        ('OP_NETWORK_CONNECT', 'Activate Network'),
        ('OP_NETWORK_DISCONNECT', 'Deactivate Network'),
        ('OP_NETWORK_REMOVE', 'Remove Network'),
        # These are listed here for completeness,
        # and are ignored for the time being
        ('OP_NETWORK_SET_PARAMS', 'Set Network Parameters'),
        ('OP_NETWORK_QUERY_DATA', 'Query Network Data')
    )

    # The operating state of a Netowork,
    # upon the successful completion of a backend operation.
    # IMPORTANT: Make sure all keys have a corresponding
    # entry in BACKEND_OPCODES if you update this field, see #1035, #1111.
    OPER_STATE_FROM_OPCODE = {
        'OP_NETWORK_ADD': 'PENDING',
        'OP_NETWORK_CONNECT': 'ACTIVE',
        'OP_NETWORK_DISCONNECT': 'PENDING',
        'OP_NETWORK_REMOVE': 'DELETED',
        'OP_NETWORK_SET_PARAMS': None,
        'OP_NETWORK_QUERY_DATA': None
    }

    network = models.ForeignKey(Network, related_name='backend_networks')
    backend = models.ForeignKey(Backend, related_name='networks',
                                on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField('Deleted', default=False)
    mac_prefix = models.CharField('MAC Prefix', max_length=32, null=False)
    operstate = models.CharField(choices=OPER_STATES, max_length=30,
                                 default='PENDING')
    backendjobid = models.PositiveIntegerField(null=True)
    backendopcode = models.CharField(choices=BACKEND_OPCODES, max_length=30,
                                     null=True)
    backendjobstatus = models.CharField(choices=BACKEND_STATUSES,
                                        max_length=30, null=True)
    backendlogmsg = models.TextField(null=True)
    backendtime = models.DateTimeField(null=False,
                                       default=datetime.datetime.min)

    class Meta:
        # Ensure one entry for each network in each backend
        unique_together = (("network", "backend"))

    def __init__(self, *args, **kwargs):
        """Initialize state for just created BackendNetwork instances."""
        super(BackendNetwork, self).__init__(*args, **kwargs)
        if not self.mac_prefix:
            # Generate the MAC prefix of the BackendNetwork, by combining
            # the Network prefix with the index of the Backend
            net_prefix = self.network.mac_prefix
            backend_suffix = hex(self.backend.index).replace('0x', '')
            mac_prefix = net_prefix + backend_suffix
            try:
                utils.validate_mac(mac_prefix + ":00:00:00")
            except utils.InvalidMacAddress:
                raise utils.InvalidMacAddress("Invalid MAC prefix '%s'" %
                                              mac_prefix)
            self.mac_prefix = mac_prefix

    def __unicode__(self):
        return '<%s@%s>' % (self.network, self.backend)


class NetworkInterface(models.Model):
    FIREWALL_PROFILES = (
        ('ENABLED', 'Enabled'),
        ('DISABLED', 'Disabled'),
        ('PROTECTED', 'Protected')
    )

    STATES = (
        ("ACTIVE", "Active"),
        ("BUILDING", "Building"),
        ("ERROR", "Error"),
    )

    machine = models.ForeignKey(VirtualMachine, related_name='nics')
    network = models.ForeignKey(Network, related_name='nics')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    index = models.IntegerField(null=True)
    mac = models.CharField(max_length=32, null=True, unique=True)
    ipv4 = models.CharField(max_length=15, null=True)
    ipv6 = models.CharField(max_length=100, null=True)
    firewall_profile = models.CharField(choices=FIREWALL_PROFILES,
                                        max_length=30, null=True)
    dirty = models.BooleanField(default=False)
    state = models.CharField(max_length=32, null=False, default="ACTIVE",
                             choices=STATES)

    def __unicode__(self):
        return "<%s:vm:%s network:%s ipv4:%s ipv6:%s>" % \
            (self.index, self.machine_id, self.network_id, self.ipv4,
             self.ipv6)

    @property
    def is_floating_ip(self):
        network = self.network
        if self.ipv4 and network.floating_ip_pool:
            return network.floating_ips.filter(machine=self.machine,
                                               ipv4=self.ipv4,
                                               deleted=False).exists()
        return False


class FloatingIP(models.Model):
    userid = models.CharField("UUID of the owner", max_length=128,
                              null=False, db_index=True)
    ipv4 = models.IPAddressField(null=False, unique=True, db_index=True)
    network = models.ForeignKey(Network, related_name="floating_ips",
                                null=False)
    machine = models.ForeignKey(VirtualMachine, related_name="floating_ips",
                                null=True)
    created = models.DateTimeField(auto_now_add=True)
    deleted = models.BooleanField(default=False, null=False)
    serial = models.ForeignKey(QuotaHolderSerial,
                               related_name="floating_ips", null=True)

    def __unicode__(self):
        return "<FIP: %s@%s>" % (self.ipv4, self.network.id)

    def in_use(self):
        if self.machine is None:
            return False
        else:
            return (not self.machine.deleted)


class PoolTable(models.Model):
    available_map = models.TextField(default="", null=False)
    reserved_map = models.TextField(default="", null=False)
    size = models.IntegerField(null=False)

    # Optional Fields
    base = models.CharField(null=True, max_length=32)
    offset = models.IntegerField(null=True)

    class Meta:
        abstract = True

    @classmethod
    def get_pool(cls):
        try:
            pool_row = cls.objects.select_for_update().get()
            return pool_row.pool
        except cls.DoesNotExist:
            raise pools.EmptyPool

    @property
    def pool(self):
        return self.manager(self)


class BridgePoolTable(PoolTable):
    manager = pools.BridgePool


class MacPrefixPoolTable(PoolTable):
    manager = pools.MacPrefixPool


class IPPoolTable(PoolTable):
    manager = pools.IPPool


@contextmanager
def pooled_rapi_client(obj):
        if isinstance(obj, (VirtualMachine, BackendNetwork)):
            backend = obj.backend
        else:
            backend = obj

        if backend.offline:
            log.warning("Trying to connect with offline backend: %s", backend)
            raise faults.ServiceUnavailable("Can not connect to offline"
                                            " backend: %s" % backend)

        b = backend
        client = get_rapi_client(b.id, b.hash, b.clustername, b.port,
                                 b.username, b.password)
        try:
            yield client
        finally:
            put_rapi_client(client)


class VirtualMachineDiagnosticManager(models.Manager):
    """
    Custom manager for :class:`VirtualMachineDiagnostic` model.
    """

    # diagnostic creation helpers
    def create_for_vm(self, vm, level, message, **kwargs):
        attrs = {'machine': vm, 'level': level, 'message': message}
        attrs.update(kwargs)
        # update instance updated time
        self.create(**attrs)
        vm.save()

    def create_error(self, vm, **kwargs):
        self.create_for_vm(vm, 'ERROR', **kwargs)

    def create_debug(self, vm, **kwargs):
        self.create_for_vm(vm, 'DEBUG', **kwargs)

    def since(self, vm, created_since, **kwargs):
        return self.get_query_set().filter(vm=vm, created__gt=created_since,
                                           **kwargs)


class VirtualMachineDiagnostic(models.Model):
    """
    Model to store backend information messages that relate to the state of
    the virtual machine.
    """

    TYPES = (
        ('ERROR', 'Error'),
        ('WARNING', 'Warning'),
        ('INFO', 'Info'),
        ('DEBUG', 'Debug'),
    )

    objects = VirtualMachineDiagnosticManager()

    created = models.DateTimeField(auto_now_add=True)
    machine = models.ForeignKey('VirtualMachine', related_name="diagnostics")
    level = models.CharField(max_length=20, choices=TYPES)
    source = models.CharField(max_length=100)
    source_date = models.DateTimeField(null=True)
    message = models.CharField(max_length=255)
    details = models.TextField(null=True)

    class Meta:
        ordering = ['-created']
