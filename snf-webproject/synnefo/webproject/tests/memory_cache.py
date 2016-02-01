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

from mock import patch
from time import time, sleep

from django.test import TestCase
from django.core.cache import cache
from django.conf import settings

from synnefo.webproject.memory_cache import MemoryCache


class MemoryCacheTest(TestCase):
    prefix = 'MemoryCache_'
    user_prefix = prefix + 'user_'
    internal_prefix = prefix + 'internal_'

    def setUp(self):
        self.memory_cache = MemoryCache()

        cache.clear()

    def set_user_key(self, key, value):
        cache.set(self.user_prefix + key, value)

    def get_user_key(self, key):
        return cache.get(self.user_prefix + key)

    def set_internal_key(self, key, value):
        cache.set(self.internal_prefix + key, value)

    def get_internal_key(self, key):
        return cache.get(self.internal_prefix + key)

    def test_memory_cache_has_required_attrs(self):
        POPULATE_INTERVAL = getattr(
            settings,
            'MEMORY_CACHE_POPULATE_INTERVAL',
            300
        )
        TIMEOUT = getattr(
            settings,
            'MEMORY_CACHE_TIMEOUT',
            300
        )
        attrs = {
            'POPULATE_INTERVAL': POPULATE_INTERVAL,
            'prefix': 'MemoryCache',
            'TIMEOUT': TIMEOUT
        }
        for key in attrs.iterkeys():
            self.assertIsNotNone(getattr(self.memory_cache, key))
            self.assertEqual(getattr(self.memory_cache, key), attrs[key])

    def test_populate_raises_not_implemented(self):
        self.assertRaises(NotImplementedError, self.memory_cache.populate)

    def test_set_in_cache(self):
        value = 10
        self.memory_cache.set(a=value, b=2 * value)

        a = self.get_user_key('a')
        b = self.get_user_key('b')

        self.assertIsNotNone(a)
        self.assertIsNotNone(b)
        self.assertEqual(value, a)
        self.assertEqual(2 * value, b)

        # change TIMEOUT
        self.memory_cache.TIMEOUT = 1
        self.memory_cache.set(a=value)
        sleep(1)

        self.assertIsNone(self.get_user_key('a'))

    @patch('synnefo.api.util.MemoryCache.populate')
    def test_get_last_populate_not_in_cache(self, populate_mock):
        """If there is no record of MemoryCache_LAST_POPULATE
        call populate and initialize MemoryCache_LAST_POPULATE
        as the current time.

        """
        before_get = time()

        value = 10
        self.set_user_key('a', value)

        a = self.memory_cache.get('a')

        after_get = time()

        last_populate = self.get_internal_key('LAST_POPULATE')

        self.assertEqual(a, value)
        self.assertIsNotNone(last_populate)
        self.assertTrue(last_populate > before_get)
        self.assertTrue(last_populate < after_get)
        populate_mock.assert_called_once_with()

    @patch('synnefo.api.util.MemoryCache.populate')
    def test_get_interval_passed(self, populate_mock):
        """If LAST_POPULATE exists but the POPULATE_INTERVAL has
        passed, call populate.

        """
        value = 10
        last_populate_before = time() - (60 + self.memory_cache.POPULATE_INTERVAL)
        self.set_user_key('a', value)
        self.set_internal_key('LAST_POPULATE', last_populate_before)

        a = self.memory_cache.get('a')
        last_populate_after = self.get_internal_key('LAST_POPULATE')

        self.assertEqual(a, value)
        populate_mock.assert_called_once_with()
        self.assertNotEqual(last_populate_before, last_populate_after)
        self.assertTrue(last_populate_after > last_populate_before)
        self.assertTrue(last_populate_after < time())

    @patch('synnefo.api.util.MemoryCache.populate')
    def test_get_interval_not_passed(self, populate_mock):
        """If LAST_POPULATE exists and the POPULATE_INTERVAL hasn't
        passed do not call populate.

        """
        value = 10
        last_populate_before = time() + 60 * 60 + self.memory_cache.POPULATE_INTERVAL
        self.set_user_key('a', value)
        self.set_internal_key('LAST_POPULATE', last_populate_before)

        a = self.memory_cache.get('a')

        last_populate_after = self.get_internal_key('LAST_POPULATE')

        self.assertEqual(a, value)
        self.assertEqual(last_populate_after, last_populate_before)
        self.assertFalse(populate_mock.called)

    def test_increment(self):
        value = 10
        inc = 5
        last_populate = time() + 60 * 60 + self.memory_cache.POPULATE_INTERVAL
        self.set_user_key('a', value)
        self.set_internal_key('LAST_POPULATE', last_populate)

        # increment should increase the value by inc
        self.memory_cache.increment('a', inc)
        a = self.get_user_key('a')
        self.assertEqual(a, value + inc)

        self.set_user_key('a', value)

        # if inc is not specified increment should increase by 1
        self.memory_cache.increment('a')
        a = self.get_user_key('a')
        self.assertEqual(a, value + 1)

    def test_decrement(self):
        value = 10
        dec = 5
        last_populate = time() + 60 * 60 + self.memory_cache.POPULATE_INTERVAL
        self.set_user_key('a', value)
        self.set_internal_key('LAST_POPULATE', last_populate)

        # decrement should decrease the value by dec
        self.memory_cache.decrement('a', dec)
        a = self.get_user_key('a')
        self.assertEqual(a, value - dec)

        self.set_user_key('a', value)

        # if dec is not specified decrement should decrease by 1
        self.memory_cache.decrement('a')
        a = self.get_user_key('a')
        self.assertEqual(a, value - 1)

    def test_delete(self):
        value = 10
        self.set_user_key('a', value)

        self.memory_cache.delete('a')

        a = self.get_user_key('a')

        self.assertIsNone(a)
