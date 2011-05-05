import os
import sqlite3
import logging
import types
import hashlib
import shutil
import basebackend

logger = logging.getLogger(__name__)

class BackEnd(basebackend.BaseBackEnd):

    def __init__(self, basepath):
        self.basepath = basepath
        
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
    
    # TODO: Create/delete account?
    # TODO: Catch OSError exceptions.
    
    def get_account_meta(self, account):
        """
        returns a dictionary with the account metadata
        """
        logger.debug("get_account_meta: %s", account)
        fullname = os.path.join(self.basepath, account)
        if not os.path.exists(fullname):
            raise NameError('Account does not exist')
        contents = os.listdir(fullname)
        count = len(contents)
        size = os.stat(fullname).st_size
        meta = self.__get_metadata(account)
        meta.update({'name': account, 'count': count, 'bytes': size})
        return meta

    def update_account_meta(self, account, meta):
        """
        updates the metadata associated with the account
        """
        logger.debug("update_account_meta: %s %s", account, meta)
        fullname = os.path.join(self.basepath, account)
        if not os.path.exists(fullname):
            os.makedirs(fullname)
        self.__put_metadata(account, meta)
        return
    
    def create_container(self, account, name):
        """
        creates a new container with the given name
        if it doesn't exist under the basepath
        """
        logger.debug("create_container: %s %s", account, name)
        fullname = os.path.join(self.basepath, account, name)
        if not os.path.exists(fullname):
            os.makedirs(fullname)
        else:
            raise NameError('Container already exists')
        return
    
    def delete_container(self, account, name):
        """
        deletes the container with the given name
        if it exists under the basepath and is empty
        """
        logger.debug("delete_container: %s %s", account, name)
        fullname = os.path.join(self.basepath, account, name)
        if not os.path.exists(fullname):
            raise NameError('Container does not exist')
        if os.listdir(fullname):
            raise IndexError('Container is not empty')
        else:
            os.rmdir(fullname)
            self.__del_dbpath(os.path.join(account, name))
        return
    
    def get_container_meta(self, account, name):
        """
        returns a dictionary with the container metadata
        """
        logger.debug("get_container_meta: %s %s", account, name)
        fullname = os.path.join(self.basepath, account, name)
        if not os.path.exists(fullname):
            raise NameError('Container does not exist')
        contents = os.listdir(fullname)
        count = len(contents)
        size = os.stat(fullname).st_size
        meta = self.__get_metadata(os.path.join(account, name))
        meta.update({'name': name, 'count': count, 'bytes': size})
        return meta
    
    def update_container_meta(self, account, name, meta):
        """
        updates the metadata associated with the container
        """
        logger.debug("update_container_meta: %s %s %s", account, name, meta)
        fullname = os.path.join(self.basepath, account, name)
        if not os.path.exists(fullname):
            raise NameError('Container does not exist')
        self.__put_metadata(os.path.join(account, name), meta)
        return
    
    def list_containers(self, account, marker = None, limit = 10000):
        """
        returns a list of at most limit (default = 10000) containers 
        starting from the next item after the optional marker
        """
        logger.debug("list_containers: %s %s %s", account, marker, limit)
        fullname = os.path.join(self.basepath, account)
        if not os.path.exists(fullname):
            raise NameError('Account does not exist')
        containers = os.listdir(fullname)
        start = 0
        if marker:
            try:
                start = containers.index(marker) + 1
            except ValueError:
                pass
        if not limit or limit > 10000:
            limit = 10000
        
        return containers[start:start + limit]
    
    def list_objects(self, account, container, prefix = '', delimiter = None, marker = None, limit = 10000):
        """
        returns a list of objects existing under a container
        """
        logger.info("list_objects: %s %s %s %s %s %s", account, container, prefix, delimiter, marker, limit)
        fullname = os.path.join(self.basepath, account, container)
        if not os.path.exists(fullname):
            raise NameError('Container does not exist')
        
        while prefix.startswith('/'):
            prefix = prefix[1:]
        # TODO: Test this with various prefixes. Does '//' bother it?
        prefix = os.path.join(account, container, prefix)
        c = self.con.execute('select * from objects where name like ''?'' order by name', (os.path.join(prefix, '%'),))
        objects = [x[0][len(prefix):] for x in c.fetchall()]
        if delimiter:
            pseudo_objects = []
            for x in objects:
                pseudo_name = x
                i = pseudo_name.find(delimiter)
                if i != -1:
                    pseudo_name = pseudo_name[:i]
                if pseudo_name not in pseudo_objects:
                    pseudo_objects.append(pseudo_name)
                # TODO: Virtual directories.
            objects = pseudo_objects
        
        start = 0
        if marker:
            try:
                start = objects.index(marker) + 1
            except ValueError:
                pass
        if not limit or limit > 10000:
            limit = 10000
        
        return objects[start:start + limit]
    
    def get_object_meta(self, account, container, name, keys = None):
        """
        returns a dictionary with the object metadata
        """
        logger.info("get_object_meta: %s %s %s %s", account, container, name, keys)
        fullname = os.path.join(self.basepath, account, container)
        if not os.path.exists(fullname):
            raise NameError('Container does not exist')
        
        link = self.__get_linkinfo(os.path.join(account, container, name))
        location = os.path.join(self.basepath, account, container, link)
        size = os.path.getsize(location)
        mtime = os.path.getmtime(location)
        meta = self.__get_metadata(os.path.join(account, container, name))
        meta.update({'name': name, 'bytes': size, 'last_modified': mtime})
        if 'hash' not in meta:
            meta['hash'] = self.__object_hash(location)
        if 'content_type' not in meta:
            meta['content_type'] = 'application/octet-stream'
        return meta
    
    def update_object_meta(self, account, container, name, meta):
        """
        updates the metadata associated with the object
        """
        logger.info("update_object_meta: %s %s %s %s", account, container, name, meta)
        fullname = os.path.join(self.basepath, account, container)
        if not os.path.exists(fullname):
            raise NameError('Container does not exist')
        try:
            link = self.__get_linkinfo(os.path.join(account, container, name))
        except NameError:
            raise NameError('Object does not exist')
        self.__put_metadata(os.path.join(account, container, name), meta)
        return
    
    def get_object(self, account, container, name, offset = 0, length = -1):
        """
        returns the object data
        """
        logger.info("get_object: %s %s %s %s %s", account, container, name, offset, length)
        fullname = os.path.join(self.basepath, account, container)
        if not os.path.exists(fullname):
            raise NameError('Container does not exist')
        
        link = self.__get_linkinfo(os.path.join(account, container, name))
        location = os.path.join(self.basepath, account, container, link)
        f = open(location, 'r')
        if offset:
            f.seek(offset)
        data = f.read(length)
        f.close()
        return data

    def update_object(self, account, container, name, data, offset = 0):
        """
        creates/updates an object with the specified data
        """
        logger.info("put_object: %s %s %s %s %s", account, container, name, data, offset)
        fullname = os.path.join(self.basepath, account, container)
        if not os.path.exists(fullname):
            raise NameError('Container does not exist')

        try:
            link = self.__get_linkinfo(os.path.join(account, container, name))
        except NameError:
            # new object
            link = self.__put_linkinfo(os.path.join(account, container, name))
        location = os.path.join(self.basepath, account, container, link)
        f = open(location, 'w')
        if offset:
            f.seek(offset)
        f.write(data)
        f.close()
        self.__put_metadata(os.path.join(account, container, name), {'hash': self.__object_hash(location)})
        return
    
    def copy_object(self, account, src_container, src_name, dest_container, dest_name):
        """
        copies an object
        """
        logger.info("copy_object: %s %s %s %s %s", account, src_container, src_name, dest_container, dest_name)
        link = self.__get_linkinfo(os.path.join(account, src_container, src_name))
        src_location = os.path.join(self.basepath, account, src_container, link)
        
        dest_fullname = os.path.join(self.basepath, account, dest_container)
        if not os.path.exists(dest_fullname):
            raise NameError('Destination container does not exist')        
        try:
            link = self.__get_linkinfo(os.path.join(account, dest_container, dest_name))
        except NameError:
            # new object
            link = self.__put_linkinfo(os.path.join(account, dest_container, dest_name))
        dest_location = os.path.join(self.basepath, account, dest_container, link)
        
        shutil.copyfile(src_location, dest_location)
        # TODO: accept metadata changes
        self.__put_metadata(os.path.join(account, dest_container, dest_name), self.__get_metadata(os.path.join(account, src_container, src_name)))
        return
    
    def delete_object(self, account, container, name):
        """
        deletes an object
        """
        logger.info("delete_object: %s %s %s", account, container, name)
        fullname = os.path.join(self.basepath, account, container)
        if not os.path.exists(fullname):
            raise NameError('Container does not exist')
        
        # delete object data
        link = self.__get_linkinfo(os.path.join(account, container, name))
        location = os.path.join(self.basepath, account, container, link)
        try:
            os.remove(location)
        except:
            pass
        # delete object metadata
        self.__del_dbpath(os.path.join(account, container, name))
        return

    def __get_linkinfo(self, path):
        c = self.con.execute('select rowid from objects where name=''?''', (path,))
        row = c.fetchone()
        if row:
            return str(row[0])
        else:
            raise NameError('Requested path not found')
    
    def __put_linkinfo(self, path):
        id = self.con.execute('insert into objects (name) values (?)', (path,)).lastrowid
        self.con.commit()
        return str(id)
    
    def __get_metadata(self, path):
        c = self.con.execute('select m.name, m.value from metadata m, objects o where o.rowid = m.object_id and o.name = ''?''', (path,))
        return dict(c.fetchall())
    
    def __put_metadata(self, path, meta):
        c = self.con.execute('select rowid from objects where name=''?''', (path,))
        row = c.fetchone()
        if row:
            link = str(row[0])
        else:
            link = self.con.execute('insert into objects (name) values (?)', (path,)).lastrowid      
        for k, v in meta.iteritems():
            self.con.execute('insert or replace into metadata (object_id, name, value) values (?, ?, ?)', (link, k, v))
        self.con.commit()
        return

    def __del_dbpath(self, path):
        self.con.execute('delete from metadata where object_id in (select rowid from objects where name = ''?'')', (path,))
        self.con.execute('delete from objects where name = ''?''', (path,))
        self.con.commit()
        return
    
    def __object_hash(self, location, block_size = 8192):
        md5 = hashlib.md5()
        f = open(location, 'r')
        while True:
            data = f.read(block_size)
            if not data:
                break
            md5.update(data)
        f.close()
        return md5.hexdigest()
