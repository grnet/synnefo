
class CommissionException(Exception):
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

