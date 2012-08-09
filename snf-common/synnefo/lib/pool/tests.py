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

from synnefo.lib.pool import ObjectPool

# Use backported unittest functionality if Python < 2.7
try:
    import unittest2 as unittest
except ImportError:
    if sys.version_info < (2, 7):
        raise Exception("The unittest2 package is required for Python < 2.7")
    import unittest


class NumbersPool(ObjectPool):
    max = 0

    def _create(self):
        n = self.max
        self.max += 1
        return n

    def _cleanup(self, obj):
        pass


class ObjectPoolTestCase(unittest.TestCase):
    def test_create_pool_requires_size(self):
        """Test __init__() requires valid size argument"""
        self.assertRaises(ValueError, ObjectPool)
        self.assertRaises(ValueError, ObjectPool, {"size": 'size10'})
        self.assertRaises(ValueError, ObjectPool, {"size": 0})
        self.assertRaises(ValueError, ObjectPool, {"size": -1})

    def test_create_pool(self):
        """Test pool creation works"""
        pool = ObjectPool(100)
        self.assertEqual(pool.size, 100)

    def test_get_not_implemented(self):
        """Test get() method not implemented in abstract class"""
        pool = ObjectPool(100)
        self.assertRaises(NotImplementedError, pool.get)

    def test_put_not_implemented(self):
        """Test put() method not implemented in abstract class"""
        pool = ObjectPool(100)
        self.assertRaises(NotImplementedError, pool.put, None)


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
            n.append(self.numbers.get())
        self.assertEqual(n, range(0, self.N))
        for i in n:
            self.numbers.put(i)
        self.assertEqual(self.numbers._set, set(n))

    def test_parallel_allocate_all(self):
        """Allocate all pool objects in parallel"""
        def allocate_one(pool, results, index):
            n = pool.get()
            results[index] = n

        results = [None] * self.N
        threads = [threading.Thread(target=allocate_one,
                                    args=(self.numbers, results, i,))
                   for i in xrange(0, self.N)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # This nonblocking pool get() should fail
        self.assertIsNone(self.numbers.get(blocking=False))
        self.assertEqual(sorted(results), range(0, self.N))

    def test_parallel_get_blocks(self):
        """Test threads block if no object left in the pool"""
        def allocate_one_and_sleep(pool, sec, result, index):
            n = pool.get()
            time.sleep(sec)
            result[index] = n
            pool.put(n)

        results = [None] * (2 * self.N + 1)
        threads = [threading.Thread(target=allocate_one_and_sleep,
                                    args=(self.numbers, self.SEC, results, i,))
                   for i in xrange(0, 2 * self.N + 1)]

        # This should take 3 * SEC seconds
        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        diff = time.time() - start
        self.assertTrue(diff > 3 * self.SEC)
        self.assertLess((diff - 3 * self.SEC) / 3 * self.SEC, .5)

        # One number must have been used three times,
        # all others must have been used once
        freq = {}
        for r in results:
            freq[r] = freq.get(r, 0) + 1
        self.assertTrue(len([r for r in results if freq[r] == 2]), self. N)
        triples = [r for r in freq if freq[r] == 3]
        self.assertTrue(len(triples), 1)
        self.assertEqual(sorted(results),
                         sorted(2 * range(0, self.N) + triples))


if __name__ == '__main__':
    unittest.main()
