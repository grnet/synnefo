# Copyright (C) 2010-2016 GRNET S.A. and individual contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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


class VolumeType(models.Model):
    NAME_LENGTH = 255
    DISK_TEMPLATE_LENGTH = 32
    name = models.CharField("Name", max_length=NAME_LENGTH)
    disk_template = models.CharField('Disk Template',
                                     max_length=DISK_TEMPLATE_LENGTH)
    deleted = models.BooleanField('Deleted', default=False)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u"<VolumeType %s(disk_template:%s)>" % \
            (self.name, self.disk_template)

    @property
    def template(self):
        return self.disk_template.split("_")[0]

    @property
    def provider(self):
        if "_" in self.disk_template:
            return self.disk_template.split("_", 1)[1]
        else:
            return None


class Flavor(models.Model):
    cpu = models.IntegerField('Number of CPUs', default=0)
    ram = models.IntegerField('RAM size in MiB', default=0)
    disk = models.IntegerField('Disk size in GiB', default=0)
    volume_type = models.ForeignKey(VolumeType, related_name="flavors",
                                    on_delete=models.PROTECT, null=False)
    deleted = models.BooleanField('Deleted', default=False)
    # Whether the flavor can be used to create new servers
    allow_create = models.BooleanField(default=True, null=False)

    class Meta:
        verbose_name = u'Virtual machine flavor'
        unique_together = ('cpu', 'ram', 'disk', 'volume_type')

    @property
    def name(self):
        """Returns flavor name (generated)"""
        return u'C%sR%sD%s%s' % (self.cpu, self.ram, self.disk,
                                 self.volume_type.disk_template)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u"<%s:%s>" % (self.id, self.name)


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

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u"%s(id:%s)" % (self.clustername, self.id)

    @property
    def backend_id(self):
        return self.id

    def get_client(self):
        """Get or create a client. """
        if self.offline:
            raise faults.ServiceUnavailable("Backend '%s' is offline" %
                                            self)
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
                raise Exception("Cannot create more than 16 backends")

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

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u"<serial: %s>" % self.serial


class VirtualMachineManager(models.Manager):
    """Custom manager for :class:`VirtualMachine` model."""

    def for_user(self, userid=None, projects=None):
        """Return VMs that are accessible by the user.

        VMs that are accessible by the user are those that are owned by the
        user and those that are shared to the projects that the user is member.

        """

        _filter = models.Q()

        if userid:
            _filter |= models.Q(userid=userid)
        if projects:
            _filter |= (models.Q(shared_to_project=True) &\
                        models.Q(project__in=projects))

        return self.get_queryset().filter(_filter)


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

    VIRTUAL_MACHINE_NAME_LENGTH = 255

    objects = VirtualMachineManager()

    name = models.CharField('Virtual Machine Name',
                            max_length=VIRTUAL_MACHINE_NAME_LENGTH)
    userid = models.CharField('User ID of the owner', max_length=100,
                              db_index=True, null=False)
    project = models.CharField(max_length=255, null=True, db_index=True)
    shared_to_project = models.BooleanField('Shared to project',
                                            default=False)
    backend = models.ForeignKey(Backend, null=True,
                                related_name="virtual_machines",
                                on_delete=models.PROTECT)
    backend_hash = models.CharField(max_length=128, null=True, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    imageid = models.CharField(max_length=100, null=False)
    key_name = models.CharField(max_length=100, null=True)
    image_version = models.IntegerField(null=True)
    hostid = models.CharField(max_length=100)
    flavor = models.ForeignKey(Flavor, on_delete=models.PROTECT)
    deleted = models.BooleanField('Deleted', default=False, db_index=True)
    suspended = models.BooleanField('Administratively Suspended',
                                    default=False)
    serial = models.ForeignKey(QuotaHolderSerial,
                               related_name='virtual_machine', null=True,
                               on_delete=models.SET_NULL)
    helper = models.BooleanField(default=False, null=False)

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
            raise faults.ServiceUnavailable("VirtualMachine without backend")

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

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u"<vm:%s@backend:%s>" % (self.id, self.backend_id)

    # Error classes
    class InvalidBackendIdError(ValueError):
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
    KEY_LENGTH = 50
    VALUE_LENGTH = 500
    meta_key = models.CharField(max_length=KEY_LENGTH)
    meta_value = models.CharField(max_length=VALUE_LENGTH)
    vm = models.ForeignKey(VirtualMachine, related_name='metadata',
                           on_delete=models.CASCADE)

    class Meta:
        unique_together = (('meta_key', 'vm'),)
        verbose_name = u'Key-value pair of metadata for a VM.'

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u'<Metadata %s: %s>' % (self.meta_key, self.meta_value)


class Image(models.Model):
    """Model representing Images of created VirtualMachines.

    This model stores basic information about Images which have been used to
    create VirtualMachines or Volumes.

    """

    uuid = models.CharField(max_length=128)
    version = models.IntegerField(null=False)
    owner = models.CharField(max_length=128, null=False)
    name = models.CharField(max_length=256, null=False)
    location = models.TextField()
    mapfile = models.CharField(max_length=256, null=False)
    is_public = models.BooleanField(default=False, null=False)
    is_snapshot = models.BooleanField(default=False, null=False)
    is_system = models.BooleanField(default=False, null=False)
    os = models.CharField(max_length=256)
    osfamily = models.CharField(max_length=256)

    class Meta:
        unique_together = (('uuid', 'version'),)


class NetworkManager(models.Manager):
    """Custom manager for :class:`Network` model."""

    def for_user(self, userid=None, projects=None, public=True):
        """Return networks that are accessible by the user.

        Networks that are accessible by the user are those that are owned by
        the user, those that are shared to the projects that the user is
        member, and public networks.

        """

        _filter = models.Q()

        if userid:
            _filter |= models.Q(userid=userid)
        if projects:
            _filter |= (models.Q(shared_to_project=True) &\
                        models.Q(project__in=projects))
        if public:
            _filter |= models.Q(public=True)

        return self.get_queryset().filter(_filter)


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
            'link': None,
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

    NETWORK_NAME_LENGTH = 128

    objects = NetworkManager()

    name = models.CharField('Network Name', max_length=NETWORK_NAME_LENGTH)
    userid = models.CharField('User ID of the owner', max_length=128,
                              null=True, db_index=True)
    project = models.CharField(max_length=255, null=True, db_index=True)
    shared_to_project = models.BooleanField('Shared to project',
                                            default=False)
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
    external_router = models.BooleanField(default=False)
    serial = models.ForeignKey(QuotaHolderSerial, related_name='network',
                               null=True, on_delete=models.SET_NULL)
    subnet_ids = fields.SeparatedValuesField("Subnet IDs", null=True)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u"<Network: %s>" % self.id

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

    def get_ip_pools(self, locked=True):
        subnets = self.subnets.filter(ipversion=4, deleted=False)\
                              .prefetch_related("ip_pools")
        return [ip_pool for subnet in subnets
                for ip_pool in subnet.get_ip_pools(locked=locked)]

    def reserve_address(self, address, external=False):
        for ip_pool in self.get_ip_pools():
            if ip_pool.contains(address):
                ip_pool.reserve(address, external=external)
                ip_pool.save()
                return
        raise pools.InvalidValue("Network %s does not have an IP pool that"
                                 " contains address %s" % (self, address))

    def release_address(self, address, external=False):
        for ip_pool in self.get_ip_pools():
            if ip_pool.contains(address):
                ip_pool.put(address, external=external)
                ip_pool.save()
                return
        raise pools.InvalidValue("Network %s does not have an IP pool that"
                                 " contains address %s" % (self, address))

    @property
    def subnet4(self):
        return self.get_subnet(version=4)

    @property
    def subnet6(self):
        return self.get_subnet(version=6)

    def get_subnet(self, version=4):
        for subnet in self.subnets.all():
            if subnet.ipversion == version:
                return subnet
        return None

    def ip_count(self):
        """Return the total and free IPv4 addresses of the network."""
        total, free = 0, 0
        ip_pools = self.get_ip_pools(locked=False)
        for ip_pool in ip_pools:
            total += ip_pool.pool_size
            free += ip_pool.count_available()
        return total, free

    class InvalidBackendIdError(ValueError):
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


class SubnetManager(models.Manager):
    """Custom manager for :class:`Subnet` model."""

    def for_user(self, userid=None, projects=None, public=True):
        """Return subnets that are accessible by the user.

        Subnets that are accessible by the user are those that belong
        to a network that is accessible by the user.

        """

        networks = Network.objects.for_user(userid, projects, public=public)

        return self.get_queryset().filter(network__in=networks)


class Subnet(models.Model):
    SUBNET_NAME_LENGTH = 128

    objects = SubnetManager()

    userid = models.CharField('User ID of the owner', max_length=128,
                              null=True, db_index=True)
    public = models.BooleanField(default=False, db_index=True)

    network = models.ForeignKey('Network', null=False, db_index=True,
                                related_name="subnets",
                                on_delete=models.PROTECT)
    name = models.CharField('Subnet Name', max_length=SUBNET_NAME_LENGTH,
                            null=True, default="")
    ipversion = models.IntegerField('IP Version', default=4, null=False)
    cidr = models.CharField('Subnet', max_length=64, null=False)
    gateway = models.CharField('Gateway', max_length=64, null=True)
    dhcp = models.BooleanField('DHCP', default=True, null=False)
    deleted = models.BooleanField('Deleted', default=False, db_index=True,
                                  null=False)
    host_routes = fields.SeparatedValuesField('Host Routes', null=True)
    dns_nameservers = fields.SeparatedValuesField('DNS Nameservers', null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        msg = u"<Subnet %s, Network: %s, CIDR: %s>"
        return msg % (self.id, self.network_id, self.cidr)

    def get_ip_pools(self, locked=True):
        ip_pools = self.ip_pools
        if locked:
            ip_pools = ip_pools.select_for_update()
        return map(lambda ip_pool: ip_pool.pool, ip_pools.all())


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

    network = models.ForeignKey(Network, related_name='backend_networks',
                                on_delete=models.PROTECT)
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

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u'<BackendNetwork %s@%s>' % (self.network, self.backend)


class IPAddressManager(models.Manager):
    """Custom manager for :class:`IPAddress` model."""

    def for_user(self, userid=None, projects=None):
        """Return IP addresses that are accessible by the user.

        IP addresses that are accessible by the user are those that are owned
        by the user or are shared to a project that the user is member.

        """
        _filter = models.Q()

        if userid:
            _filter |= models.Q(userid=userid)
        if projects:
            _filter |= (models.Q(shared_to_project=True) &\
                        models.Q(project__in=projects))

        return self.get_queryset().filter(_filter)


class IPAddress(models.Model):
    objects = IPAddressManager()

    subnet = models.ForeignKey("Subnet", related_name="ips", null=False,
                               on_delete=models.PROTECT)
    network = models.ForeignKey(Network, related_name="ips", null=False,
                                on_delete=models.PROTECT)
    nic = models.ForeignKey("NetworkInterface", related_name="ips", null=True,
                            on_delete=models.SET_NULL)
    userid = models.CharField("UUID of the owner", max_length=128, null=False,
                              db_index=True)
    project = models.CharField(max_length=255, null=True, db_index=True)
    shared_to_project = models.BooleanField('Shared to project',
                                            default=False)
    address = models.CharField("IP Address", max_length=64, null=False)
    floating_ip = models.BooleanField("Floating IP", null=False, default=False)
    ipversion = models.IntegerField("IP Version", null=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False, null=False)

    serial = models.ForeignKey(QuotaHolderSerial,
                               related_name="ips", null=True,
                               on_delete=models.SET_NULL)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        ip_type = "floating" if self.floating_ip else "static"
        return u"<IPAddress: %s, Network: %s, Subnet: %s, Type: %s>"\
               % (self.address, self.network_id, self.subnet_id, ip_type)

    def in_use(self):
        if self.nic is None or self.nic.machine is None:
            return False
        else:
            return (not self.nic.machine.deleted)

    class Meta:
        unique_together = ("network", "address", "deleted")

    def release_address(self):
        """Release the IPv4 address."""
        if self.ipversion == 4:
            for pool_row in self.subnet.ip_pools.all():
                ip_pool = pool_row.pool
                if ip_pool.contains(self.address):
                    ip_pool.put(self.address)
                    ip_pool.save()
                    return
            log.error("Cannot release address %s of NIC %s. Address does not"
                      " belong to any of the IP pools of the subnet %s !",
                      self.address, self.nic, self.subnet_id)


class IPAddressLog(models.Model):
    address = models.CharField("IP Address", max_length=64, null=False,
                               db_index=True)
    server_id = models.IntegerField("Server", null=False)
    network_id = models.IntegerField("Network", null=False)
    allocated_at = models.DateTimeField("Datetime IP allocated to server",
                                        auto_now_add=True)
    released_at = models.DateTimeField("Datetime IP released from server",
                                       null=True)
    active = models.BooleanField("Whether IP still allocated to server",
                                 default=True)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u"<Address: %s, Server: %s, Network: %s, Allocated at: %s>"\
               % (self.address, self.server_id, self.network_id,
                  self.allocated_at)


class IPAddressHistory(models.Model):
    ASSOCIATE = "associate"
    DISASSOCIATE = "disassociate"

    address = models.CharField("IP Address", max_length=64, null=False,
                               db_index=True)
    server_id = models.IntegerField("Server", null=False)
    network_id = models.IntegerField("Network", null=False)
    user_id = models.CharField("IP user", max_length=128, null=False,
                              db_index=True)
    action = models.CharField("Action", max_length=255, null=False)
    action_date = models.DateTimeField("Datetime of IP action",
                                       default=datetime.datetime.now)
    action_reason = models.CharField("Action reason", max_length=1024,
                                     default="")

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u"<Address: %s, Server: %s, Network: %s, User: %s,"\
            " Date: %s Action: %s>"\
            % (self.address, self.network_id, self.server_id, self.user_id,
               self.action_date, self.action)


class NetworkInterfaceManager(models.Manager):
    """Custom manager for :class:`NetworkInterface` model."""

    def for_user(self, userid=None, projects=None):
        """Return ports (NetworkInterfaces) that are accessible by the user.

        Ports that are accessible by the user are those that:
        * are owned by the user
        * are attached to a VM that is accessible by the user
        * are attached to a Network that is accessible by the user (but
          not public)

        """

        vms = VirtualMachine.objects.for_user(userid, projects)
        networks = Network.objects.for_user(userid, projects, public=False)\
                                  .filter(public=False)
        ips = IPAddress.objects.for_user(userid, projects).filter(floating_ip=True)

        _filter = models.Q()
        if userid:
            _filter |= models.Q(userid=userid)

        _filter |= models.Q(machine__in=vms)
        _filter |= models.Q(network__in=networks)
        _filter |= models.Q(ips__in=ips)

        return self.get_queryset().filter(_filter)


class NetworkInterface(models.Model):
    FIREWALL_PROFILES = (
        ('ENABLED', 'Enabled'),
        ('DISABLED', 'Disabled'),
        ('PROTECTED', 'Protected')
    )

    STATES = (
        ("ACTIVE", "Active"),
        ("BUILD", "Building"),
        ("ERROR", "Error"),
        ("DOWN", "Down"),
    )

    NETWORK_IFACE_NAME_LENGTH = 128

    objects = NetworkInterfaceManager()

    name = models.CharField('NIC name', max_length=NETWORK_IFACE_NAME_LENGTH,
                            null=True, default="")
    userid = models.CharField("UUID of the owner", max_length=128,
                              null=False, db_index=True)
    machine = models.ForeignKey(VirtualMachine, related_name='nics',
                                on_delete=models.PROTECT, null=True)
    network = models.ForeignKey(Network, related_name='nics',
                                on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    index = models.IntegerField(null=True)
    mac = models.CharField(max_length=32, null=True, unique=True)
    firewall_profile = models.CharField(choices=FIREWALL_PROFILES,
                                        max_length=30, null=True)
    security_groups = models.ManyToManyField("SecurityGroup", null=True)
    state = models.CharField(max_length=32, null=False, default="ACTIVE",
                             choices=STATES)
    public = models.BooleanField(default=False)
    device_owner = models.CharField('Device owner', max_length=128, null=True)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u"<NIC %s:vm:%s network:%s>" % \
            (self.id, self.machine_id, self.network_id)

    @property
    def backend_uuid(self):
        """Return the backend id by prepending backend-prefix."""
        return u"%snic-%s" % (settings.BACKEND_PREFIX_ID, str(self.id))

    @property
    def ipv4_address(self):
        return self.get_ip_address(version=4)

    @property
    def ipv6_address(self):
        return self.get_ip_address(version=6)

    def get_ip_address(self, version=4):
        for ip in self.ips.all():
            if ip.ipversion == version:
                return ip.address
        return None

    def get_ip_addresses_subnets(self):
        return self.ips.values_list("address", "subnet__id")


class SecurityGroup(models.Model):
    SECURITY_GROUP_NAME_LENGTH = 128
    name = models.CharField('group name',
                            max_length=SECURITY_GROUP_NAME_LENGTH)

    @property
    def backend_uuid(self):
        """Return the name of NIC in Ganeti."""
        return "%snic-%s" % (settings.BACKEND_PREFIX_ID, str(self.id))


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

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u"<BridgePool id:%s>" % self.id


class MacPrefixPoolTable(PoolTable):
    manager = pools.MacPrefixPool

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u"<MACPrefixPool id:%s>" % self.id


class IPPoolTable(PoolTable):
    manager = pools.IPPool

    subnet = models.ForeignKey('Subnet', related_name="ip_pools",
                               on_delete=models.PROTECT,
                               db_index=True, null=True)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u"<IPv4AdressPool, Subnet: %s>" % self.subnet_id


@contextmanager
def pooled_rapi_client(obj):
        if isinstance(obj, (VirtualMachine, BackendNetwork)):
            backend = obj.backend
        else:
            backend = obj

        if backend.offline:
            log.warning("Trying to connect with offline backend: %s", backend)
            raise faults.ServiceUnavailable("Cannot connect to offline"
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
        return self.get_queryset().filter(vm=vm, created__gt=created_since,
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
    machine = models.ForeignKey('VirtualMachine', related_name="diagnostics",
                                on_delete=models.CASCADE)
    level = models.CharField(max_length=20, choices=TYPES)
    source = models.CharField(max_length=100)
    source_date = models.DateTimeField(null=True)
    message = models.CharField(max_length=255)
    details = models.TextField(null=True)

    class Meta:
        ordering = ['-created']


class VolumeManager(models.Manager):
    """Custom manager for :class:`Volume` model."""

    def for_user(self, userid=None, projects=None):
        """Return volumes that are accessible by the user.

        Volumes that are accessible by the user are those that are owned by the
        user and those that are shared to the projects that the user is member.

        """

        _filter = models.Q()

        if userid:
            _filter |= models.Q(userid=userid)
        if projects:
            _filter |= (models.Q(shared_to_project=True) &\
                        models.Q(project__in=projects))

        return self.get_queryset().filter(_filter)


class Volume(models.Model):
    """Model representing a detachable block storage device."""

    STATUS_VALUES = (
        ("CREATING", "The volume is being created"),
        ("AVAILABLE", "The volume is ready to be attached to an instance"),
        ("ATTACHING", "The volume is attaching to an instance"),
        ("DETACHING", "The volume is detaching from an instance"),
        ("IN_USE", "The volume is attached to an instance"),
        ("DELETING", "The volume is being deleted"),
        ("DELETED", "The volume has been deleted"),
        ("ERROR", "An error has occured with the volume"),
        ("ERROR_DELETING", "There was an error deleting this volume"),
        ("BACKING_UP", "The volume is being backed up"),
        ("RESTORING_BACKUP", "A backup is being restored to the volume"),
        ("ERROR_RESTORING", "There was an error restoring a backup from the"
                            " volume")
    )

    NAME_LENGTH = 255
    DESCRIPTION_LENGTH = 255
    SOURCE_IMAGE_PREFIX = "image:"
    SOURCE_SNAPSHOT_PREFIX = "snapshot:"
    SOURCE_VOLUME_PREFIX = "volume:"

    objects = VolumeManager()
    name = models.CharField("Name", max_length=NAME_LENGTH, null=True)
    description = models.CharField("Description",
                                   max_length=DESCRIPTION_LENGTH, null=True)
    userid = models.CharField("Owner's UUID", max_length=100, null=False,
                              db_index=True)
    project = models.CharField(max_length=255, null=True, db_index=True)
    shared_to_project = models.BooleanField('Shared to project',
                                            default=False)
    size = models.IntegerField("Volume size in GB",  null=False)
    volume_type = models.ForeignKey(VolumeType, related_name="volumes",
                                    on_delete=models.PROTECT, null=False)

    delete_on_termination = models.BooleanField("Delete on Server Termination",
                                                default=True, null=False)

    source = models.CharField(max_length=128, null=True)
    source_version = models.IntegerField(null=True)
    origin = models.CharField(max_length=128, null=True)

    deleted = models.BooleanField("Deleted", default=False, null=False,
                                  db_index=True)
    # Datetime fields
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    # Status
    status = models.CharField("Status", max_length=64,
                              choices=STATUS_VALUES,
                              default="CREATING", null=False)
    snapshot_counter = models.PositiveIntegerField(default=0, null=False)

    machine = models.ForeignKey("VirtualMachine",
                                related_name="volumes",
                                null=True)
    index = models.IntegerField("Index", null=True)
    backendjobid = models.PositiveIntegerField(null=True)
    serial = models.ForeignKey(QuotaHolderSerial, related_name='volume',
                               null=True, on_delete=models.SET_NULL)

    # This field will be used only for pre 0.4.1-2 Archipelago volumes, since
    # they used the Ganeti name and not the canonical name that Synnefo
    # provides. For more info, please consult the design document for
    # detachable volumes.
    legacy_backend_volume_uuid = models.CharField("Legacy volume UUID in"
                                                  " backend", max_length=128,
                                                  null=True)

    @property
    def backend_volume_uuid(self):
        return (self.legacy_backend_volume_uuid or
                u"%svol-%d" % (settings.BACKEND_PREFIX_ID, self.id))

    @property
    def backend_disk_uuid(self):
        return (self.legacy_backend_volume_uuid or
                u"%sdisk-%d" % (settings.BACKEND_PREFIX_ID, self.id))

    @property
    def source_image_id(self):
        src = self.source
        if src and src.startswith(self.SOURCE_IMAGE_PREFIX):
            return src[len(self.SOURCE_IMAGE_PREFIX):]
        else:
            return None

    @property
    def source_snapshot_id(self):
        src = self.source
        if src and src.startswith(self.SOURCE_SNAPSHOT_PREFIX):
            return src[len(self.SOURCE_SNAPSHOT_PREFIX):]
        else:
            return None

    @property
    def source_volume_id(self):
        src = self.source
        if src and src.startswith(self.SOURCE_VOLUME_PREFIX):
            return src[len(self.SOURCE_VOLUME_PREFIX):]
        else:
            return None

    @staticmethod
    def prefix_source(source_id, source_type):
        if source_type == "volume":
            return Volume.SOURCE_VOLUME_PREFIX + str(source_id)
        if source_type == "snapshot":
            return Volume.SOURCE_SNAPSHOT_PREFIX + str(source_id)
        if source_type == "image":
            return Volume.SOURCE_IMAGE_PREFIX + str(source_id)
        elif source_type == "blank":
            return None

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u"<Volume %s:vm:%s>" % (self.id, self.machine_id)


class Metadata(models.Model):
    KEY_LENGTH = 64
    VALUE_LENGTH = 255
    key = models.CharField("Metadata Key", max_length=KEY_LENGTH)
    value = models.CharField("Metadata Value", max_length=VALUE_LENGTH)

    class Meta:
        abstract = True

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u"<%s: %s>" % (self.key, self.value)


class VolumeMetadata(Metadata):
    volume = models.ForeignKey("Volume", related_name="metadata")

    class Meta:
        unique_together = (("volume", "key"),)
        verbose_name = u"Key-Value pair of Volumes metadata"
