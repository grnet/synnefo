
class CallError(Exception):

    def __new__(cls, *args, **kw):
        call_error = kw.get('call_error', None)
        if call_error is None:
            call_error = cls.__name__
        else:
            call_error = str(call_error)
        cls = globals().get(call_error, cls)
        self = Exception.__new__(cls, *args)
        return self

    def __init__(self, *args, **kw):
        self.call_error = kw.get('call_error', self.__class__.__name__)
        self.args = args

    def __str__(self):
    	return '\n--------\n'.join((self.call_error + ':',) + self.args)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, ','.join(self.args))

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

class CorruptedError(CallError):
    pass

class InvalidDataError(CallError):
    pass
