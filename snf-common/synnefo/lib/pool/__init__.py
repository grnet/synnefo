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

    def pool_create_free(self):
        """Create a free new object that is not put into the pool.

        Just for convenience, let the users create objects with
        the exact same configuration as those that are used with the pool

        """
        obj = self._pool_create_free()
        return obj

    def _pool_create_free(self):
        """Create a free new object that is not put into the pool.

        This should be overriden by pool classes.
        Otherwise, it just calls _pool_create().

        """
        return self._pool_create()

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


class PooledObject(object):
    """Generic Object Pool context manager and pooled object proxy.

    The PooledObject instance acts as a context manager to
    be used in a with statement:

        with PooledObject(...) as obj:
            use(obj)

    The with block above is roughly equivalent to:

        pooled = PooledObject(...):
        try:
            obj = pooled.acquire()
            assert(obj is pooled.obj)
            use(obj)
        finally:
            pooled.release()

    After exiting the with block, or releasing,
    the code MUST not use the obj again in any way.

    """

    # NOTE: We need all definitions at class-level
    # to avoid infinite __gettatr__() recursion.
    # This is also true for subclasses.

    # NOTE: Typically you will only need to override
    #       __init__() and get_pool

    # Initialization. Do not customize.
    _pool_settings = None
    _pool_get_settings = None
    _pool_kwargs = None
    _pool = None
    obj = None

    #####################################################
    ### Subclass attribute customization begins here. ###

    _pool_log_prefix = "POOL"
    _pool_class = ObjectPool

    # default keyword args to pass to pool initialization
    _pool_default_settings = (
            ('size', 25),
        )

    # keyword args to pass to pool_get
    _pool_default_get_settings = (
            ('blocking', True),
            #('timeout', None),
            ('create', True),
            ('verify', True),
        )

    # behavior settings
    _pool_attach_context = False
    _pool_disable_after_release = True
    _pool_ignore_double_release = False

    ###  Subclass attribute customization ends here.  ###
    #####################################################

    def __init__(self, pool_settings=None,
                       get_settings=None,
                       attach_context=None,
                       disable_after_release=None,
                       ignore_double_release=None,
                       **kwargs):
        """Initialize a PooledObject instance.

        Accept only keyword arguments.
        Some of them are filtered for this instance's configuration,
        and the rest are saved in ._pool_kwargs for later use.

        The filtered keywords are:

        pool_settings:  keyword args forwarded to pool instance initialization
                        in get_pool(), on top of the class defaults.
                        If not given, the remaining keyword args are
                        forwarded instead.

        get_settings:   keyword args forwarded to the pool's .pool_get() on top
                        of the class defaults.

        attach_context: boolean overriding the class default.
                        If True, after getting an object from the pool,
                        attach self onto it before returning it,
                        so that the context manager caller can have
                        access to the manager object within the with: block.

        disable_after_release:
                        boolean overriding the class default.
                        If True, the PooledObject will not allow a second
                        acquisition after the first release. For example,
                        the second with will raise an AssertionError:
                        manager = PooledObject()
                        with manager as c:
                            pass
                        with manager as c:
                            pass

        ignore_double_release:
                        boolean overriding the class default.
                        If True, the PooledObject will allow consecutive
                        calls to release the underlying pooled object.
                        Only the first one has an effect.
                        If False, an AssertionError is raised.

        """
        self._pool_kwargs = kwargs
        self._pool = None
        self.obj = None

        _get_settings = dict(self._pool_default_get_settings)
        if get_settings is not None:
            _get_settings.update(get_settings)
        self._pool_get_settings = _get_settings

        if attach_context is not None:
            self._pool_attach_context = attach_context

        if pool_settings is None:
            pool_settings = kwargs

        _pool_settings = dict(self._pool_default_settings)
        _pool_settings.update(**pool_settings)
        self._pool_settings = _pool_settings

    def get_pool(self):
        """Return a suitable pool object to work with.

        Called within .acquire(), it is meant to be
        overriden by sublasses, to create a new pool,
        or retrieve an existing one, based on the PooledObject
        initialization keywords stored in self._pool_kwargs.

        """
        pool = self._pool_class(**self._pool_settings)
        return pool

    ### Maybe overriding get_pool() and __init__() above is enough ###

    def __repr__(self):
        return ("<object %s of class %s: "
                "proxy for object (%r) in pool (%r)>" % (
                id(self), self.__class__.__name__,
                self.obj, self._pool))

    __str__ = __repr__

    ## Proxy the real object. Disabled until needed.
    ##
    ##def __getattr__(self, name):
    ##    return getattr(self.obj, name)

    ##def __setattr__(self, name, value):
    ##    if hasattr(self, name):
    ##        _setattr = super(PooledObject, self).__setattr__
    ##        _setattr(name, value)
    ##    else:
    ##        setattr(self.obj, name, value)

    ##def __delattr_(self, name):
    ##    _delattr = super(PooledObject, self).__delattr__
    ##    if hasattr(self, name):
    ##        _delattr(self, name)
    ##    else:
    ##        delattr(self.obj, name)

    def __enter__(self):
        return self.acquire()

    def __exit__(self, exc_type, exc_value, trace):
        return self.release()

    def acquire(self):
        log.debug("%s Acquiring (context: %r)", self._pool_log_prefix, self)
        pool = self._pool
        if pool is False:
            m = "%r: has been released. No further pool access allowed." % (
                self,)
            raise AssertionError(m)
        if pool is not None:
            m = "Double acquire in %r" % self
            raise AssertionError(m)

        pool = self.get_pool()
        self._pool = pool

        obj = pool.pool_get(**self._pool_get_settings)
        if self._pool_attach_context:
            obj._pool_context = self
        self.obj = obj
        log.debug("%s Acquired %r", self._pool_log_prefix, obj)
        return obj

    def release(self):
        log.debug("%s Releasing (context: %r)", self._pool_log_prefix, self)
        pool = self._pool
        if pool is None:
            m = "%r: no pool" % (self,)
            raise AssertionError(m)

        obj = self.obj
        if obj is None:
            if self._pool_ignore_double_release:
                return
            m = "%r: no object. Double release?" % (self,)
            raise AssertionError(m)

        pool.pool_put(obj)
        self.obj = None
        if self._pool_disable_after_release:
            self._pool = False
