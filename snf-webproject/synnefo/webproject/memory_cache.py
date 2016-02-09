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

from time import time

from django.core.cache import cache
from django.conf import settings


class MemoryCache(object):
    POPULATE_INTERVAL = getattr(settings, 'MEMORY_CACHE_POPULATE_INTERVAL', 300)
    # The cache timeout. Set to None so that the cache keys will never expire
    TIMEOUT = getattr(settings, 'MEMORY_CACHE_TIMEOUT', 300)

    user_prefix = 'user'
    internal_prefix = 'internal'

    def __init__(self):
        self.prefix = self.__class__.__name__
        self.user_prefix_full = self.prefix + '_' + self.user_prefix + '_'
        self.internal_prefix_full = self.prefix + '_' + self.internal_prefix + '_'

    def to_user_key(self, key):
        return self.user_prefix_full + key

    def to_internal_key(self, key):
        return self.internal_prefix_full + key

    def time_to_populate(self):
        """Return `True` if `POPULATE_INTERVAL` or more seconds
        have passed since the last time `populate` was called,
        otherwise return `False`.

        """
        last_populate = cache.get(self.to_internal_key('LAST_POPULATE'))
        now = time()

        if not last_populate or last_populate + self.POPULATE_INTERVAL < now:
            return True

        return False

    def check_for_populate(self):
        """If `time_to_populate` returns `True` call `populate`
        and set the `LAST_POPULATE` key in the cache as the current time.

        """
        if self.time_to_populate():
            self.populate()
            self.set_internal(LAST_POPULATE=time())

    def get(self, key):
        """Populate if needed. Retrieve and return from the
        cache the value of the key provided.

        """
        self.check_for_populate()

        return cache.get(self.to_user_key(key))

    def set(self, **kwargs):
        """Set all the key-value pairs provided in
        the cache with the user prefix.
        Example of a `set` call:
        set(key1="value1", key2="value2")

        """
        for key in kwargs.iterkeys():
            cache.set(self.to_user_key(key), kwargs[key], self.TIMEOUT)

    def set_internal(self, **kwargs):
        """Set all the key-value pairs provided in
        the cache with the internal prefix.

        """
        for key in kwargs.iterkeys():
            cache.set(self.to_internal_key(key), kwargs[key])

    def increment(self, key, inc=1):
        """If `time_to_populate` returns `True` do nothing.
        Otherwise increment the key's cache value by `inc`.
        If `inc` is not provided increment by 1.

        """
        if self.time_to_populate():
            return

        cache.incr(self.to_user_key(key), inc)

    def decrement(self, key, dec=1):
        """If `time_to_populate` returns `True` do nothing.
        Otherwise decrement the key's cache value by `dec`.
        If `dec` is not provided decrement by 1.

        """
        if self.time_to_populate():
            return

        cache.decr(self.to_user_key(key), dec)

    def populate(self):
        """The implementation of this method is required from all
        subclasses. `populate` should do two things:
        1. Initialize the values needed in the cache.
        2. Update the values after `POPULATE_INTERVAL`
        seconds pass since the last `populate` call.

        To change the `POPULATE_INTERVAL` set it as an attribute
        to the created subclass to a different value.

        """
        raise NotImplementedError("Implementation of `populate` is required")

