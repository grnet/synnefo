# Copyright 2012 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

import factory
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


class FlavorFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.Flavor

    cpu = factory.Sequence(lambda n: n + 2, type=int)
    ram = factory.Sequence(lambda n: n * 512, type=int)
    disk = factory.Sequence(lambda n: n * 10, type=int)
    disk_template = 'drbd'
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

    disk_templates = ["file", "plain", "drbd"]


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
    operstate = factory.Sequence(round_seq_first(FACTORY_FOR.OPER_STATES))


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
    link = factory.Sequence(prefix_seq('link'))
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

    network = factory.SubFactory(NetworkFactory)
    backend = factory.SubFactory(BackendFactory)
    operstate = factory.Sequence(round_seq_first(FACTORY_FOR.OPER_STATES))


class NetworkInterfaceFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.NetworkInterface

    name = factory.LazyAttribute(lambda self: random_string(30))
    machine = factory.SubFactory(VirtualMachineFactory)
    network = factory.SubFactory(NetworkFactory)
    index = factory.Sequence(lambda x: x, type=int)
    mac = factory.Sequence(lambda n: 'aa:{0}{0}:{0}{0}:aa:{0}{0}:{0}{0}'
                           .format(hex(int(n) % 15)[2:3]))
    state = "ACTIVE"
    firewall_profile =\
        factory.Sequence(round_seq_first(FACTORY_FOR.FIREWALL_PROFILES))


class IPPoolTableFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.IPPoolTable
    size = 0


class SubnetFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.Subnet
    network = factory.SubFactory(NetworkFactory, state="ACTIVE")
    name = factory.LazyAttribute(lambda self: random_string(30))
    dhcp = True
    dns_nameservers = []
    host_routes = []


class IPv4SubnetFactory(SubnetFactory):
    ipversion = 4
    cidr = factory.Sequence(lambda n: '192.168.{0}.0/24'.format(n))
    gateway = factory.LazyAttribute(lambda a: a.cidr[:-4] + '1')
    pool = factory.RelatedFactory(IPPoolTableFactory, 'subnet')


class IPv6SubnetFactory(SubnetFactory):
    ipversion = 6
    cidr = "2001:648:2ffc:1112::/64"
    gateway = None


class NetworkWithSubnetFactory(NetworkFactory):
    subnet = factory.RelatedFactory(IPv4SubnetFactory, 'network')
    subnet6 = factory.RelatedFactory(IPv6SubnetFactory, 'network')


class IPv4AddressFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.IPAddress

    network = factory.SubFactory(NetworkFactory)
    subnet = factory.SubFactory(IPv4SubnetFactory,
                                network=factory.SelfAttribute('..network'))
    address =\
        factory.LazyAttributeSequence(lambda self, n: self.subnet.cidr[:-4] +
                                      '{0}'.format(int(n) + 2))
    nic = factory.SubFactory(NetworkInterfaceFactory,
                             network=factory.SelfAttribute('..network'))


class IPv6AddressFactory(IPv4AddressFactory):
    FACTORY_FOR = models.IPAddress

    subnet = factory.SubFactory(IPv6SubnetFactory)
    network = factory.SubFactory(NetworkFactory)
    address = "babe::"
    nic = factory.SubFactory(NetworkInterfaceFactory,
                             network=factory.SelfAttribute('..network'))


class FloatingIPFactory(IPv4AddressFactory):
    network = factory.SubFactory(NetworkFactory, public=True,
                                 floating_ip_pool=True)
    floating_ip = True


class SecurityGroupFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.SecurityGroup

    name = factory.LazyAttribute(lambda self: random_string(30))


class BridgePoolTableFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.BridgePoolTable

    size = 20
    base = 'prv'


class MacPrefixPoolTableFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.MacPrefixPoolTable
    size = 100
    base = 'aa:00:0'


class QuotaHolderSerialFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.QuotaHolderSerial
    serial = factory.Sequence(lambda x: x, type=int)
