from .quotaholder import QuotaholderAPI
from .exception import ( InvalidKeyError, NoEntityError,
                         NoQuantityError, NoCapacityError,
                         ExportLimitError, ImportLimitError,
                         CorruptedError, InvalidDataError)

API_Spec = QuotaholderAPI
