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
import hashlib
import binascii

from synnefo.lib.quotaholder import QuotaholderClient

from base import DEFAULT_QUOTA, DEFAULT_VERSIONING, NotAllowedError, QuotaError, BaseBackend, \
    AccountExists, ContainerExists, AccountNotEmpty, ContainerNotEmpty, ItemNotExists, VersionNotExists

# Stripped-down version of the HashMap class found in tools.


class HashMap(list):

    def __init__(self, blocksize, blockhash):
        super(HashMap, self).__init__()
        self.blocksize = blocksize
        self.blockhash = blockhash

    def _hash_raw(self, v):
        h = hashlib.new(self.blockhash)
        h.update(v)
        return h.digest()

    def hash(self):
        if len(self) == 0:
            return self._hash_raw('')
        if len(self) == 1:
            return self.__getitem__(0)

        h = list(self)
        s = 2
        while s < len(h):
            s = s * 2
        h += [('\x00' * len(h[0]))] * (s - len(h))
        while len(h) > 1:
            h = [self._hash_raw(h[x] + h[x + 1]) for x in range(0, len(h), 2)]
        return h[0]

# Default modules and settings.
DEFAULT_DB_MODULE = 'pithos.backends.lib.sqlalchemy'
DEFAULT_DB_CONNECTION = 'sqlite:///backend.db'
DEFAULT_BLOCK_MODULE = 'pithos.backends.lib.hashfiler'
DEFAULT_BLOCK_PATH = 'data/'
DEFAULT_BLOCK_UMASK = 0o022
#DEFAULT_QUEUE_MODULE = 'pithos.backends.lib.rabbitmq'
DEFAULT_BLOCK_PARAMS = { 'mappool': None, 'blockpool': None }
#DEFAULT_QUEUE_HOSTS = '[amqp://guest:guest@localhost:5672]'
#DEFAULT_QUEUE_EXCHANGE = 'pithos'
DEFAULT_PUBLIC_URL_ALPHABET = ('0123456789'
                               'abcdefghijklmnopqrstuvwxyz'
                               'ABCDEFGHIJKLMNOPQRSTUVWXYZ')
DEFAULT_PUBLIC_URL_SECURITY = 8

QUEUE_MESSAGE_KEY_PREFIX = 'pithos.%s'
QUEUE_CLIENT_ID = 'pithos'
QUEUE_INSTANCE_ID = '1'

(CLUSTER_NORMAL, CLUSTER_HISTORY, CLUSTER_DELETED) = range(3)

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
        serials = []
        self.serials = serials
        self.messages = []

        try:
            ret = func(self, *args, **kw)
            for m in self.messages:
                self.queue.send(*m)
            if serials:
                self.quotaholder.accept_commission(
                            context     =   {},
                            clientkey   =   'pithos',
                            serials     =   serials)
            self.wrapper.commit()
            return ret
        except:
            if serials:
                self.quotaholder.reject_commission(
                            context     =   {},
                            clientkey   =   'pithos',
                            serials     =   serials)
            self.wrapper.rollback()
            raise
    return fn


class ModularBackend(BaseBackend):
    """A modular backend.

    Uses modules for SQL functions and storage.
    """

    def __init__(self, db_module=None, db_connection=None,
                 block_module=None, block_path=None, block_umask=None,
                 queue_module=None, queue_hosts=None, queue_exchange=None,
                 quotaholder_enabled=False,
                 quotaholder_url=None, quotaholder_token=None,
                 quotaholder_client_poolsize=None,
                 free_versioning=True, block_params=None,
                 public_url_security=None,
                 public_url_alphabet=None):
        db_module = db_module or DEFAULT_DB_MODULE
        db_connection = db_connection or DEFAULT_DB_CONNECTION
        block_module = block_module or DEFAULT_BLOCK_MODULE
        block_path = block_path or DEFAULT_BLOCK_PATH
        block_umask = block_umask or DEFAULT_BLOCK_UMASK
        block_params = block_params or DEFAULT_BLOCK_PARAMS
        #queue_module = queue_module or DEFAULT_QUEUE_MODULE

        self.default_policy = {'quota': DEFAULT_QUOTA, 'versioning': DEFAULT_VERSIONING}
        #queue_hosts = queue_hosts or DEFAULT_QUEUE_HOSTS
        #queue_exchange = queue_exchange or DEFAULT_QUEUE_EXCHANGE

        self.public_url_security = public_url_security or DEFAULT_PUBLIC_URL_SECURITY
        self.public_url_alphabet = public_url_alphabet or DEFAULT_PUBLIC_URL_ALPHABET

        self.hash_algorithm = 'sha256'
        self.block_size = 4 * 1024 * 1024  # 4MB
        self.free_versioning = free_versioning

        self.default_policy = {'quota': DEFAULT_QUOTA,
                               'versioning': DEFAULT_VERSIONING}

        def load_module(m):
            __import__(m)
            return sys.modules[m]

        self.db_module = load_module(db_module)
        self.wrapper = self.db_module.DBWrapper(db_connection)
        params = {'wrapper': self.wrapper}
        self.permissions = self.db_module.Permissions(**params)
        self.config = self.db_module.Config(**params)
        self.quotaholder_serials = self.db_module.QuotaholderSerial(**params)
        for x in ['READ', 'WRITE']:
            setattr(self, x, getattr(self.db_module, x))
        self.node = self.db_module.Node(**params)
        for x in ['ROOTNODE', 'SERIAL', 'HASH', 'SIZE', 'TYPE', 'MTIME', 'MUSER', 'UUID', 'CHECKSUM', 'CLUSTER', 'MATCH_PREFIX', 'MATCH_EXACT']:
            setattr(self, x, getattr(self.db_module, x))

        self.block_module = load_module(block_module)
        self.block_params = block_params
        params = {'path': block_path,
                  'block_size': self.block_size,
                  'hash_algorithm': self.hash_algorithm,
                  'umask': block_umask}
        params.update(self.block_params)
        self.store = self.block_module.Store(**params)

        if queue_module and queue_hosts:
            self.queue_module = load_module(queue_module)
            params = {'hosts': queue_hosts,
                      'exchange': queue_exchange,
                      'client_id': QUEUE_CLIENT_ID}
            self.queue = self.queue_module.Queue(**params)
        else:
            class NoQueue:
                def send(self, *args):
                    pass

                def close(self):
                    pass

            self.queue = NoQueue()

        self.quotaholder_enabled = quotaholder_enabled
        if quotaholder_enabled:
            self.quotaholder_url = quotaholder_url
            self.quotaholder_token = quotaholder_token
            self.quotaholder = QuotaholderClient(
                                    quotaholder_url,
                                    token=quotaholder_token,
                                    poolsize=quotaholder_client_poolsize)

        self.serials = []
        self.messages = []

    def close(self):
        self.wrapper.close()
        self.queue.close()

    @property
    def using_external_quotaholder(self):
        return self.quotaholder_enabled

    @backend_method
    def list_accounts(self, user, marker=None, limit=10000):
        """Return a list of accounts the user can access."""

        logger.debug("list_accounts: %s %s %s", user, marker, limit)
        allowed = self._allowed_accounts(user)
        start, limit = self._list_limits(allowed, marker, limit)
        return allowed[start:start + limit]

    @backend_method
    def get_account_meta(
            self, user, account, domain, until=None, include_user_defined=True,
            external_quota=None):
        """Return a dictionary with the account metadata for the domain."""

        logger.debug(
            "get_account_meta: %s %s %s %s", user, account, domain, until)
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
            modified = self._get_statistics(
                node)[2]  # Overall last modification.
            modified = max(modified, mtime)

        if user != account:
            meta = {'name': account}
        else:
            meta = {}
            if props is not None and include_user_defined:
                meta.update(
                    dict(self.node.attribute_get(props[self.SERIAL], domain)))
            if until is not None:
                meta.update({'until_timestamp': tstamp})
            meta.update({'name': account, 'count': count, 'bytes': bytes})
            if self.using_external_quotaholder:
                external_quota = external_quota or {}
                meta['bytes'] = external_quota.get('currValue', 0)
        meta.update({'modified': modified})
        return meta

    @backend_method
    def update_account_meta(self, user, account, domain, meta, replace=False):
        """Update the metadata associated with the account for the domain."""

        logger.debug("update_account_meta: %s %s %s %s %s", user,
                     account, domain, meta, replace)
        if user != account:
            raise NotAllowedError
        path, node = self._lookup_account(account, True)
        self._put_metadata(user, node, domain, meta, replace)

    @backend_method
    def get_account_groups(self, user, account):
        """Return a dictionary with the user groups defined for this account."""

        logger.debug("get_account_groups: %s %s", user, account)
        if user != account:
            if account not in self._allowed_accounts(user):
                raise NotAllowedError
            return {}
        self._lookup_account(account, True)
        return self.permissions.group_dict(account)

    @backend_method
    def update_account_groups(self, user, account, groups, replace=False):
        """Update the groups associated with the account."""

        logger.debug("update_account_groups: %s %s %s %s", user,
                     account, groups, replace)
        if user != account:
            raise NotAllowedError
        self._lookup_account(account, True)
        self._check_groups(groups)
        if replace:
            self.permissions.group_destroy(account)
        for k, v in groups.iteritems():
            if not replace:  # If not already deleted.
                self.permissions.group_delete(account, k)
            if v:
                self.permissions.group_addmany(account, k, v)

    @backend_method
    def get_account_policy(self, user, account, external_quota=None):
        """Return a dictionary with the account policy."""

        logger.debug("get_account_policy: %s %s", user, account)
        if user != account:
            if account not in self._allowed_accounts(user):
                raise NotAllowedError
            return {}
        path, node = self._lookup_account(account, True)
        policy = self._get_policy(node)
        if self.using_external_quotaholder:
            external_quota = external_quota or {}
            policy['quota'] = external_quota.get('maxValue', 0)
        return policy

    @backend_method
    def update_account_policy(self, user, account, policy, replace=False):
        """Update the policy associated with the account."""

        logger.debug("update_account_policy: %s %s %s %s", user,
                     account, policy, replace)
        if user != account:
            raise NotAllowedError
        path, node = self._lookup_account(account, True)
        self._check_policy(policy)
        self._put_policy(node, policy, replace)

    @backend_method
    def put_account(self, user, account, policy=None):
        """Create a new account with the given name."""

        logger.debug("put_account: %s %s %s", user, account, policy)
        policy = policy or {}
        if user != account:
            raise NotAllowedError
        node = self.node.node_lookup(account)
        if node is not None:
            raise AccountExists('Account already exists')
        if policy:
            self._check_policy(policy)
        node = self._put_path(user, self.ROOTNODE, account)
        self._put_policy(node, policy, True)

    @backend_method
    def delete_account(self, user, account):
        """Delete the account with the given name."""

        logger.debug("delete_account: %s %s", user, account)
        if user != account:
            raise NotAllowedError
        node = self.node.node_lookup(account)
        if node is None:
            return
        if not self.node.node_remove(node):
            raise AccountNotEmpty('Account is not empty')
        self.permissions.group_destroy(account)

    @backend_method
    def list_containers(self, user, account, marker=None, limit=10000, shared=False, until=None, public=False):
        """Return a list of containers existing under an account."""

        logger.debug("list_containers: %s %s %s %s %s %s %s", user,
                     account, marker, limit, shared, until, public)
        if user != account:
            if until or account not in self._allowed_accounts(user):
                raise NotAllowedError
            allowed = self._allowed_containers(user, account)
            start, limit = self._list_limits(allowed, marker, limit)
            return allowed[start:start + limit]
        if shared or public:
            allowed = set()
            if shared:
                allowed.update([x.split('/', 2)[1] for x in self.permissions.access_list_shared(account)])
            if public:
                allowed.update([x[0].split('/', 2)[1] for x in self.permissions.public_list(account)])
            allowed = sorted(allowed)
            start, limit = self._list_limits(allowed, marker, limit)
            return allowed[start:start + limit]
        node = self.node.node_lookup(account)
        containers = [x[0] for x in self._list_object_properties(
            node, account, '', '/', marker, limit, False, None, [], until)]
        start, limit = self._list_limits(
            [x[0] for x in containers], marker, limit)
        return containers[start:start + limit]

    @backend_method
    def list_container_meta(self, user, account, container, domain, until=None):
        """Return a list with all the container's object meta keys for the domain."""

        logger.debug("list_container_meta: %s %s %s %s %s", user,
                     account, container, domain, until)
        allowed = []
        if user != account:
            if until:
                raise NotAllowedError
            allowed = self.permissions.access_list_paths(
                user, '/'.join((account, container)))
            if not allowed:
                raise NotAllowedError
        path, node = self._lookup_container(account, container)
        before = until if until is not None else inf
        allowed = self._get_formatted_paths(allowed)
        return self.node.latest_attribute_keys(node, domain, before, CLUSTER_DELETED, allowed)

    @backend_method
    def get_container_meta(self, user, account, container, domain, until=None, include_user_defined=True):
        """Return a dictionary with the container metadata for the domain."""

        logger.debug("get_container_meta: %s %s %s %s %s", user,
                     account, container, domain, until)
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
            modified = self._get_statistics(
                node)[2]  # Overall last modification.
            modified = max(modified, mtime)

        if user != account:
            meta = {'name': container}
        else:
            meta = {}
            if include_user_defined:
                meta.update(
                    dict(self.node.attribute_get(props[self.SERIAL], domain)))
            if until is not None:
                meta.update({'until_timestamp': tstamp})
            meta.update({'name': container, 'count': count, 'bytes': bytes})
        meta.update({'modified': modified})
        return meta

    @backend_method
    def update_container_meta(self, user, account, container, domain, meta, replace=False):
        """Update the metadata associated with the container for the domain."""

        logger.debug("update_container_meta: %s %s %s %s %s %s",
                     user, account, container, domain, meta, replace)
        if user != account:
            raise NotAllowedError
        path, node = self._lookup_container(account, container)
        src_version_id, dest_version_id = self._put_metadata(
            user, node, domain, meta, replace)
        if src_version_id is not None:
            versioning = self._get_policy(node)['versioning']
            if versioning != 'auto':
                self.node.version_remove(src_version_id)

    @backend_method
    def get_container_policy(self, user, account, container):
        """Return a dictionary with the container policy."""

        logger.debug(
            "get_container_policy: %s %s %s", user, account, container)
        if user != account:
            if container not in self._allowed_containers(user, account):
                raise NotAllowedError
            return {}
        path, node = self._lookup_container(account, container)
        return self._get_policy(node)

    @backend_method
    def update_container_policy(self, user, account, container, policy, replace=False):
        """Update the policy associated with the container."""

        logger.debug("update_container_policy: %s %s %s %s %s",
                     user, account, container, policy, replace)
        if user != account:
            raise NotAllowedError
        path, node = self._lookup_container(account, container)
        self._check_policy(policy)
        self._put_policy(node, policy, replace)

    @backend_method
    def put_container(self, user, account, container, policy=None):
        """Create a new container with the given name."""

        logger.debug(
            "put_container: %s %s %s %s", user, account, container, policy)
        policy = policy or {}
        if user != account:
            raise NotAllowedError
        try:
            path, node = self._lookup_container(account, container)
        except NameError:
            pass
        else:
            raise ContainerExists('Container already exists')
        if policy:
            self._check_policy(policy)
        path = '/'.join((account, container))
        node = self._put_path(
            user, self._lookup_account(account, True)[1], path)
        self._put_policy(node, policy, True)

    @backend_method
    def delete_container(self, user, account, container, until=None, prefix='', delimiter=None):
        """Delete/purge the container with the given name."""

        logger.debug("delete_container: %s %s %s %s %s %s", user,
                     account, container, until, prefix, delimiter)
        if user != account:
            raise NotAllowedError
        path, node = self._lookup_container(account, container)

        if until is not None:
            hashes, size, serials = self.node.node_purge_children(
                node, until, CLUSTER_HISTORY)
            for h in hashes:
                self.store.map_delete(h)
            self.node.node_purge_children(node, until, CLUSTER_DELETED)
            if not self.free_versioning:
                self._report_size_change(
                    user, account, -size, {
                        'action':'container purge',
                        'path': path,
                        'versions': ','.join(str(i) for i in serials)
                    }
                )
            return

        if not delimiter:
            if self._get_statistics(node)[0] > 0:
                raise ContainerNotEmpty('Container is not empty')
            hashes, size, serials = self.node.node_purge_children(
                node, inf, CLUSTER_HISTORY)
            for h in hashes:
                self.store.map_delete(h)
            self.node.node_purge_children(node, inf, CLUSTER_DELETED)
            self.node.node_remove(node)
            if not self.free_versioning:
                self._report_size_change(
                    user, account, -size, {
                        'action':'container purge',
                        'path': path,
                        'versions': ','.join(str(i) for i in serials)
                    }
                )
        else:
            # remove only contents
            src_names = self._list_objects_no_limit(user, account, container, prefix='', delimiter=None, virtual=False, domain=None, keys=[], shared=False, until=None, size_range=None, all_props=True, public=False)
            paths = []
            for t in src_names:
                path = '/'.join((account, container, t[0]))
                node = t[2]
                src_version_id, dest_version_id = self._put_version_duplicate(user, node, size=0, type='', hash=None, checksum='', cluster=CLUSTER_DELETED)
                del_size = self._apply_versioning(
                    account, container, src_version_id)
                self._report_size_change(
                        user, account, -del_size, {
                                'action': 'object delete',
                                'path': path,
                        'versions': ','.join([str(dest_version_id)])
                     }
                )
                self._report_object_change(
                    user, account, path, details={'action': 'object delete'})
                paths.append(path)
            self.permissions.access_clear_bulk(paths)

    def _list_objects(self, user, account, container, prefix, delimiter, marker, limit, virtual, domain, keys, shared, until, size_range, all_props, public):
        if user != account and until:
            raise NotAllowedError
        if shared and public:
            # get shared first
            shared = self._list_object_permissions(
                user, account, container, prefix, shared=True, public=False)
            objects = set()
            if shared:
                path, node = self._lookup_container(account, container)
                shared = self._get_formatted_paths(shared)
                objects |= set(self._list_object_properties(node, path, prefix, delimiter, marker, limit, virtual, domain, keys, until, size_range, shared, all_props))

            # get public
            objects |= set(self._list_public_object_properties(
                user, account, container, prefix, all_props))
            objects = list(objects)

            objects.sort(key=lambda x: x[0])
            start, limit = self._list_limits(
                [x[0] for x in objects], marker, limit)
            return objects[start:start + limit]
        elif public:
            objects = self._list_public_object_properties(
                user, account, container, prefix, all_props)
            start, limit = self._list_limits(
                [x[0] for x in objects], marker, limit)
            return objects[start:start + limit]

        allowed = self._list_object_permissions(
            user, account, container, prefix, shared, public)
        if shared and not allowed:
            return []
        path, node = self._lookup_container(account, container)
        allowed = self._get_formatted_paths(allowed)
        objects = self._list_object_properties(node, path, prefix, delimiter, marker, limit, virtual, domain, keys, until, size_range, allowed, all_props)
        start, limit = self._list_limits(
            [x[0] for x in objects], marker, limit)
        return objects[start:start + limit]

    def _list_public_object_properties(self, user, account, container, prefix, all_props):
        public = self._list_object_permissions(
            user, account, container, prefix, shared=False, public=True)
        paths, nodes = self._lookup_objects(public)
        path = '/'.join((account, container))
        cont_prefix = path + '/'
        paths = [x[len(cont_prefix):] for x in paths]
        props = self.node.version_lookup_bulk(nodes, all_props=all_props)
        objects = [(path,) + props for path, props in zip(paths, props)]
        return objects

    def _list_objects_no_limit(self, user, account, container, prefix, delimiter, virtual, domain, keys, shared, until, size_range, all_props, public):
        objects = []
        while True:
            marker = objects[-1] if objects else None
            limit = 10000
            l = self._list_objects(user, account, container, prefix, delimiter, marker, limit, virtual, domain, keys, shared, until, size_range, all_props, public)
            objects.extend(l)
            if not l or len(l) < limit:
                break
        return objects

    def _list_object_permissions(self, user, account, container, prefix, shared, public):
        allowed = []
        path = '/'.join((account, container, prefix)).rstrip('/')
        if user != account:
            allowed = self.permissions.access_list_paths(user, path)
            if not allowed:
                raise NotAllowedError
        else:
            allowed = set()
            if shared:
                allowed.update(self.permissions.access_list_shared(path))
            if public:
                allowed.update(
                    [x[0] for x in self.permissions.public_list(path)])
            allowed = sorted(allowed)
            if not allowed:
                return []
        return allowed

    @backend_method
    def list_objects(self, user, account, container, prefix='', delimiter=None, marker=None, limit=10000, virtual=True, domain=None, keys=None, shared=False, until=None, size_range=None, public=False):
        """Return a list of object (name, version_id) tuples existing under a container."""

        logger.debug("list_objects: %s %s %s %s %s %s %s %s %s %s %s %s %s %s", user, account, container, prefix, delimiter, marker, limit, virtual, domain, keys, shared, until, size_range, public)
        keys = keys or []
        return self._list_objects(user, account, container, prefix, delimiter, marker, limit, virtual, domain, keys, shared, until, size_range, False, public)

    @backend_method
    def list_object_meta(self, user, account, container, prefix='', delimiter=None, marker=None, limit=10000, virtual=True, domain=None, keys=None, shared=False, until=None, size_range=None, public=False):
        """Return a list of object metadata dicts existing under a container."""

        logger.debug("list_object_meta: %s %s %s %s %s %s %s %s %s %s %s %s %s %s", user, account, container, prefix, delimiter, marker, limit, virtual, domain, keys, shared, until, size_range, public)
        keys = keys or []
        props = self._list_objects(user, account, container, prefix, delimiter, marker, limit, virtual, domain, keys, shared, until, size_range, True, public)
        objects = []
        for p in props:
            if len(p) == 2:
                objects.append({'subdir': p[0]})
            else:
                objects.append({'name': p[0],
                                'bytes': p[self.SIZE + 1],
                                'type': p[self.TYPE + 1],
                                'hash': p[self.HASH + 1],
                                'version': p[self.SERIAL + 1],
                                'version_timestamp': p[self.MTIME + 1],
                                'modified': p[self.MTIME + 1] if until is None else None,
                                'modified_by': p[self.MUSER + 1],
                                'uuid': p[self.UUID + 1],
                                'checksum': p[self.CHECKSUM + 1]})
        return objects

    @backend_method
    def list_object_permissions(self, user, account, container, prefix=''):
        """Return a list of paths that enforce permissions under a container."""

        logger.debug("list_object_permissions: %s %s %s %s", user,
                     account, container, prefix)
        return self._list_object_permissions(user, account, container, prefix, True, False)

    @backend_method
    def list_object_public(self, user, account, container, prefix=''):
        """Return a dict mapping paths to public ids for objects that are public under a container."""

        logger.debug("list_object_public: %s %s %s %s", user,
                     account, container, prefix)
        public = {}
        for path, p in self.permissions.public_list('/'.join((account, container, prefix))):
            public[path] = p
        return public

    @backend_method
    def get_object_meta(self, user, account, container, name, domain, version=None, include_user_defined=True):
        """Return a dictionary with the object metadata for the domain."""

        logger.debug("get_object_meta: %s %s %s %s %s %s", user,
                     account, container, name, domain, version)
        self._can_read(user, account, container, name)
        path, node = self._lookup_object(account, container, name)
        props = self._get_version(node, version)
        if version is None:
            modified = props[self.MTIME]
        else:
            try:
                modified = self._get_version(
                    node)[self.MTIME]  # Overall last modification.
            except NameError:  # Object may be deleted.
                del_props = self.node.version_lookup(
                    node, inf, CLUSTER_DELETED)
                if del_props is None:
                    raise ItemNotExists('Object does not exist')
                modified = del_props[self.MTIME]

        meta = {}
        if include_user_defined:
            meta.update(
                dict(self.node.attribute_get(props[self.SERIAL], domain)))
        meta.update({'name': name,
                     'bytes': props[self.SIZE],
                     'type': props[self.TYPE],
                     'hash': props[self.HASH],
                     'version': props[self.SERIAL],
                     'version_timestamp': props[self.MTIME],
                     'modified': modified,
                     'modified_by': props[self.MUSER],
                     'uuid': props[self.UUID],
                     'checksum': props[self.CHECKSUM]})
        return meta

    @backend_method
    def update_object_meta(self, user, account, container, name, domain, meta, replace=False):
        """Update the metadata associated with the object for the domain and return the new version."""

        logger.debug("update_object_meta: %s %s %s %s %s %s %s",
                     user, account, container, name, domain, meta, replace)
        self._can_write(user, account, container, name)
        path, node = self._lookup_object(account, container, name)
        src_version_id, dest_version_id = self._put_metadata(
            user, node, domain, meta, replace)
        self._apply_versioning(account, container, src_version_id)
        return dest_version_id

    @backend_method
    def get_object_permissions(self, user, account, container, name):
        """Return the action allowed on the object, the path
        from which the object gets its permissions from,
        along with a dictionary containing the permissions."""

        logger.debug("get_object_permissions: %s %s %s %s", user,
                     account, container, name)
        allowed = 'write'
        permissions_path = self._get_permissions_path(account, container, name)
        if user != account:
            if self.permissions.access_check(permissions_path, self.WRITE, user):
                allowed = 'write'
            elif self.permissions.access_check(permissions_path, self.READ, user):
                allowed = 'read'
            else:
                raise NotAllowedError
        self._lookup_object(account, container, name)
        return (allowed, permissions_path, self.permissions.access_get(permissions_path))

    @backend_method
    def update_object_permissions(self, user, account, container, name, permissions):
        """Update the permissions associated with the object."""

        logger.debug("update_object_permissions: %s %s %s %s %s",
                     user, account, container, name, permissions)
        if user != account:
            raise NotAllowedError
        path = self._lookup_object(account, container, name)[0]
        self._check_permissions(path, permissions)
        self.permissions.access_set(path, permissions)
        self._report_sharing_change(user, account, path, {'members':
                                    self.permissions.access_members(path)})

    @backend_method
    def get_object_public(self, user, account, container, name):
        """Return the public id of the object if applicable."""

        logger.debug(
            "get_object_public: %s %s %s %s", user, account, container, name)
        self._can_read(user, account, container, name)
        path = self._lookup_object(account, container, name)[0]
        p = self.permissions.public_get(path)
        return p

    @backend_method
    def update_object_public(self, user, account, container, name, public):
        """Update the public status of the object."""

        logger.debug("update_object_public: %s %s %s %s %s", user,
                     account, container, name, public)
        self._can_write(user, account, container, name)
        path = self._lookup_object(account, container, name)[0]
        if not public:
            self.permissions.public_unset(path)
        else:
            self.permissions.public_set(
                path, self.public_url_security, self.public_url_alphabet
            )

    @backend_method
    def get_object_hashmap(self, user, account, container, name, version=None):
        """Return the object's size and a list with partial hashes."""

        logger.debug("get_object_hashmap: %s %s %s %s %s", user,
                     account, container, name, version)
        self._can_read(user, account, container, name)
        path, node = self._lookup_object(account, container, name)
        props = self._get_version(node, version)
        hashmap = self.store.map_get(binascii.unhexlify(props[self.HASH]))
        return props[self.SIZE], [binascii.hexlify(x) for x in hashmap]

    def _update_object_hash(self, user, account, container, name, size, type, hash, checksum, domain, meta, replace_meta, permissions, src_node=None, src_version_id=None, is_copy=False):
        if permissions is not None and user != account:
            raise NotAllowedError
        self._can_write(user, account, container, name)
        if permissions is not None:
            path = '/'.join((account, container, name))
            self._check_permissions(path, permissions)

        account_path, account_node = self._lookup_account(account, True)
        container_path, container_node = self._lookup_container(
            account, container)
        path, node = self._put_object_node(
            container_path, container_node, name)
        pre_version_id, dest_version_id = self._put_version_duplicate(user, node, src_node=src_node, size=size, type=type, hash=hash, checksum=checksum, is_copy=is_copy)

        # Handle meta.
        if src_version_id is None:
            src_version_id = pre_version_id
        self._put_metadata_duplicate(
            src_version_id, dest_version_id, domain, meta, replace_meta)

        del_size = self._apply_versioning(account, container, pre_version_id)
        size_delta = size - del_size
        if not self.using_external_quotaholder: # Check account quota.
            if size_delta > 0:
                account_quota = long(self._get_policy(account_node)['quota'])
                account_usage = self._get_statistics(account_node)[1] + size_delta
                if (account_quota > 0 and account_usage > account_quota):
                    raise QuotaError('account quota exceeded: limit: %s, usage: %s' % (
                        account_quota, account_usage
                    ))

        # Check container quota.
        container_quota = long(self._get_policy(container_node)['quota'])
        container_usage = self._get_statistics(container_node)[1] + size_delta
        if (container_quota > 0 and container_usage > container_quota):
            # This must be executed in a transaction, so the version is
            # never created if it fails.
            raise QuotaError('container quota exceeded: limit: %s, usage: %s' % (
                container_quota, container_usage
            ))

        self._report_size_change(user, account, size_delta,
                                 {'action': 'object update', 'path': path,
                                  'versions': ','.join([str(dest_version_id)])})
        if permissions is not None:
            self.permissions.access_set(path, permissions)
            self._report_sharing_change(user, account, path, {'members': self.permissions.access_members(path)})

        self._report_object_change(user, account, path, details={'version': dest_version_id, 'action': 'object update'})
        return dest_version_id

    @backend_method
    def update_object_hashmap(self, user, account, container, name, size, type, hashmap, checksum, domain, meta=None, replace_meta=False, permissions=None):
        """Create/update an object with the specified size and partial hashes."""

        logger.debug("update_object_hashmap: %s %s %s %s %s %s %s %s", user,
                     account, container, name, size, type, hashmap, checksum)
        meta = meta or {}
        if size == 0:  # No such thing as an empty hashmap.
            hashmap = [self.put_block('')]
        map = HashMap(self.block_size, self.hash_algorithm)
        map.extend([binascii.unhexlify(x) for x in hashmap])
        missing = self.store.block_search(map)
        if missing:
            ie = IndexError()
            ie.data = [binascii.hexlify(x) for x in missing]
            raise ie

        hash = map.hash()
        dest_version_id = self._update_object_hash(user, account, container, name, size, type, binascii.hexlify(hash), checksum, domain, meta, replace_meta, permissions)
        self.store.map_put(hash, map)
        return dest_version_id

    @backend_method
    def update_object_checksum(self, user, account, container, name, version, checksum):
        """Update an object's checksum."""

        logger.debug("update_object_checksum: %s %s %s %s %s %s",
                     user, account, container, name, version, checksum)
        # Update objects with greater version and same hashmap and size (fix metadata updates).
        self._can_write(user, account, container, name)
        path, node = self._lookup_object(account, container, name)
        props = self._get_version(node, version)
        versions = self.node.node_get_versions(node)
        for x in versions:
            if x[self.SERIAL] >= int(version) and x[self.HASH] == props[self.HASH] and x[self.SIZE] == props[self.SIZE]:
                self.node.version_put_property(
                    x[self.SERIAL], 'checksum', checksum)

    def _copy_object(self, user, src_account, src_container, src_name, dest_account, dest_container, dest_name, type, dest_domain=None, dest_meta=None, replace_meta=False, permissions=None, src_version=None, is_move=False, delimiter=None):
        dest_meta = dest_meta or {}
        dest_version_ids = []
        self._can_read(user, src_account, src_container, src_name)
        path, node = self._lookup_object(src_account, src_container, src_name)
        # TODO: Will do another fetch of the properties in duplicate version...
        props = self._get_version(
            node, src_version)  # Check to see if source exists.
        src_version_id = props[self.SERIAL]
        hash = props[self.HASH]
        size = props[self.SIZE]
        is_copy = not is_move and (src_account, src_container, src_name) != (
            dest_account, dest_container, dest_name)  # New uuid.
        dest_version_ids.append(self._update_object_hash(user, dest_account, dest_container, dest_name, size, type, hash, None, dest_domain, dest_meta, replace_meta, permissions, src_node=node, src_version_id=src_version_id, is_copy=is_copy))
        if is_move and (src_account, src_container, src_name) != (dest_account, dest_container, dest_name):
            self._delete_object(user, src_account, src_container, src_name)

        if delimiter:
            prefix = src_name + \
                delimiter if not src_name.endswith(delimiter) else src_name
            src_names = self._list_objects_no_limit(user, src_account, src_container, prefix, delimiter=None, virtual=False, domain=None, keys=[], shared=False, until=None, size_range=None, all_props=True, public=False)
            src_names.sort(key=lambda x: x[2])  # order by nodes
            paths = [elem[0] for elem in src_names]
            nodes = [elem[2] for elem in src_names]
            # TODO: Will do another fetch of the properties in duplicate version...
            props = self._get_versions(nodes)  # Check to see if source exists.

            for prop, path, node in zip(props, paths, nodes):
                src_version_id = prop[self.SERIAL]
                hash = prop[self.HASH]
                vtype = prop[self.TYPE]
                size = prop[self.SIZE]
                dest_prefix = dest_name + delimiter if not dest_name.endswith(
                    delimiter) else dest_name
                vdest_name = path.replace(prefix, dest_prefix, 1)
                dest_version_ids.append(self._update_object_hash(user, dest_account, dest_container, vdest_name, size, vtype, hash, None, dest_domain, meta={}, replace_meta=False, permissions=None, src_node=node, src_version_id=src_version_id, is_copy=is_copy))
                if is_move and (src_account, src_container, src_name) != (dest_account, dest_container, dest_name):
                    self._delete_object(user, src_account, src_container, path)
        return dest_version_ids[0] if len(dest_version_ids) == 1 else dest_version_ids

    @backend_method
    def copy_object(self, user, src_account, src_container, src_name, dest_account, dest_container, dest_name, type, domain, meta=None, replace_meta=False, permissions=None, src_version=None, delimiter=None):
        """Copy an object's data and metadata."""

        logger.debug("copy_object: %s %s %s %s %s %s %s %s %s %s %s %s %s %s", user, src_account, src_container, src_name, dest_account, dest_container, dest_name, type, domain, meta, replace_meta, permissions, src_version, delimiter)
        meta = meta or {}
        dest_version_id = self._copy_object(user, src_account, src_container, src_name, dest_account, dest_container, dest_name, type, domain, meta, replace_meta, permissions, src_version, False, delimiter)
        return dest_version_id

    @backend_method
    def move_object(self, user, src_account, src_container, src_name, dest_account, dest_container, dest_name, type, domain, meta=None, replace_meta=False, permissions=None, delimiter=None):
        """Move an object's data and metadata."""

        logger.debug("move_object: %s %s %s %s %s %s %s %s %s %s %s %s %s", user, src_account, src_container, src_name, dest_account, dest_container, dest_name, type, domain, meta, replace_meta, permissions, delimiter)
        meta = meta or {}
        if user != src_account:
            raise NotAllowedError
        dest_version_id = self._copy_object(user, src_account, src_container, src_name, dest_account, dest_container, dest_name, type, domain, meta, replace_meta, permissions, None, True, delimiter)
        return dest_version_id

    def _delete_object(self, user, account, container, name, until=None, delimiter=None):
        if user != account:
            raise NotAllowedError

        if until is not None:
            path = '/'.join((account, container, name))
            node = self.node.node_lookup(path)
            if node is None:
                return
            hashes = []
            size = 0
            serials = []
            h, s, v = self.node.node_purge(node, until, CLUSTER_NORMAL)
            hashes += h
            size += s
            serials += v
            h, s, v = self.node.node_purge(node, until, CLUSTER_HISTORY)
            hashes += h
            if not self.free_versioning:
                size += s
            serials += v
            for h in hashes:
                self.store.map_delete(h)
            self.node.node_purge(node, until, CLUSTER_DELETED)
            try:
                props = self._get_version(node)
            except NameError:
                self.permissions.access_clear(path)
            self._report_size_change(
                user, account, -size, {
                    'action': 'object purge',
                    'path': path,
                    'versions': ','.join(str(i) for i in serials)
                }
            )
            return

        path, node = self._lookup_object(account, container, name)
        src_version_id, dest_version_id = self._put_version_duplicate(user, node, size=0, type='', hash=None, checksum='', cluster=CLUSTER_DELETED)
        del_size = self._apply_versioning(account, container, src_version_id)
        self._report_size_change(user, account, -del_size,
                                 {'action': 'object delete', 'path': path,
                                  'versions': ','.join([str(dest_version_id)])})
        self._report_object_change(
            user, account, path, details={'action': 'object delete'})
        self.permissions.access_clear(path)

        if delimiter:
            prefix = name + delimiter if not name.endswith(delimiter) else name
            src_names = self._list_objects_no_limit(user, account, container, prefix, delimiter=None, virtual=False, domain=None, keys=[], shared=False, until=None, size_range=None, all_props=True, public=False)
            paths = []
            for t in src_names:
                path = '/'.join((account, container, t[0]))
                node = t[2]
                src_version_id, dest_version_id = self._put_version_duplicate(user, node, size=0, type='', hash=None, checksum='', cluster=CLUSTER_DELETED)
                del_size = self._apply_versioning(
                    account, container, src_version_id)
                self._report_size_change(user, account, -del_size,
                                         {'action': 'object delete',
                                          'path': path,
                                          'versions': ','.join([str(dest_version_id)])})
                self._report_object_change(
                    user, account, path, details={'action': 'object delete'})
                paths.append(path)
            self.permissions.access_clear_bulk(paths)

    @backend_method
    def delete_object(self, user, account, container, name, until=None, prefix='', delimiter=None):
        """Delete/purge an object."""

        logger.debug("delete_object: %s %s %s %s %s %s %s", user,
                     account, container, name, until, prefix, delimiter)
        self._delete_object(user, account, container, name, until, delimiter)

    @backend_method
    def list_versions(self, user, account, container, name):
        """Return a list of all (version, version_timestamp) tuples for an object."""

        logger.debug(
            "list_versions: %s %s %s %s", user, account, container, name)
        self._can_read(user, account, container, name)
        path, node = self._lookup_object(account, container, name)
        versions = self.node.node_get_versions(node)
        return [[x[self.SERIAL], x[self.MTIME]] for x in versions if x[self.CLUSTER] != CLUSTER_DELETED]

    @backend_method
    def get_uuid(self, user, uuid):
        """Return the (account, container, name) for the UUID given."""

        logger.debug("get_uuid: %s %s", user, uuid)
        info = self.node.latest_uuid(uuid, CLUSTER_NORMAL)
        if info is None:
            raise NameError
        path, serial = info
        account, container, name = path.split('/', 2)
        self._can_read(user, account, container, name)
        return (account, container, name)

    @backend_method
    def get_public(self, user, public):
        """Return the (account, container, name) for the public id given."""

        logger.debug("get_public: %s %s", user, public)
        path = self.permissions.public_path(public)
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
            raise ItemNotExists('Block does not exist')
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
        self.node.version_create(node, None, 0, '', None, user,
                                 self._generate_uuid(), '', CLUSTER_NORMAL)
        return node

    def _lookup_account(self, account, create=True):
        node = self.node.node_lookup(account)
        if node is None and create:
            node = self._put_path(
                account, self.ROOTNODE, account)  # User is account.
        return account, node

    def _lookup_container(self, account, container):
        path = '/'.join((account, container))
        node = self.node.node_lookup(path)
        if node is None:
            raise ItemNotExists('Container does not exist')
        return path, node

    def _lookup_object(self, account, container, name):
        path = '/'.join((account, container, name))
        node = self.node.node_lookup(path)
        if node is None:
            raise ItemNotExists('Object does not exist')
        return path, node

    def _lookup_objects(self, paths):
        nodes = self.node.node_lookup_bulk(paths)
        return paths, nodes

    def _get_properties(self, node, until=None):
        """Return properties until the timestamp given."""

        before = until if until is not None else inf
        props = self.node.version_lookup(node, before, CLUSTER_NORMAL)
        if props is None and until is not None:
            props = self.node.version_lookup(node, before, CLUSTER_HISTORY)
        if props is None:
            raise ItemNotExists('Path does not exist')
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
                raise ItemNotExists('Object does not exist')
        else:
            try:
                version = int(version)
            except ValueError:
                raise VersionNotExists('Version does not exist')
            props = self.node.version_get_properties(version)
            if props is None or props[self.CLUSTER] == CLUSTER_DELETED:
                raise VersionNotExists('Version does not exist')
        return props

    def _get_versions(self, nodes):
        return self.node.version_lookup_bulk(nodes, inf, CLUSTER_NORMAL)

    def _put_version_duplicate(self, user, node, src_node=None, size=None, type=None, hash=None, checksum=None, cluster=CLUSTER_NORMAL, is_copy=False):
        """Create a new version of the node."""

        props = self.node.version_lookup(
            node if src_node is None else src_node, inf, CLUSTER_NORMAL)
        if props is not None:
            src_version_id = props[self.SERIAL]
            src_hash = props[self.HASH]
            src_size = props[self.SIZE]
            src_type = props[self.TYPE]
            src_checksum = props[self.CHECKSUM]
        else:
            src_version_id = None
            src_hash = None
            src_size = 0
            src_type = ''
            src_checksum = ''
        if size is None:  # Set metadata.
            hash = src_hash  # This way hash can be set to None (account or container).
            size = src_size
        if type is None:
            type = src_type
        if checksum is None:
            checksum = src_checksum
        uuid = self._generate_uuid(
        ) if (is_copy or src_version_id is None) else props[self.UUID]

        if src_node is None:
            pre_version_id = src_version_id
        else:
            pre_version_id = None
            props = self.node.version_lookup(node, inf, CLUSTER_NORMAL)
            if props is not None:
                pre_version_id = props[self.SERIAL]
        if pre_version_id is not None:
            self.node.version_recluster(pre_version_id, CLUSTER_HISTORY)

        dest_version_id, mtime = self.node.version_create(node, hash, size, type, src_version_id, user, uuid, checksum, cluster)
        return pre_version_id, dest_version_id

    def _put_metadata_duplicate(self, src_version_id, dest_version_id, domain, meta, replace=False):
        if src_version_id is not None:
            self.node.attribute_copy(src_version_id, dest_version_id)
        if not replace:
            self.node.attribute_del(dest_version_id, domain, (
                k for k, v in meta.iteritems() if v == ''))
            self.node.attribute_set(dest_version_id, domain, (
                (k, v) for k, v in meta.iteritems() if v != ''))
        else:
            self.node.attribute_del(dest_version_id, domain)
            self.node.attribute_set(dest_version_id, domain, ((
                k, v) for k, v in meta.iteritems()))

    def _put_metadata(self, user, node, domain, meta, replace=False):
        """Create a new version and store metadata."""

        src_version_id, dest_version_id = self._put_version_duplicate(
            user, node)
        self._put_metadata_duplicate(
            src_version_id, dest_version_id, domain, meta, replace)
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

    def _list_object_properties(self, parent, path, prefix='', delimiter=None, marker=None, limit=10000, virtual=True, domain=None, keys=None, until=None, size_range=None, allowed=None, all_props=False):
        keys = keys or []
        allowed = allowed or []
        cont_prefix = path + '/'
        prefix = cont_prefix + prefix
        start = cont_prefix + marker if marker else None
        before = until if until is not None else inf
        filterq = keys if domain else []
        sizeq = size_range

        objects, prefixes = self.node.latest_version_list(parent, prefix, delimiter, start, limit, before, CLUSTER_DELETED, allowed, domain, filterq, sizeq, all_props)
        objects.extend([(p, None) for p in prefixes] if virtual else [])
        objects.sort(key=lambda x: x[0])
        objects = [(x[0][len(cont_prefix):],) + x[1:] for x in objects]
        return objects

    # Reporting functions.

    def _report_size_change(self, user, account, size, details=None):
        details = details or {}

        if size == 0:
            return

        account_node = self._lookup_account(account, True)[1]
        total = self._get_statistics(account_node)[1]
        details.update({'user': user, 'total': total})
        logger.debug(
            "_report_size_change: %s %s %s %s", user, account, size, details)
        self.messages.append((QUEUE_MESSAGE_KEY_PREFIX % ('resource.diskspace',),
                              account, QUEUE_INSTANCE_ID, 'diskspace',
                              float(size), details))

        if not self.using_external_quotaholder:
            return

        try:
            serial = self.quotaholder.issue_commission(
                    context     =   {},
                    target      =   account,
                    key         =   '1',
                    clientkey   =   'pithos',
                    ownerkey    =   '',
                    name        =   details['path'] if 'path' in details else '',
                    provisions  =   (('pithos+', 'pithos+.diskspace', size),)
            )
        except BaseException, e:
            raise QuotaError(e)
        else:
            self.serials.append(serial)

    def _report_object_change(self, user, account, path, details=None):
        details = details or {}
        details.update({'user': user})
        logger.debug("_report_object_change: %s %s %s %s", user,
                     account, path, details)
        self.messages.append((QUEUE_MESSAGE_KEY_PREFIX % ('object',),
                              account, QUEUE_INSTANCE_ID, 'object', path, details))

    def _report_sharing_change(self, user, account, path, details=None):
        logger.debug("_report_permissions_change: %s %s %s %s",
                     user, account, path, details)
        details = details or {}
        details.update({'user': user})
        self.messages.append((QUEUE_MESSAGE_KEY_PREFIX % ('sharing',),
                              account, QUEUE_INSTANCE_ID, 'sharing', path, details))

    # Policy functions.

    def _check_policy(self, policy):
        for k in policy.keys():
            if policy[k] == '':
                policy[k] = self.default_policy.get(k)
        for k, v in policy.iteritems():
            if k == 'quota':
                q = int(v)  # May raise ValueError.
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
        elif self.free_versioning:
            return self.node.version_get_properties(
                version_id, keys=('size',))[0]
        return 0

    # Access control functions.

    def _check_groups(self, groups):
        # raise ValueError('Bad characters in groups')
        pass

    def _check_permissions(self, path, permissions):
        # raise ValueError('Bad characters in permissions')
        pass

    def _get_formatted_paths(self, paths):
        formatted = []
        for p in paths:
            node = self.node.node_lookup(p)
            props = None
            if node is not None:
                props = self.node.version_lookup(node, inf, CLUSTER_NORMAL)
            if props is not None:
                if props[self.TYPE].split(';', 1)[0].strip() in ('application/directory', 'application/folder'):
                    formatted.append((p.rstrip('/') + '/', self.MATCH_PREFIX))
                formatted.append((p, self.MATCH_EXACT))
        return formatted

    def _get_permissions_path(self, account, container, name):
        path = '/'.join((account, container, name))
        permission_paths = self.permissions.access_inherit(path)
        permission_paths.sort()
        permission_paths.reverse()
        for p in permission_paths:
            if p == path:
                return p
            else:
                if p.count('/') < 2:
                    continue
                node = self.node.node_lookup(p)
                props = None
                if node is not None:
                    props = self.node.version_lookup(node, inf, CLUSTER_NORMAL)
                if props is not None:
                    if props[self.TYPE].split(';', 1)[0].strip() in ('application/directory', 'application/folder'):
                        return p
        return None

    def _can_read(self, user, account, container, name):
        if user == account:
            return True
        path = '/'.join((account, container, name))
        if self.permissions.public_get(path) is not None:
            return True
        path = self._get_permissions_path(account, container, name)
        if not path:
            raise NotAllowedError
        if not self.permissions.access_check(path, self.READ, user) and not self.permissions.access_check(path, self.WRITE, user):
            raise NotAllowedError

    def _can_write(self, user, account, container, name):
        if user == account:
            return True
        path = '/'.join((account, container, name))
        path = self._get_permissions_path(account, container, name)
        if not path:
            raise NotAllowedError
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
