# Copyright 2012, 2013 GRNET S.A. All rights reserved.
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


def str_or_utf8(s):
    if isinstance(s, unicode):
        return s.encode('utf8')
    return str(s)


class CallError(Exception):
    exceptions = {}

    def __new__(cls, *args, **kw):
        call_error = kw.get('call_error', None)
        if call_error is None:
            call_error = cls.__name__
        else:
            call_error = str(call_error)
        cls = CallError.exceptions.get(call_error, cls)
        self = Exception.__new__(cls)
        return self

    def __init__(self, *args, **kw):
        self.call_error = kw.pop('call_error', self.__class__.__name__)
        self.args = args
        self.kwargs = kw

    def __str__(self):
        return '\n--------\n'.join(str_or_utf8(x) for x in self.args)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__,
                           ','.join(repr(x) for x in self.args))

    @classmethod
    def from_exception(cls, exc):
        args = None
        try:
            args = tuple(exc.args)
        except (TypeError, AttributeError), e:
            pass

        if args is None:
            args = (str(exc),)
        self = cls(*args, call_error=exc.__class__.__name__)
        return self

    def to_dict(self):
        args = tuple(str_or_utf8(x) for x in self.args)
        kwargs = dict((str_or_utf8(k), str_or_utf8(v))
                      for k, v in self.kwargs.iteritems())
        return {'call_error': self.call_error,
                'error_args': (args, kwargs)}

    @classmethod
    def from_dict(cls, dictobj):
        args = None
        try:
            if 'error_args' in dictobj and 'call_error' in dictobj:
                args = dictobj['error_args']
                call_error = dictobj['call_error']
        except TypeError, e:
            pass

        if args is None:
            args = (str(dictobj),)
            call_error = 'UnknownError'
            kw = {}
        else:
            args, kw = args

        self = cls(*args, call_error=call_error, **kw)
        return self

def register_exceptions(*exceptions):
    for exception in exceptions:
        if not issubclass(exception, CallError):
            m = "Registering '%s': is not a CallError subclass" % (exception,) 
            raise ValueError(m)
        CallError.exceptions[exception.__name__] = exception

def register_exception(exc):
    register_exceptions(exc)
    return exc

@register_exception
class CorruptedError(CallError):
    pass

@register_exception
class InvalidDataError(CallError):
    pass

class ReturnButFail(Exception):
    def __init__(self, retval=None):
        self.data = retval
