import astakos.im.api.backends.errors

(SUCCESS, FAILURE) = range(2)

class BaseBackend(object):
    #TODO filled
    pass

class SuccessResult():
    def __init__(self, data):
        self.data = data
    
    @property
    def is_success(self):
        return True

class FailureResult():
    def __init__(self, reason):
        self.reason = reason
    
    @property
    def is_success(self):
        return False
