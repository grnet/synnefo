import os.path as ospath

class EntityHName(object):
    """
    Hierarchical entity name
    """
    def __init__(self, local_name, parent_full_name = None):
        self.__local_name = local_name
        self.__parent_full_name = parent_full_name
        if parent_full_name:
            self.__full_name = '%s/%s' % (parent_full_name, local_name)
        else:
            self.__full_name = local_name

    def local_name(self):
        return self.__local_name

    def full_name(self):
        return self.__full_name

    def level(self):
        if self.__parent_full_name:
            return 1 + self.parent().level()
        else:
            return 0

    def parent(self):
        if self.__parent_full_name:
            parent_parent_full_name, parent_local_name = ospath.split(self.__parent_full_name)
            return EntityHName(parent_local_name, parent_parent_full_name)
        else:
            # must be system
            return self

    def child(self, child_name):
        return EntityHName(child_name, self.__parent_full_name)

    def __str__(self):
        return self.__full_name

    def __repr__(self):
        return 'EntityHName(%s)' % (str(self), )

SystemEntityHName = EntityHName('system')
GroupsEntityHName = SystemEntityHName.child('groups')
ResourcesEntityHName = SystemEntityHName.child('resources')
UsersEntityHName = SystemEntityHName.child('users')