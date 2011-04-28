import os
import sqlite3
import json

basepath = '/Users/butters/src/pithos/backends/content' #full path
if not os.path.exists(basepath):
    os.makedirs(basepath)
db = '/'.join([basepath, 'db'])
con = sqlite3.connect(db)
# Create tables
print 'Creating tables....'
sql = '''create table if not exists objects(name varchar(2560))'''
print sql
con.execute(sql)
# Save (commit) the changes
con.commit()
    
def create_container(name):
    """ creates a new container with the given name
    if it doesn't exists under the basepath """
    fullname = '/'.join([basepath, name])    
    if not os.path.exists(fullname):
        os.chdir(basepath)
        os.mkdir(name)
    else:
        raise NameError('Container already exists')
    return

def delete_container(name):
    """ deletes the container with the given name
        if it exists under the basepath """
    fullname = '/'.join([basepath, name])    
    if not os.path.exists(fullname):
        raise NameError('Container does not exist')
    if not list_objects(name):
        raise Error('Container is not empty')
    else:
        os.chdir(basepath)
        os.rmdir(name)
    return

def get_container_meta(name):
    """ returns a dictionary with the container metadata """
    fullname = '/'.join([basepath, name])
    if not os.path.exists(fullname):
        raise NameError('Container does not exist')
    contents = os.listdir(fullname) 
    count = len(contents)
    size = sum(os.path.getsize('/'.join([basepath, name, objectname])) for objectname in contents)
    return {'name': name, 'count': count, 'bytes': size}

def list_containers():
    return os.listdir(basepath) 

def list_objects(container, prefix='', delimiter=None):
    dir = '/'.join([basepath, container])
    if not os.path.exists(dir):
        raise NameError('Container does not exist')
    search_str = ''
    if prefix:
        search_str = '/'.join([search_str, prefix])
    #if delimiter:
    if None:
        search_str = ''.join(['%', search_str, '%', delimiter])
        print search_str
        c = con.execute('select * from objects where name like ''?'' order by name', (search_str,))
    else:
        search_str = ''.join(['%', search_str, '%'])
        print search_str
        c = con.execute('select * from objects where name like ''?'' order by name', (search_str,))
    l = []
    for row in c.fetchall():
        s = ''
        print row[0]
        rest = str(row[0]).split(prefix)[1]
        print rest
        #if delimiter:
        #    rest = rest.partition(delimiter)[0]
        #print rest
        folders = rest.split('/')[:-1]
        for folder in folders:
            path = ''.join([s, folder, '/'])
            if path not in l:
                l.append(path)
            s = ''.join([s, folder, '/'])
        l.append(rest)
    return l

def get_object_meta(container, name):
    dir = '/'.join([basepath, container])
    if not os.path.exists(dir):
        raise NameError('Container does not exist')
    else:
        os.chdir(dir)
    location = __get_object_linkinfo('/'.join([container, name]))
    location = '.'.join([location, 'meta'])
    f = open(location, 'r')
    data = json.load(f)
    f.close()
    return data

def get_object_data(container, name, offset=0, length=-1):
    dir = '/'.join([basepath, container])
    if not os.path.exists(dir):
        raise NameError('Container does not exist')
    else:
        os.chdir(dir)
    location = __get_object_linkinfo('/'.join([container, name]))
    f = open(location, 'r')
    if offset:
        f.seek(offset)
    data = f.read(length)
    f.close()
    return data

def update_object(container, name, data):
    dir = '/'.join([basepath, container])
    if not os.path.exists(dir):
        raise NameError('Container does not exist')
    try:
        location = __get_object_linkinfo('/'.join([container, name]))
    except NameError:
        # new object
        location = str(__save_linkinfo('/'.join([container, name])))
        print ':'.join(['Creating new location', location])
    __store_data(location, container, data)
    return

def update_object_meta(container, name, meta):
    dir = '/'.join([basepath, container])
    if not os.path.exists(dir):
        raise NameError('Container does not exist')
    try:
        location = __get_object_linkinfo('/'.join([container, name]))
    except NameError:
        # new object
        location = str(__save_linkinfo('/'.join([container, name])))
        print ':'.join(['Creating new location', location])
    __store_metadata(location, container, meta)
    return

def copy_object(src_container, src_name, dest_container, dest_name, meta):
    fullname = '/'.join([basepath, dest_container])    
    if not os.path.exists(fullname):
        raise NameError('Destination container does not exist')
    update_object(dest_container, dest_name, get_object_data(src_container, src_name))
    src_object_meta = get_object_meta(src_container, src_name)
    if (type(src_object_meta) == types.DictType):
        distinct_keys = [k for k in src_object_meta.keys() if k not in meta.keys()]
        for k in distinct_keys:
            meta[k] = src_object_meta[k]
            update_object_meta(dest_container, dest_name, meta)
    else:
        update_object_meta(dest_container, dest_name, meta)
    return

def delete_object(container, name):
    return

def __store_metadata(location, container, meta):
    dir = '/'.join([basepath, container])
    if not os.path.exists(dir):
        raise NameError('Container does not exist')
    else:
        os.chdir(dir)
    location = '.'.join([location, 'meta'])
    f = open(location, 'w')
    data = json.dumps(meta)
    f.write(data)
    f.close()

def __store_data(location, container, data):
    dir = '/'.join([basepath, container])
    if not os.path.exists(dir):
        raise NameError('Container does not exist')
    else:
        os.chdir(dir)
    f = open(location, 'w')
    f.write(data)
    f.close()
    
def __get_object_linkinfo(name):
    c = con.execute('select rowid from objects where name=''?''', (name,))
    row = c.fetchone()
    if row:
        return str(row[0])
    else:
        raise NameError('Object not found')

def __save_linkinfo(name):
    id = con.execute('insert into objects(name) values(?)', (name,)).lastrowid
    con.commit()
    return id
    
if __name__ == '__main__':
    dirname = 'papagian'
    #create_container(dirname)
    #assert os.path.exists(dirname)
    #assert os.path.isdir(dirname)
    
    #print get_container_meta(dirname)
    
    #update_object_meta(dirname, 'photos/animals/dog.jpg', {'name':'dog.jpg'})
    #update_object_meta(dirname, 'photos/animals/dog.jpg', {'name':'dog.jpg', 'type':'image', 'size':400})
    #print get_object_meta(dirname, 'photos/animals/dog.jpg')
    
    #f = open('dummy.py')
    #data  = f.read()
    #update_object(dirname, 'photos/animals/dog.jpg', data)
    #update_object(dirname, 'photos/animals/cat.jpg', data)
    #update_object(dirname, 'photos/animals/thumbs/cat.jpg', data)
    #update_object(dirname, 'photos/fruits/banana.jpg', data)
    
    #print list_objects(dirname, 'photos/animals');
    
    copy_object(dirname, 'photos/animals/dog.jpg', 'photos/animals/dog2.jpg')
    copy_object(dirname, 'photos/animals/dg.jpg', 'photos/animals/dog2.jpg')
    
