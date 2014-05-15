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


from django.test import TestCase
from synnefo.db.pools import (PoolManager, EmptyPool, BridgePool,
                              MacPrefixPool, IPPool, find_padding,
                              bitarray_to_map, ValueNotAvailable,
                              InvalidValue)
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
            self.assertRaises(InvalidValue, pool.is_available, i)
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

    def test_shrink_in_use(self):
        obj = DummyObject(8)
        pool = DummyPool(obj)
        pool._reserve(6)
        self.assertRaises(Exception, pool.shrink, 3)

    def test_count(self):
        obj = DummyObject(10)
        pool = DummyPool(obj)
        pool._reserve(1)
        pool._reserve(3)
        pool._reserve(4)
        pool._reserve(2, external=True)
        self.assertEqual(pool.count_available(), 6)
        self.assertEqual(pool.count_unavailable(), 4)
        self.assertEqual(pool.count_reserved(), 1)
        self.assertEqual(pool.count_unreserved(), 9)


class HelpersTestCase(TestCase):
    def test_find_padding(self):
        self.assertEqual(find_padding(1), 7)
        self.assertEqual(find_padding(8), 0)
        self.assertEqual(find_padding(12), 4)
        self.assertEqual(find_padding(16), 0)

    def test_bitarray_to_map(self):
        bt = bitarray('01001100101')
        map_ = bitarray_to_map(bt)
        self.assertEqual(map_, 'X.XX..XX.X.')


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
        for i in range(0, 65535):
            self.assertEqual(pool.is_available(i, index=True), False)

    def test_mac_prefix_conversion(self):
        obj = DummyObject(13)
        obj.base = 'aa:00:0'
        pool = MacPrefixPool(obj)
        for i in range(1, 9):
            self.assertEqual("aa:00:%s" % i, pool.get())

    def test_value_to_index(self):
        obj = DummyObject(13)
        obj.base = 'aa:00:0'
        pool = MacPrefixPool(obj)
        index = pool.value_to_index('aa:bc:ee')
        val = pool.index_to_value(index)
        self.assertEqual(val, 'aa:bc:ee')


class IPPoolTestCase(TestCase):
    def test_get_with_value(self):
        obj = DummyObject(16)
        subnet = DummyObject(0)
        obj.subnet = subnet
        subnet.cidr = "192.168.2.0/28"
        subnet.gateway = None
        obj.base = "192.168.2.0/28"
        obj.offset = 0
        pool = IPPool(obj)
        # Test if reserved
        pool.reserve("192.168.2.2")
        self.assertRaises(ValueNotAvailable, pool.get, "192.168.2.2")
        # Test if externally reserved
        pool.reserve("192.168.2.3", external=True)
        self.assertRaises(ValueNotAvailable, pool.get, "192.168.2.3")
        self.assertRaises(InvalidValue, pool.get, "192.168.2.16")
