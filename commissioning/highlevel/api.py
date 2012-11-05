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
from util import check_def_resource_name
from util import last_part_of_abs_node_name
from util import last_part_of_abs_resource_name
from util import reparent_child_name_under
from util import reparent_group_node_name
from util import reparent_resource_under
from util import check_resource_name
from util import abs_parent_name_of
from util import is_child_of_abs_name

class HighLevelAPI(object):
    """
    High-level Quota Holder API that supports definitions of resources,
    resource pools, groups and users and the transfer of resource quotas from
    respective pools to both groups and users.
    """

    def __init__(self, qh, **kwd):
        self.__qh = qh
        self.__context = check_context(kwd.get('context') or {})
        self.__node_keys = {
            NameOfSystemNode: check_string('system_key',
                                           kwd.get('system_key') or ''),
            NameOfResourcesNode: check_string('resources_key',
                                              kwd.get('resources_key') or ''),
            NameOfGroupsNode: check_string('groups_key',
                                           kwd.get('groups_key') or '')
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
    @returns(bool)
    def has_node(self, node_name):
        """
        Checks if an entity with the absolute ``node_name`` exists.
        
        Returns ``True``/``False`` accordingly.
        """
        check_node_name(node_name)
        node_key = self.get_cached_node_key(node_name)
        entity_owner_list = self.__qh.get_entity(
            context=self.__context,
            get_entity=[(node_name, node_key)]
        )
        return len(entity_owner_list) == 1 # TODO: any other check here?


    @method_accepts(str)
    @returns(str)
    def create_node(self, node_name):
        """
        Creates an entity with an absolute ``node_name``.
        
        If the hierarchy up to ``node_name`` does not exist, then it is
        created on demand.
        
        Returns the absolute ``node_name``.
        
        The implementation maps a node to a Quota Holder entity.
        """
        check_node_name(node_name)
        if is_system_node(node_name):
            # ``system`` entity always exists
            return node_name

        parent_node_name = abs_parent_name_of(node_name)
        # Recursively create hierarchy. Beware the keys must be known.
        self.ensure_node(parent_node_name)

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
        if len(rejected) > 0:
            raise Exception("Could not create node '%s'" % (node_name,))
        else:
            return node_name


    @method_accepts(str)
    @returns(bool)
    def has_global_resource(self, global_resource_name):
        check_resource_name(global_resource_name)
        return self.has_node(global_resource_name)


    def define_global_resource(self, global_resource_name):
        """
        Defines a resource globally known to Quota Holder.
        The ``global_resource_name`` must be in absolute form.
        
        Returns the ``global_resource_name``.
        
        The implementation maps a global resource to a Quota Holder entity
        (so this is equivalent to a node in the high-level API but an extra
        check is made to ensure the resource is under 'system/resources').
        """
        check_resource_name(global_resource_name)
        if not is_child_of_abs_name(global_resource_name, NameOfResourcesNode):
            raise Exception(
                "Cannot define global resource '%s' because it is not under '%s'" % (
                    global_resource_name, NameOfResourcesNode,))
        
        return self.create_node(global_resource_name)
        
    
    @method_accepts(str, str, int)
    @returns(str)
    def define_attribute_of_global_resource(self,
                                            global_resource_name,
                                            attribute_simple_name,
                                            attribute_value):
        """
        Defines an ``int`` attribute for global resource named
        ``global_resource_name``.
        
        The ``attribute_simple_name`` must be simple, that is not an absolute name.
        
        Returns the absolute name of the created attribute.
        
        The implementation maps the attribute to a Quota Holder resource under
        the node (Quota Holder entity) named ``global_resource_name``. The
        respective value is defines via Quota Holder quotas. 
        """
        check_resource_name(global_resource_name)
        
        if not self.has_global_resource(global_resource_name):
            raise Exception(
                "Cannot define attribute %s for global resource '%s'" % (
                    (attribute_simple_name, attribute_value),
                    global_resource_name
            ))
            
        if attribute_simple_name.index('/') >= 0:
            raise Exception(
                "Cannot define attribute %s for global resource '%s' because the atribute name is not simple" % (
                    (attribute_simple_name, attribute_value),
                    global_resource_name
            ))
            
        abs_attribute_name = reparent_child_name_under(
            child_name=attribute_simple_name,
            parent_node_name=global_resource_name
        )
        
        rejected  = self.__qh.set_quota(
            context=self.__context,
            set_quota=[(
                global_resource_name,
                abs_attribute_name,
                self.get_cached_node_key(global_resource_name),
                attribute_value, # quantity
                0, # capacity
                0, # import limit
                0, # export limit
                0  # flag
            )]
        )
        if len(rejected) > 0:
            raise Exception(
                "Could not create attribute %s for global resource '%s'" % (
                    (attribute_simple_name, attribute_value),
                    global_resource_name
            ))
        
        return abs_attribute_name
    
    @method_accepts(str, str, str, int, int, int, int, int)
    @returns(str)
    def create_node_resource(self,
                               parent_node_name,
                               global_resource_name,
                               resource_name_prefix, # 'def_peruser', 'def_pergroup', ''
                               quantity,
                               capacity,
                               import_limit,
                               export_limit,
                               flags):
        """
        Creates a local resource under a node (e.g. a group).
        The ``parent_node_name`` must be in absolute form. The
        ``global_resource_name`` is adjusted, if necessary, so as to reside
        under 'parent_node_name'.
        
        Note that ``global_resource_name`` must represent a global resource,
        that is one created by ``define_global_resource``.
        
        Returns the absolute resource name. This will contain
        ``parent_node_name`` as a prefix and so will defer from the given
        ``global_resource_name``.
        
        The implementation creates a Quota Holder resource for the node (
        Quota Holder entity) named ``parent_node_name`` and assigns to it the
        respective Quota Holder quotas.
        """
        check_node_name(parent_node_name)
        check_resource_name(global_resource_name)
        
        if not self.has_global_resource(global_resource_name):
            raise Exception("Unknown global resource '%s'" % (global_resource_name))
        
        if not self.has_node(parent_node_name):
            raise Exception("Cannot create resource '%s' under parent '%s' because parent does not exist" %
                            (global_resource_name, parent_node_name))
        
        resource_simple_name = last_part_of_abs_resource_name(global_resource_name)
        if len(resource_name_prefix) > 0:
            def_resource_simple_name = '%s_%s' % (resource_name_prefix,
                                                  resource_simple_name)
        else:
            def_resource_simple_name = '%s' % (resource_simple_name,) 
        
        abs_resource_name = reparent_child_name_under(resource_simple_name,
                                                 parent_node_name)
        
        rejected = self.__qh.set_quota(
            context=self.__context,
            set_quota=[(
                parent_node_name,
                abs_resource_name,
                self.get_cached_node_key(parent_node_name),
                quantity,
                capacity,
                import_limit,
                export_limit
                
            )]
        )
        if len(rejected) > 0:
            raise Exception("Could not create node resource '%s' with %s" % (
                abs_resource_name,
                (quantity, capacity, import_limit, export_limit)
            ))
        else:
            return abs_resource_name

    @method_accepts(str)
    @returns(str)
    def ensure_node(self, node_name):
        if not self.has_node(node_name):
            return self.create_node(node_name)
        else:
            return node_name

    
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
    def create_group(self, group_node_name, group_node_key=''):
        """
        Creates a new group under 'system/groups'.

        The ``group_node_name`` can either be a full path
        (e.g. 'system/groups/mygroup') or just the last part (e.g. 'mygroup').
        Note that if it is the full path, then everything but the last part is
        ignored. You must always use the returned ``group_node_name`` as the
        most authoritative value instead of the one passed as a parameter.

        No further resource assignment is done, you must use
        ``define_group_resource``.
        
        Returns the absolute group name. 

        The implementation maps a group to a Quota Holder entity.
        """
        check_node_name(group_node_name)
        check_node_key(group_node_key)

        groups_node_name = self.ensure_groups_node()

         # We are forgiving...
        group_node_name = reparent_group_node_name(group_node_name)
        
        group_node_name = self.create_node(
            group_node_name,
            groups_node_name,
            group_node_key,
            self.__groups_key)
        self.set_cached_node_key(group_node_name, group_node_key)

        return group_node_name


    @method_accepts(str, str, int, int, int, int, int, int, int)
    @returns(str, str, str)
    def define_group_resource(self,
                              group_node_name,
                              global_resource_name,
                              limit_per_group,
                              limit_per_user,
                              operational_quantity,
                              operational_capacity,
                              operational_import_limit,
                              operational_export_limit,
                              operational_flags = 0):
        """
        Defines a resource that a group provides to its users.
        """
        check_node_name(group_node_name)
        check_node_name(global_resource_name)
        
        if not self.has_global_resource(global_resource_name):
            raise Exception(
                "Cannot define resource '%s' under group '%s' because the global resource is unknown" %(
                    global_resource_name, group_node_name))
            
        if not self.has_node(group_node_name):
            raise Exception(
                "Cannot define resource '%s' under group '%s' because the group is unknown" %(
                    global_resource_name, group_node_name))

        last_resource_node_name = self.last_part_of_abs_node_name(global_resource_name)

        # 1. Create a per-this-group definitional resource under the group node.
        #    This resource defines the limit for this group.
        #    E.g. A resource named 'pithos+' gives rise to
        #    'def_pergroup_pithos+'
        self.create_node_resource(parent_node_name=group_node_name,
                                  global_resource_name=global_resource_name,
                                  resource_name_prefix='def_pergroup',
                                  quantity=limit_per_group,
                                  capacity=0,
                                  import_limit=0,
                                  export_limit=0,
                                  flags=0)

        # 2. Create a per-user definitional resource under the group node.
        #    This resource defines the limit per user.
        #    E.g. A resource named 'pithos+' gives rise to
        #    'def_peruser_pithos+'
        self.create_node_resource(parent_node_name=group_node_name,
                                  global_resource_name=global_resource_name,
                                  resource_name_prefix='def_peruser',
                                  quantity=limit_per_user,
                                  capacity=0,
                                  import_limit=0,
                                  export_limit=0,
                                  flags=0)

        # 3. Create the operational resource node under the group.
        #    This resource is a big bucket with the operational quantity and
        #    capacity. Everything is put into and out of this bucket.
        self.create_node_resource(parent_node_name=group_node_name,
                                  global_resource_name=global_resource_name,
                                  resource_name_prefix='operational',
                                  quantity=operational_quantity,
                                  capacity=operational_capacity,
                                  import_limit=operational_import_limit,
                                  export_limit=operational_export_limit,
                                  flags=operational_flags)




