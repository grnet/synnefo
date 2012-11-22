from commissioning import (CallError, register_exception,
                           InvalidDataError, CorruptedError)

@register_exception
class CommissionException(CallError):
    pass

@register_exception
class InvalidKeyError(CommissionException):
    pass

@register_exception
class NoEntityError(CommissionException):
    pass

@register_exception
class NoQuantityError(CommissionException):
    pass

@register_exception
class NoCapacityError(CommissionException):
    pass

@register_exception
class ExportLimitError(CommissionException):
    pass

@register_exception
class ImportLimitError(CommissionException):
    pass
