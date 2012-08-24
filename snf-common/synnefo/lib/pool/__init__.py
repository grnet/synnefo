# Copyright 2011-2012 GRNET S.A. All rights reserved.
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


"""Classes to support pools of arbitrary objects.

The :class:`ObjectPool` class in this module abstracts a pool
of arbitrary objects. Subclasses need to define the details regarding
creation, destruction, allocation and release of their specific objects.

"""

# This should work under gevent, because gevent monkey patches 'threading'
# if not, we can detect if running under gevent, e.g. using
# if 'gevent' in sys.modules:
#     from gevent.coros import Semaphore
# else:
#     from threading import Semaphore
from threading import Semaphore, Lock


__all__ = ['ObjectPool']


class ObjectPoolError(Exception):
    pass


class PoolEmptyError(ObjectPoolError):
    pass


class ObjectPool(object):
    def __init__(self, size=None):
        try:
            self.size = int(size)
            assert size >= 1
        except:
            raise ValueError("Invalid size for pool (positive integer "
                             "required): %r" % (size,))

        self._semaphore = Semaphore(size)  # Pool grows up to size
        self._mutex = Lock()  # Protect shared _set oject
        self._set = set()

    def pool_get(self, blocking=True, timeout=None, create=True):
        """Get an object from the pool.

        Get an object from the pool. By default (create=True), create a new
        object if the pool has not reached its maximum size yet. If
        create == False, the caller is responsible for creating the object and
        put()ting it back into the pool when done.

        """
        # timeout argument only supported by gevent and py3k variants
        # of Semaphore. acquire() will raise TypeError if timeout
        # is specified but not supported by the underlying implementation.
        kw = {"blocking": blocking}
        if timeout is not None:
            kw["timeout"] = timeout
        r = self._semaphore.acquire(**kw)
        if not r:
            raise PoolEmptyError()
        with self._mutex:
            try:
                obj = self._set.pop()
            except KeyError:
                obj = self._pool_create() if create else None
            except:
                self._semaphore.release()
                raise
        # We keep _semaphore locked, put() will release it
        return obj

    def pool_put(self, obj):
        """Put an object back into the pool.

        Return an object to the pool, for subsequent retrieval
        by pool_get() calls. If _pool_cleanup() returns True,
        the object has died and is not put back into self._set.

        """
        with self._mutex:
            if not self._pool_cleanup(obj):
                self._set.add(obj)
        self._semaphore.release()

    def _pool_create(self):
        """Create a new object to be used with this pool.

        Create a new object to be used with this pool,
        should be overriden in subclasses.

        """
        raise NotImplementedError

    def _pool_cleanup(self, obj):
        """Cleanup an object before being put back into the pool.

        Cleanup an object before it can be put back into the pull,
        ensure it is in a stable, reusable state.

        """
        raise NotImplementedError
