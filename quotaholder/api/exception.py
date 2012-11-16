from commissioning import CallError

class CommissionException(CallError):
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
