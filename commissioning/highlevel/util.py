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

def check_node_name(node_name):
    assert len(node_name) > 0
    return node_name

def check_node_key(node_key):
    assert (node_key is None) or isinstance(node_key, str)
    return node_key

def is_system_node(node_name):
    check_node_name(node_name)
    return node_name == 'system'

def parent_node_name_of(node_name):
    if is_system_node(node_name):
        return node_name
    else:
        check_node_name(node_name)

        # For 'a/b/c' we get ['a', 'b', 'c']
        # And for 'a' we get ['a']
        elements = node_name.split('/')
        if len(elements) == 1:
            raise Exception("Only 'system' is the top level entity, you provided '%s'" % (node_name))
        else:
            upto_name = '/'.join(elements[:-1])
            return upto_name

NameOfSystemNode = 'system'
NameOfResourcesNode = 'system/resources'
NameOfGroupsNode = 'system/groups'
NameOfUsersNode = 'system/users'
