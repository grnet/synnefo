from commissioning.clients.http import HTTP_API_Client
from commissioning import QuotaholderAPI

def new_quota_holder_client(QH_URL):
    """
    Create a new quota holder api client
    """
    class QuotaholderHTTP(HTTP_API_Client):
        api_spec = QuotaholderAPI()

    return QuotaholderHTTP(QH_URL)

def check_string(name, value):
    assert isinstance(value, str), "%s is not a string, but a %s" % (name, type(value))
    return value

def check_context(context):
    assert isinstance(context, dict)
    return context

def check_node_name(node_name):
    assert isinstance(node_name, str)
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