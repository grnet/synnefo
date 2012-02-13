# Copyright 2011-2012 GRNET S.A. All rights reserved.
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

import sys
import os
import time
import uuid as uuidlib
import logging
import binascii

from base import DEFAULT_QUOTA, DEFAULT_VERSIONING, NotAllowedError, QuotaError, BaseBackend

from pithos.lib.hashmap import HashMap

# Default modules and settings.
DEFAULT_DB_MODULE = 'pithos.backends.lib.sqlalchemy'
DEFAULT_DB_CONNECTION = 'sqlite:///backend.db'
DEFAULT_BLOCK_MODULE = 'pithos.backends.lib.hashfiler'
DEFAULT_BLOCK_PATH = 'data/'
#DEFAULT_QUEUE_MODULE = 'pithos.backends.lib.rabbitmq'
#DEFAULT_QUEUE_CONNECTION = 'rabbitmq://guest:guest@localhost:5672/pithos'

QUEUE_MESSAGE_KEY = '#'
QUEUE_CLIENT_ID = 2 # Pithos.

( CLUSTER_NORMAL, CLUSTER_HISTORY, CLUSTER_DELETED ) = range(3)

inf = float('inf')

ULTIMATE_ANSWER = 42


logger = logging.getLogger(__name__)


def backend_method(func=None, autocommit=1):
    if func is None:
        def fn(func):
            return backend_method(func, autocommit)
        return fn

    if not autocommit:
        return func
    def fn(self, *args, **kw):
        self.wrapper.execute()
        try:
            ret = func(self, *args, **kw)
            self.wrapper.commit()
            return ret
        except:
            self.wrapper.rollback()
            raise
    return fn


class ModularBackend(BaseBackend):
    """A modular backend.
    
    Uses modules for SQL functions and storage.
    """
    
    def __init__(self, db_module=None, db_connection=None,
                 block_module=None, block_path=None,
                 queue_module=None, queue_connection=None):
        db_module = db_module or DEFAULT_DB_MODULE
        db_connection = db_connection or DEFAULT_DB_CONNECTION
        block_module = block_module or DEFAULT_BLOCK_MODULE
        block_path = block_path or DEFAULT_BLOCK_PATH
        #queue_module = queue_module or DEFAULT_QUEUE_MODULE
        #queue_connection = queue_connection or DEFAULT_QUEUE_CONNECTION
        
        self.hash_algorithm = 'sha256'
        self.block_size = 4 * 1024 * 1024 # 4MB
        
        self.default_policy = {'quota': DEFAULT_QUOTA, 'versioning': DEFAULT_VERSIONING}
        
        def load_module(m):
            __import__(m)
            return sys.modules[m]
        
        self.db_module = load_module(db_module)
        self.wrapper = self.db_module.DBWrapper(db_connection)
        params = {'wrapper': self.wrapper}
        self.permissions = self.db_module.Permissions(**params)
        for x in ['READ', 'WRITE']:
            setattr(self, x, getattr(self.db_module, x))
        self.node = self.db_module.Node(**params)
        for x in ['ROOTNODE', 'SERIAL', 'HASH', 'SIZE', 'MTIME', 'MUSER', 'UUID', 'CLUSTER']:
            setattr(self, x, getattr(self.db_module, x))
        
        self.block_module = load_module(block_module)
        params = {'path': block_path,
                  'block_size': self.block_size,
                  'hash_algorithm': self.hash_algorithm}
        self.store = self.block_module.Store(**params)

        if queue_module and queue_connection:
            self.queue_module = load_module(queue_module)
            params = {'exchange': queue_connection,
                      'message_key': QUEUE_MESSAGE_KEY,
                      'client_id': QUEUE_CLIENT_ID}
            self.queue = self.queue_module.Queue(**params)
        else:
            class NoQueue:
                def send(self, *args):
                    pass
            
            self.queue = NoQueue()
    
    def close(self):
        self.wrapper.close()
    
    @backend_method
    def list_accounts(self, user, marker=None, limit=10000):
        """Return a list of accounts the user can access."""
        
        logger.debug("list_accounts: %s %s %s", user, marker, limit)
        allowed = self._allowed_accounts(user)
        start, limit = self._list_limits(allowed, marker, limit)
        return allowed[start:start + limit]
    
    @backend_method
    def get_account_meta(self, user, account, domain, until=None):
        """Return a dictionary with the account metadata for the domain."""
        
        logger.debug("get_account_meta: %s %s %s", account, domain, until)
        path, node = self._lookup_account(account, user == account)
        if user != account:
            if until or node is None or account not in self._allowed_accounts(user):
                raise NotAllowedError
        try:
            props = self._get_properties(node, until)
            mtime = props[self.MTIME]
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
                meta.update(dict(self.node.attribute_get(props[self.SERIAL], domain)))
            if until is not None:
                meta.update({'until_timestamp': tstamp})
            meta.update({'name': account, 'count': count, 'bytes': bytes})
        meta.update({'modified': modified})
        return meta
    
    @backend_method
    def update_account_meta(self, user, account, domain, meta, replace=False):
        """Update the metadata associated with the account for the domain."""
        
        logger.debug("update_account_meta: %s %s %s %s", account, domain, meta, replace)
        if user != account:
            raise NotAllowedError
        path, node = self._lookup_account(account, True)
        self._put_metadata(user, node, domain, meta, replace)
    
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
    def get_account_policy(self, user, account):
        """Return a dictionary with the account policy."""
        
        logger.debug("get_account_policy: %s", account)
        if user != account:
            if account not in self._allowed_accounts(user):
                raise NotAllowedError
            return {}
        path, node = self._lookup_account(account, True)
        return self._get_policy(node)
    
    @backend_method
    def update_account_policy(self, user, account, policy, replace=False):
        """Update the policy associated with the account."""
        
        logger.debug("update_account_policy: %s %s %s", account, policy, replace)
        if user != account:
            raise NotAllowedError
        path, node = self._lookup_account(account, True)
        self._check_policy(policy)
        self._put_policy(node, policy, replace)
    
    @backend_method
    def put_account(self, user, account, policy={}):
        """Create a new account with the given name."""
        
        logger.debug("put_account: %s %s", account, policy)
        if user != account:
            raise NotAllowedError
        node = self.node.node_lookup(account)
        if node is not None:
            raise NameError('Account already exists')
        if policy:
            self._check_policy(policy)
        node = self._put_path(user, self.ROOTNODE, account)
        self._put_policy(node, policy, True)
    
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
            allowed = list(set(allowed))
            start, limit = self._list_limits(allowed, marker, limit)
            return allowed[start:start + limit]
        node = self.node.node_lookup(account)
        return [x[0] for x in self._list_objects(node, account, '', '/', marker, limit, False, None, [], until)]
    
    @backend_method
    def get_container_meta(self, user, account, container, domain, until=None):
        """Return a dictionary with the container metadata for the domain."""
        
        logger.debug("get_container_meta: %s %s %s %s", account, container, domain, until)
        if user != account:
            if until or container not in self._allowed_containers(user, account):
                raise NotAllowedError
        path, node = self._lookup_container(account, container)
        props = self._get_properties(node, until)
        mtime = props[self.MTIME]
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
            meta = dict(self.node.attribute_get(props[self.SERIAL], domain))
            if until is not None:
                meta.update({'until_timestamp': tstamp})
            meta.update({'name': container, 'count': count, 'bytes': bytes})
        meta.update({'modified': modified})
        return meta
    
    @backend_method
    def update_container_meta(self, user, account, container, domain, meta, replace=False):
        """Update the metadata associated with the container for the domain."""
        
        logger.debug("update_container_meta: %s %s %s %s %s", account, container, domain, meta, replace)
        if user != account:
            raise NotAllowedError
        path, node = self._lookup_container(account, container)
        self._put_metadata(user, node, domain, meta, replace)
    
    @backend_method
    def get_container_policy(self, user, account, container):
        """Return a dictionary with the container policy."""
        
        logger.debug("get_container_policy: %s %s", account, container)
        if user != account:
            if container not in self._allowed_containers(user, account):
                raise NotAllowedError
            return {}
        path, node = self._lookup_container(account, container)
        return self._get_policy(node)
    
    @backend_method
    def update_container_policy(self, user, account, container, policy, replace=False):
        """Update the policy associated with the container."""
        
        logger.debug("update_container_policy: %s %s %s %s", account, container, policy, replace)
        if user != account:
            raise NotAllowedError
        path, node = self._lookup_container(account, container)
        self._check_policy(policy)
        self._put_policy(node, policy, replace)
    
    @backend_method
    def put_container(self, user, account, container, policy={}):
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
        node = self._put_path(user, self._lookup_account(account, True)[1], path)
        self._put_policy(node, policy, True)
    
    @backend_method
    def delete_container(self, user, account, container, until=None):
        """Delete/purge the container with the given name."""
        
        logger.debug("delete_container: %s %s %s", account, container, until)
        if user != account:
            raise NotAllowedError
        path, node = self._lookup_container(account, container)
        
        if until is not None:
            hashes, size = self.node.node_purge_children(node, until, CLUSTER_HISTORY)
            for h in hashes:
                self.store.map_delete(h)
            self.node.node_purge_children(node, until, CLUSTER_DELETED)
            self._report_size_change(user, account, -size, {'action': 'container purge'})
            return
        
        if self._get_statistics(node)[0] > 0:
            raise IndexError('Container is not empty')
        hashes, size = self.node.node_purge_children(node, inf, CLUSTER_HISTORY)
        for h in hashes:
            self.store.map_delete(h)
        self.node.node_purge_children(node, inf, CLUSTER_DELETED)
        self.node.node_remove(node)
        self._report_size_change(user, account, -size, {'action': 'container delete'})
    
    @backend_method
    def list_objects(self, user, account, container, prefix='', delimiter=None, marker=None, limit=10000, virtual=True, domain=None, keys=[], shared=False, until=None, size_range=None):
        """Return a list of objects existing under a container."""
        
        logger.debug("list_objects: %s %s %s %s %s %s %s %s %s %s %s", account, container, prefix, delimiter, marker, limit, virtual, domain, keys, shared, until)
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
        return self._list_objects(node, path, prefix, delimiter, marker, limit, virtual, domain, keys, until, size_range, allowed)
    
    @backend_method
    def list_object_meta(self, user, account, container, domain, until=None):
        """Return a list with all the container's object meta keys for the domain."""
        
        logger.debug("list_object_meta: %s %s %s %s", account, container, domain, until)
        allowed = []
        if user != account:
            if until:
                raise NotAllowedError
            allowed = self.permissions.access_list_paths(user, '/'.join((account, container)))
            if not allowed:
                raise NotAllowedError
        path, node = self._lookup_container(account, container)
        before = until if until is not None else inf
        return self.node.latest_attribute_keys(node, domain, before, CLUSTER_DELETED, allowed)
    
    @backend_method
    def get_object_meta(self, user, account, container, name, domain, version=None):
        """Return a dictionary with the object metadata for the domain."""
        
        logger.debug("get_object_meta: %s %s %s %s %s", account, container, name, domain, version)
        self._can_read(user, account, container, name)
        path, node = self._lookup_object(account, container, name)
        props = self._get_version(node, version)
        if version is None:
            modified = props[self.MTIME]
        else:
            try:
                modified = self._get_version(node)[self.MTIME] # Overall last modification.
            except NameError: # Object may be deleted.
                del_props = self.node.version_lookup(node, inf, CLUSTER_DELETED)
                if del_props is None:
                    raise NameError('Object does not exist')
                modified = del_props[self.MTIME]
        
        meta = dict(self.node.attribute_get(props[self.SERIAL], domain))
        meta.update({'name': name, 'bytes': props[self.SIZE], 'hash':props[self.HASH]})
        meta.update({'version': props[self.SERIAL], 'version_timestamp': props[self.MTIME]})
        meta.update({'modified': modified, 'modified_by': props[self.MUSER], 'uuid': props[self.UUID]})
        return meta
    
    @backend_method
    def update_object_meta(self, user, account, container, name, domain, meta, replace=False):
        """Update the metadata associated with the object for the domain and return the new version."""
        
        logger.debug("update_object_meta: %s %s %s %s %s %s", account, container, name, domain, meta, replace)
        self._can_write(user, account, container, name)
        path, node = self._lookup_object(account, container, name)
        src_version_id, dest_version_id = self._put_metadata(user, node, domain, meta, replace)
        self._apply_versioning(account, container, src_version_id)
        return dest_version_id
    
    @backend_method
    def get_object_permissions(self, user, account, container, name):
        """Return the action allowed on the object, the path
        from which the object gets its permissions from,
        along with a dictionary containing the permissions."""
        
        logger.debug("get_object_permissions: %s %s %s", account, container, name)
        allowed = 'write'
        if user != account:
            path = '/'.join((account, container, name))
            if self.permissions.access_check(path, self.WRITE, user):
                allowed = 'write'
            elif self.permissions.access_check(path, self.READ, user):
                allowed = 'read'
            else:
                raise NotAllowedError
        path = self._lookup_object(account, container, name)[0]
        return (allowed,) + self.permissions.access_inherit(path)
    
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
        """Return the public id of the object if applicable."""
        
        logger.debug("get_object_public: %s %s %s", account, container, name)
        self._can_read(user, account, container, name)
        path = self._lookup_object(account, container, name)[0]
        p = self.permissions.public_get(path)
        if p is not None:
            p += ULTIMATE_ANSWER
        return p
    
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
        hashmap = self.store.map_get(binascii.unhexlify(props[self.HASH]))
        return props[self.SIZE], [binascii.hexlify(x) for x in hashmap]
    
    def _update_object_hash(self, user, account, container, name, size, hash, permissions, src_node=None, is_copy=False):
        if permissions is not None and user != account:
            raise NotAllowedError
        self._can_write(user, account, container, name)
        if permissions is not None:
            path = '/'.join((account, container, name))
            self._check_permissions(path, permissions)
        
        account_path, account_node = self._lookup_account(account, True)
        container_path, container_node = self._lookup_container(account, container)
        path, node = self._put_object_node(container_path, container_node, name)
        pre_version_id, dest_version_id = self._put_version_duplicate(user, node, src_node=src_node, size=size, hash=hash, is_copy=is_copy)
        
        # Check quota.
        del_size = self._apply_versioning(account, container, pre_version_id)
        size_delta = size - del_size
        if size_delta > 0:
            account_quota = long(self._get_policy(account_node)['quota'])
            container_quota = long(self._get_policy(container_node)['quota'])
            if (account_quota > 0 and self._get_statistics(account_node)[1] + size_delta > account_quota) or \
               (container_quota > 0 and self._get_statistics(container_node)[1] + size_delta > container_quota):
                # This must be executed in a transaction, so the version is never created if it fails.
                raise QuotaError
        self._report_size_change(user, account, size_delta, {'action': 'object update'})
        
        if permissions is not None:
            self.permissions.access_set(path, permissions)
        return pre_version_id, dest_version_id
    
    @backend_method
    def update_object_hashmap(self, user, account, container, name, size, hashmap, domain, meta={}, replace_meta=False, permissions=None):
        """Create/update an object with the specified size and partial hashes."""
        
        logger.debug("update_object_hashmap: %s %s %s %s %s", account, container, name, size, hashmap)
        if size == 0: # No such thing as an empty hashmap.
            hashmap = [self.put_block('')]
        map = HashMap(self.block_size, self.hash_algorithm)
        map.extend([binascii.unhexlify(x) for x in hashmap])
        missing = self.store.block_search(map)
        if missing:
            ie = IndexError()
            ie.data = [binascii.hexlify(x) for x in missing]
            raise ie
        
        hash = map.hash()
        pre_version_id, dest_version_id = self._update_object_hash(user, account, container, name, size, binascii.hexlify(hash), permissions)
        self._put_metadata_duplicate(pre_version_id, dest_version_id, domain, meta, replace_meta)
        self.store.map_put(hash, map)
        return dest_version_id
    
    def _copy_object(self, user, src_account, src_container, src_name, dest_account, dest_container, dest_name, dest_domain=None, dest_meta={}, replace_meta=False, permissions=None, src_version=None, is_move=False):
        self._can_read(user, src_account, src_container, src_name)
        path, node = self._lookup_object(src_account, src_container, src_name)
        # TODO: Will do another fetch of the properties in duplicate version...
        props = self._get_version(node, src_version) # Check to see if source exists.
        src_version_id = props[self.SERIAL]
        hash = props[self.HASH]
        size = props[self.SIZE]
        
        is_copy = not is_move and (src_account, src_container, src_name) != (dest_account, dest_container, dest_name) # New uuid.
        pre_version_id, dest_version_id = self._update_object_hash(user, dest_account, dest_container, dest_name, size, hash, permissions, src_node=node, is_copy=is_copy)
        self._put_metadata_duplicate(src_version_id, dest_version_id, dest_domain, dest_meta, replace_meta)
        return dest_version_id
    
    @backend_method
    def copy_object(self, user, src_account, src_container, src_name, dest_account, dest_container, dest_name, domain, meta={}, replace_meta=False, permissions=None, src_version=None):
        """Copy an object's data and metadata."""
        
        logger.debug("copy_object: %s %s %s %s %s %s %s %s %s %s %s", src_account, src_container, src_name, dest_account, dest_container, dest_name, domain, meta, replace_meta, permissions, src_version)
        dest_version_id = self._copy_object(user, src_account, src_container, src_name, dest_account, dest_container, dest_name, domain, meta, replace_meta, permissions, src_version, False)
        return dest_version_id
    
    @backend_method
    def move_object(self, user, src_account, src_container, src_name, dest_account, dest_container, dest_name, domain, meta={}, replace_meta=False, permissions=None):
        """Move an object's data and metadata."""
        
        logger.debug("move_object: %s %s %s %s %s %s %s %s %s %s", src_account, src_container, src_name, dest_account, dest_container, dest_name, domain, meta, replace_meta, permissions)
        if user != src_account:
            raise NotAllowedError
        dest_version_id = self._copy_object(user, src_account, src_container, src_name, dest_account, dest_container, dest_name, domain, meta, replace_meta, permissions, None, True)
        if (src_account, src_container, src_name) != (dest_account, dest_container, dest_name):
            self._delete_object(user, src_account, src_container, src_name)
        return dest_version_id
    
    def _delete_object(self, user, account, container, name, until=None):
        if user != account:
            raise NotAllowedError
        
        if until is not None:
            path = '/'.join((account, container, name))
            node = self.node.node_lookup(path)
            if node is None:
                return
            hashes = []
            size = 0
            h, s = self.node.node_purge(node, until, CLUSTER_NORMAL)
            hashes += h
            size += s
            h, s = self.node.node_purge(node, until, CLUSTER_HISTORY)
            hashes += h
            size += s
            for h in hashes:
                self.store.map_delete(h)
            self.node.node_purge(node, until, CLUSTER_DELETED)
            try:
                props = self._get_version(node)
            except NameError:
                self.permissions.access_clear(path)
            self._report_size_change(user, account, -size, {'action': 'object purge'})
            return
        
        path, node = self._lookup_object(account, container, name)
        src_version_id, dest_version_id = self._put_version_duplicate(user, node, size=0, hash=None, cluster=CLUSTER_DELETED)
        del_size = self._apply_versioning(account, container, src_version_id)
        if del_size:
            self._report_size_change(user, account, -del_size, {'action': 'object delete'})
        self.permissions.access_clear(path)
    
    @backend_method
    def delete_object(self, user, account, container, name, until=None):
        """Delete/purge an object."""
        
        logger.debug("delete_object: %s %s %s %s", account, container, name, until)
        self._delete_object(user, account, container, name, until)
    
    @backend_method
    def list_versions(self, user, account, container, name):
        """Return a list of all (version, version_timestamp) tuples for an object."""
        
        logger.debug("list_versions: %s %s %s", account, container, name)
        self._can_read(user, account, container, name)
        path, node = self._lookup_object(account, container, name)
        versions = self.node.node_get_versions(node)
        return [[x[self.SERIAL], x[self.MTIME]] for x in versions if x[self.CLUSTER] != CLUSTER_DELETED]
    
    @backend_method
    def get_uuid(self, user, uuid):
        """Return the (account, container, name) for the UUID given."""
        
        logger.debug("get_uuid: %s", uuid)
        info = self.node.latest_uuid(uuid)
        if info is None:
            raise NameError
        path, serial = info
        account, container, name = path.split('/', 2)
        self._can_read(user, account, container, name)
        return (account, container, name)
    
    @backend_method
    def get_public(self, user, public):
        """Return the (account, container, name) for the public id given."""
        
        logger.debug("get_public: %s", public)
        if public is None or public < ULTIMATE_ANSWER:
            raise NameError
        path = self.permissions.public_path(public - ULTIMATE_ANSWER)
        if path is None:
            raise NameError
        account, container, name = path.split('/', 2)
        self._can_read(user, account, container, name)
        return (account, container, name)
    
    @backend_method(autocommit=0)
    def get_block(self, hash):
        """Return a block's data."""
        
        logger.debug("get_block: %s", hash)
        block = self.store.block_get(binascii.unhexlify(hash))
        if not block:
            raise NameError('Block does not exist')
        return block
    
    @backend_method(autocommit=0)
    def put_block(self, data):
        """Store a block and return the hash."""
        
        logger.debug("put_block: %s", len(data))
        return binascii.hexlify(self.store.block_put(data))
    
    @backend_method(autocommit=0)
    def update_block(self, hash, data, offset=0):
        """Update a known block and return the hash."""
        
        logger.debug("update_block: %s %s %s", hash, len(data), offset)
        if offset == 0 and len(data) == self.block_size:
            return self.put_block(data)
        h = self.store.block_update(binascii.unhexlify(hash), offset, data)
        return binascii.hexlify(h)
    
    # Path functions.
    
    def _generate_uuid(self):
        return str(uuidlib.uuid4())
    
    def _put_object_node(self, path, parent, name):
        path = '/'.join((path, name))
        node = self.node.node_lookup(path)
        if node is None:
            node = self.node.node_create(parent, path)
        return path, node
    
    def _put_path(self, user, parent, path):
        node = self.node.node_create(parent, path)
        self.node.version_create(node, None, 0, None, user, self._generate_uuid(), CLUSTER_NORMAL)
        return node
    
    def _lookup_account(self, account, create=True):
        node = self.node.node_lookup(account)
        if node is None and create:
            node = self._put_path(account, self.ROOTNODE, account) # User is account.
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
            try:
                version = int(version)
            except ValueError:
                raise IndexError('Version does not exist')
            props = self.node.version_get_properties(version)
            if props is None or props[self.CLUSTER] == CLUSTER_DELETED:
                raise IndexError('Version does not exist')
        return props
    
    def _put_version_duplicate(self, user, node, src_node=None, size=None, hash=None, cluster=CLUSTER_NORMAL, is_copy=False):
        """Create a new version of the node."""
        
        props = self.node.version_lookup(node if src_node is None else src_node, inf, CLUSTER_NORMAL)
        if props is not None:
            src_version_id = props[self.SERIAL]
            src_hash = props[self.HASH]
            src_size = props[self.SIZE]
        else:
            src_version_id = None
            src_hash = None
            src_size = 0
        if size is None:
            hash = src_hash # This way hash can be set to None.
            size = src_size
        uuid = self._generate_uuid() if (is_copy or src_version_id is None) else props[self.UUID]
        
        if src_node is None:
            pre_version_id = src_version_id
        else:
            pre_version_id = None
            props = self.node.version_lookup(node, inf, CLUSTER_NORMAL)
            if props is not None:
                pre_version_id = props[self.SERIAL]
        if pre_version_id is not None:
            self.node.version_recluster(pre_version_id, CLUSTER_HISTORY)
        
        dest_version_id, mtime = self.node.version_create(node, hash, size, src_version_id, user, uuid, cluster)
        return pre_version_id, dest_version_id
    
    def _put_metadata_duplicate(self, src_version_id, dest_version_id, domain, meta, replace=False):
        if src_version_id is not None:
            self.node.attribute_copy(src_version_id, dest_version_id)
        if not replace:
            self.node.attribute_del(dest_version_id, domain, (k for k, v in meta.iteritems() if v == ''))
            self.node.attribute_set(dest_version_id, domain, ((k, v) for k, v in meta.iteritems() if v != ''))
        else:
            self.node.attribute_del(dest_version_id, domain)
            self.node.attribute_set(dest_version_id, domain, ((k, v) for k, v in meta.iteritems()))
    
    def _put_metadata(self, user, node, domain, meta, replace=False):
        """Create a new version and store metadata."""
        
        src_version_id, dest_version_id = self._put_version_duplicate(user, node)
        self._put_metadata_duplicate(src_version_id, dest_version_id, domain, meta, replace)
        return src_version_id, dest_version_id
    
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
    
    def _list_objects(self, parent, path, prefix='', delimiter=None, marker=None, limit=10000, virtual=True, domain=None, keys=[], until=None, size_range=None, allowed=[]):
        cont_prefix = path + '/'
        prefix = cont_prefix + prefix
        start = cont_prefix + marker if marker else None
        before = until if until is not None else inf
        filterq = keys if domain else []
        sizeq = size_range
        
        objects, prefixes = self.node.latest_version_list(parent, prefix, delimiter, start, limit, before, CLUSTER_DELETED, allowed, domain, filterq, sizeq)
        objects.extend([(p, None) for p in prefixes] if virtual else [])
        objects.sort(key=lambda x: x[0])
        objects = [(x[0][len(cont_prefix):], x[1]) for x in objects]
        
        start, limit = self._list_limits([x[0] for x in objects], marker, limit)
        return objects[start:start + limit]
    
    # Reporting functions.
    
    def _report_size_change(self, user, account, size, details={}):
        logger.debug("_report_size_change: %s %s %s %s", user, account, size, details)
        account_node = self._lookup_account(account, True)[1]
        total = self._get_statistics(account_node)[1]
        details.update({'user': user, 'total': total})
        self.queue.send(account, 'diskspace', size, details)
    
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
                if v not in ['auto', 'none']:
                    raise ValueError
            else:
                raise ValueError
    
    def _put_policy(self, node, policy, replace):
        if replace:
            for k, v in self.default_policy.iteritems():
                if k not in policy:
                    policy[k] = v
        self.node.policy_set(node, policy)
    
    def _get_policy(self, node):
        policy = self.default_policy.copy()
        policy.update(self.node.policy_get(node))
        return policy
    
    def _apply_versioning(self, account, container, version_id):
        """Delete the provided version if such is the policy.
           Return size of object removed.
        """
        
        if version_id is None:
            return 0
        path, node = self._lookup_container(account, container)
        versioning = self._get_policy(node)['versioning']
        if versioning != 'auto':
            hash, size = self.node.version_remove(version_id)
            self.store.map_delete(hash)
            return size
        return 0
    
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
        if not self.permissions.access_check(path, self.READ, user) and not self.permissions.access_check(path, self.WRITE, user):
            raise NotAllowedError
    
    def _can_write(self, user, account, container, name):
        if user == account:
            return True
        path = '/'.join((account, container, name))
        if not self.permissions.access_check(path, self.WRITE, user):
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
