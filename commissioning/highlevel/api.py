from util import parent_node_name_of
from util import check_node_name
from util import check_node_key
from util import is_system_node
from util import check_context
from util import check_string
from util import method_accepts
from util import returns
from util import NameOfSystemNode
from util import NameOfResourcesNode
from util import NameOfGroupsNode
from util import NameOfUsersNode

class HighLevelAPI(object):
    """
    High-level Quota Holder API that supports definitions of resources, resource pools, groups and users and
    the transfer of resource quotas from respective pools to both groups and users.
    """

    def __init__(self, qh, **kwd):
        self.__qh = qh
        self.__context = check_context(kwd.get('context') or {})
        self.__node_keys = {
            NameOfSystemNode: check_string('system_key', kwd.get('system_key') or ''),
            NameOfResourcesNode: check_string('resources_key', kwd.get('resources_key') or ''),
            NameOfGroupsNode: check_string('groups_key', kwd.get('groups_key') or '')
        }


    @method_accepts(str)
    @returns(str)
    def get_cached_node_key(self, node_name):
        check_node_name(node_name)
        return self.__node_keys.get(node_name) or '' # sane default


    @method_accepts(str, str)
    @returns(type(None))
    def set_cached_node_key(self, node_name, node_key):
        check_node_name(node_name)
        check_node_key(node_key)
        if node_key is None:
            node_key = ''
        self.__node_keys[node_name] = node_key


    @returns(dict)
    def node_keys(self):
        return self.__node_keys.copy() # Client cannot mess with the original


    @method_accepts(str)
    @returns(str)
    def qh_create_node(self, node_name):
        check_node_name(node_name)
        if is_system_node(node_name):
            return node_name

        parent_node_name = parent_node_name_of(node_name)
        self.ensure_node(parent_node_name) # Recursively create hierarchy. Beware the keys must be known.

        node_key = self.get_cached_node_key(node_name)
        parent_node_key = self.get_cached_node_key(parent_node_name)

        rejected = self.__qh.create_entity(
            context=self.__context,
            create_entity=[
                (
                    node_name,
                    parent_node_name,
                    node_key,
                    parent_node_key
                    )
            ]
        )
        if(len(rejected) > 0):
            raise Exception("Could not create node '%s'" % (node_name,))
        else:
            return node_name


    @method_accepts(str)
    @returns(str)
    def ensure_node(self, node_name):
        if not self.qh_has_node(node_name):
            return self.qh_create_node(node_name)
        else:
            return node_name


    @method_accepts(str)
    @returns(bool)
    def qh_has_node(self, node_name):
        check_node_name(node_name)
        node_key = self.get_cached_node_key(node_name)
        entity_owner_list = self.__qh.get_entity(
            context=self.__context,
            get_entity=[(node_name, node_key)]
        )
        return len(entity_owner_list) == 1 # TODO: any other check here?


    @returns(str)
    def ensure_resources_node(self):
        """
        Ensure that the node 'system/resources' exists.
        """
        return self.ensure_node(NameOfResourcesNode)


    @returns(str)
    def ensure_groups_node(self):
        """
        Ensure that the node 'system/groups' exists.
        """
        return self.ensure_node(NameOfGroupsNode)


    @returns(str)
    def ensure_users_node(self):
        """
        Ensure that the node 'system/users' exists.
        """
        return self.ensure_node(NameOfUsersNode)


    @method_accepts(str, str)
    @returns(str)
    def normalize_child_node_name(self, child_node_name, parent_node_name):
        check_node_name(child_node_name)
        check_node_name(parent_node_name)
        last_part_child_node_name = self.last_part_of_node_name(child_node_name)
        normalized_child_node_name = '%s/%s' % (
            parent_node_name,
            last_part_child_node_name
        ) # recreate full node name
        return normalized_child_node_name


    @method_accepts(str)
    @returns(str)
    def normalize_group_node_name(self, group_node_name):
        return self.normalize_child_node_name(group_node_name, NameOfGroupsNode)


    @method_accepts(str)
    @returns(str)
    def last_part_of_node_name(self, node_name):
        """
        Collapses a full node name to its last part, that is the name after the last slash,
        and returns that last part.

        So, a name 'system/groups/foogrooop' is collapsed to 'foogrooop' and the
        latter is returned.
        """
        check_node_name(node_name)
        bottom_node_name = node_name.split('/')[-1:] # collapse and keep the last part
        return bottom_node_name


    @method_accepts(str, str)
    @returns(str)
    def create_group(self, group_node_name, group_node_key):
        """
        Creates a new group under 'system/groups'.

        The ``group_node_name`` can either be a full path (e.g. 'system/groups/mygroup') or just the last part
        (e.g. 'mygroup'). Note that if it is the full path, then everything but the last part is ignored.
        You must always use the returned ``group_node_name`` as the most authoritative value instead of
        the one passed as a parameter.

        No further resource assignment is done, you must use ````.

        ``group_name`` - The name of the new group.
        ``group_key``  - The key (password) for the new group.

        :type group_node_key: str
        :type group_node_name: str
        """
        check_node_name(group_node_name)
        check_node_key(group_node_key)

        groups_node_name = self.ensure_groups_node()

        group_node_name = self.normalize_group_node_name(group_node_name) # We are forgiving...
        group_node_name = self.qh_create_node(
            group_node_name,
            groups_node_name,
            group_node_key,
            self.__groups_key)
        self.set_cached_node_key(group_node_name, group_node_key)

        return group_node_name


    @method_accepts(str, str, int, int, int)
    @returns(str)
    def group_define_resource(self,
                              group_node_name,
                              resource_node_name,
                              limit_per_user,
                              bucket_quantity,
                              bucket_capacity):
        """
        Defines a resource that a group provides to its users.
        """
        check_node_name(group_node_name)
        check_node_name(resource_node_name)

        # 1. Create a definitional resource node under the group.
        #    This resource defines the limit per user.
        #    E.g. A resource named 'pithos+' gives rise to a resource/node named 'def_pithos+'
        last_resource_node_name = self.last_part_of_node_name(resource_node_name)
        def_last_resource_node_name = 'def_%s' % (last_resource_node_name,)
        def_resource_node_name = self.normalize_child_node_name(
            def_last_resource_node_name,
            group_node_name
        )
        if not self.qh_has_node(def_resource_node_name):
            def_resource_node_name = self.qh_create_node(def_resource_node_name)
        # TODO: make policy with the limit

        # 2. Create the operational resource node under the group.
        #    This resource is a big bucket with the operational quantity and capacity.
        #    Everything is put into and out of this bucket.




