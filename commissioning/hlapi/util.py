import sys
from commissioning.clients.http import HTTP_API_Client
from commissioning import QuotaholderAPI

def new_quota_holder_client(QH_URL):
    """
    Create a new quota holder api client
    """
    class QuotaholderHTTP(HTTP_API_Client):
        api_spec = QuotaholderAPI()

    return QuotaholderHTTP(QH_URL)

def method_accepts(*types):
    '''Method decorator. Checks decorated function's arguments are
    of the expected types. The self argument is ignored. This is
    based on the ``accepts`` decorator.

    Parameters:
    types -- The expected types of the inputs to the decorated function.
             Must specify type for each parameter.
    '''
    try:
        def decorator(f):
            def newf(*args):
                args_to_check = args[1:] # Throw away self (or cls)
                assert len(args_to_check) == len(types)
                argtypes = tuple(map(type, args_to_check))
                if argtypes != types:
                    msg = info(f.__name__, types, argtypes, 0)
                    raise TypeError, msg
                return f(*args)
            newf.__name__ = f.__name__
            return newf
        return decorator
    except KeyError, key:
        raise KeyError, key + "is not a valid keyword argument"
    except TypeError, msg:
        raise TypeError, msg

# http://wiki.python.org/moin/PythonDecoratorLibrary#Type_Enforcement_.28accepts.2Freturns.29
# Slightly modified to always raise an error
def accepts(*types):
    '''Function decorator. Checks decorated function's arguments are
    of the expected types.

    Parameters:
    types -- The expected types of the inputs to the decorated function.
             Must specify type for each parameter.
    '''
    try:
        def decorator(f):
            def newf(*args):
                assert len(args) == len(types)
                argtypes = tuple(map(type, args))
                if argtypes != types:
                    msg = info(f.__name__, types, argtypes, 0)
                    raise TypeError, msg
                return f(*args)
            newf.__name__ = f.__name__
            return newf
        return decorator
    except KeyError, key:
        raise KeyError, key + "is not a valid keyword argument"
    except TypeError, msg:
        raise TypeError, msg

# http://wiki.python.org/moin/PythonDecoratorLibrary#Type_Enforcement_.28accepts.2Freturns.29
# Slightly modified to always raise an error
def returns(ret_type):
    '''Function decorator. Checks decorated function's return value
    is of the expected type.

    Parameters:
    ret_type -- The expected type of the decorated function's return value.
                Must specify type for each parameter.
    '''
    try:
        def decorator(f):
            def newf(*args):
                result = f(*args)
                res_type = type(result)
                if res_type != ret_type:
                    msg = info(f.__name__, (ret_type,), (res_type,), 1)
                    raise TypeError, msg
                return result
            newf.__name__ = f.__name__
            return newf
        return decorator
    except KeyError, key:
        raise KeyError, key + "is not a valid keyword argument"
    except TypeError, msg:
        raise TypeError, msg

# http://wiki.python.org/moin/PythonDecoratorLibrary#Type_Enforcement_.28accepts.2Freturns.29
def info(fname, expected, actual, flag):
    '''Convenience function returns nicely formatted error/warning msg.'''
    format = lambda types: ', '.join([str(t).split("'")[1] for t in types])
    expected, actual = format(expected), format(actual)
    msg = "'{}' method ".format( fname )\
          + ("accepts", "returns")[flag] + " ({}), but ".format(expected)\
          + ("was given", "result is")[flag] + " ({})".format(actual)
    return msg

def check_string(label, value):
    if not isinstance(value, str):
        raise Exception(
            "%s is not a string, but a(n) %s with value %s" % (
                label, type(value), value))
    return value

def check_context(context):
    assert isinstance(context, dict)
    return context

@accepts(str, str)
@returns(bool)
def is_abs_name(name, label='name'):
    check_string(label, name)
    return (name == 'system') or name.startswith('system/') 
    
    
def check_abs_name(abs_name, label = 'abs_name'):
    check_string(label, abs_name)
    if len(abs_name) == 0:
        raise Exception("Absolute abs_name '%s' is empty" % (label,))
    
    if abs_name.startswith('/'):
        raise Exception(
            "Absolute abs_name %s (='%s') starts with '/'" % (label, abs_name))
        
    if abs_name.endswith('/'):
        raise Exception(
            "Absolute abs_name %s (='%s') ends with '/'" % (label, abs_name))

    if (abs_name != 'system') or (not abs_name.startswith('system/')):
        raise Exception(
            "Unknown hierarchy for absolute abs_name %s (='%s'). Should be 'system' or start with 'system/'" % (
                label, abs_name))
    
    return abs_name

def check_relative_name(relative_name, label='relative_name'):
    check_string(label, relative_name)
    if relative_name.startswith('system') or relative_name.startswith('system/'):
        raise Exception("%s (='%s'), which was intended as relative, has absolute form" % (label, relative_name))
            
    return relative_name

def check_name(name, label='name'):
    check_string(label, name)
    if len(name) == 0:
        raise Exception("Name %s is empty" % (label,))
    return name


def check_abs_global_resource_name(abs_resource_name,
                                   label='abs_resource_name'):
    """
    ``abs_resource_name`` must always be a string in absolute form.
    """
    check_abs_name(abs_resource_name, label)
    if not abs_resource_name.startswith(NameOfResourcesNode):
        raise Exception("'%s' is not a global resource name" % (abs_resource_name,))
        
    return abs_resource_name


def check_node_key(node_key):
    if node_key is not None:
        check_string('node_key', node_key)
    return node_key


def is_system_node(node_name):
    return node_name == 'system'


@accepts(str, str)
@returns(bool)
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

@accepts(str)
@returns(str)
def last_part_of_abs_name(abs_name, label='abs_name'):
    """
    Given an absolute abs_name, which is made of simple parts separated with
    slashes), computes the last part, that is the one after the last
    slash.
    """
    check_abs_name(abs_name, label)
    last_part = abs_name.split('/')[-1:]
    return last_part


@accepts(str, str, str, str)
@returns(str)
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

def make_abs_global_resource_name(global_resource_name):
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
    
@accepts(str, str, str, str)
@returns(str)
def relative_child_name_under(child_name,
                              parent_name,
                              child_label='child_name',
                              parent_label='parent_name'):
    check_abs_name(parent_name, parent_label)
    
    if child_name == parent_name:
        raise Exception(
            "%s is the same as %s (='%s')" % (
                child_label,
                parent_label,
                parent_name)) 

    if not child_name.startswith(parent_name):
        raise Exception(
            "%s (='%s') is not a child of %s (='%s')" % (
                child_label,
                child_name,
                parent_label,
                parent_name))

    return child_name[len(parent_name) + 1:]


@accepts(str, str)
@returns(str)
def make_rel_group_name(group_name, label='group_name'):
    check_name(group_name, label)
    return relative_child_name_under(child_name=group_name,
                                     parent_name=NameOfGroupsNode,
                                     child_label='group_name',
                                     parent_label='NameOfGroupsNode')
    

@accepts(str, str)
@returns(str)
def make_rel_global_resource_name(resource_name, label='resource_name'):
    check_name(resource_name, label)
    return relative_child_name_under(child_name=resource_name,
                                     parent_name=NameOfResourcesNode,
                                     child_label='resource_name',
                                     parent_label='NameOfResourcesNode')
    

@accepts(str, str)
@returns(str)
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

