import os
import time
import sqlite3
import logging
import types
import hashlib
import shutil
import pickle

from base import BaseBackend


logger = logging.getLogger(__name__)


class SimpleBackend(BaseBackend):
    """A simple backend.
    
    Uses SQLite for storage.
    """
    
    def __init__(self, db):
        self.hash_algorithm = 'sha1'
        self.block_size = 128 * 1024 # 128KB
        
        basepath = os.path.split(db)[0]
        if basepath and not os.path.exists(basepath):
            os.makedirs(basepath)
        
        self.con = sqlite3.connect(db)
        sql = '''create table if not exists objects (
                    name text, tstamp text, primary key (name))'''
        self.con.execute(sql)
        sql = '''create table if not exists metadata (
                    name text, key text, value text, primary key (name, key))'''
        self.con.execute(sql)
        sql = '''create table if not exists versions (
                    object_id int, version int, size int, primary key (object_id, version))'''
        self.con.execute(sql)
        sql = '''create table if not exists blocks (
                    block_id text, data blob, primary key (block_id))'''
        self.con.execute(sql)
        sql = '''create table if not exists hashmaps (
                    version_id int, pos int, block_id text, primary key (version_id, pos))'''
        self.con.execute(sql)
        self.con.commit()
    
    def get_account_meta(self, account):
        """Return a dictionary with the account metadata."""
        
        logger.debug("get_account_meta: %s", account)
        count, bytes = self._get_pathstats(account)
        
        # Proper count.
        sql = 'select count(name) from objects where name glob ? and not name glob ?'
        c = self.con.execute(sql, (account + '/*', account + '/*/*'))
        row = c.fetchone()
        count = row[0]
        
        meta = self._get_metadata(account)
        meta.update({'name': account, 'count': count, 'bytes': bytes})
        return meta
    
    def update_account_meta(self, account, meta, replace=False):
        """Update the metadata associated with the account."""
        
        logger.debug("update_account_meta: %s %s %s", account, meta, replace)
        self._update_metadata(account, None, None, meta, replace)
    
    def put_container(self, account, name):
        """Create a new container with the given name."""
        
        logger.debug("put_container: %s %s", account, name)
        try:
            path, link, tstamp = self._get_containerinfo(account, name)
        except NameError:
            path = os.path.join(account, name)
            link = self._put_linkinfo(path)
        else:
            raise NameError('Container already exists')
        self._update_metadata(account, name, None, None)
    
    def delete_container(self, account, name):
        """Delete the container with the given name."""
        
        logger.debug("delete_container: %s %s", account, name)
        path, link, tstamp = self._get_containerinfo(account, name)
        count, bytes = self._get_pathstats(path)
        if count > 0:
            raise IndexError('Container is not empty')
        self._del_path(path)
        self._update_metadata(account, None, None, None)
    
    def get_container_meta(self, account, name):
        """Return a dictionary with the container metadata."""
        
        logger.debug("get_container_meta: %s %s", account, name)
        path, link, tstamp = self._get_containerinfo(account, name)
        count, bytes = self._get_pathstats(path)
        meta = self._get_metadata(path)
        meta.update({'name': name, 'count': count, 'bytes': bytes, 'created': tstamp})
        return meta
    
    def update_container_meta(self, account, name, meta, replace=False):
        """Update the metadata associated with the container."""
        
        logger.debug("update_container_meta: %s %s %s %s", account, name, meta, replace)
        path, link, tstamp = self._get_containerinfo(account, name)
        self._update_metadata(account, name, None, meta, replace)
    
    def list_containers(self, account, marker=None, limit=10000):
        """Return a list of containers existing under an account."""
        
        logger.debug("list_containers: %s %s %s", account, marker, limit)
        return self._list_objects(account, '', '/', marker, limit, False, [])
    
    def list_objects(self, account, container, prefix='', delimiter=None, marker=None, limit=10000, virtual=True, keys=[]):
        """Return a list of objects existing under a container."""
        
        logger.debug("list_objects: %s %s %s %s %s %s", account, container, prefix, delimiter, marker, limit)
        path, link, tstamp = self._get_containerinfo(account, container)
        return self._list_objects(path, prefix, delimiter, marker, limit, virtual, keys)
    
    def list_object_meta(self, account, name):
        """Return a list with all the container's object meta keys."""
        
        logger.debug("list_object_meta: %s %s", account, name)
        path, link, tstamp = self._get_containerinfo(account, name)
        sql = 'select distinct key from metadata where name like ?'
        c = self.con.execute(sql, (path + '/%',))
        return [x[0] for x in c.fetchall()]
    
    def get_object_meta(self, account, container, name):
        """Return a dictionary with the object metadata."""
        
        logger.debug("get_object_meta: %s %s %s", account, container, name)
        path, link, tstamp = self._get_containerinfo(account, container)
        path, link, tstamp, version, size = self._get_objectinfo(account, container, name)
        meta = self._get_metadata(path)
        meta.update({'name': name, 'bytes': size, 'version': version, 'created': tstamp})
        return meta
    
    def update_object_meta(self, account, container, name, meta, replace=False):
        """Update the metadata associated with the object."""
        
        logger.debug("update_object_meta: %s %s %s %s %s", account, container, name, meta, replace)
        path, link, tstamp = self._get_containerinfo(account, container)
        path, link, tstamp, version, size = self._get_objectinfo(account, container, name)
        if 'versioned' in meta:
            if meta['versioned']:
                if version == 0:
                    sql = 'update versions set version = 1 where object_id = ?'
                    self.con.execute(sql, (link,))
                    self.con.commit()
            else:
                if version > 0:
                    self._del_uptoversion(link, version)
                    sql = 'update versions set version = 0 where object_id = ?'
                    self.con.execute(sql, (link,))
                    self.con.commit()
            del(meta['versioned'])
        self._update_metadata(account, container, name, meta, replace)
    
    def get_object_hashmap(self, account, container, name, version=None):
        """Return the object's size and a list with partial hashes."""
        
        logger.debug("get_object_hashmap: %s %s %s %s", account, container, name, version)
        path, link, tstamp = self._get_containerinfo(account, container)
        path, link, tstamp, version, size = self._get_objectinfo(account, container, name, version)
        
        sql = '''select block_id from hashmaps where version_id =
                    (select rowid from versions where object_id = ? and version = ?)
                    order by pos'''
        c = self.con.execute(sql, (link, version))
        hashmap = [x[0] for x in c.fetchall()]
        return size, hashmap
    
    def update_object_hashmap(self, account, container, name, size, hashmap):
        """Create/update an object with the specified size and partial hashes."""
        
        logger.debug("update_object_hashmap: %s %s %s %s", account, container, name, hashmap)
        path, link, tstamp = self._get_containerinfo(account, container)
        try:
            path, link, tstamp, version, s = self._get_objectinfo(account, container, name)
        except NameError:
            version = 0
        
        if version == 0:
            path = os.path.join(account, container, name)
            
            self._del_path(path, delmeta=False)
            link = self._put_linkinfo(path)
        else:
            version = version + 1
        
        sql = 'insert or replace into versions (object_id, version, size) values (?, ?, ?)'
        version_id = self.con.execute(sql, (link, version, size)).lastrowid
        for i in range(len(hashmap)):
            sql = 'insert or replace into hashmaps (version_id, pos, block_id) values (?, ?, ?)'
            self.con.execute(sql, (version_id, i, hashmap[i]))
        self.con.commit()
    
    def copy_object(self, account, src_container, src_name, dest_container, dest_name, dest_meta={}, replace_meta=False):
        """Copy an object's data and metadata."""
        
        logger.debug("copy_object: %s %s %s %s %s %s %s", account, src_container, src_name, dest_container, dest_name, dest_meta, replace_meta)
        size, hashmap = self.get_object_hashmap(account, src_container, src_name)
        self.update_object_hashmap(account, dest_container, dest_name, size, hashmap)
        if not replace_meta:
            meta = self._get_metadata(os.path.join(account, src_container, src_name))
            meta.update(dest_meta)
        else:
            meta = dest_meta
        self._update_metadata(account, dest_container, dest_name, meta, replace_meta)
    
    def move_object(self, account, src_container, src_name, dest_container, dest_name, dest_meta={}, replace_meta=False):
        """Move an object's data and metadata."""
        
        logger.debug("move_object: %s %s %s %s %s %s %s", account, src_container, src_name, dest_container, dest_name, dest_meta, replace_meta)
        self.copy_object(account, src_container, src_name, dest_container, dest_name, dest_meta, replace_meta)
        self.delete_object(account, src_container, src_name)
    
    def delete_object(self, account, container, name):
        """Delete an object."""
        
        logger.debug("delete_object: %s %s %s", account, container, name)
        path, link, tstamp = self._get_containerinfo(account, container)
        path = os.path.join(account, container, name)
        link, tstamp = self._get_linkinfo(path)
        self._del_path(path)
        self._update_metadata(account, container, None, None)
    
    def get_block(self, hash):
        """Return a block's data."""
        
        c = self.con.execute('select data from blocks where block_id = ?', (hash,))
        row = c.fetchone()
        if row:
            return str(row[0])
        else:
            raise NameError('Block does not exist')
    
    def put_block(self, data):
        """Create a block and return the hash."""
        
        h = hashlib.new(self.hash_algorithm)
        h.update(data.rstrip('\x00'))
        hash = h.hexdigest()
        sql = 'insert or ignore into blocks (block_id, data) values (?, ?)'
        self.con.execute(sql, (hash, buffer(data)))
        self.con.commit()
        return hash
    
    def update_block(self, hash, data, offset=0):
        """Update a known block and return the hash."""
        
        src_data = self.get_block(hash)
        bs = self.block_size
        if offset < 0 or offset > bs or offset + len(data) > bs:
            raise IndexError('Offset or data outside block limits')
        dest_data = src_data[:offset] + data + src_data[offset + len(data):]
        return self.put_block(dest_data)
    
    def _get_linkinfo(self, path):
        c = self.con.execute('select rowid, tstamp from objects where name = ?', (path,))
        row = c.fetchone()
        if row:
            return str(row[0]), str(row[1])
        else:
            raise NameError('Object does not exist')
    
    def _put_linkinfo(self, path):
        sql = 'insert into objects (name, tstamp) values (?, ?)'
        id = self.con.execute(sql, (path, int(time.time()))).lastrowid
        self.con.commit()
        return str(id)
    
    def _get_containerinfo(self, account, container):
        path = os.path.join(account, container)
        try:
            link, tstamp = self._get_linkinfo(path)
        except NameError:
            raise NameError('Container does not exist')
        return path, link, tstamp
    
    def _get_objectinfo(self, account, container, name, version=None):
        path = os.path.join(account, container, name)
        link, tstamp = self._get_linkinfo(path)
        if not version: # If zero or None.
            sql = '''select version, size from versions v,
                        (select object_id, max(version) as m from versions
                            where object_id = ? group by object_id) as g
                        where v.object_id = g.object_id and v.version = g.m'''
            c = self.con.execute(sql, (link,))
        else:
            sql = 'select version, size from versions where object_id = ? and version = ?'
            c = self.con.execute(sql, (link, version))
        row = c.fetchone()
        if not row:
            raise IndexError('Version does not exist')
        
        return path, link, tstamp, int(row[0]), int(row[1])
    
    def _get_pathstats(self, path):
        """Return count and sum of size of all objects under path."""
        
        sql = '''select count(o), total(size) from (
                    select v.object_id as o, v.size from versions v,
                        (select object_id, max(version) as m from versions where object_id in
                            (select rowid from objects where name like ?) group by object_id) as g
                        where v.object_id = g.object_id and v.version = g.m
                    union
                    select rowid as o, 0 as size from objects where name like ?
                        and rowid not in (select object_id from versions))'''
        c = self.con.execute(sql, (path + '/%', path + '/%'))
        row = c.fetchone()
        return int(row[0]), int(row[1])
    
    def _list_objects(self, path, prefix='', delimiter=None, marker=None, limit=10000, virtual=True, keys=[]):
        cont_prefix = path + '/'
        if keys and len(keys) > 0:
            sql = '''select o.name from objects o, metadata m where o.name like ? and
                        m.name = o.name and m.key in (%s) order by o.name'''
            sql = sql % ', '.join('?' * len(keys))
            param = (cont_prefix + prefix + '%',) + tuple(keys)
        else:
            sql = 'select name from objects where name like ? order by name'
            param = (cont_prefix + prefix + '%',)
        c = self.con.execute(sql, param)
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
    
    def _get_metadata(self, path):
        sql = 'select key, value from metadata where name = ?'
        c = self.con.execute(sql, (path,))
        return dict(c.fetchall())
    
    def _put_metadata(self, path, meta, replace=False):
        if replace:
            sql = 'delete from metadata where name = ?'
            self.con.execute(sql, (path,))
        for k, v in meta.iteritems():
            sql = 'insert or replace into metadata (name, key, value) values (?, ?, ?)'
            self.con.execute(sql, (path, k, v))
        self.con.commit()
    
    def _update_metadata(self, account, container, name, meta, replace=False):
        """Recursively update metadata and set modification time."""
        
        modified = {'modified': int(time.time())}
        if not meta:
            meta = {}
        meta.update(modified)
        path = (account, container, name)
        for x in reversed(range(3)):
            if not path[x]:
                continue
            self._put_metadata(os.path.join(*path[:x+1]), meta, replace)
            break
        for y in reversed(range(x)):
            self._put_metadata(os.path.join(*path[:y+1]), modified)
    
    def _del_uptoversion(self, link, version):
        sql = '''delete from hashmaps where version_id
                    (select rowid from versions where object_id = ? and version < ?)'''
        self.con.execute(sql, (link, version))
        self.con.execute('delete from versions where object_id = ?', (link,))
        self.con.commit()
    
    def _del_path(self, path, delmeta=True):
        sql = '''delete from hashmaps where version_id in
                    (select rowid from versions where object_id in
                    (select rowid from objects where name = ?))'''
        self.con.execute(sql, (path,))
        sql = '''delete from versions where object_id in
                    (select rowid from objects where name = ?)'''
        self.con.execute(sql, (path,))
        self.con.execute('delete from objects where name = ?', (path,))
        if delmeta:
            self.con.execute('delete from metadata where name = ?', (path,))
        self.con.commit()
