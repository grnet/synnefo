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
    subnet = factory.Sequence(lambda n: '192.168.{0}.0/24'.format(n))
    gateway = factory.LazyAttribute(lambda a: a.subnet[:-4] + '1')
    dhcp = False
    flavor = factory.Sequence(round_seq(models.Network.FLAVORS.keys()))
    mode = factory.LazyAttribute(lambda a:
                                 models.Network.FLAVORS[a.flavor]['mode'])
    link = factory.Sequence(prefix_seq('link'))
    mac_prefix = 'aa:00:0'
    tags = factory.LazyAttribute(lambda a:
                                 models.Network.FLAVORS[a.flavor]['tags'])
    public = False
    deleted = False
    state = factory.Sequence(round_seq_first(models.Network.OPER_STATES))


class DeletedNetwork(NetworkFactory):
    deleted = True


class BackendNetworkFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.BackendNetwork

    network = factory.SubFactory(NetworkFactory)
    backend = factory.SubFactory(BackendFactory)
    operstate = factory.Sequence(round_seq_first(FACTORY_FOR.OPER_STATES))


class NetworkInterfaceFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.NetworkInterface

    machine = factory.SubFactory(VirtualMachineFactory)
    network = factory.SubFactory(NetworkFactory)
    index = factory.Sequence(lambda x: x, type=int)
    mac = factory.Sequence(lambda n:
        'aa:{0}{0}:{0}{0}:aa:{0}{0}:{0}{0}'.format(hex(int(n) % 15)[2:3]))
    ipv4 = factory.LazyAttributeSequence(lambda a, n: a.network.subnet[:-4] +
                                         '{0}'.format(int(n) + 2))
    state = "ACTIVE"
    firewall_profile =\
        factory.Sequence(round_seq_first(FACTORY_FOR.FIREWALL_PROFILES))


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
