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

def check_string(name, value):
    assert isinstance(value, str), "%s is not a string, but a %s" % (name, type(value))
    return value

def check_context(context):
    assert isinstance(context, dict)
    return context

def check_abs_name(name):
    check_string('name', name)
    assert len(name) > 0
    assert not name.startswith('/') # Although absolute, no / prefix is needed
    assert not name.endswith('/')
    assert name == 'system' or name.startswith('system/')
    return name

def check_node_name(node_name):
    """
    A ``node_name`` must always be a string in absolute form.
    """
    check_string('node_name', node_name)
    return check_abs_name(node_name)

def check_resource_name(resource_name):
    """
    A ``resource_name`` must always be a string in absolute form.
    """
    check_string('resource_name', resource_name)
    return check_abs_name(resource_name)

def check_def_resource_name(resource_name):
    check_abs_name(resource_name)
    assert resource_name.startswith('def_')

def check_node_key(node_key):
    if node_key is not None:
        check_string('node_key', node_key)
    return node_key

def is_system_node(node_name):
    check_node_name(node_name)
    return node_name == 'system'

@accepts(str, str)
@returns(bool)
def is_child_of_abs_name(child, parent):
    check_abs_name(parent)
    return child.startswith(parent) and child != parent
    
def abs_parent_name_of(abs_name):
    """
    Given an absolute name, it returns its parent.
    If ``abs_name`` is 'system' then it returns 'system', since this is
    the convention of Quota Holder.
    """
    if is_system_node(abs_name):
        return abs_name
    else:
        check_abs_name(abs_name)

        # For 'a/b/c' we get ['a', 'b', 'c']
        # And for 'a' we get ['a']
        elements = abs_name.split('/')
        if len(elements) == 1:
            raise Exception("Only 'system' is the top level entity, you provided '%s'" % (abs_name))
        else:
            upto_name = '/'.join(elements[:-1])
            return upto_name

@accepts(str)
@returns(str)
def last_part_of_abs_name(name):
    """
    Given an absolute name, which is made of simple parts separated with
    slashes), computes the last part, that is the one after the last
    slash.
    """
    last_part = name.split('/')[-1:]
    return last_part

@accepts(str)
@returns(str)
def last_part_of_abs_node_name(node_name):
    check_node_name(node_name)
    last_part = last_part_of_abs_name(node_name)
    return last_part

@accepts(str)
@returns(str)
def last_part_of_abs_resource_name(resource_name):
    check_resource_name(resource_name)
    last_part = last_part_of_abs_name(resource_name)
    return last_part

@accepts(str, str)
@returns(str)
def reparent_child_name_under(self, child_name, parent_node_name):
    """
    Given a child name and an absolute parent node name, creates an
    absolute name for the child so as to reside under the given parent.
    Only the last part is used from the child name.
    """
    check_node_name(parent_node_name)
    last_part_child_node_name = last_part_of_abs_name(child_name)
    normalized_child_abs_name = '%s/%s' % (
        parent_node_name,
        last_part_child_node_name
    ) # recreate full node name
    return normalized_child_abs_name

@accepts(str)
@returns(str)
def reparent_group_node_name(group_node_name):
    return reparent_child_name_under(group_node_name, NameOfGroupsNode)

@accepts(str)
@returns(str)
def reparent_resource_under(resource_name, parent_abs_name):
    return reparent_child_name_under(resource_name, parent_abs_name)

NameOfSystemNode = 'system'
NameOfResourcesNode = 'system/resources'
NameOfGroupsNode = 'system/groups'
NameOfUsersNode = 'system/users'
