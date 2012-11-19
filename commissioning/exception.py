
class CallError(Exception):

    def __init__(self, *args, **kw):
        call_error = kw.get('call_error', None)
        if call_error is None:
            call_error = self.__class__.__name__
        else:
            call_error = str(call_error)
        self.call_error = call_error
        self.args = tuple(str(a) for a in args)

    def __str__(self):
    	return '\n--------\n'.join((self.call_error + ':',) + self.args)

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
