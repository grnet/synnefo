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

"""
Plankton attributes are divided in 3 categories:
  - generated: They are dynamically generated and not stored anywhere.
  - user: Stored as user accessible metadata and can be modified from within
            Pithos apps. They are visible as prefixed with PLANKTON_PREFIX.
  - system: Stored as metadata but can not be modified though Pithos.

In more detail, Plankton attributes are the following:
  - checksum: generated based on the merkle hash of the file
  - container_format: stored as a user meta
  - created_at: generated based on the modified attribute of the first version
  - deleted_at: generated based on the timestamp of the last version
  - disk_format: stored as a user meta
  - id: generated based on location and stored as system meta
  - is_public: True if there is a * entry for the read permission
  - location: generated based on the object's path
  - name: stored as a user meta
  - owner: identical to the object's account
  - properties: stored as user meta prefixed with PROPERTY_PREFIX
  - size: generated based from 'bytes' value
  - status: stored as a system meta
  - store: is always 'pithos'
  - updated_at: generated based on the modified attribute
"""

import json
import warnings

from binascii import hexlify
from functools import partial
from hashlib import md5
from operator import itemgetter
from time import gmtime, strftime, time
from uuid import UUID

from django.conf import settings

from pithos.backends import connect_backend
from pithos.backends.base import NotAllowedError


PLANKTON_PREFIX = 'plankton:'
PROPERTY_PREFIX = 'property:'

SYSTEM_META = set(['id', 'status'])
USER_META = set(['name', 'container_format', 'disk_format'])


def prefix_keys(keys):
    prefixed = []
    for key in keys:
        if key in SYSTEM_META:
            key = PLANKTON_PREFIX + key
        elif key in USER_META:
            key = 'X-Object-Meta-' + PLANKTON_PREFIX + key
        else:
            assert False, "Invalid filter key"
        prefixed.append(key)
    return prefixed

def prefix_meta(meta):
    prefixed = {}
    for key, val in meta.items():
        key = key.lower()
        if key in SYSTEM_META:
            key = PLANKTON_PREFIX + key
        elif key in USER_META:
            key = 'X-Object-Meta-' + PLANKTON_PREFIX + key
        elif key == 'properties':
            for k, v in val.items():
                k = k.lower()
                k = 'X-Object-Meta-' + PLANKTON_PREFIX + PROPERTY_PREFIX + k
                prefixed[k] = v
            continue
        else:
            assert False, "Invalid metadata key"
        prefixed[key] = val
    return prefixed


def get_image_id(location):
    return str(UUID(bytes=md5(location).digest()))


def get_location(account, container, object):
    assert '/' not in account, "Invalid account"
    assert '/' not in container, "Invalid container"
    return 'pithos://%s/%s/%s' % (account, container, object)

def split_location(location):
    """Returns (accout, container, object) from a location string"""
    t = location.split('/', 4)
    assert len(t) == 5, "Invalid location"
    return t[2:5]


class BackendException(Exception): pass


class ImageBackend(object):
    """A wrapper arround the pithos backend to simplify image handling."""
    
    def __init__(self, user):
        self.user = user
        self.container = settings.PITHOS_IMAGE_CONTAINER
        
        original_filters = warnings.filters
        warnings.simplefilter('ignore')         # Suppress SQLAlchemy warnings
        self.backend = connect_backend()
        warnings.filters = original_filters     # Restore warnings
        
        try:
            self.backend.put_container(self.user, self.user, self.container)
        except NameError:
            pass    # Container already exists
    
    def _get_image(self, location):
        def format_timestamp(t):
            return strftime('%Y-%m-%d %H:%M:%S', gmtime(t))
        
        account, container, object = split_location(location)
        
        try:
            versions = self.backend.list_versions(self.user, account,
                    container, object)
        except NameError:
            return None
        
        image = {}
        
        meta = self._get_meta(location)
        if meta:
            image['deleted_at'] = ''
        else:
            # Object was deleted, use the latest version
            version, timestamp = versions[-1]
            meta = self._get_meta(location, version)
            image['deleted_at'] = format_timestamp(timestamp)
        
        permissions = self._get_permissions(location)
        
        image['checksum'] = meta['_hash']
        image['created_at'] = format_timestamp(versions[0][1])
        image['is_public'] = '*' in permissions.get('read', [])
        image['location'] = location
        image['owner'] = account
        image['size'] = meta['_bytes']
        image['store'] = 'pithos'
        image['updated_at'] = format_timestamp(meta['_modified'])
        image['properties'] = {}
        
        for key, val in meta.items():
            if key in SYSTEM_META | USER_META:
                image[key] = val
            elif key.startswith(PROPERTY_PREFIX):
                key = key[len(PROPERTY_PREFIX):]
                image['properties'][key] = val
        
        if 'id' in image:
            return image
        else:
            return None
    
    def _get_meta(self, location, version=None, user=None):
        user = user or self.user
        account, container, object = split_location(location)
        try:
            _meta = self.backend.get_object_meta(user, account, container,
                    object, version)
        except NameError:
            return None
        
        user_prefix = 'x-object-meta-' + PLANKTON_PREFIX
        system_prefix = PLANKTON_PREFIX
        meta = {}
        
        for key, val in _meta.items():
            key = key.lower()
            if key.startswith(user_prefix):
                key = key[len(user_prefix):]
            elif key.startswith(system_prefix):
                key = key[len(system_prefix):]
            else:
                key = '_' + key
            meta[key] = val
        
        return meta
    
    def _get_permissions(self, location):
        account, container, object = split_location(location)
        action, path, permissions = self.backend.get_object_permissions(
                self.user, account, container, object)
        return permissions
    
    def _iter(self, keys=[], public=False):
        backend = self.backend
        container = self.container
        user = None if public else self.user
        
        accounts = set(backend.list_accounts(user))
        if user:
            accounts.add(user)
        
        for account in accounts:
            for path, version_id in backend.list_objects(user, account,
                    container, prefix='', delimiter='/',
                    keys=prefix_keys(keys)):
                try:
                    location = get_location(account, container, path)
                    image = self._get_image(location)
                    if image:
                        yield image
                except NotAllowedError:
                    continue
    
    def _store(self, f, size=None):
        """Breaks data into blocks and stores them in the backend"""
        
        bytes = 0
        hashmap = []
        backend = self.backend
        blocksize = backend.block_size
        
        data = f.read(blocksize)
        while data:
            hash = backend.put_block(data)
            hashmap.append(hash)
            bytes += len(data)
            data = f.read(blocksize)
        
        if size and size != bytes:
            raise BackendException("Invalid size")
        
        return hashmap, bytes
    
    def _update(self, location, size, hashmap, meta, permissions):
        account, container, object = split_location(location)
        self.backend.update_object_hashmap(self.user, account, container,
                object, size, hashmap, meta=prefix_meta(meta),
                replace_meta=True, permissions=permissions)
    
    def _update_meta(self, location, meta):
        account, container, object = split_location(location)
        self.backend.update_object_meta(self.user, account, container, object,
                prefix_meta(meta))
    
    def _update_permissions(self, location, permissions):
        account, container, object = split_location(location)
        self.backend.update_object_permissions(self.user, account, container,
                object, permissions)
    
    def add_user(self, image_id, user):
        image = self.get_meta(image_id)
        assert image, "Image not found"
        
        location = image['location']
        permissions = self._get_permissions(location)
        read = set(permissions.get('read', []))
        read.add(user)
        permissions['read'] = list(read)
        self._update_permissions(location, permissions)
    
    def close(self):
        self.backend.close()
    
    def get_data(self, location):
        account, container, object = split_location(location)
        size, hashmap = self.backend.get_object_hashmap(self.user, account,
                container, object)
        data = ''.join(self.backend.get_block(hash) for hash in hashmap)
        assert len(data) == size
        return data
    
    def get_meta(self, image_id):
        # This is an inefficient implementation.
        # Due to limitations of the backend we have to iterate all files
        # in order to find the one with specific id.
        for image in self._iter(keys=['id']):
            if image and image['id'] == image_id:
                return image
        return None
    
    def iter_public(self, filters):
        keys = set()
        for key, val in filters.items():
            if key in ('size_min', 'size_max'):
                key = 'size'
            keys.add(key)
        
        for image in self._iter(keys=keys, public=True):
            for key, val in filters.items():
                if key == 'size_min':
                    if image['size'] < int(val):
                        break
                elif key == 'size_max':
                    if image['size'] > int(val):
                        break
                else:
                    if image[key] != val:
                        break
            else:
                yield image
    
    def iter_shared(self, member):
        """Iterate over image ids shared to this member"""
        
        # To get the list we connect as member and get the list shared by us
        user = member
        account = self.user
        container = self.container
        
        for path, version_id in self.backend.list_objects(member, account,
                container, prefix='', delimiter='/'):
            try:
                location = get_location(account, container, path)
                meta = self._get_meta(location, user=user)
                if 'id' in meta:
                    yield meta['id']
            except NotAllowedError:
                continue
    
    def list_public(self, filters, params):
        images = list(self.iter_public(filters))
        key = itemgetter(params.get('sort_key', 'created_at'))
        reverse = params.get('sort_dir', 'desc') == 'desc'
        images.sort(key=key, reverse=reverse)
        return images
    
    def list_users(self, image_id):
        image = self.get_meta(image_id)
        assert image, "Image not found"
        
        permissions = self._get_permissions(image['location'])
        return [user for user in permissions.get('read', []) if user != '*']
    
    def put(self, name, f, params):
        assert 'checksum' not in params, "Passing a checksum is not supported"
        assert 'id' not in params, "Passing an ID is not supported"
        assert params.pop('store', 'pithos') == 'pithos', "Invalid store"
        assert params.setdefault('disk_format',
                settings.DEFAULT_DISK_FORMAT) in \
                settings.ALLOWED_DISK_FORMATS, "Invalid disk_format"
        assert params.setdefault('container_format',
                settings.DEFAULT_CONTAINER_FORMAT) in \
                settings.ALLOWED_CONTAINER_FORMATS, "Invalid container_format"
        
        filename = params.pop('filename', name)
        location = 'pithos://%s/%s/%s' % (self.user, self.container, filename)
        image_id = get_image_id(location)
        is_public = params.pop('is_public', False)
        permissions = {'read': ['*']} if is_public else {}
        size = params.pop('size', None)
        
        hashmap, size = self._store(f, size)
        
        meta = {}
        meta['properties'] = params.pop('properties', {})
        meta.update(id=image_id, name=name, status='available', **params)
        
        self._update(location, size, hashmap, meta, permissions)
        return self.get_meta(image_id)
    
    def register(self, name, location, params):
        assert 'id' not in params, "Passing an ID is not supported"
        assert location.startswith('pithos://'), "Invalid location"
        assert params.pop('store', 'pithos') == 'pithos', "Invalid store"
        assert params.setdefault('disk_format',
                settings.DEFAULT_DISK_FORMAT) in \
                settings.ALLOWED_DISK_FORMATS, "Invalid disk_format"
        assert params.setdefault('container_format',
                settings.DEFAULT_CONTAINER_FORMAT) in \
                settings.ALLOWED_CONTAINER_FORMATS, "Invalid container_format"
        
        user = self.user
        account, container, object = split_location(location)
        image_id = get_image_id(location)
        
        meta = self._get_meta(location)
        assert meta, "File not found"
        
        size = params.pop('size', meta['_bytes'])
        if size != meta['_bytes']:
            raise BackendException("Invalid size")
        
        checksum = params.pop('checksum', meta['_hash'])
        if checksum != meta['_hash']:
            raise BackendException("Invalid checksum")
        
        is_public = params.pop('is_public', False)
        permissions = {'read': ['*']} if is_public else {}
        
        meta = {}
        meta['properties'] = params.pop('properties', {})
        meta.update(id=image_id, name=name, status='available', **params)
        
        self._update_meta(location, meta)
        self._update_permissions(location, permissions)
        return self.get_meta(image_id)
    
    def remove_user(self, image_id, user):
        image = self.get_meta(image_id)
        assert image, "Image not found"
        
        location = image['location']
        permissions = self._get_permissions(location)
        try:
            permissions.get('read', []).remove(user)
        except ValueError:
            return      # User did not have access anyway
        self._update_permissions(location, permissions)
    
    def replace_users(self, image_id, users):
        image = self.get_meta(image_id)
        assert image, "Image not found"
        
        location = image['location']
        permissions = self._get_permissions(location)
        permissions['read'] = users
        if image.get('is_public', False):
            permissions['read'].append('*')
        self._update_permissions(location, permissions)
    
    def update(self, image_id, params):
        image = self.get_meta(image_id)
        assert image, "Image not found"
        
        location = image['location']
        is_public = params.pop('is_public', None)
        if is_public is not None:
            permissions = self._get_permissions(location)
            read = set(permissions.get('read', []))
            if is_public:
                read.add('*')
            else:
                read.discard('*')
            permissions['read'] = list(read)
            self.backend._update_permissions(location, permissions)
        
        meta = {}
        meta['properties'] = params.pop('properties', {})
        meta.update(**params)
        
        self._update_meta(location, meta)
        return self.get_meta(image_id)
