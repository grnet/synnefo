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


from django.test import TestCase
from synnefo.db.pools import (PoolManager, EmptyPool, BridgePool,
                              MacPrefixPool, IPPool)
from bitarray import bitarray


class DummyObject():
    def __init__(self, size):
        self.size = size

        self.available_map = ''
        self.reserved_map = ''

    def save(self):
        pass


class DummyPool(PoolManager):
    def value_to_index(self, index):
        return index

    def index_to_value(self, value):
        return value


class PoolManagerTestCase(TestCase):
    def test_created_pool(self):
        obj = DummyObject(42)
        pool = DummyPool(obj)
        self.assertEqual(pool.to_01(), '1' * 42)
        self.assertEqual(pool.to_map(), '.' * 42)
        self.assertEqual(pool.available, bitarray('1' * 42 + '0' * 6))
        self.assertEqual(pool.reserved, bitarray('1' * 42 + '0' * 6))

    def test_save_pool(self):
        obj = DummyObject(42)
        pool = DummyPool(obj)
        pool.save()
        self.assertNotEqual(obj.available_map, '')
        available_map = obj.available_map
        b = DummyPool(obj)
        b.save()
        self.assertEqual(obj.available_map, available_map)

    def test_empty_pool(self):
        obj = DummyObject(42)
        pool = DummyPool(obj)
        self.assertEqual(pool.empty(), False)
        for i in range(0, 42):
            self.assertEqual(pool.get(), i)
        self.assertEqual(pool.empty(), True)
        self.assertRaises(EmptyPool, pool.get)

    def test_reserved_value(self):
        obj = DummyObject(42)
        pool = DummyPool(obj)
        available = pool.count_available()
        value = pool.get()
        self.assertEqual(pool.is_available(value), False)
        self.assertEqual(pool.count_available(), available - 1)
        pool.put(value)
        self.assertEqual(pool.is_available(value), True)
        self.assertEqual(pool.count_available(), available)

    def test_external_reserved(self):
        obj = DummyObject(42)
        pool = DummyPool(obj)
        for i in range(42, 48):
            self.assertEqual(pool.is_available(i), False)
        pool.reserve(32, external=True)
        values = []
        while True:
            try:
                values.append(pool.get())
            except EmptyPool:
                break
        self.assertEqual(32 not in values, True)

    def test_external_reserved_2(self):
        obj = DummyObject(42)
        pool = DummyPool(obj)
        self.assertEqual(pool.get(), 0)
        pool.reserve(0, external=True)
        pool.put(0)
        self.assertEqual(pool.get(), 1)

    def test_extend_pool(self):
        obj = DummyObject(42)
        pool = DummyPool(obj)
        pool.extend(7)
        self.assertEqual(pool.to_01(), '1' * 49)
        self.assertEqual(pool.to_map(), '.' * 49)
        self.assertEqual(pool.available, bitarray('1' * 49 + '0' * 7))
        self.assertEqual(pool.reserved, bitarray('1' * 49 + '0' * 7))

    def test_shrink_pool(self):
        obj = DummyObject(42)
        pool = DummyPool(obj)
        pool.shrink(3)
        self.assertEqual(pool.to_01(), '1' * 39)
        self.assertEqual(pool.to_map(), '.' * 39)
        self.assertEqual(pool.available, bitarray('1' * 39 + '0' * 1))
        self.assertEqual(pool.reserved, bitarray('1' * 39 + '0' * 1))


class BridgePoolTestCase(TestCase):
    def test_bridge_conversion(self):
        obj = DummyObject(13)
        obj.base = "bridge"
        pool = BridgePool(obj)
        for i in range(0, 13):
            self.assertEqual("bridge" + str(i + 1), pool.get())
        pool.put("bridge2")
        pool.put("bridge6")
        self.assertEqual("bridge2", pool.get())
        self.assertEqual("bridge6", pool.get())
        self.assertEqual(pool.empty(), True)


class MacPrefixPoolTestCase(TestCase):
    def test_invalid_mac_reservation(self):
        obj = DummyObject(65636)
        obj.base = 'ab:ff:ff'
        pool = MacPrefixPool(obj)
        for i in range(0, 65536):
            self.assertEqual(pool.is_available(i, index=True), False)


class IPPoolTestCase(TestCase):
    def test_auto_reservations(self):
        obj = DummyObject(0)
        network = DummyObject(0)
        obj.network = network
        network.subnet = '192.168.2.0/24'
        network.gateway = '192.168.2.1'
        pool = IPPool(obj)
        self.assertEqual(pool.is_available('192.168.2.0'), False)
        self.assertEqual(pool.is_available('192.168.2.1'), False)
        self.assertEqual(pool.is_available('192.168.2.255'), False)
        self.assertEqual(pool.count_available(), 253)
        self.assertEqual(pool.get(), '192.168.2.2')

    def test_auto_reservations_2(self):
        obj = DummyObject(0)
        network = DummyObject(0)
        obj.network = network
        network.subnet = '192.168.2.0/31'
        network.gateway = '192.168.2.1'
        pool = IPPool(obj)
        self.assertEqual(pool.is_available('192.168.2.0'), False)
        self.assertEqual(pool.is_available('192.168.2.1'), False)
        self.assertEqual(pool.size(), 8)
        self.assertEqual(pool.empty(), True)
