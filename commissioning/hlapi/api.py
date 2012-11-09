from util import check_abs_name
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
from util import make_abs_global_resource_name
from util import make_abs_group_name
from util import make_abs_user_name
from util import reparent_child_name_under 
from util import check_abs_global_resource_name
from util import parent_abs_name_of
from util import relative_child_name_under
from util import make_rel_global_resource_name
from util import make_rel_group_name
from util import make_rel_user_name
from util import check_name

class HighLevelAPI(object):
    """
    High-level Quota Holder API that supports definitions of resources,
    groups and users and the transfer of resource quotas from
    respective resources to both groups and users.
    
    Internally it uses the low-level Quota Holder API, so it maps everything
    into Entities, Resources, Policies and Limits.
    
    High-level API Terminology
    
    A node is just an entity with an absolute name. The root node called
    ``system`` is always present and is enforced by the low-level API.
    
    The meaning of a few default nodes, called the default parent nodes,
    is predefined.
    ``system/resources`` is the parent node of all resources known to ~okeanos.
    ``system/groups`` is the parent node of all user groups known to ~okeanos.
    ``system/users`` is the parent node of all users known to ~okeanos.
        
    A resource is always a node under ``system/resources``.
    A group is always a node under ``system/groups``.
    A user is always a node under ``system/users``.
    
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


    # internal API
    @method_accepts(str, str, str, str, int, int, int, int, int)
    @returns(str)
    def __create_attribute_of_node_for_resource(self,
                                                abs_or_not_node_name,
                                                intended_parent_node_name,
                                                resource_name,
                                                simple_attribute_name,
                                                quantity,
                                                capacity,
                                                import_limit,
                                                export_limit,
                                                flags):
        #
        check_abs_name(intended_parent_node_name,
                        'intended_parent_node_name')
        
        intended_parent_node_name = self.ensure_node(intended_parent_node_name)
        
        # Fix node name to its intended absolute form just in case
        node_name = reparent_child_name_under(child_name=abs_or_not_node_name,
                                              parent_node_name=intended_parent_node_name,
                                              child_label='abs_or_not_node_name',
                                              parent_label='intended_parent_node_name')

        self.ensure_resources_node()
        
        abs_resource_name = make_abs_global_resource_name(resource_name)
        self.ensure_node(abs_resource_name)
        
        # Fix resource name to its relative form just in case
        relative_resource_name = make_rel_global_resource_name(resource_name,
                                                                  'resource_name')
        
        computed_attribute_name = '%s_%s' % (simple_attribute_name,
                                             relative_resource_name)
        
        rejected  = self.__qh.set_quota(
            context=self.__context,
            set_quota=[(
                node_name,               # Node -> QH entity
                computed_attribute_name, # Attribute -> QH resource
                self.get_cached_node_key(node_name),
                quantity,
                capacity, 
                import_limit, 
                export_limit, 
                flags
            )]
        )
        
        if len(rejected) > 0:
            raise Exception(
                "Could not create attribute '%s' [='%s'] for node '%s' [='%s'], related to resource '%s' [='%s']" % (
                    simple_attribute_name,
                    computed_attribute_name,
                    abs_or_not_node_name,
                    node_name,
                    resource_name,
                    abs_resource_name
            ))
            
        return computed_attribute_name


    @method_accepts(str)
    @returns(str)
    def get_cached_node_key(self, abs_node_name):
        check_abs_name(abs_node_name, 'abs_node_name')
        return self.__node_keys.get(abs_node_name) or '' # sane default


    @method_accepts(str, str)
    @returns(type(None))
    def set_cached_node_key(self, abs_node_name, node_key, label='abs_node_name'):
        check_abs_name(abs_node_name, label)
        check_node_key(node_key)
        if node_key is None:
            node_key = ''
        self.__node_keys[abs_node_name] = node_key


    @returns(dict)
    def node_keys(self):
        return self.__node_keys.copy() # Client cannot mess with the original
    
    
    @method_accepts(str, str)
    @returns(str)
    def ensure_node(self, abs_node_name, label='abs_node_name'):
        if not self.has_node(abs_node_name, label):
            return self.create_node(abs_node_name, label)
        else:
            return abs_node_name

    
    @returns(str)
    def ensure_resources_node(self):
        """
        Ensure that the node 'system/resources' exists.
        """
        return self.ensure_node(NameOfResourcesNode, 'NameOfResourcesNode')


    @returns(str)
    def ensure_groups_node(self):
        """
        Ensure that the node 'system/groups' exists.
        """
        return self.ensure_node(NameOfGroupsNode, 'NameOfGroupsNode')


    @returns(str)
    def ensure_users_node(self):
        """
        Ensure that the node 'system/users' exists.
        """
        return self.ensure_node(NameOfUsersNode, 'NameOfGroupsNode')


    @method_accepts(str, str)
    @returns(bool)
    def has_node(self, abs_node_name, label='abs_node_name'):
        """
        Checks if an entity with the absolute name ``abs_node_name`` exists.
        
        Returns ``True``/``False`` accordingly.
        """
        check_abs_name(abs_node_name, label)
        node_key = self.get_cached_node_key(abs_node_name)
        entity_owner_list = self.__qh.get_entity(
            context=self.__context,
            get_entity=[(abs_node_name, node_key)]
        )
        return len(entity_owner_list) == 1 # TODO: any other check here?


    @method_accepts(str, str)
    @returns(str)
    def create_node(self, node_name, label='node_name'):
        """
        Creates a node with an absolute name ``node_name``.
        
        If the hierarchy up to ``node_name`` does not exist, then it is
        created on demand.
        
        Returns the absolute ``node_name``.
        
        The implementation maps a node to a Quota Holder entity.
        """
        check_abs_name(node_name, label)
        
        if is_system_node(node_name):
            # ``system`` entity always exists
            return node_name

        parent_node_name = parent_abs_name_of(node_name, label)
        # Recursively create hierarchy. Beware the keys must be known.
        self.ensure_node(parent_node_name, label)

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
    def has_global_resource(self, abs_resource_name):
        check_abs_global_resource_name(abs_resource_name)
        return self.has_node(abs_resource_name)


    @method_accepts(str)
    def define_global_resource(self, resource_name):
        """
        Defines a resource globally known to Quota Holder.
        
        Returns the absolute name of the created resource. Note that this may
        be different from ``resource_name``.
        
        The implementation maps a global resource to a Quota Holder entity
        (so this is equivalent to a node in the high-level API but an extra
        check is made to ensure the resource is under 'system/resources').
        """
        
        # If the name is not in absolute form, make it so.
        # E.g. if it is 'pithos+' make it 'system/resources/pithos+'
        abs_resource_name = make_abs_global_resource_name(resource_name)
        
        # Create hierarchy on demand
        return self.create_node(abs_resource_name, 'abs_resource_name')
        
    
    @method_accepts(str, str, int, int, int, int, int)
    @returns(str)
    def define_attribute_of_global_resource(self,
                                            global_resource_name,
                                            attribute_name,
                                            quantity,
                                            capacity,
                                            import_limit,
                                            export_limit,
                                            flags):
        """
        Defines an ``int`` attribute for global resource named
        ``global_resource_name``.
        
        The ``attribute_name`` must be simple, that is not an absolute name.
        
        Returns the computed name of the created attribute. Note that the
        computed name is not the same as ``attribute_name``.
        
        The implementation maps the attribute to a Quota Holder resource under
        the node (Quota Holder entity) named ``global_resource_name``. The
        respective value is defined via Quota Holder quotas. 
        """
        
        return self.__create_attribute_of_node_for_resource(
            abs_or_not_node_name=global_resource_name,
            intended_parent_node_name=NameOfResourcesNode,
            resource_name=global_resource_name,
            # r means we define for Resource
            # The attribute name goes next
            # The relative resource name goes next
            #    (will be added by the called method)
            simple_attribute_name='r_%s' % (attribute_name),
            quantity=quantity,
            capacity=capacity,
            import_limit=import_limit,
            export_limit=export_limit,
            flags=flags)

            
    
    @method_accepts(str, str)
    @returns(str)
    def define_group(self, group_name, group_node_key=''):
        """
        Creates a new group under 'system/groups'.

        The ``group_name`` can either be an absolute name
        (e.g. 'system/groups/mygroup') or a relative name (e.g. 'mygroup').
        
        Returns the absolute group name of the created group. Note that this
        may be different from ``group_name``. 
        
        You must always use the returned ``group_name`` as the
        most authoritative value instead of the one passed as a parameter.

        No further resource assignment is done, you must use
        ``define_group_resource``.

        The implementation maps a group to a Quota Holder entity.
        """
        check_node_key(group_node_key)

        self.ensure_groups_node()
        # get name in absolute form
        abs_group_name = make_abs_group_name(group_name)

        # Create hierarchy on demand
        self.create_node(abs_group_name, 'abs_group_name')
        self.set_cached_node_key(abs_group_name, group_node_key)
        return abs_group_name
    

    
    @method_accepts(str, str, str, int, int, int, int, int)
    @returns(str)
    def define_attribute_of_group_for_resource(self,
                                               group_name,
                                               attribute_name,
                                               resource_name,
                                               quantity,
                                               capacity,
                                               import_limit,
                                               export_limit,
                                               flags):
        
        return self.__create_attribute_of_node_for_resource(
            abs_or_not_node_name=group_name,
            intended_parent_node_name=NameOfGroupsNode,
            resource_name=resource_name,
            # g means we define for G
            # The attribute name goes next
            # The relative resource name goes next
            #    (will be added by the called method)
            simple_attribute_name='g_%s' % (attribute_name),
            quantity=quantity,
            capacity=capacity,
            import_limit=import_limit,
            export_limit=export_limit,
            flags=flags)


    @method_accepts(str, str, int, int, int, int, int, int, int)
    @returns(str, str, str)
    def define_group_resource(self,
                              group_name,
                              resource_name,
                              limit_per_group,
                              limit_per_user,
                              operational_quantity,
                              operational_capacity,
                              operational_import_limit,
                              operational_export_limit,
                              operational_flags):
        """
        Defines a resource that a group provides to its users.
        """
        abs_group_name = make_abs_group_name(group_name)
        abs_resource_name = make_abs_global_resource_name(resource_name)
        
        if not self.has_global_resource(abs_resource_name):
            raise Exception(
                "Cannot define resource '%s' for group '%s' because the global resource '%s' does not exist" %(
                    resource_name,
                    group_name,
                    abs_resource_name))
            
        if not self.has_node(abs_group_name):
            raise Exception(
                "Cannot define resource '%s' for group '%s' because the group does not exist" %(
                    resource_name,
                    group_name))

        if limit_per_user >= 0:
            self.define_attribute_of_group_for_resource(group_name=abs_group_name,
                                                        attribute_name='def_peruser',
                                                        resource_name=abs_resource_name,
                                                        quantity=0,
                                                        capacity=limit_per_user,
                                                        import_limit=0,
                                                        export_limit=0,
                                                        flags=0)
        else:
            # The limit will always be obtained from the global resource
            pass

        self.define_attribute_of_group_for_resource(group_name=abs_group_name,
                                                    attribute_name='def_pergroup',
                                                    resource_name=abs_resource_name,
                                                    quantity=0,
                                                    capacity=limit_per_group,
                                                    import_limit=0,
                                                    export_limit=0,
                                                    flags=0)

        self.define_attribute_of_group_for_resource(group_name=abs_group_name,
                                                    attribute_name='operational',
                                                    resource_name=abs_resource_name,
                                                    quantity=operational_quantity,
                                                    capacity=operational_capacity,
                                                    import_limit=operational_import_limit,
                                                    export_limit=operational_export_limit,
                                                    flags=operational_flags)

