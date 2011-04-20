
def create_container(name):
    return

def delete_container(name):
    return

def get_container_meta(name):
    return {'name': name, 'count': 0, 'bytes': 0}

def list_containers():
    return []

def list_objects(container, prefix='', delimiter='/'):
    return []

def get_object_meta(container, name):
    return {'name': name, 'hash': '', 'bytes': 0}

def get_object_data(container, name, offset=0, length=0):
    return ''

def update_object(container, name, meta, data):
    return

def update_object_meta(container, name, meta):
    return

def copy_object(container, name, new_name):
    return

def delete_object(container, name):
    return
