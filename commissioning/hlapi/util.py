import sys

def show(x):
    if isinstance(x, dict):
        for k in x:
            print "%s: %s" % (k, x[k])
    elif isinstance(x, list):
        for i, e in enumerate(x):
            print "[%s] %s" % (i, e)
    else:
        print x


def isstr(s):
    return issubclass(type(s), basestring)

def check_string(label, value):
    if not issubclass(type(value), basestring):
        raise Exception(
            "%s is not a string, but a(n) %s with value %s" % (
                label, type(value), value))
    return value


def check_context(context):
    assert isinstance(context, dict)
    return context


def is_abs_name(name, label='name'):
    check_string(label, name)
    return (name == 'system') or name.startswith('system/') 
    
    
def check_abs_name(abs_name, label = 'abs_name'):
    check_string(label, abs_name)
    if len(abs_name) == 0:
        raise Exception("Absolute %s is empty" % (label,))
    
    if abs_name.startswith('/'):
        raise Exception(
            "Absolute %s='%s' starts with '/'" % (label, abs_name))
        
    if abs_name.endswith('/'):
        raise Exception(
            "Absolute %s='%s' ends with '/'" % (label, abs_name))

    if (abs_name != 'system') and (not abs_name.startswith('system/')):
        raise Exception(
            "Unknown hierarchy for %s='%s'. Should be 'system' or start with 'system/'" % (
                label, abs_name))

    if abs_name.find('//') >= 0:
        raise Exception("// is not allowed in %s='%s'" % (
                label, abs_name))
         
    return abs_name

def check_attribute_name(name, label='simple_name'):
    check_name(name, label)
    if name.find('/') >= 0:
        raise Exception("'%s' is not a valid attribute name (contains '/')")
    if name.find(' ') >= 0:
        raise Exception("'%s' is not a valid attribute name (contains ' ')")
    if name.find(':') >= 0:
        raise Exception("'%s' is not a valid attribute name (contains ':')")

def check_relative_name(relative_name, label='relative_name'):
    check_string(label, relative_name)
    if relative_name.startswith('system') or relative_name.startswith('system/'):
        raise Exception("%s (='%s'), which was intended as relative, has absolute form" % (label, relative_name))
            
    return relative_name

def check_name(name, label='name'):
    check_string(label, name)
    if len(name) == 0:
        raise Exception("Name %s is empty" % (label,))
    
    if name.find('//') >= 0:
        raise Exception("// is not allowed in %s (='%s')" % (
                label, name))
        
    return name


def check_abs_resource_name(abs_resource_name,
                            label='abs_resource_name'):
    """
    ``abs_resource_name`` must always be a string in absolute form.
    """
    check_abs_name(abs_resource_name, label)
    if not abs_resource_name.startswith(NameOfResourcesNode):
        raise Exception("'%s' is not a resource name. It must be under '%s'" % (
                abs_resource_name, NameOfResourcesNode))
        
    return abs_resource_name


def check_abs_group_name(abs_group_name,
                            label='abs_group_name'):
    """
    ``abs_group_name`` must always be a in absolute form.
    """
    check_abs_name(abs_group_name, label)
    if not abs_group_name.startswith(NameOfGroupsNode):
        raise Exception("'%s' is not a group name. It must be under '%s'" % (
                abs_group_name, NameOfGroupsNode))
        
    return abs_group_name


def check_node_key(node_key):
    if node_key is not None:
        check_string('node_key', node_key)
    return node_key


def is_system_node(node_name):
    check_string('node_name', node_name)
    return node_name == 'system'


def is_abs_resource_name(name):
    return name.startswith(NameOfResourcesNode)


def is_abs_group_name(name):
    return name.startswith(NameOfGroupsNode)


def is_abs_user_name(name):
    return name.startswith(NameOfUsersNode)


def level_of_node(node_name):
    """
    Returns the level of a node in the absolute hierarchy, that is under
    node 'system'.
    
    By convention, 'system' has level zero.
    """
    check_abs_name(node_name, 'node_name')
    len(node_name.split('/')) - 1
    

def is_child_of_abs_name(child, parent):
    check_abs_name(parent)
    return child.startswith(parent) and child != parent


def parent_abs_name_of(abs_name, label='abs_name'):
    """
    Given an absolute name, it returns its parent.
    If ``abs_name`` is 'system' then it returns 'system', since this is
    the convention of Quota Holder.
    """
    if is_system_node(abs_name):
        return abs_name
    else:
        check_abs_name(abs_name, label)

        # For 'a/b/c' we get ['a', 'b', 'c']
        # And for 'a' we get ['a']
        elements = abs_name.split('/')
        
        if len(elements) == 1:
            # This must be normally caught by the call check_abs_name(abs_name)
            # but let's be safe anyway 
            raise Exception(
                "Only 'system' is the top level entity, you provided '%s'" % (
                    abs_name))
        else:
            upto_name = '/'.join(elements[:-1])
            return upto_name


def last_part_of_abs_name(abs_name, label='abs_name'):
    """
    Given an absolute abs_name, which is made of simple parts separated with
    slashes), computes the last part, that is the one after the last
    slash.
    """
    check_abs_name(abs_name, label)
    last_part = abs_name.split('/')[-1:]
    return last_part


def reparent_child_name_under(child_name,
                              parent_node_name,
                              child_label='child_name',
                              parent_label='parent_node_name'):
    """
    Given a child name and an absolute parent node name, creates an
    absolute name for the child so as to reside under the given parent.
    """
    check_abs_name(parent_node_name, parent_label)

    if child_name == parent_node_name:
        raise Exception(
            "%s is the same as %s (='%s')" % (
                child_label,
                parent_label,
                parent_node_name)) 

    # If already under this parent, we are set.
    if child_name.startswith(parent_node_name):
        return child_name
    
    # Else, just make the new absolute name by concatenation
    return '%s/%s' % (parent_node_name, child_name)


def make_abs_group_name(group_name):
    check_name(group_name, 'group_name')
    return reparent_child_name_under(child_name=group_name,
                                     parent_node_name=NameOfGroupsNode,
                                     child_label='group_name',
                                     parent_label='NameOfGroupsNode')

def make_abs_resource_name(global_resource_name):
    check_name(global_resource_name, 'global_resource_name')
    return reparent_child_name_under(child_name=global_resource_name,
                                     parent_node_name=NameOfResourcesNode,
                                     child_label='global_resource_name',
                                     parent_label='NameOfResourcesNode') 

def make_abs_user_name(user_name):
    check_name(user_name, 'user_name')
    return reparent_child_name_under(child_name=user_name,
                                     parent_node_name=NameOfUsersNode,
                                     child_label='user_name',
                                     parent_label='NameOfUsersNode')


def relative_child_name_under(child_name,
                              parent_name,
                              child_label='child_name',
                              parent_label='parent_name'):
    check_abs_name(parent_name, parent_label)
    
    if child_name == parent_name:
        raise Exception(
            "%s='%s' is the same as %s='%s'" % (
                child_label,
                child_name,
                parent_label,
                parent_name)) 

    if is_abs_name(child_name, child_label):
        if child_name.startswith(parent_name):
            return child_name[len(parent_name) + 1:]
        else:
            raise Exception(
                "%s='%s' is not a child of %s='%s'" % (
                    child_label,
                    child_name,
                    parent_label,
                    parent_name))
    else:
        return child_name

def make_rel_group_name(group_name, label='group_name'):
    check_name(group_name, label)
    return relative_child_name_under(child_name=group_name,
                                     parent_name=NameOfGroupsNode,
                                     child_label='group_name',
                                     parent_label='NameOfGroupsNode')
    

def make_rel_global_resource_name(resource_name, label='resource_name'):
    check_name(resource_name, label)
    return relative_child_name_under(child_name=resource_name,
                                     parent_name=NameOfResourcesNode,
                                     child_label='resource_name',
                                     parent_label='NameOfResourcesNode')
    

def make_rel_user_name(user_name, label='user_name'):
    check_name(user_name, label)
    return relative_child_name_under(child_name=user_name,
                                     parent_name=NameOfUsersNode,
                                     child_label='user_name',
                                     parent_label='NameOfUsersNode')


NameOfSystemNode = 'system'
NameOfResourcesNode = 'system/resources'
NameOfGroupsNode = 'system/groups'
NameOfUsersNode = 'system/users'


ResourceAttributePrefixes = {
    NameOfResourcesNode: 'r',
    NameOfGroupsNode: 'g',
    NameOfUsersNode: 'u'
}

