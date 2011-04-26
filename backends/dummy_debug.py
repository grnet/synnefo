"""
Dummy backend with debugging output

A backend with no functionality other than producing debugging output.
"""

import logging

def binary_search_name(a, x, lo = 0, hi = None):
    """
    Search a sorted array of dicts for the value of the key 'name'.
    Raises ValueError if the value is not found.
    
    a -- the array
    x -- the value to search for
    """
    if hi is None:
        hi = len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        midval = a[mid]['name']
        if midval < x:
            lo = mid + 1
        elif midval > x: 
            hi = mid
        else:
            return mid
    raise ValueError()

def get_account_meta(account):
    logging.debug("get_account_meta: %s %s", account, name)
    return {'count': 13, 'bytes': 3148237468}

def create_container(account, name):
    """
    Returns True if the container was created, False if it already exists.
    """
    logging.debug("create_container: %s %s", account, name)
    return True

def delete_container(account, name):
    logging.debug("delete_container: %s %s", account, name)
    return

def get_container_meta(account, name):
    logging.debug("get_container_meta: %s %s", account, name)
    return {'count': 22, 'bytes': 245}

def list_containers(account, marker = None, limit = 10000):
    logging.debug("list_containers: %s %s %s", account, marker, limit)
    
    containers = [
            {'name': '1', 'count': 2, 'bytes': 123},
            {'name': '2', 'count': 22, 'bytes': 245},
            {'name': '3', 'count': 222, 'bytes': 83745},
            {'name': 'four', 'count': 2222, 'bytes': 274365}
        ]
    
    start = 0
    if marker:
        try:
            start = binary_search_name(containers, marker) + 1
        except ValueError:
            pass
    if not limit or limit > 10000:
        limit = 10000
    
    return containers[start:start + limit]

def list_objects(account, container, prefix = None, delimiter = None, marker = None, limit = 10000):
    logging.debug("list_objects: %s %s %s %s %s %s", account, container, prefix, delimiter, marker, limit)

    objects = [
            {'name': 'other', 'hash': 'dfgs', 'bytes': 0, 'content_type': 'application/directory', 'last_modified': 23453454},
            {'name': 'other/something', 'hash': 'vkajf', 'bytes': 234, 'content_type': 'application/octet-stream', 'last_modified': 878434562},
            {'name': 'photos', 'hash': 'kajdsn', 'bytes': 0, 'content_type': 'application/directory', 'last_modified': 1983274},
            {'name': 'photos/asdf', 'hash': 'jadsfkj', 'bytes': 0, 'content_type': 'application/directory', 'last_modified': 378465873},
            {'name': 'photos/asdf/test', 'hash': 'sudfhius', 'bytes': 37284, 'content_type': 'text/plain', 'last_modified': 93674212},
            {'name': 'photos/me.jpg', 'hash': 'sdgsdfgsf', 'bytes': 534, 'content_type': 'image/jpeg', 'last_modified': 262345345},
            {'name': 'photos/text.txt', 'hash': 'asdfasd', 'bytes': 34243, 'content_type': 'text/plain', 'last_modified': 45345345}
        ]
    
    if prefix or delimiter:
        if prefix:
            objects = [x for x in objects if x['name'].startswith(prefix)]
        if delimiter:
            pseudo_objects = {}
            for x in objects:
                pseudo_name = x['name'][len(prefix):]
                i = pseudo_name.find(delimiter)
                if i != -1:
                    pseudo_name = pseudo_name[:i]
                # TODO: Virtual directories.
                if pseudo_name not in pseudo_objects:
                    pseudo_objects[pseudo_name] = x
            objects = sorted(pseudo_objects.values(), key=lambda o: o['name'])
        
    start = 0
    if marker:
        try:
            start = binary_search_name(objects, marker) + 1
        except ValueError:
            pass
    if not limit or limit > 10000:
        limit = 10000
    
    return objects[start:start + limit]

def get_object_meta(account, container, name):
    logging.debug("get_object_meta: %s %s %s", account, container, name)
    meta = {'meat': 'bacon', 'fruit': 'apple'}
    return {'hash': 'asdfasd', 'bytes': 34243, 'content_type': 'text/plain', 'last_modified': 45345345, 'meta': meta}

def update_object_meta(account, container, name, meta):
    logging.debug("update_object_meta: %s %s %s %s", account, container, name, meta)
    for k, v in meta.iteritems():
        pass
    return

def get_object_data(account, container, name, offset=0, length=0):
    return ''

def update_object_data(account, container, name, meta, data):
    return

def copy_object(account, container, name, new_name):
    return

def delete_object(account, container, name):
    logging.debug("delete_object: %s %s %s", account, container, name)
    return
