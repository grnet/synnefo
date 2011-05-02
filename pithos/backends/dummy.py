import os
import sqlite3
import json
import logging
import types

class BackEnd:
    def __init__(self, basepath, log_file='backend.out', log_level=logging.DEBUG):
        self.basepath = basepath
        logging.basicConfig(filename=log_file,level=log_level,)
        if not os.path.exists(basepath):
            os.makedirs(basepath)
        db = os.path.join(basepath, 'db')
        self.con = sqlite3.connect(db)
        # Create tables
        sql = '''create table if not exists objects(name text)'''
        self.con.execute(sql)
        sql = '''create table if not exists metadata(object_id int, name text, value text)'''
        self.con.execute(sql)
        self.con.commit()

    def get_account_meta(self, account):
        """
        returns a dictionary with the container metadata
        """
        logging.info("get_account_meta: %s", account)
        fullname = os.path.join(self.basepath, account)
        print fullname
        if not os.path.exists(fullname):
            raise NameError('Account does not exist')
        contents = os.listdir(fullname) 
        count = len(contents)
        size = sum(os.path.getsize(os.path.join(self.basepath, account, objectname)) for objectname in contents)
        return {'name': account, 'count': count, 'bytes': size}
        
    def create_container(self, account, name):
        """
        creates a new container with the given name
        if it doesn't exists under the basepath
        """
        logging.info("create_container: %s %s", account, name)
        fullname = os.path.join(self.basepath, account, name)    
        if not os.path.exists(fullname):
            os.makedirs(fullname)
        else:
            raise NameError('Container already exists')
        return

    def delete_container(self, account, name):
        """
        deletes the container with the given name
        if it exists under the basepath
        and it's empty
        """
        logging.debug("delete_container: %s %s", account, name)
        fullname = os.path.join(self.basepath, account, name)    
        if not os.path.exists(fullname):
            raise NameError('Container does not exist')
        if os.listdir(fullname):
            raise Exception('Container is not empty')
        else:
            os.rmdir(fullname)
        return
    
    def get_container_meta(self, account, name):
        """
        returns a dictionary with the container metadata
        """
        fullname = os.path.join(self.basepath, account, name)
        if not os.path.exists(fullname):
            raise NameError('Container does not exist')
        contents = os.listdir(fullname) 
        count = len(contents)
        size = sum(os.path.getsize(os.path.join(self.basepath, account, name, objectname)) for objectname in contents)
        return {'name': name, 'count': count, 'bytes': size}
    
    def list_containers(self, account, marker = None, limit = 10000):
        """
        returns a list of at most limit (default = 10000) account containers 
        starting from the next item after marker
        if optinal parameter marker is provided
        or the 1st item otherwise
        """
        containers = os.listdir(os.path.join(self.basepath, account))
        start = 0
        if marker:
            try:
                start = containers.index(marker)
            except ValueError:
                pass
        return containers[start:limit]
    
    def list_objects(self, account, container, prefix='', delimiter=None, marker = None, limit = 10000):
        """
        returns a list of the objects existing under a specific account container
        """
        logging.info("list_objects: %s %s %s %s %s %s", account, container, prefix, delimiter, marker, limit)
        dir = os.path.join(self.basepath, account, container)
        if not os.path.exists(dir):
            raise NameError('Container does not exist')
        p1 = ''.join(['%', prefix, '%'])
        p2 = '/'.join([account, container, '%'])
        search_str = (prefix and [p1] or [p2])[0]
        c = self.con.execute('select * from objects where name like ''?'' order by name', (search_str,))
        objects = c.fetchall()
        if delimiter:
            pseudo_objects = {}
            for x in objects:
                pseudo_name = x[0][len(prefix):]
                i = pseudo_name.find(delimiter)
                if i != -1:
                    pseudo_name = pseudo_name[:i]
                #TODO: Virtual directories.
                pseudo_objects[pseudo_name] = x
            objects = pseudo_objects.keys()
        start = 0
        if marker:
            try:
                start = objects.index(marker)
            except ValueError:
                pass
        if not limit or limit > 10000:
            limit = 10000
        return objects[start:start + limit]
    
    def get_object_meta(self, account, container, name, keys='*'):
        dir = os.path.join(self.basepath, account, container)
        if not os.path.exists(dir):
            raise NameError('Container does not exist')
        else:
            os.chdir(dir)
        location = self.__get_object_linkinfo('/'.join([account, container, name]))
        location = '.'.join([location, 'meta'])
        f = open(location, 'r')
        data = json.load(f)
        f.close()
        return data
    
    def get_object_data(self, account, container, name, offset=0, length=-1):
        dir = os.path.join(self.basepath, account, container)
        if not os.path.exists(dir):
            raise NameError('Container does not exist')
        else:
            os.chdir(dir)
        location = self.__get_object_linkinfo(os.path.join(account, container, name))
        f = open(location, 'r')
        if offset:
            f.seek(offset)
        data = f.read(length)
        f.close()
        return data
    
    def update_object(self, account, container, name, data):
        dir = os.path.join(self.basepath, account, container)
        if not os.path.exists(dir):
            raise NameError('Container does not exist')
        try:
            location = self.__get_object_linkinfo(os.path.join(account, container, name))
        except NameError:
            # new object
            location = str(self.__save_linkinfo(os.path.join(account, container, name)))
        self.__store_data(location, account, container, data)
        return
    
    def update_object_meta(self, account, container, name, meta):
        dir = os.path.join(self.basepath, account, container)
        if not os.path.exists(dir):
            raise NameError('Container does not exist')
        try:
            location = self.__get_object_linkinfo(os.path.join(account, container, name))
        except NameError:
            # new object
            location = str(self.__save_linkinfo(os.path.join(account, container, name)))
        self.__store_metadata(location, account, container, meta)
        return
    
    def copy_object(self, account, src_container, src_name, dest_container, dest_name, meta):
        fullname = os.path.join(self.basepath, account, dest_container)    
        if not os.path.exists(fullname):
            raise NameError('Destination container does not exist')
        data = self.get_object_data(account, src_container, src_name)
        self.update_object(account, dest_container, dest_name, data)
        src_object_meta = self.get_object_meta(account, src_container, src_name)
        if (type(src_object_meta) == types.DictType):
            distinct_keys = [k for k in src_object_meta.keys() if k not in meta.keys()]
            for k in distinct_keys:
                meta[k] = src_object_meta[k]
                self.update_object_meta(account, dest_container, dest_name, meta)
        else:
            self.update_object_meta(account, dest_container, dest_name, meta)
        return
    
    def delete_object(self, account, container, name):
        dir = os.path.join(self.basepath, account, container)
        if not os.path.exists(dir):
            raise NameError('Container does not exist')
        else:
            os.chdir(dir)
        location = self.__get_object_linkinfo(os.path.join(account, container, name))
        # delete object data
        self.__delete_data(location, account, container)
        # delete object metadata
        location = '.'.join([location, 'meta'])
        self.__delete_data(location, account, container)
        return
    
    def __store_metadata(self, location, account, container, meta):
        dir = os.path.join(self.basepath, account, container)
        if not os.path.exists(dir):
            raise NameError('Container does not exist')
        else:
            os.chdir(dir)
        location = '.'.join([location, 'meta'])
        f = open(location, 'w')
        data = json.dumps(meta)
        f.write(data)
        f.close()
    
    def __store_data(self, location, account, container, data):
        dir = os.path.join(self.basepath, account, container)
        if not os.path.exists(dir):
            raise NameError('Container does not exist')
        else:
            os.chdir(dir)
        f = open(location, 'w')
        f.write(data)
        f.close()
        
    def __delete_data(self, location, account, container):
        file = os.path.join(self.basepath, account, container, location)
        if not os.path.exists(dir):
            raise NameError('Container does not exist')
        else:
            os.remove(file)
        
    def __get_object_linkinfo(self, name):
        c = self.con.execute('select rowid from objects where name=''?''', (name,))
        row = c.fetchone()
        if row:
            return str(row[0])
        else:
            raise NameError('Object not found')
    
    def __save_linkinfo(self, name):
        id = self.con.execute('insert into objects(name) values(?)', (name,)).lastrowid
        self.con.commit()
        return id
    
    def __delete_linkinfo(self, name):
        self.con.execute('delete from objects where name = ?', (name,))
        self.cont.commit()
        return