# Copyright 2011 GRNET S.A. All rights reserved.
# 
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
# 
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
# 
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# 
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

import os
import time
import sqlite3
import logging
import types
import hashlib
import shutil
import pickle

from base import NotAllowedError, BaseBackend


logger = logging.getLogger(__name__)


class SimpleBackend(BaseBackend):
    """A simple backend.
    
    Uses SQLite for storage.
    """
    
    # TODO: Automatic/manual clean-up after a time interval.
    
    def __init__(self, db):
        self.hash_algorithm = 'sha1'
        self.block_size = 128 * 1024 # 128KB
        
        basepath = os.path.split(db)[0]
        if basepath and not os.path.exists(basepath):
            os.makedirs(basepath)
        
        self.con = sqlite3.connect(db, check_same_thread=False)
        sql = '''create table if not exists versions (
                    version_id integer primary key,
                    name text,
                    user text,
                    tstamp datetime default current_timestamp,
                    size integer default 0,
                    hide integer default 0)'''
        self.con.execute(sql)
        sql = '''create table if not exists metadata (
                    version_id integer, key text, value text, primary key (version_id, key))'''
        self.con.execute(sql)
        sql = '''create table if not exists blocks (
                    block_id text, data blob, primary key (block_id))'''
        self.con.execute(sql)
        sql = '''create table if not exists hashmaps (
                    version_id integer, pos integer, block_id text, primary key (version_id, pos))'''
        self.con.execute(sql)
        sql = '''create table if not exists permissions (
                    name text, read text, write text, primary key (name))'''
        self.con.execute(sql)
        self.con.commit()
    
    def delete_account(self, user, account):
        """Delete the account with the given name."""
        
        logger.debug("delete_account: %s", account)
        if user != account:
            raise NotAllowedError
        count, bytes, tstamp = self._get_pathstats(account)
        if count > 0:
            raise IndexError('Account is not empty')
        self._del_path(account) # Point of no return.
    
    def get_account_meta(self, user, account, until=None):
        """Return a dictionary with the account metadata."""
        
        logger.debug("get_account_meta: %s %s", account, until)
        if user != account:
            raise NotAllowedError
        try:
            version_id, mtime = self._get_accountinfo(account, until)
        except NameError:
            version_id = None
            mtime = 0
        count, bytes, tstamp = self._get_pathstats(account, until)
        if mtime > tstamp:
            tstamp = mtime
        if until is None:
            modified = tstamp
        else:
            modified = self._get_pathstats(account)[2] # Overall last modification
            if mtime > modified:
                modified = mtime
        
        # Proper count.
        sql = 'select count(name) from (%s) where name glob ? and not name glob ?'
        sql = sql % self._sql_until(until)
        c = self.con.execute(sql, (account + '/*', account + '/*/*'))
        row = c.fetchone()
        count = row[0]
        
        meta = self._get_metadata(account, version_id)
        meta.update({'name': account, 'count': count, 'bytes': bytes})
        if modified:
            meta.update({'modified': modified})
        if until is not None:
            meta.update({'until_timestamp': tstamp})
        return meta
    
    def update_account_meta(self, user, account, meta, replace=False):
        """Update the metadata associated with the account."""
        
        logger.debug("update_account_meta: %s %s %s", account, meta, replace)
        if user != account:
            raise NotAllowedError
        self._put_metadata(user, account, meta, replace)
    
    def list_containers(self, user, account, marker=None, limit=10000, until=None):
        """Return a list of containers existing under an account."""
        
        logger.debug("list_containers: %s %s %s %s", account, marker, limit, until)
        if user != account:
            raise NotAllowedError
        return self._list_objects(account, '', '/', marker, limit, False, [], until)
    
    def put_container(self, user, account, container):
        """Create a new container with the given name."""
        
        logger.debug("put_container: %s %s", account, container)
        if user != account:
            raise NotAllowedError
        try:
            path, version_id, mtime = self._get_containerinfo(account, container)
        except NameError:
            path = os.path.join(account, container)
            version_id = self._put_version(path, user)
        else:
            raise NameError('Container already exists')
    
    def delete_container(self, user, account, container):
        """Delete the container with the given name."""
        
        logger.debug("delete_container: %s %s", account, container)
        if user != account:
            raise NotAllowedError
        path, version_id, mtime = self._get_containerinfo(account, container)
        count, bytes, tstamp = self._get_pathstats(path)
        if count > 0:
            raise IndexError('Container is not empty')
        self._del_path(path) # Point of no return.
        self._copy_version(user, account, account, True, True) # New account version.
    
    def get_container_meta(self, user, account, container, until=None):
        """Return a dictionary with the container metadata."""
        
        logger.debug("get_container_meta: %s %s %s", account, container, until)
        if user != account:
            raise NotAllowedError
        path, version_id, mtime = self._get_containerinfo(account, container, until)
        count, bytes, tstamp = self._get_pathstats(path, until)
        if mtime > tstamp:
            tstamp = mtime
        if until is None:
            modified = tstamp
        else:
            modified = self._get_pathstats(path)[2] # Overall last modification
            if mtime > modified:
                modified = mtime
        
        meta = self._get_metadata(path, version_id)
        meta.update({'name': container, 'count': count, 'bytes': bytes, 'modified': modified})
        if until is not None:
            meta.update({'until_timestamp': tstamp})
        return meta
    
    def update_container_meta(self, user, account, container, meta, replace=False):
        """Update the metadata associated with the container."""
        
        logger.debug("update_container_meta: %s %s %s %s", account, container, meta, replace)
        if user != account:
            raise NotAllowedError
        path, version_id, mtime = self._get_containerinfo(account, container)
        self._put_metadata(user, path, meta, replace)
    
    def list_objects(self, user, account, container, prefix='', delimiter=None, marker=None, limit=10000, virtual=True, keys=[], until=None):
        """Return a list of objects existing under a container."""
        
        logger.debug("list_objects: %s %s %s %s %s %s %s", account, container, prefix, delimiter, marker, limit, until)
        if user != account:
            raise NotAllowedError
        path, version_id, mtime = self._get_containerinfo(account, container, until)
        return self._list_objects(path, prefix, delimiter, marker, limit, virtual, keys, until)
    
    def list_object_meta(self, user, account, container, until=None):
        """Return a list with all the container's object meta keys."""
        
        logger.debug("list_object_meta: %s %s %s", account, container, until)
        if user != account:
            raise NotAllowedError
        path, version_id, mtime = self._get_containerinfo(account, container, until)
        sql = '''select distinct m.key from (%s) o, metadata m
                    where m.version_id = o.version_id and o.name like ?'''
        sql = sql % self._sql_until(until)
        c = self.con.execute(sql, (path + '/%',))
        return [x[0] for x in c.fetchall()]
    
    def get_object_meta(self, user, account, container, name, version=None):
        """Return a dictionary with the object metadata."""
        
        logger.debug("get_object_meta: %s %s %s %s", account, container, name, version)
        self._can_read(user, account, container, name)
        path, version_id, muser, mtime, size = self._get_objectinfo(account, container, name, version)
        if version is None:
            modified = mtime
        else:
            modified = self._get_version(path, version)[2] # Overall last modification
        
        meta = self._get_metadata(path, version_id)
        meta.update({'name': name, 'bytes': size})
        meta.update({'version': version_id, 'version_timestamp': mtime})
        meta.update({'modified': modified, 'modified_by': muser})
        return meta
    
    def update_object_meta(self, user, account, container, name, meta, replace=False):
        """Update the metadata associated with the object."""
        
        logger.debug("update_object_meta: %s %s %s %s %s", account, container, name, meta, replace)
        self._can_write(user, account, container, name)
        path, version_id, muser, mtime, size = self._get_objectinfo(account, container, name)
        self._put_metadata(user, path, meta, replace)
    
    def get_object_permissions(self, user, account, container, name):
        """Return the path from which this object gets its permissions from,\
        along with a dictionary containing the permissions."""
        
        logger.debug("get_object_permissions: %s %s %s", account, container, name)
        self._can_read(user, account, container, name)
        path = self._get_objectinfo(account, container, name)[0]
        return self._get_permissions(path)
    
    def update_object_permissions(self, user, account, container, name, permissions):
        """Update the permissions associated with the object."""
        
        logger.debug("update_object_permissions: %s %s %s %s", account, container, name, permissions)
        if user != account:
            raise NotAllowedError
        path = self._get_objectinfo(account, container, name)[0]
        r, w = self._check_permissions(path, permissions)
        self._put_permissions(path, r, w)
    
    def get_object_hashmap(self, user, account, container, name, version=None):
        """Return the object's size and a list with partial hashes."""
        
        logger.debug("get_object_hashmap: %s %s %s %s", account, container, name, version)
        self._can_read(user, account, container, name)
        path, version_id, muser, mtime, size = self._get_objectinfo(account, container, name, version)
        sql = 'select block_id from hashmaps where version_id = ? order by pos asc'
        c = self.con.execute(sql, (version_id,))
        hashmap = [x[0] for x in c.fetchall()]
        return size, hashmap
    
    def update_object_hashmap(self, user, account, container, name, size, hashmap, meta={}, replace_meta=False, permissions=None):
        """Create/update an object with the specified size and partial hashes."""
        
        logger.debug("update_object_hashmap: %s %s %s %s %s", account, container, name, size, hashmap)
        if permissions is not None and user != account:
            raise NotAllowedError
        self._can_write(user, account, container, name)
        path = self._get_containerinfo(account, container)[0]
        path = os.path.join(path, name)
        if permissions is not None:
            r, w = self._check_permissions(path, permissions)
        src_version_id, dest_version_id = self._copy_version(user, path, path, not replace_meta, False)
        sql = 'update versions set size = ? where version_id = ?'
        self.con.execute(sql, (size, dest_version_id))
        # TODO: Check for block_id existence.
        for i in range(len(hashmap)):
            sql = 'insert or replace into hashmaps (version_id, pos, block_id) values (?, ?, ?)'
            self.con.execute(sql, (dest_version_id, i, hashmap[i]))
        for k, v in meta.iteritems():
            sql = 'insert or replace into metadata (version_id, key, value) values (?, ?, ?)'
            self.con.execute(sql, (dest_version_id, k, v))
        if permissions is not None:
            sql = 'insert or replace into permissions (name, read, write) values (?, ?, ?)'
            self.con.execute(sql, (path, r, w))
        self.con.commit()
    
    def copy_object(self, user, account, src_container, src_name, dest_container, dest_name, dest_meta={}, replace_meta=False, permissions=None, src_version=None):
        """Copy an object's data and metadata."""
        
        logger.debug("copy_object: %s %s %s %s %s %s %s %s %s", account, src_container, src_name, dest_container, dest_name, dest_meta, replace_meta, permissions, src_version)
        if permissions is not None and user != account:
            raise NotAllowedError
        self._can_read(user, account, src_container, src_name)
        self._can_write(user, account, dest_container, dest_name)
        self._get_containerinfo(account, src_container)
        if src_version is None:
            src_path = self._get_objectinfo(account, src_container, src_name)[0]
        else:
            src_path = os.path.join(account, src_container, src_name)
        dest_path = self._get_containerinfo(account, dest_container)[0]
        dest_path = os.path.join(dest_path, dest_name)
        if permissions is not None:
            r, w = self._check_permissions(dest_path, permissions)
        src_version_id, dest_version_id = self._copy_version(user, src_path, dest_path, not replace_meta, True, src_version)
        for k, v in dest_meta.iteritems():
            sql = 'insert or replace into metadata (version_id, key, value) values (?, ?, ?)'
            self.con.execute(sql, (dest_version_id, k, v))
        if permissions is not None:
            sql = 'insert or replace into permissions (name, read, write) values (?, ?, ?)'
            self.con.execute(sql, (dest_path, r, w))
        self.con.commit()
    
    def move_object(self, user, account, src_container, src_name, dest_container, dest_name, dest_meta={}, replace_meta=False, permissions=None):
        """Move an object's data and metadata."""
        
        logger.debug("move_object: %s %s %s %s %s %s %s %s", account, src_container, src_name, dest_container, dest_name, dest_meta, replace_meta, permissions)
        self.copy_object(user, account, src_container, src_name, dest_container, dest_name, dest_meta, replace_meta, permissions, None)
        self.delete_object(user, account, src_container, src_name)
    
    def delete_object(self, user, account, container, name):
        """Delete an object."""
        
        logger.debug("delete_object: %s %s %s", account, container, name)
        if user != account:
            raise NotAllowedError
        path = self._get_objectinfo(account, container, name)[0]
        self._put_version(path, user, 0, 1)
        sql = 'delete from permissions where name = ?'
        self.con.execute(sql, (path,))
        self.con.commit()
    
    def list_versions(self, user, account, container, name):
        """Return a list of all (version, version_timestamp) tuples for an object."""
        
        logger.debug("list_versions: %s %s %s", account, container, name)
        self._can_read(user, account, container, name)
        # This will even show deleted versions.
        path = os.path.join(account, container, name)
        sql = '''select distinct version_id, strftime('%s', tstamp) from versions where name = ? and hide = 0'''
        c = self.con.execute(sql, (path,))
        return [(int(x[0]), int(x[1])) for x in c.fetchall()]
    
    def get_block(self, hash):
        """Return a block's data."""
        
        logger.debug("get_block: %s", hash)
        c = self.con.execute('select data from blocks where block_id = ?', (hash,))
        row = c.fetchone()
        if row:
            return str(row[0])
        else:
            raise NameError('Block does not exist')
    
    def put_block(self, data):
        """Create a block and return the hash."""
        
        logger.debug("put_block: %s", len(data))
        h = hashlib.new(self.hash_algorithm)
        h.update(data.rstrip('\x00'))
        hash = h.hexdigest()
        sql = 'insert or ignore into blocks (block_id, data) values (?, ?)'
        self.con.execute(sql, (hash, buffer(data)))
        self.con.commit()
        return hash
    
    def update_block(self, hash, data, offset=0):
        """Update a known block and return the hash."""
        
        logger.debug("update_block: %s %s %s", hash, len(data), offset)
        if offset == 0 and len(data) == self.block_size:
            return self.put_block(data)
        src_data = self.get_block(hash)
        bs = self.block_size
        if offset < 0 or offset > bs or offset + len(data) > bs:
            raise IndexError('Offset or data outside block limits')
        dest_data = src_data[:offset] + data + src_data[offset + len(data):]
        return self.put_block(dest_data)
    
    def _sql_until(self, until=None):
        """Return the sql to get the latest versions until the timestamp given."""
        if until is None:
            until = int(time.time())
        sql = '''select version_id, name, strftime('%s', tstamp) as tstamp, size from versions v
                    where version_id = (select max(version_id) from versions
                                        where v.name = name and tstamp <= datetime(%s, 'unixepoch'))
                    and hide = 0'''
        return sql % ('%s', until)
    
    def _get_pathstats(self, path, until=None):
        """Return count and sum of size of everything under path and latest timestamp."""
        
        sql = 'select count(version_id), total(size), max(tstamp) from (%s) where name like ?'
        sql = sql % self._sql_until(until)
        c = self.con.execute(sql, (path + '/%',))
        row = c.fetchone()
        tstamp = row[2] if row[2] is not None else 0
        return int(row[0]), int(row[1]), int(tstamp)
    
    def _get_version(self, path, version=None):
        if version is None:
            sql = '''select version_id, user, strftime('%s', tstamp), size, hide from versions where name = ?
                        order by version_id desc limit 1'''
            c = self.con.execute(sql, (path,))
            row = c.fetchone()
            if not row or int(row[4]):
                raise NameError('Object does not exist')
        else:
            # The database (sqlite) will not complain if the version is not an integer.
            sql = '''select version_id, user, strftime('%s', tstamp), size from versions where name = ?
                        and version_id = ?'''
            c = self.con.execute(sql, (path, version))
            row = c.fetchone()
            if not row:
                raise IndexError('Version does not exist')
        return str(row[0]), str(row[1]), int(row[2]), int(row[3])
    
    def _put_version(self, path, user, size=0, hide=0):
        sql = 'insert into versions (name, user, size, hide) values (?, ?, ?, ?)'
        id = self.con.execute(sql, (path, user, size, hide)).lastrowid
        self.con.commit()
        return str(id)
    
    def _copy_version(self, user, src_path, dest_path, copy_meta=True, copy_data=True, src_version=None):
        if src_version is not None:
            src_version_id, muser, mtime, size = self._get_version(src_path, src_version)
        else:
            # Latest or create from scratch.
            try:
                src_version_id, muser, mtime, size = self._get_version(src_path)
            except NameError:
                src_version_id = None
                size = 0
        if not copy_data:
            size = 0
        dest_version_id = self._put_version(dest_path, user, size)
        if copy_meta and src_version_id is not None:
            sql = 'insert into metadata select %s, key, value from metadata where version_id = ?'
            sql = sql % dest_version_id
            self.con.execute(sql, (src_version_id,))
        if copy_data and src_version_id is not None:
            sql = 'insert into hashmaps select %s, pos, block_id from hashmaps where version_id = ?'
            sql = sql % dest_version_id
            self.con.execute(sql, (src_version_id,))
        self.con.commit()
        return src_version_id, dest_version_id
    
    def _get_versioninfo(self, account, container, name, until=None):
        """Return path, latest version, associated timestamp and size until the timestamp given."""
        
        p = (account, container, name)
        try:
            p = p[:p.index(None)]
        except ValueError:
            pass
        path = os.path.join(*p)
        sql = '''select version_id, tstamp, size from (%s) where name = ?'''
        sql = sql % self._sql_until(until)
        c = self.con.execute(sql, (path,))
        row = c.fetchone()
        if row is None:
            raise NameError('Path does not exist')
        return path, str(row[0]), int(row[1]), int(row[2])
    
    def _get_accountinfo(self, account, until=None):
        try:
            path, version_id, mtime, size = self._get_versioninfo(account, None, None, until)
            return version_id, mtime
        except:
            raise NameError('Account does not exist')
    
    def _get_containerinfo(self, account, container, until=None):
        try:
            path, version_id, mtime, size = self._get_versioninfo(account, container, None, until)
            return path, version_id, mtime
        except:
            raise NameError('Container does not exist')
    
    def _get_objectinfo(self, account, container, name, version=None):
        path = os.path.join(account, container, name)
        version_id, muser, mtime, size = self._get_version(path, version)
        return path, version_id, muser, mtime, size
    
    def _get_metadata(self, path, version):
        sql = 'select key, value from metadata where version_id = ?'
        c = self.con.execute(sql, (version,))
        return dict(c.fetchall())
    
    def _put_metadata(self, user, path, meta, replace=False):
        """Create a new version and store metadata."""
        
        src_version_id, dest_version_id = self._copy_version(user, path, path, not replace, True)
        for k, v in meta.iteritems():
            if not replace and v == '':
                sql = 'delete from metadata where version_id = ? and key = ?'
                self.con.execute(sql, (dest_version_id, k))
            else:
                sql = 'insert or replace into metadata (version_id, key, value) values (?, ?, ?)'
                self.con.execute(sql, (dest_version_id, k, v))
        self.con.commit()
    
    def _is_allowed(self, user, account, container, name, op='read'):
        if user == account:
            return True
        path = os.path.join(account, container, name)
        perm_path, perms = self._get_permissions(path)
        if op == 'read' and user in perms.get('read', []):
            return True
        if user in perms.get('write', []):
            return True
        return False
    
    def _can_read(self, user, account, container, name):
        if not self._is_allowed(user, account, container, name, 'read'):
            raise NotAllowedError
    
    def _can_write(self, user, account, container, name):
        if not self._is_allowed(user, account, container, name, 'write'):
            raise NotAllowedError
    
    def _check_permissions(self, path, permissions):
        # Check for existing permissions.
        sql = '''select name from permissions
                    where name != ? and (name like ? or ? like name || ?)'''
        c = self.con.execute(sql, (path, path + '%', path, '%'))
        rows = c.fetchall()
        if rows:
            raise AttributeError('Permissions already set')
        
        # Format given permissions.
        if len(permissions) == 0:
            return '', ''
        r = permissions.get('read', [])
        w = permissions.get('write', [])
        if True in [False or ',' in x for x in r]:
            raise ValueError('Bad characters in read permissions')
        if True in [False or ',' in x for x in w]:
            raise ValueError('Bad characters in write permissions')
        return ','.join(r), ','.join(w)
    
    def _get_permissions(self, path):
        # Check for permissions at path or above.
        sql = 'select name, read, write from permissions where ? like name || ?'
        c = self.con.execute(sql, (path, '%'))
        row = c.fetchone()
        if not row:
            return path, {}
        
        name, r, w = row
        ret = {}
        if w != '':
            ret['write'] = w.split(',')
        if r != '':
            ret['read'] = r.split(',')
        return name, ret
    
    def _put_permissions(self, path, r, w):
        if r == '' and w == '':
            sql = 'delete from permissions where name = ?'
            self.con.execute(sql, (path,))
        else:
            sql = 'insert or replace into permissions (name, read, write) values (?, ?, ?)'
            self.con.execute(sql, (path, r, w))
        self.con.commit()
    
    def _list_objects(self, path, prefix='', delimiter=None, marker=None, limit=10000, virtual=True, keys=[], until=None):
        cont_prefix = path + '/'
        if keys and len(keys) > 0:
            sql = '''select distinct o.name, o.version_id from (%s) o, metadata m where o.name like ? and
                        m.version_id = o.version_id and m.key in (%s) order by o.name'''
            sql = sql % (self._sql_until(until), ', '.join('?' * len(keys)))
            param = (cont_prefix + prefix + '%',) + tuple(keys)
        else:
            sql = 'select name, version_id from (%s) where name like ? order by name'
            sql = sql % self._sql_until(until)
            param = (cont_prefix + prefix + '%',)
        c = self.con.execute(sql, param)
        objects = [(x[0][len(cont_prefix):], x[1]) for x in c.fetchall()]
        if delimiter:
            pseudo_objects = []
            for x in objects:
                pseudo_name = x[0]
                i = pseudo_name.find(delimiter, len(prefix))
                if not virtual:
                    # If the delimiter is not found, or the name ends
                    # with the delimiter's first occurence.
                    if i == -1 or len(pseudo_name) == i + len(delimiter):
                        pseudo_objects.append(x)
                else:
                    # If the delimiter is found, keep up to (and including) the delimiter.
                    if i != -1:
                        pseudo_name = pseudo_name[:i + len(delimiter)]
                    if pseudo_name not in [y[0] for y in pseudo_objects]:
                        if pseudo_name == x[0]:
                            pseudo_objects.append(x)
                        else:
                            pseudo_objects.append((pseudo_name, None))
            objects = pseudo_objects
        
        start = 0
        if marker:
            try:
                start = [x[0] for x in objects].index(marker) + 1
            except ValueError:
                pass
        if not limit or limit > 10000:
            limit = 10000
        return objects[start:start + limit]
    
    def _del_path(self, path):
        sql = '''delete from hashmaps where version_id in
                    (select version_id from versions where name = ?)'''
        self.con.execute(sql, (path,))
        sql = '''delete from metadata where version_id in
                    (select version_id from versions where name = ?)'''
        self.con.execute(sql, (path,))
        sql = '''delete from versions where name = ?'''
        self.con.execute(sql, (path,))
        sql = '''delete from permissions where name like ?'''
        self.con.execute(sql, (path + '%',)) # Redundant.
        self.con.commit()
