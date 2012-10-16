#!/usr/bin/env python
#
# -*- coding: utf-8 -*-
#
# Copyright 2011 GRNET S.A. All rights reserved.
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
#
#

"""Unit Tests for the pool classes in synnefo.lib.pool

Provides unit tests for the code implementing pool
classes in the synnefo.lib.pool module.

"""

# Support running under a gevent-monkey-patched environment
# if the "monkey" argument is specified in the command line.
import sys
if "monkey" in sys.argv:
    from gevent import monkey
    monkey.patch_all()
    sys.argv.pop(sys.argv.index("monkey"))

import sys
import time
import threading
from collections import defaultdict

from synnefo.lib.pool import ObjectPool, PoolLimitError, PoolVerificationError
from synnefo.lib.pool.http import get_http_connection
from synnefo.lib.pool.http import _pools as _http_pools

# Use backported unittest functionality if Python < 2.7
try:
    import unittest2 as unittest
except ImportError:
    if sys.version_info < (2, 7):
        raise Exception("The unittest2 package is required for Python < 2.7")
    import unittest


from threading import Lock

mutex = Lock()


class NumbersPool(ObjectPool):
    max = 0

    def _pool_create_safe(self):
        with mutex:
            n = self.max
            self.max += 1
        return n

    def _pool_create_unsafe(self):
        n = self.max
        self.max += 1
        return n

    # set this to _pool_create_unsafe to check
    # the thread-safety test
    #_pool_create = _pool_create_unsafe
    _pool_create = _pool_create_safe

    def _pool_verify(self, obj):
        return True

    def _pool_cleanup(self, obj):
        n = int(obj)
        if n < 0:
            return True
        return False


class ObjectPoolTestCase(unittest.TestCase):
    def test_create_pool_requires_size(self):
        """Test __init__() requires valid size argument"""
        self.assertRaises(ValueError, ObjectPool)
        self.assertRaises(ValueError, ObjectPool, size="size10")
        self.assertRaises(ValueError, ObjectPool, size=0)
        self.assertRaises(ValueError, ObjectPool, size=-1)

    def test_create_pool(self):
        """Test pool creation works"""
        pool = ObjectPool(100)
        self.assertEqual(pool.size, 100)

    def test_get_not_implemented(self):
        """Test pool_get() method not implemented in abstract class"""
        pool = ObjectPool(100)
        self.assertRaises(NotImplementedError, pool._pool_create)
        self.assertRaises(NotImplementedError, pool._pool_verify, None)

    def test_put_not_implemented(self):
        """Test pool_put() method not implemented in abstract class"""
        pool = ObjectPool(100)
        self.assertRaises(NotImplementedError, pool._pool_cleanup, None)


class NumbersPoolTestCase(unittest.TestCase):
    N = 1500
    SEC = 0.5
    maxDiff = None

    def setUp(self):
        self.numbers = NumbersPool(self.N)

    def test_initially_empty(self):
        """Test pool is empty upon creation"""
        self.assertEqual(self.numbers._set, set([]))

    def test_seq_allocate_all(self):
        """Test allocation and deallocation of all pool objects"""
        n = []
        for _ in xrange(0, self.N):
            n.append(self.numbers.pool_get())
        self.assertEqual(n, range(0, self.N))
        for i in n:
            self.numbers.pool_put(i)
        self.assertEqual(self.numbers._set, set(n))

    def test_parallel_allocate_all(self):
        """Allocate all pool objects in parallel"""
        def allocate_one(pool, results, index):
            n = pool.pool_get()
            results[index] = n

        results = [None] * self.N
        threads = [threading.Thread(target=allocate_one,
                                    args=(self.numbers, results, i))
                   for i in xrange(0, self.N)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # This nonblocking pool_get() should fail
        self.assertRaises(PoolLimitError, self.numbers.pool_get,
                          blocking=False)
        self.assertEqual(sorted(results), range(0, self.N))

    def test_allocate_no_create(self):
        """Allocate objects from the pool without creating them"""
        for i in xrange(0, self.N):
            self.assertIsNone(self.numbers.pool_get(create=False))

        # This nonblocking pool_get() should fail
        self.assertRaises(PoolLimitError, self.numbers.pool_get,
                          blocking=False)

    def test_pool_cleanup_returns_failure(self):
        """Put a broken object, test a new one is retrieved eventually"""
        n = []
        for _ in xrange(0, self.N):
            n.append(self.numbers.pool_get())
        self.assertEqual(n, range(0, self.N))

        del n[-1:]
        self.numbers.pool_put(-1)  # This is a broken object
        self.assertFalse(self.numbers._set)
        self.assertEqual(self.numbers.pool_get(), self.N)

    def test_parallel_get_blocks(self):
        """Test threads block if no object left in the pool"""
        def allocate_one_and_sleep(pool, sec, result, index):
            n = pool.pool_get()
            time.sleep(sec)
            result[index] = n
            pool.pool_put(n)

        nr_threads = 2 * self.N + 1
        results = [None] * nr_threads
        threads = [threading.Thread(target=allocate_one_and_sleep,
                                    args=(self.numbers, self.SEC, results, i))
                   for i in xrange(nr_threads)]

        # This should take 3 * SEC seconds
        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        diff = time.time() - start
        self.assertTrue(diff > 3 * self.SEC)
        self.assertLess((diff - 3 * self.SEC) / 3 * self.SEC, .5)

        freq = defaultdict(int)
        for r in results:
            freq[r] += 1

        # The maximum number used must be exactly the pool size.
        self.assertEqual(max(results), self.N - 1)
        # At least one number must have been used three times
        triples = [r for r in freq if freq[r] == 3]
        self.assertGreater(len(triples), 0)
        # The sum of all frequencies must equal to the number of threads.
        self.assertEqual(sum(freq.values()), nr_threads)

    def test_verify_create(self):
        numbers = self.numbers
        nums = [numbers.pool_get() for _ in xrange(self.N)]
        for num in nums:
            numbers.pool_put(num)

        def verify(num):
            if num in nums:
                return False
            return True

        self.numbers._pool_verify = verify
        self.assertEqual(numbers.pool_get(), self.N)

    def test_verify_error(self):
        numbers = self.numbers
        nums = [numbers.pool_get() for _ in xrange(self.N)]
        for num in nums:
            numbers.pool_put(num)

        def false(*args):
            return False

        self.numbers._pool_verify = false
        self.assertRaises(PoolVerificationError, numbers.pool_get)


class ThreadSafetyTestCase(unittest.TestCase):

    pool_class = NumbersPool

    def setUp(self):
        size = 3000
        self.size = size
        self.pool = self.pool_class(size)

    def test_parallel_sleeping_create(self):
        def create(pool, results, i):
            time.sleep(1)
            results[i] = pool._pool_create()

        pool = self.pool
        N = self.size
        results = [None] * N
        threads = [threading.Thread(target=create, args=(pool, results, i))
                   for i in xrange(N)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        freq = defaultdict(int)
        for r in results:
            freq[r] += 1

        mults = [(n, c) for n, c in freq.items() if c > 1]
        if mults:
            #print mults
            raise AssertionError("_pool_create() is not thread safe")


class TestHTTPConnectionTestCase(unittest.TestCase):
    def test_double_close(self):
        conn = get_http_connection("127.0.0.1", "http")
        self.assertEqual(conn._pool, _http_pools[("http", "127.0.0.1")])
        conn.close()
        self.assertIsNone(conn._pool)
        # This call does nothing, because conn._pool is already None
        conn.close()
        self.assertIsNone(conn._pool)

    def test_distinct_pools_per_scheme(self):
        conn = get_http_connection("127.0.0.1", "http")
        pool = conn._pool
        self.assertTrue(pool is _http_pools[("http", "127.0.0.1")])
        conn.close()
        conn2 = get_http_connection("127.0.0.1", "https")
        self.assertTrue(conn is not conn2)
        self.assertNotEqual(pool, conn2._pool)
        self.assertTrue(conn2._pool is _http_pools[("https", "127.0.0.1")])
        conn2.close()

if __name__ == '__main__':
    unittest.main()
