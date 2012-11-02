class ItemNotExists(NameError):
    pass


class ItemExists(NameError):
    pass


class MissingIdentifier(IOError):
    pass


class BaseBackend(object):
    def update_user():
        pass

    def create_user():
        pass
