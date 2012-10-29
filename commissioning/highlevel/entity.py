from entityhname import EntityHName
from entityhname import SystemEntityHName

class Entity(object):
    def __init__(self, entity_hname, key):
        assert isinstance(entity_hname, EntityHName), "Not an EntityHName: %s" % (entity_hname, )
        self.__entity_hname = entity_hname
        self.__key = key

    def entity_hname(self):
        return self.__entity_hname

    def full_name(self):
        return self.entity_hname().full_name()

    def key(self):
        return self.__key

    def create_child(self, child_entity_name, child_key, qh):
        assert isinstance(child_entity_name, str), "child_entity_name is not a string: %s" % (child_entity_name,)
        assert isinstance(child_key, str), "child_key is not a string: %s" % (child_key,)
        assert len(child_entity_name) > 0, "Empty child_entity_name"
        assert len(child_key) > 0, "Empty child_key"
        assert qh is not None, "No quota holder client"
        child_entity_hname = self.entity_hname().child(child_entity_name)
        rejected = qh.create_entity(
            context={},
            create_entity=[
                (child_entity_hname.full_name(),
                 self.full_name(),
                 child_key,
                 self.key(),
                )
            ]
        )

        if len(rejected) > 0:
            raise Exception(
                "Cannot create child entity %s of %s due to %s" % (
                    child_entity_name,
                    self.full_name(),
                    repr(rejected)
                    )
            )
        else:
            return Entity(child_entity_hname, child_key)

