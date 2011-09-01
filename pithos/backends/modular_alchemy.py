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
import hashlib
import binascii

from base import NotAllowedError, BaseBackend
from lib_alchemy.node import Node, ROOTNODE, SERIAL, SIZE, MTIME, MUSER, CLUSTER
from lib_alchemy.permissions import Permissions, READ, WRITE
from lib_alchemy.policy import Policy
from sqlalchemy import create_engine
from lib.hashfiler import Mapper, Blocker

( CLUSTER_NORMAL, CLUSTER_HISTORY, CLUSTER_DELETED ) = range(3)

inf = float('inf')


logger = logging.getLogger(__name__)

def backend_method(func=None, autocommit=1):
    if func is None:
        def fn(func):
            return backend_method(func, autocommit)
        return fn

    if not autocommit:
        return func
    def fn(self, *args, **kw):
        trans = self.con.begin()
        try:
            ret = func(self, *args, **kw)
            trans.commit()
            return ret
        except:
            trans.rollback()
            raise
    return fn


class ModularBackend(BaseBackend):
    """A modular backend.
    
    Uses modules for SQL functions and storage.
    """
    
    def __init__(self, db, db_options):
        self.hash_algorithm = 'sha256'
        self.block_size = 4 * 1024 * 1024 # 4MB
        
        self.default_policy = {'quota': 0, 'versioning': 'auto'}
        
        basepath = os.path.split(db)[0]
        if basepath and not os.path.exists(basepath):
            os.makedirs(basepath)
        if not os.path.isdir(basepath):
            raise RuntimeError("Cannot open database at '%s'" % (db,))
        
        connection_str = 'postgresql://%s:%s@%s/%s' % db_options
        engine = create_engine(connection_str, echo=True)
        self.con = engine.connect()
        
        params = {'blocksize': self.block_size,
                  'blockpath': basepath + '/blocks',
                  'hashtype': self.hash_algorithm}
        self.blocker = Blocker(**params)
        
        params = {'mappath': basepath + '/maps',
                  'namelen': self.blocker.hashlen}
        self.mapper = Mapper(**params)
        
        params = {'connection': self.con,
                  'engine': engine}
        self.permissions = Permissions(**params)
        self.policy = Policy(**params)
        self.node = Node(**params)
    
    @backend_method
    def list_accounts(self, user, marker=None, limit=10000):
        """Return a list of accounts the user can access."""
        
        logger.debug("list_accounts: %s %s %s", user, marker, limit)
        allowed = self._allowed_accounts(user)
        start, limit = self._list_limits(allowed, marker, limit)
        return allowed[start:start + limit]
    
    @backend_method
    def get_account_meta(self, user, account, until=None):
        """Return a dictionary with the account metadata."""
        
        logger.debug("get_account_meta: %s %s", account, until)
        path, node = self._lookup_account(account, user == account)
        if user != account:
            if until or node is None or account not in self._allowed_accounts(user):
                raise NotAllowedError
        try:
            props = self._get_properties(node, until)
            mtime = props[MTIME]
        except NameError:
            props = None
            mtime = until
        count, bytes, tstamp = self._get_statistics(node, until)
        tstamp = max(tstamp, mtime)
        if until is None:
            modified = tstamp
        else:
            modified = self._get_statistics(node)[2] # Overall last modification.
            modified = max(modified, mtime)
        
        if user != account:
            meta = {'name': account}
        else:
            meta = {}
            if props is not None:
                meta.update(dict(self.node.attribute_get(props[SERIAL])))
            if until is not None:
                meta.update({'until_timestamp': tstamp})
            meta.update({'name': account, 'count': count, 'bytes': bytes})
        meta.update({'modified': modified})
        return meta
    
    @backend_method
    def update_account_meta(self, user, account, meta, replace=False):
        """Update the metadata associated with the account."""
        
        logger.debug("update_account_meta: %s %s %s", account, meta, replace)
        if user != account:
            raise NotAllowedError
        path, node = self._lookup_account(account, True)
        self._put_metadata(user, node, meta, replace, False)
    
    @backend_method
    def get_account_groups(self, user, account):
        """Return a dictionary with the user groups defined for this account."""
        
        logger.debug("get_account_groups: %s", account)
        if user != account:
            if account not in self._allowed_accounts(user):
                raise NotAllowedError
            return {}
        self._lookup_account(account, True)
        return self.permissions.group_dict(account)
    
    @backend_method
    def update_account_groups(self, user, account, groups, replace=False):
        """Update the groups associated with the account."""
        
        logger.debug("update_account_groups: %s %s %s", account, groups, replace)
        if user != account:
            raise NotAllowedError
        self._lookup_account(account, True)
        self._check_groups(groups)
        if replace:
            self.permissions.group_destroy(account)
        for k, v in groups.iteritems():
            if not replace: # If not already deleted.
                self.permissions.group_delete(account, k)
            if v:
                self.permissions.group_addmany(account, k, v)
    
    @backend_method
    def put_account(self, user, account):
        """Create a new account with the given name."""
        
        logger.debug("put_account: %s", account)
        if user != account:
            raise NotAllowedError
        node = self.node.node_lookup(account)
        if node is not None:
            raise NameError('Account already exists')
        self._put_path(user, ROOTNODE, account)
    
    @backend_method
    def delete_account(self, user, account):
        """Delete the account with the given name."""
        
        logger.debug("delete_account: %s", account)
        if user != account:
            raise NotAllowedError
        node = self.node.node_lookup(account)
        if node is None:
            return
        if not self.node.node_remove(node):
            raise IndexError('Account is not empty')
        self.permissions.group_destroy(account)
    
    @backend_method
    def list_containers(self, user, account, marker=None, limit=10000, shared=False, until=None):
        """Return a list of containers existing under an account."""
        
        logger.debug("list_containers: %s %s %s %s %s", account, marker, limit, shared, until)
        if user != account:
            if until or account not in self._allowed_accounts(user):
                raise NotAllowedError
            allowed = self._allowed_containers(user, account)
            start, limit = self._list_limits(allowed, marker, limit)
            return allowed[start:start + limit]
        if shared:
            allowed = [x.split('/', 2)[1] for x in self.permissions.access_list_shared(account)]
            start, limit = self._list_limits(allowed, marker, limit)
            return allowed[start:start + limit]
        node = self.node.node_lookup(account)
        return [x[0] for x in self._list_objects(node, account, '', '/', marker, limit, False, [], until)]
    
    @backend_method
    def get_container_meta(self, user, account, container, until=None):
        """Return a dictionary with the container metadata."""
        
        logger.debug("get_container_meta: %s %s %s", account, container, until)
        if user != account:
            if until or container not in self._allowed_containers(user, account):
                raise NotAllowedError
        path, node = self._lookup_container(account, container)
        props = self._get_properties(node, until)
        mtime = props[MTIME]
        count, bytes, tstamp = self._get_statistics(node, until)
        tstamp = max(tstamp, mtime)
        if until is None:
            modified = tstamp
        else:
            modified = self._get_statistics(node)[2] # Overall last modification.
            modified = max(modified, mtime)
        
        if user != account:
            meta = {'name': container}
        else:
            meta = dict(self.node.attribute_get(props[SERIAL]))
            if until is not None:
                meta.update({'until_timestamp': tstamp})
            meta.update({'name': container, 'count': count, 'bytes': bytes})
        meta.update({'modified': modified})
        return meta
    
    @backend_method
    def update_container_meta(self, user, account, container, meta, replace=False):
        """Update the metadata associated with the container."""
        
        logger.debug("update_container_meta: %s %s %s %s", account, container, meta, replace)
        if user != account:
            raise NotAllowedError
        path, node = self._lookup_container(account, container)
        self._put_metadata(user, node, meta, replace, False)
    
    @backend_method
    def get_container_policy(self, user, account, container):
        """Return a dictionary with the container policy."""
        
        logger.debug("get_container_policy: %s %s", account, container)
        if user != account:
            if container not in self._allowed_containers(user, account):
                raise NotAllowedError
            return {}
        path = self._lookup_container(account, container)[0]
        return self.policy.policy_get(path)
    
    @backend_method
    def update_container_policy(self, user, account, container, policy, replace=False):
        """Update the policy associated with the account."""
        
        logger.debug("update_container_policy: %s %s %s %s", account, container, policy, replace)
        if user != account:
            raise NotAllowedError
        path = self._lookup_container(account, container)[0]
        self._check_policy(policy)
        if replace:
            for k, v in self.default_policy.iteritems():
                if k not in policy:
                    policy[k] = v
        self.policy.policy_set(path, policy)
    
    @backend_method
    def put_container(self, user, account, container, policy=None):
        """Create a new container with the given name."""
        
        logger.debug("put_container: %s %s %s", account, container, policy)
        if user != account:
            raise NotAllowedError
        try:
            path, node = self._lookup_container(account, container)
        except NameError:
            pass
        else:
            raise NameError('Container already exists')
        if policy:
            self._check_policy(policy)
        path = '/'.join((account, container))
        self._put_path(user, self._lookup_account(account, True)[1], path)
        for k, v in self.default_policy.iteritems():
            if k not in policy:
                policy[k] = v
        self.policy.policy_set(path, policy)
    
    @backend_method
    def delete_container(self, user, account, container, until=None):
        """Delete/purge the container with the given name."""
        
        logger.debug("delete_container: %s %s %s", account, container, until)
        if user != account:
            raise NotAllowedError
        path, node = self._lookup_container(account, container)
        
        if until is not None:
            versions = self.node.node_purge_children(node, until, CLUSTER_HISTORY)
            for v in versions:
                self.mapper.map_remv(v)
            self.node.node_purge_children(node, until, CLUSTER_DELETED)
            return
        
        if self._get_statistics(node)[0] > 0:
            raise IndexError('Container is not empty')
        versions = self.node.node_purge_children(node, inf, CLUSTER_HISTORY)
        for v in versions:
            self.mapper.map_remv(v)
        self.node.node_purge_children(node, inf, CLUSTER_DELETED)
        self.node.node_remove(node)
        self.policy.policy_unset(path)
    
    @backend_method
    def list_objects(self, user, account, container, prefix='', delimiter=None, marker=None, limit=10000, virtual=True, keys=[], shared=False, until=None):
        """Return a list of objects existing under a container."""
        
        logger.debug("list_objects: %s %s %s %s %s %s %s %s %s %s", account, container, prefix, delimiter, marker, limit, virtual, keys, shared, until)
        allowed = []
        if user != account:
            if until:
                raise NotAllowedError
            allowed = self.permissions.access_list_paths(user, '/'.join((account, container)))
            if not allowed:
                raise NotAllowedError
        else:
            if shared:
                allowed = self.permissions.access_list_shared('/'.join((account, container)))
                if not allowed:
                    return []
        path, node = self._lookup_container(account, container)
        return self._list_objects(node, path, prefix, delimiter, marker, limit, virtual, keys, until, allowed)
    
    @backend_method
    def list_object_meta(self, user, account, container, until=None):
        """Return a list with all the container's object meta keys."""
        
        logger.debug("list_object_meta: %s %s %s", account, container, until)
        allowed = []
        if user != account:
            if until:
                raise NotAllowedError
            allowed = self.permissions.access_list_paths(user, '/'.join((account, container)))
            if not allowed:
                raise NotAllowedError
        path, node = self._lookup_container(account, container)
        before = until if until is not None else inf
        return self.node.latest_attribute_keys(node, before, CLUSTER_DELETED, allowed)
    
    @backend_method
    def get_object_meta(self, user, account, container, name, version=None):
        """Return a dictionary with the object metadata."""
        
        logger.debug("get_object_meta: %s %s %s %s", account, container, name, version)
        self._can_read(user, account, container, name)
        path, node = self._lookup_object(account, container, name)
        props = self._get_version(node, version)
        if version is None:
            modified = props[MTIME]
        else:
            modified = self._get_version(node)[MTIME] # Overall last modification.
        
        meta = dict(self.node.attribute_get(props[SERIAL]))
        meta.update({'name': name, 'bytes': props[SIZE]})
        meta.update({'version': props[SERIAL], 'version_timestamp': props[MTIME]})
        meta.update({'modified': modified, 'modified_by': props[MUSER]})
        return meta
    
    @backend_method
    def update_object_meta(self, user, account, container, name, meta, replace=False):
        """Update the metadata associated with the object."""
        
        logger.debug("update_object_meta: %s %s %s %s %s", account, container, name, meta, replace)
        self._can_write(user, account, container, name)
        path, node = self._lookup_object(account, container, name)
        self._put_metadata(user, node, meta, replace)
    
    @backend_method
    def get_object_permissions(self, user, account, container, name):
        """Return the path from which this object gets its permissions from,\
        along with a dictionary containing the permissions."""
        
        logger.debug("get_object_permissions: %s %s %s", account, container, name)
        self._can_read(user, account, container, name)
        path = self._lookup_object(account, container, name)[0]
        return self.permissions.access_inherit(path)
    
    @backend_method
    def update_object_permissions(self, user, account, container, name, permissions):
        """Update the permissions associated with the object."""
        
        logger.debug("update_object_permissions: %s %s %s %s", account, container, name, permissions)
        if user != account:
            raise NotAllowedError
        path = self._lookup_object(account, container, name)[0]
        self._check_permissions(path, permissions)
        self.permissions.access_set(path, permissions)
    
    @backend_method
    def get_object_public(self, user, account, container, name):
        """Return the public URL of the object if applicable."""
        
        logger.debug("get_object_public: %s %s %s", account, container, name)
        self._can_read(user, account, container, name)
        path = self._lookup_object(account, container, name)[0]
        if self.permissions.public_check(path):
            return '/public/' + path
        return None
    
    @backend_method
    def update_object_public(self, user, account, container, name, public):
        """Update the public status of the object."""
        
        logger.debug("update_object_public: %s %s %s %s", account, container, name, public)
        self._can_write(user, account, container, name)
        path = self._lookup_object(account, container, name)[0]
        if not public:
            self.permissions.public_unset(path)
        else:
            self.permissions.public_set(path)
    
    @backend_method
    def get_object_hashmap(self, user, account, container, name, version=None):
        """Return the object's size and a list with partial hashes."""
        
        logger.debug("get_object_hashmap: %s %s %s %s", account, container, name, version)
        self._can_read(user, account, container, name)
        path, node = self._lookup_object(account, container, name)
        props = self._get_version(node, version)
        hashmap = self.mapper.map_retr(props[SERIAL])
        return props[SIZE], [binascii.hexlify(x) for x in hashmap]
    
    @backend_method
    def update_object_hashmap(self, user, account, container, name, size, hashmap, meta={}, replace_meta=False, permissions=None):
        """Create/update an object with the specified size and partial hashes."""
        
        logger.debug("update_object_hashmap: %s %s %s %s %s", account, container, name, size, hashmap)
        if permissions is not None and user != account:
            raise NotAllowedError
        self._can_write(user, account, container, name)
        missing = self.blocker.block_ping([binascii.unhexlify(x) for x in hashmap])
        if missing:
            ie = IndexError()
            ie.data = missing
            raise ie
        if permissions is not None:
            self._check_permissions(path, permissions)
        path, node = self._put_object_node(account, container, name)
        src_version_id, dest_version_id = self._copy_version(user, node, None, node, size)
        self.mapper.map_stor(dest_version_id, [binascii.unhexlify(x) for x in hashmap])
        if not replace_meta and src_version_id is not None:
            self.node.attribute_copy(src_version_id, dest_version_id)
        self.node.attribute_set(dest_version_id, ((k, v) for k, v in meta.iteritems()))
        if permissions is not None:
            self.permissions.access_set(path, permissions)
    
    @backend_method
    def copy_object(self, user, account, src_container, src_name, dest_container, dest_name, dest_meta={}, replace_meta=False, permissions=None, src_version=None):
        """Copy an object's data and metadata."""
        
        logger.debug("copy_object: %s %s %s %s %s %s %s %s %s", account, src_container, src_name, dest_container, dest_name, dest_meta, replace_meta, permissions, src_version)
        if permissions is not None and user != account:
            raise NotAllowedError
        self._can_read(user, account, src_container, src_name)
        self._can_write(user, account, dest_container, dest_name)
        src_path, src_node = self._lookup_object(account, src_container, src_name)
        if permissions is not None:
            self._check_permissions(dest_path, permissions)
        dest_path, dest_node = self._put_object_node(account, dest_container, dest_name)
        src_version_id, dest_version_id = self._copy_version(user, src_node, src_version, dest_node)
        if src_version_id is not None:
            self._copy_data(src_version_id, dest_version_id)
        if not replace_meta and src_version_id is not None:
            self.node.attribute_copy(src_version_id, dest_version_id)
        self.node.attribute_set(dest_version_id, ((k, v) for k, v in dest_meta.iteritems()))
        if permissions is not None:
            self.permissions.access_set(dest_path, permissions)
    
    @backend_method
    def move_object(self, user, account, src_container, src_name, dest_container, dest_name, dest_meta={}, replace_meta=False, permissions=None):
        """Move an object's data and metadata."""
        
        logger.debug("move_object: %s %s %s %s %s %s %s %s", account, src_container, src_name, dest_container, dest_name, dest_meta, replace_meta, permissions)
        self.copy_object(user, account, src_container, src_name, dest_container, dest_name, dest_meta, replace_meta, permissions, None)
        self.delete_object(user, account, src_container, src_name)
    
    @backend_method
    def delete_object(self, user, account, container, name, until=None):
        """Delete/purge an object."""
        
        logger.debug("delete_object: %s %s %s %s", account, container, name, until)
        if user != account:
            raise NotAllowedError
        
        if until is not None:
            path = '/'.join((account, container, name))
            node = self.node.node_lookup(path)
            if node is None:
                return
            versions = self.node.node_purge(node, until, CLUSTER_NORMAL)
            versions += self.node.node_purge(node, until, CLUSTER_HISTORY)
            for v in versions:
                self.mapper.map_remv(v)
            self.node.node_purge_children(node, until, CLUSTER_DELETED)
            try:
                props = self._get_version(node)
            except NameError:
                pass
            else:
                self.permissions.access_clear(path)
            return
        
        path, node = self._lookup_object(account, container, name)
        self._copy_version(user, node, None, node, 0, CLUSTER_DELETED)
        self.permissions.access_clear(path)
    
    @backend_method
    def list_versions(self, user, account, container, name):
        """Return a list of all (version, version_timestamp) tuples for an object."""
        
        logger.debug("list_versions: %s %s %s", account, container, name)
        self._can_read(user, account, container, name)
        path, node = self._lookup_object(account, container, name)
        return self.node.node_get_versions(node, ['serial', 'mtime'])
    
    @backend_method(autocommit=0)
    def get_block(self, hash):
        """Return a block's data."""
        
        logger.debug("get_block: %s", hash)
        blocks = self.blocker.block_retr((binascii.unhexlify(hash),))
        if not blocks:
            raise NameError('Block does not exist')
        return blocks[0]
    
    @backend_method(autocommit=0)
    def put_block(self, data):
        """Store a block and return the hash."""
        
        logger.debug("put_block: %s", len(data))
        hashes, absent = self.blocker.block_stor((data,))
        return binascii.hexlify(hashes[0])
    
    @backend_method(autocommit=0)
    def update_block(self, hash, data, offset=0):
        """Update a known block and return the hash."""
        
        logger.debug("update_block: %s %s %s", hash, len(data), offset)
        if offset == 0 and len(data) == self.block_size:
            return self.put_block(data)
        h, e = self.blocker.block_delta(binascii.unhexlify(hash), ((offset, data),))
        return binascii.hexlify(h)
    
    # Path functions.
    
    def _put_object_node(self, account, container, name):
        path, parent = self._lookup_container(account, container)
        path = '/'.join((path, name))
        node = self.node.node_lookup(path)
        if node is None:
            node = self.node.node_create(parent, path)
        return path, node
    
    def _put_path(self, user, parent, path):
        node = self.node.node_create(parent, path)
        self.node.version_create(node, 0, None, user, CLUSTER_NORMAL)
        return node
    
    def _lookup_account(self, account, create=True):
        node = self.node.node_lookup(account)
        if node is None and create:
            node = self._put_path(account, ROOTNODE, account) # User is account.
        return account, node
    
    def _lookup_container(self, account, container):
        path = '/'.join((account, container))
        node = self.node.node_lookup(path)
        if node is None:
            raise NameError('Container does not exist')
        return path, node
    
    def _lookup_object(self, account, container, name):
        path = '/'.join((account, container, name))
        node = self.node.node_lookup(path)
        if node is None:
            raise NameError('Object does not exist')
        return path, node
    
    def _get_properties(self, node, until=None):
        """Return properties until the timestamp given."""
        
        before = until if until is not None else inf
        props = self.node.version_lookup(node, before, CLUSTER_NORMAL)
        if props is None and until is not None:
            props = self.node.version_lookup(node, before, CLUSTER_HISTORY)
        if props is None:
            raise NameError('Path does not exist')
        return props
    
    def _get_statistics(self, node, until=None):
        """Return count, sum of size and latest timestamp of everything under node."""
        
        if until is None:
            stats = self.node.statistics_get(node, CLUSTER_NORMAL)
        else:
            stats = self.node.statistics_latest(node, until, CLUSTER_DELETED)
        if stats is None:
            stats = (0, 0, 0)
        return stats
    
    def _get_version(self, node, version=None):
        if version is None:
            props = self.node.version_lookup(node, inf, CLUSTER_NORMAL)
            if props is None:
                raise NameError('Object does not exist')
        else:
            props = self.node.version_get_properties(version)
            if props is None or props[CLUSTER] == CLUSTER_DELETED:
                raise IndexError('Version does not exist')
        return props
    
    def _copy_version(self, user, src_node, src_version, dest_node, dest_size=None, dest_cluster=CLUSTER_NORMAL):
        
        # Get source serial and size.
        if src_version is not None:
            src_props = self._get_version(src_node, src_version)
            src_version_id = src_props[SERIAL]
            size = src_props[SIZE]
        else:
            # Latest or create from scratch.
            try:
                src_props = self._get_version(src_node)
                src_version_id = src_props[SERIAL]
                size = src_props[SIZE]
            except NameError:
                src_version_id = None
                size = 0
        if dest_size is not None:
            size = dest_size
        
        # Move the latest version at destination to CLUSTER_HISTORY and create new.
        if src_node == dest_node and src_version is None and src_version_id is not None:
            self.node.version_recluster(src_version_id, CLUSTER_HISTORY)
        else:
            dest_props = self.node.version_lookup(dest_node, inf, CLUSTER_NORMAL)
            if dest_props is not None:
                self.node.version_recluster(dest_props[SERIAL], CLUSTER_HISTORY)
        dest_version_id, mtime = self.node.version_create(dest_node, size, src_version_id, user, dest_cluster)
        
        return src_version_id, dest_version_id
    
    def _copy_data(self, src_version, dest_version):
        hashmap = self.mapper.map_retr(src_version)
        self.mapper.map_stor(dest_version, hashmap)
    
    def _get_metadata(self, version):
        if version is None:
            return {}
        return dict(self.node.attribute_get(version))
    
    def _put_metadata(self, user, node, meta, replace=False, copy_data=True):
        """Create a new version and store metadata."""
        
        src_version_id, dest_version_id = self._copy_version(user, node, None, node)
        if not replace:
            if src_version_id is not None:
                self.node.attribute_copy(src_version_id, dest_version_id)
            self.node.attribute_del(dest_version_id, (k for k, v in meta.iteritems() if v == ''))
            self.node.attribute_set(dest_version_id, ((k, v) for k, v in meta.iteritems() if v != ''))
        else:
            self.node.attribute_set(dest_version_id, ((k, v) for k, v in meta.iteritems()))
        if copy_data and src_version_id is not None:
            self._copy_data(src_version_id, dest_version_id)
    
    def _list_limits(self, listing, marker, limit):
        start = 0
        if marker:
            try:
                start = listing.index(marker) + 1
            except ValueError:
                pass
        if not limit or limit > 10000:
            limit = 10000
        return start, limit
    
    def _list_objects(self, parent, path, prefix='', delimiter=None, marker=None, limit=10000, virtual=True, keys=[], until=None, allowed=[]):
        cont_prefix = path + '/'
        prefix = cont_prefix + prefix
        start = cont_prefix + marker if marker else None
        before = until if until is not None else inf
        filterq = ','.join(keys) if keys else None
        
        objects, prefixes = self.node.latest_version_list(parent, prefix, delimiter, start, limit, before, CLUSTER_DELETED, allowed, filterq)
        objects.extend([(p, None) for p in prefixes] if virtual else [])
        objects.sort()
        objects = [(x[0][len(cont_prefix):], x[1]) for x in objects]
        
        start, limit = self._list_limits([x[0] for x in objects], marker, limit)
        return objects[start:start + limit]
    
    # Policy functions.
    
    def _check_policy(self, policy):
        for k in policy.keys():
            if policy[k] == '':
                policy[k] = self.default_policy.get(k)
        for k, v in policy.iteritems():
            if k == 'quota':
                q = int(v) # May raise ValueError.
                if q < 0:
                    raise ValueError
            elif k == 'versioning':
                if v not in ['auto', 'manual', 'none']:
                    raise ValueError
            else:
                raise ValueError
    
    # Access control functions.
    
    def _check_groups(self, groups):
        # raise ValueError('Bad characters in groups')
        pass
    
    def _check_permissions(self, path, permissions):
        # raise ValueError('Bad characters in permissions')
        
        # Check for existing permissions.
        paths = self.permissions.access_list(path)
        if paths:
            ae = AttributeError()
            ae.data = paths
            raise ae
    
    def _can_read(self, user, account, container, name):
        if user == account:
            return True
        path = '/'.join((account, container, name))
        if not self.permissions.access_check(path, READ, user) and not self.permissions.access_check(path, WRITE, user):
            raise NotAllowedError
    
    def _can_write(self, user, account, container, name):
        if user == account:
            return True
        path = '/'.join((account, container, name))
        if not self.permissions.access_check(path, WRITE, user):
            raise NotAllowedError
    
    def _allowed_accounts(self, user):
        allow = set()
        for path in self.permissions.access_list_paths(user):
            allow.add(path.split('/', 1)[0])
        return sorted(allow)
    
    def _allowed_containers(self, user, account):
        allow = set()
        for path in self.permissions.access_list_paths(user, account):
            allow.add(path.split('/', 2)[1])
        return sorted(allow)
