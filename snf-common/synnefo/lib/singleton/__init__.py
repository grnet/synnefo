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


class ArgBasedSingletonMeta(type):
    """Implement the Singleton pattern with a twist.

    Implement the Singleton pattern with a twist:
    The uniqueness on the object is based on the class name,
    plus the argument list (args and kwargs).

    Unique objects are store in the '_singles' class attribute.
    A distinct _singles object is used per subclass.

    """
    def __call__(cls, *args, **kwargs):
        kwlist = str([(k, kwargs[k]) for k in sorted(kwargs.keys())])
        distinct = str((cls, args, kwlist))

        # Allocate a new _singles attribute per subclass
        if not hasattr(cls, "_singles_cls") or cls != cls._singles_cls:
            cls._singles = {}
            cls._singles_cls = cls

        if distinct not in cls._singles:
            obj = super(ArgBasedSingletonMeta, cls).__call__(*args, **kwargs)
            cls._singles[distinct] = obj

        ret = cls._singles[distinct]

        return ret


class ArgBasedSingleton(object):
    __metaclass__ = ArgBasedSingletonMeta
