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

"""Unit Tests for the Singleton classes in synnefo.lib.singleton

Provides unit tests for the code implementing Singleton
classes in the synnefo.lib.singleton module.

"""

import unittest

from synnefo.lib.singleton import ArgBasedSingleton, ArgBasedSingletonMeta


class SubClassOne(ArgBasedSingleton):
    name = None

    def __init__(self, name):
        self.name = name


class SubClassTwo(ArgBasedSingleton):
    name = None

    def __init__(self, name):
        self.name = name


class SubClassThree(SubClassTwo):
    name2 = None

    def __init__(self, name):
        self.name2 = name


class SubClassKwArgs(ArgBasedSingleton):
    name = None

    def __init__(self, onearg, **kwargs):
        self.name = onearg
        for x in kwargs:
            setattr(self, x, kwargs[x])


class SubClassNoReinit(ArgBasedSingleton):
    initialized = None

    def __init__(self, *args, **kwargs):
        if self.initialized:
            raise Exception("__init__ called twice!")
        self.initialized = True


class ArgBasedSingletonTestCase(unittest.TestCase):
    def test_same_object(self):
        o1 = ArgBasedSingleton()
        o2 = ArgBasedSingleton()
        self.assertTrue(o1 is o2)


class MyMeta(ArgBasedSingletonMeta):
    def __call__(cls, *args, **kw):
        return super(MyMeta, cls).__call__(*args, **kw)


class BaseClass(object):
    __metaclass__ = MyMeta

    def ret5(self):
        return 5


class SubClassMultiple(BaseClass, ArgBasedSingleton):
    name = None

    def __init__(self, name):
        name = name


class SubClassTestCase(unittest.TestCase):
    def test_same_object(self):
        o1 = SubClassOne('one')
        o2 = SubClassOne('two')
        o1a = SubClassOne('one')

        self.assertEqual(o1.name, 'one')
        self.assertEqual(o2.name, 'two')
        self.assertEqual(o1a.name, 'one')
        self.assertFalse(o1 is o2)
        self.assertTrue(o1 is o1a)

    def test_different_classes(self):
        o1 = SubClassOne('one')
        o2 = SubClassTwo('one')

        self.assertEqual(o1.name, 'one')
        self.assertEqual(o2.name, 'one')
        self.assertFalse(o1 is o2)


class SubClassKwArgsTestCase(unittest.TestCase):
    def test_init_signature(self):
        self.assertRaises(TypeError, SubClassKwArgs, 'one', 'two')

    def test_distinct_kwargs(self):
        o1 = SubClassKwArgs('one', a=1)
        o2 = SubClassKwArgs('two')
        o1a = SubClassKwArgs('one', a=2)
        o1b = SubClassKwArgs('one', a=1)
        o1c = SubClassKwArgs('one', a=1, b=2)
        o1d = SubClassKwArgs('one', b=2, a=1)

        self.assertEqual(o1.a, 1)
        self.assertEqual(o1a.a, 2)
        self.assertEqual(o1b.a, 1)
        self.assertRaises(AttributeError, getattr, o2, 'a')
        self.assertFalse(o1 is o2)
        self.assertFalse(o1 is o1a)
        self.assertTrue(o1 is o1b)
        self.assertTrue(o1c is o1d)


class SubClassDistinctDicts(unittest.TestCase):
    def test_distinct_storage_per_subclass(self):
        o1 = SubClassOne('one')
        o2 = SubClassTwo('one')
        o1a = SubClassOne('two')
        o2a = SubClassTwo('two')

        self.assertEqual(o1.name, 'one')
        self.assertEqual(o2.name, 'one')
        self.assertEqual(o1a.name, 'two')
        self.assertEqual(o2a.name, 'two')
        self.assertTrue(o1._singles is o1a._singles)
        self.assertTrue(o2._singles is o2a._singles)
        self.assertFalse(o1._singles is o2._singles)
        self.assertFalse(o1a._singles is o2a._singles)


class SubClassThreeTestCase(unittest.TestCase):
    def test_singleton_inheritance(self):
        o1 = SubClassThree('one')
        o2 = SubClassThree('two')
        o1a = SubClassThree('one')

        self.assertEquals(o1.name2, 'one')
        self.assertEquals(o2.name2, 'two')
        self.assertEquals(o1a.name2, 'one')

        self.assertTrue(o1 is o1a)
        self.assertFalse(o1 is o2)


class SubClassMultipleTestCase(unittest.TestCase):
    def test_multiple_inheritance(self):
        o1 = SubClassMultiple('one')
        o2 = SubClassMultiple('two')
        o1a = SubClassMultiple('one')

        self.assertEquals(o1.ret5(), 5)
        self.assertEquals(o2.ret5(), 5)
        self.assertEquals(o1a.ret5(), 5)

        self.assertTrue(o1 is o1a)
        self.assertFalse(o1 is o2)


class SubClassNoReinitTestCase(unittest.TestCase):
    def test_no_reinit(self):
        o1 = SubClassNoReinit('one')
        o2 = SubClassNoReinit('one')

        self.assertTrue(o1 is o2)


if __name__ == '__main__':
    unittest.main()
