import os
import time
import sqlite3
import logging
import types
import hashlib
import shutil

from base import BaseBackend


logger = logging.getLogger(__name__)


class SimpleBackend(BaseBackend):
    def __init__(self, basepath):
        self.basepath = basepath
        
        if not os.path.exists(basepath):
            os.makedirs(basepath)
        db = os.path.join(basepath, 'db')
        self.con = sqlite3.connect(db)
        # Create tables
        sql = 'create table if not exists objects (name TEXT)'
        self.con.execute(sql)
        sql = '''create table if not exists metadata (
                    object_id int, key text, value text, primary key (object_id, key))'''
        self.con.execute(sql)
        self.con.commit()
    
    def get_account_meta(self, account):
        """Return a dictionary with the account metadata."""
        
        logger.debug("get_account_meta: %s", account)
        try:
            fullname = self._get_accountinfo(account)
        except NameError:
            return {'name': account, 'count': 0, 'bytes': 0}
        contents = os.listdir(fullname)
        count = len(contents)
        size = 0
        for y in (os.path.join(fullname, z) for z in contents):
            size += sum((os.path.getsize(os.path.join(y, x)) for x in os.listdir(y)))
        meta = self._get_metadata(account)
        meta.update({'name': account, 'count': count, 'bytes': size})
        return meta
    
    def update_account_meta(self, account, meta):
        """Update the metadata associated with the account."""
        
        logger.debug("update_account_meta: %s %s", account, meta)
        fullname = os.path.join(self.basepath, account)
        if not os.path.exists(fullname):
            os.makedirs(fullname)
        self._update_metadata(account, None, None, meta)
    
    def create_container(self, account, name):
        """Create a new container with the given name."""
        
        logger.debug("create_container: %s %s", account, name)
        fullname = os.path.join(self.basepath, account, name)
        if not os.path.exists(fullname):
            os.makedirs(fullname)
        else:
            raise NameError('Container already exists')
        self._update_metadata(account, name, None, None)
    
    def delete_container(self, account, name):
        """Delete the container with the given name."""
        
        logger.debug("delete_container: %s %s", account, name)
        fullname = self._get_containerinfo(account, name)
        if os.listdir(fullname):
            raise IndexError('Container is not empty')
        os.rmdir(fullname)
        self._del_dbpath(os.path.join(account, name))
        self._update_metadata(account, None, None, None)
    
    def get_container_meta(self, account, name):
        """Return a dictionary with the container metadata."""
        
        logger.debug("get_container_meta: %s %s", account, name)
        fullname = self._get_containerinfo(account, name)
        contents = os.listdir(fullname)
        count = len(contents)
        size = sum((os.path.getsize(os.path.join(fullname, x)) for x in contents))
        meta = self._get_metadata(os.path.join(account, name))
        meta.update({'name': name, 'count': count, 'bytes': size})
        return meta
    
    def update_container_meta(self, account, name, meta):
        """Update the metadata associated with the container."""
        
        logger.debug("update_container_meta: %s %s %s", account, name, meta)
        fullname = self._get_containerinfo(account, name)
        self._update_metadata(account, name, None, meta)
    
    def list_containers(self, account, marker=None, limit=10000):
        """Return a list of containers existing under an account."""
        
        logger.debug("list_containers: %s %s %s", account, marker, limit)
        try:
            fullname = self._get_accountinfo(account)
        except NameError:
            containers = []
        containers = os.listdir(fullname)
        containers.sort()
        
        start = 0
        if marker:
            try:
                start = containers.index(marker) + 1
            except ValueError:
                pass
        if not limit or limit > 10000:
            limit = 10000
        return containers[start:start + limit]
    
    def list_objects(self, account, container, prefix='', delimiter=None, marker=None, limit=10000, virtual=True):
        """Return a list of objects existing under a container."""
        
        logger.debug("list_objects: %s %s %s %s %s %s", account, container, prefix, delimiter, marker, limit)
        fullname = self._get_containerinfo(account, container)
        
        cont_prefix = os.path.join(account, container) + '/'
        sql = 'select * from objects where name like ? order by name'
        c = self.con.execute(sql, (cont_prefix + prefix + '%',))
        objects = [x[0][len(cont_prefix):] for x in c.fetchall()]
        if delimiter:
            pseudo_objects = []
            for x in objects:
                pseudo_name = x
                i = pseudo_name.find(delimiter, len(prefix))
                if not virtual:
                    # If the delimiter is not found, or the name ends
                    # with the delimiter's first occurence.
                    if i == -1 or len(pseudo_name) == i + len(delimiter):
                        pseudo_objects.append(pseudo_name)
                else:
                    # If the delimiter is found, keep up to (and including) the delimiter.
                    if i != -1:
                        pseudo_name = pseudo_name[:i + len(delimiter)]
                    if pseudo_name not in pseudo_objects:
                        pseudo_objects.append(pseudo_name)
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
    
    def get_object_meta(self, account, container, name):
        """Return a dictionary with the object metadata."""
        
        logger.debug("get_object_meta: %s %s %s", account, container, name)
        fullname = self._get_containerinfo(account, container)
        link = self._get_linkinfo(os.path.join(account, container, name))
        location = os.path.join(self.basepath, account, container, link)
        size = os.path.getsize(location)
        meta = self._get_metadata(os.path.join(account, container, name))
        meta.update({'name': name, 'bytes': size})
        return meta
    
    def update_object_meta(self, account, container, name, meta):
        """Update the metadata associated with the object."""
        
        logger.debug("update_object_meta: %s %s %s %s", account, container, name, meta)
        fullname = self._get_containerinfo(account, container)
        link = self._get_linkinfo(os.path.join(account, container, name))
        self._update_metadata(account, container, name, meta)
    
    def get_object(self, account, container, name, offset=0, length=-1):
        """Return the object data."""
        
        logger.debug("get_object: %s %s %s %s %s", account, container, name, offset, length)
        fullname = self._get_containerinfo(account, container)       
        link = self._get_linkinfo(os.path.join(account, container, name))
        location = os.path.join(self.basepath, account, container, link)
        f = open(location, 'r')
        if offset:
            f.seek(offset)
        data = f.read(length)
        f.close()
        return data

    def update_object(self, account, container, name, data, offset=0):
        """Create/update an object with the specified data."""
        
        logger.debug("put_object: %s %s %s %s %s", account, container, name, data, offset)
        fullname = self._get_containerinfo(account, container)
        
        try:
            link = self._get_linkinfo(os.path.join(account, container, name))
        except NameError:
            # new object
            link = self._put_linkinfo(os.path.join(account, container, name))
        location = os.path.join(self.basepath, account, container, link)
        f = open(location, 'w')
        if offset:
            f.seek(offset)
        f.write(data)
        f.close()
        self._update_metadata(account, container, name, None)
    
    def copy_object(self, account, src_container, src_name, dest_container, dest_name, dest_meta={}):
        """Copy an object's data and metadata."""
        
        logger.debug("copy_object: %s %s %s %s %s %s",
                        account, src_container, src_name, dest_container, dest_name, dest_meta)
        link = self._get_linkinfo(os.path.join(account, src_container, src_name))
        src_location = os.path.join(self.basepath, account, src_container, link)

        dest_fullname = self._get_containerinfo(account, dest_container)       
        try:
            link = self._get_linkinfo(os.path.join(account, dest_container, dest_name))
        except NameError:
            # new object
            link = self._put_linkinfo(os.path.join(account, dest_container, dest_name))
        dest_location = os.path.join(self.basepath, account, dest_container, link)
        
        shutil.copyfile(src_location, dest_location)
        
        meta = self._get_metadata(os.path.join(account, src_container, src_name))
        meta.update(dest_meta)
        self._update_metadata(account, dest_container, dest_name, meta)
        return
    
    def move_object(self, account, src_container, src_name, dest_container, dest_name, dest_meta={}):
        """Move an object's data and metadata."""
        
        logger.debug("move_object: %s %s %s %s %s %s",
                        account, src_container, src_name, dest_container, dest_name, dest_meta)
        self.copy_object(account, src_container, src_name, dest_container, dest_name, dest_meta)
        self.delete_object(account, src_container, src_name)
    
    def delete_object(self, account, container, name):
        """Delete an object."""
        
        logger.debug("delete_object: %s %s %s", account, container, name)
        fullname = self._get_containerinfo(account, container)       
        
        # delete object data
        link = self._get_linkinfo(os.path.join(account, container, name))
        location = os.path.join(self.basepath, account, container, link)
        try:
            os.remove(location)
        except:
            pass
        # delete object metadata
        self._del_dbpath(os.path.join(account, container, name))
        self._update_metadata(account, container, None, None)
    
    def _get_accountinfo(self, account):
        path = os.path.join(self.basepath, account)
        if not os.path.exists(path):
            raise NameError('Account does not exist')
        return path
    
    def _get_containerinfo(self, account, container):
        path = os.path.join(self.basepath, account, container)
        if not os.path.exists(path):
            raise NameError('Container does not exist')
        return path
    
    def _get_linkinfo(self, path):
        c = self.con.execute('select rowid from objects where name=?', (path,))
        row = c.fetchone()
        if row:
            return str(row[0])
        else:
            raise NameError('Object does not exist')
    
    def _put_linkinfo(self, path):
        id = self.con.execute('insert into objects (name) values (?)', (path,)).lastrowid
        self.con.commit()
        return str(id)
    
    def _get_metadata(self, path):
        sql = 'select m.key, m.value from metadata m, objects o where o.rowid = m.object_id and o.name = ?'
        c = self.con.execute(sql, (path,))
        return dict(c.fetchall())
    
    def _put_metadata(self, path, meta):
        c = self.con.execute('select rowid from objects where name=?', (path,))
        row = c.fetchone()
        if row:
            link = str(row[0])
        else:
            link = self.con.execute('insert into objects (name) values (?)', (path,)).lastrowid      
        for k, v in meta.iteritems():
            sql = 'insert or replace into metadata (object_id, key, value) values (?, ?, ?)'
            self.con.execute(sql, (link, k, v))
        self.con.commit()
    
    def _update_metadata(self, account, container, name, meta):
        """Recursively update metadata and set modification time."""
        
        modified = {'modified': int(time.time())}
        if not meta:
            meta = {}
        meta.update(modified)
        path = (account, container, name)
        for x in reversed(range(3)):
            if not path[x]:
                continue
            self._put_metadata(os.path.join(*path[:x+1]), meta)
            break
        for y in reversed(range(x)):
            self._put_metadata(os.path.join(*path[:y+1]), modified)
    
    def _del_dbpath(self, path):
        sql = 'delete from metadata where object_id in (select rowid from objects where name = ?)'
        self.con.execute(sql, (path,))
        self.con.execute('delete from objects where name = ?', (path,))
        self.con.commit()
        return
