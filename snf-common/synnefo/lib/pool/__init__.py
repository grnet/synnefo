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


__all__ = ['ObjectPool', 'ObjectPoolError',
           'PoolLimitError', 'PoolVerificationError']

import logging
log = logging.getLogger(__name__)


class ObjectPoolError(Exception):
    pass


class PoolLimitError(ObjectPoolError):
    pass


class PoolVerificationError(ObjectPoolError):
    pass


class ObjectPool(object):
    """Generic Object Pool.

    The pool consists of an object set and an allocation semaphore.

    pool_get() gets an allocation from the semaphore
               and an object from the pool set.

    pool_put() releases an allocation to the semaphore
               and puts an object back to the pool set.

    Subclasses must implement these thread-safe hooks:
    _pool_create()
            used as a subclass hook to auto-create new objects in pool_get().
    _pool_verify()
            verifies objects before they are returned by pool_get()
    _pool_cleanup()
            cleans up and verifies objects before their return by pool_put().

    While allocations are strictly accounted for and limited by
    the semaphore, objects are expendable:

    The hook provider and the caller are solely responsible for object
    handling.

    pool_get() may create an object if there is none in the pool set.
    pool_get() may return no object, leaving object creation to the caller.
    pool_put() may return no object to the pool set.
    Objects to pool_put() to the pool need not be those from pool_get().
    Objects to pool_get() need not be those from pool_put().


    Callers beware:
    The pool limit size must be greater than the total working set of objects,
    otherwise it will hang. When in doubt, use an impossibly large size limit.
    Since the pool grows on demand, this will not waste resources.
    However, in that case, the pool must not be used as a flow control device
    (i.e. relying on pool_get() blocking to stop threads),
    as the impossibly large pool size limit will defer blocking until too late.

    """
    def __init__(self, size=None):
        try:
            self.size = int(size)
            assert size >= 1
        except:
            raise ValueError("Invalid size for pool (positive integer "
                             "required): %r" % (size,))

        self._semaphore = Semaphore(size)  # Pool grows up to size limit
        self._mutex = Lock()  # Protect shared _set oject
        self._set = set()
        log.debug("Initialized pool %r", self)

    def __repr__(self):
        return ("<pool %d: size=%d, len(_set)=%d, semaphore=%d>" %
                (id(self), self.size, len(self._set),
                 self._semaphore._Semaphore__value))

    def pool_get(self, blocking=True, timeout=None, create=True, verify=True):
        """Get an object from the pool.

        Get a pool allocation and an object from the pool set.
        Raise PoolLimitError if the pool allocation limit has been reached.
        If the pool set is empty, create a new object (create==True),
        or return None (create==False) and let the caller create it.
        All objects returned (except None) are verified.

        """
        # timeout argument only supported by gevent and py3k variants
        # of Semaphore. acquire() will raise TypeError if timeout
        # is specified but not supported by the underlying implementation.
        log.debug("GET: about to get object from pool %r", self)
        kw = {"blocking": blocking}
        if timeout is not None:
            kw["timeout"] = timeout
        sema = self._semaphore
        r = sema.acquire(**kw)
        if not r:
            raise PoolLimitError()

        try:
            created = 0
            while 1:
                with self._mutex:
                    try:
                        obj = self._set.pop()
                    except KeyError:
                        obj = None
                if obj is None and create:
                    obj = self._pool_create()
                    created = 1

                if not self._pool_verify(obj):
                    if created:
                        m = "Pool %r cannot verify new object %r" % (self, obj)
                        raise PoolVerificationError(m)
                    continue
                break
        except:
            sema.release()
            raise

        # We keep _semaphore acquired, put() will release it
        log.debug("GOT: object %r from pool %r", obj, self)
        return obj

    def pool_put(self, obj):
        """Put an object back into the pool.

        Release an allocation and return an object to the pool.
        If obj is None, or _pool_cleanup returns True,
        then the allocation is released,
        but no object returned to the pool set

        """
        log.debug("PUT-BEFORE: about to put object %r back to pool %r",
                  obj, self)
        if obj is not None and not self._pool_cleanup(obj):
            with self._mutex:
                if obj in self._set:
                    log.warning("Object %r already in _set of pool %r",
                                obj, self)
                self._set.add(obj)
        self._semaphore.release()
        log.debug("PUT-AFTER: finished putting object %r back to pool %r",
                  obj, self)

    def _pool_create(self):
        """Create a new object to be used with this pool.

        Create a new object to be used with this pool,
        should be overriden in subclasses.
        Must be thread-safe.
        """
        raise NotImplementedError

    def _pool_verify(self, obj):
        """Verify an object after getting it from the pool.

        If it returns False, the object is discarded
        and another one is drawn from the pool.
        If the pool is empty, a new object is created.
        If the new object fails to verify, pool_get() will fail.
        Must be thread-safe.

        """
        raise NotImplementedError

    def _pool_cleanup(self, obj):
        """Cleanup an object before being put back into the pool.

        Cleanup an object before it can be put back into the pull,
        ensure it is in a stable, reusable state.
        Must be thread-safe.

        """
        raise NotImplementedError
