# Copyright (C) 2010-2014 GRNET S.A.
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

import factory
from factory.fuzzy import FuzzyChoice
from synnefo.db import models
from random import choice
from string import letters, digits


def prefix_seq(x):
    return lambda n: x + '-{0}'.format(n)


def user_seq():
    return lambda n: 'user-{0}.example.com'.format(n)


def round_seq(x):
    size = len(x)
    return lambda n: x[int(n) % size]


def round_seq_first(x):
    size = len(x)
    return lambda n: x[int(n) % size][0]


def random_string(x):
    """Returns a random string of length x"""
    return ''.join([choice(digits + letters) for i in range(x)])


class VolumeTypeFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.VolumeType
    FACTORY_DJANGO_GET_OR_CREATE = ("disk_template",)
    name = factory.Sequence(prefix_seq("vtype"))
    disk_template = FuzzyChoice(
        choices=["file", "plain", "drbd", "ext_archipelago"]
    )
    deleted = False


class FlavorFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.Flavor

    cpu = factory.Sequence(lambda n: n + 2, type=int)
    ram = factory.Sequence(lambda n: n * 512, type=int)
    disk = factory.Sequence(lambda n: n * 10, type=int)
    volume_type = factory.SubFactory(VolumeTypeFactory)
    deleted = False


class BackendFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.Backend

    clustername = factory.Sequence(prefix_seq('cluster'))
    port = 5080
    username = factory.Sequence(prefix_seq('username'))
    password = factory.Sequence(prefix_seq('password'))
    drained = False
    offline = False

    mfree = 8192
    mtotal = 16384
    dfree = 132423
    dtotal = 14921932
    pinst_cnt = 2
    ctotal = 80

    disk_templates = ["file", "plain", "drbd", "ext"]


class DrainedBackend(BackendFactory):
    drained = True


class OfflineBackend(BackendFactory):
    offline = True


class VirtualMachineFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.VirtualMachine

    name = factory.Sequence(prefix_seq('vm'))
    userid = factory.Sequence(user_seq())
    backend = factory.SubFactory(BackendFactory)
    imageid = '78491238479120243171243'
    flavor = factory.SubFactory(FlavorFactory)
    deleted = False
    suspended = False
    #operstate = factory.Sequence(round_seq_first(FACTORY_FOR.OPER_STATES))
    operstate = "STARTED"


class VolumeFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.Volume
    userid = factory.Sequence(user_seq())
    size = factory.Sequence(lambda x: x, type=int)
    name = factory.Sequence(lambda x: "volume-name-"+x, type=str)
    machine = factory.SubFactory(VirtualMachineFactory,
                                 userid=factory.SelfAttribute('..userid'))
    volume_type = factory.SubFactory(VolumeTypeFactory)


class DeletedVirtualMachine(VirtualMachineFactory):
    deleted = True


class ErrorVirtualMachine(VirtualMachineFactory):
    operstate = "ERROR"


class BuildVirtualMachine(VirtualMachineFactory):
    operstate = "BUILD"


class DestroyedVirtualMachine(VirtualMachineFactory):
    operstate = "DESTROYED"


class StartedVirtualMachine(VirtualMachineFactory):
    operstate = "STARTED"


class StopedVirtualMachine(VirtualMachineFactory):
    operstate = "STOPED"


class VirtualMachineMetadataFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.VirtualMachineMetadata

    meta_key = factory.Sequence(prefix_seq('key'))
    meta_value = factory.Sequence(prefix_seq('pass'))
    vm = factory.SubFactory(VirtualMachineFactory)


class NetworkFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.Network

    name = factory.Sequence(prefix_seq('network'))
    userid = factory.Sequence(user_seq())
    flavor = factory.Sequence(round_seq(models.Network.FLAVORS.keys()))
    mode = factory.LazyAttribute(lambda a:
                                 models.Network.FLAVORS[a.flavor]['mode'])
    link = factory.Sequence(prefix_seq('snf-link'))
    mac_prefix = 'aa:00:0'
    tags = factory.LazyAttribute(lambda a:
                                 models.Network.FLAVORS[a.flavor]['tags'])
    public = False
    deleted = False
    state = "ACTIVE"


class DeletedNetwork(NetworkFactory):
    deleted = True


class BackendNetworkFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.BackendNetwork

    network = factory.SubFactory(NetworkFactory, state="ACTIVE")
    backend = factory.SubFactory(BackendFactory)
    operstate = factory.Sequence(round_seq_first(FACTORY_FOR.OPER_STATES))


class NetworkInterfaceFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.NetworkInterface

    userid = factory.Sequence(user_seq())
    name = factory.LazyAttribute(lambda self: random_string(30))
    machine = factory.SubFactory(VirtualMachineFactory, operstate="STARTED")
    network = factory.SubFactory(NetworkFactory, state="ACTIVE")
    index = factory.Sequence(lambda x: x, type=int)
    mac = factory.Sequence(lambda n: 'aa:{0}{0}:{0}{0}:aa:{0}{0}:{0}{0}'
                           .format(hex(int(n) % 15)[2:3]))
    public = factory.LazyAttribute(lambda self: self.network.public)
    state = "ACTIVE"
    firewall_profile =\
        factory.Sequence(round_seq_first(FACTORY_FOR.FIREWALL_PROFILES))


class IPPoolTableFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.IPPoolTable


class SubnetFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.Subnet
    network = factory.SubFactory(NetworkFactory, state="ACTIVE")
    name = factory.LazyAttribute(lambda self: random_string(30))
    dhcp = True
    dns_nameservers = []
    host_routes = []
    userid = factory.LazyAttribute(lambda self: self.network.userid)
    public = factory.LazyAttribute(lambda self: self.network.public)


class IPv4SubnetFactory(SubnetFactory):
    ipversion = 4
    cidr = factory.Sequence(lambda n: '192.168.{0}.0/24'.format(n))
    gateway = factory.LazyAttribute(lambda a: a.cidr[:-4] + '1')
    pool = factory.RelatedFactory(IPPoolTableFactory, 'subnet', base=cidr,
                                  offset=2,
                                  size=253)


class IPv6SubnetFactory(SubnetFactory):
    ipversion = 6
    cidr = "2001:648:2ffc:1112::/64"
    gateway = None


class NetworkWithSubnetFactory(NetworkFactory):
    subnet = factory.RelatedFactory(IPv4SubnetFactory, 'network')
    subnet6 = factory.RelatedFactory(IPv6SubnetFactory, 'network')


class IPv4AddressFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.IPAddress

    userid = factory.Sequence(user_seq())
    network = factory.SubFactory(NetworkFactory, state="ACTIVE")
    subnet = factory.SubFactory(IPv4SubnetFactory,
                                network=factory.SelfAttribute('..network'))
    ipversion = 4
    address =\
        factory.LazyAttributeSequence(lambda self, n: self.subnet.cidr[:-4] +
                                      '{0}'.format(int(n) + 2))
    nic = factory.SubFactory(NetworkInterfaceFactory,
                             userid=factory.SelfAttribute('..userid'),
                             network=factory.SelfAttribute('..network'))


class IPv6AddressFactory(IPv4AddressFactory):
    FACTORY_FOR = models.IPAddress

    subnet = factory.SubFactory(IPv6SubnetFactory)
    network = factory.SubFactory(NetworkFactory, state="ACTIVE")
    address = "babe::"
    ipversion = 6
    nic = factory.SubFactory(NetworkInterfaceFactory,
                             network=factory.SelfAttribute('..network'))


class FloatingIPFactory(IPv4AddressFactory):
    network = factory.SubFactory(NetworkFactory, public=True,
                                 floating_ip_pool=True, state="ACTIVE")
    floating_ip = True


class SecurityGroupFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.SecurityGroup

    name = factory.LazyAttribute(lambda self: random_string(30))


class BridgePoolTableFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.BridgePoolTable

    size = 500
    base = 'snf-link-'


class MacPrefixPoolTableFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.MacPrefixPoolTable
    size = 500
    base = 'aa:00:0'


class QuotaHolderSerialFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.QuotaHolderSerial
    serial = factory.Sequence(lambda x: x, type=int)


class IPAddressLogFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.IPAddressLog
    address = "192.168.2.1"
    server_id = 1
    network_id = 1
    active = True
