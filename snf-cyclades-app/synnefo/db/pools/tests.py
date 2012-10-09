import sys
from synnefo.db.pools import (PoolManager, EmptyPool, BridgePool,
                              MacPrefixPool, IPPool)

# Use backported unittest functionality if Python < 2.7
try:
    import unittest2 as unittest
except ImportError:
    if sys.version_info < (2, 7):
        raise Exception("The unittest2 package is required for Python < 2.7")
    import unittest


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


class PoolManagerTestCase(unittest.TestCase):
    def test_created_pool(self):
        obj = DummyObject(42)
        pool = DummyPool(obj)
        self.assertEqual(pool.to_01(), '1' * 42 + '0' * 6)
        self.assertEqual(pool.to_map(), '.' * 42 + 'X' * 6)

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


class BridgePoolTestCase(unittest.TestCase):
    def test_bridge_conversion(self):
        obj = DummyObject(13)
        obj.base = "bridge"
        pool = BridgePool(obj)
        for i in range(0, 13):
            self.assertEqual("bridge" + str(i), pool.get())
        pool.put("bridge2")
        pool.put("bridge6")
        self.assertEqual("bridge2", pool.get())
        self.assertEqual("bridge6", pool.get())
        self.assertEqual(pool.empty(), True)


class MacPrefixPoolTestCase(unittest.TestCase):
    def test_invalid_mac_reservation(self):
        obj = DummyObject(65636)
        obj.base = 'ab:ff:ff'
        pool = MacPrefixPool(obj)
        for i in range(0, 65536):
            self.assertEqual(pool.is_available(i, index=True), False)

class IPPoolTestCase(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
