
class CallError(Exception):

    def __init__(self, *args, **kw):
        call_error = kw.get('call_error', None)
        if call_error is None:
            call_error = self.__class__.__name__
        else:
            call_error = str(call_error)
        self.call_error = call_error
        self.args = tuple(str(a) for a in args)

    @classmethod
    def from_exception(cls, exc):
        self = cls(*exc.args, call_error=exc.__class__.__name__)
        return self

    def to_dict(self):
        return {'call_error': self.call_error,
                'error_args': self.args}

    @classmethod
    def from_dict(cls, dictobj):
        self = cls(*dictobj['args'], call_error=dictobj['call_error'])
        return self


class CommissionException(CallError):
    pass

class CorruptedError(CommissionException):
    pass

class InvalidDataError(CommissionException):
    pass

class InvalidKeyError(CommissionException):
    pass

class NoEntityError(CommissionException):
    pass

class NoQuantityError(CommissionException):
    pass

class NoCapacityError(CommissionException):
    pass

class ExportLimitError(CommissionException):
    pass

class ImportLimitError(CommissionException):
    pass

