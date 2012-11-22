
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
        self.call_error = kw.get('call_error', self.__class__.__name__)
        self.args = args

    def __str__(self):
        return '\n--------\n'.join(str(x) for x in self.args)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__,
                           ','.join(str(x) for x in self.args))

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
        return {'call_error': self.call_error,
                'error_args': self.args}

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

        self = cls(*args, call_error=call_error)
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
