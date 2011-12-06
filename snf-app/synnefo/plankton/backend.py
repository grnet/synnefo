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
Plankton attributes are stored as user metadata in Pithos, prefixed with
PLANKTON_PREFIX.
Exceptions are the following:
  - location: generated based on the object's path
  - updated_at: generated based on the modified attribute
  - created_at: generated based on the modified attribute of the first version
  - owner: identical to the object's account
  - is_public: True if there is a * entry for the read permission

All Plankton properties are JSON serialized and stored as one user meta.
"""

import json

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


def set_plankton_attr(d, **kwargs):
    for key, val in kwargs.items():
        d[PLANKTON_PREFIX + key] = str(val) if val is not None else ''

def get_image_id(location):
    return str(UUID(bytes=md5(location).digest()))


class BackendException(Exception): pass


class ImageBackend(object):
    """A wrapper arround the pithos backend to simplify image handling."""
    
    def __init__(self, user):
        self.user = user
        self.container = settings.PITHOS_IMAGE_CONTAINER
        self.backend = connect_backend()
        try:
            self.backend.put_container(self.user, self.user, self.container)
        except NameError:
            pass    # Container already exists
    
    def _get(self, user, account, container, object):
        def format_timestamp(t):
            return strftime('%Y-%m-%d %H:%M:%S', gmtime(t))

        meta = self.backend.get_object_meta(user, account, container, object)
        image = {
            '_account': account,
            '_container': container,
            '_object': object}
        
        for key in ('id', 'status', 'name', 'disk_format', 'container_format',
                    'size', 'checksum', 'deleted_at'):
            val = meta.get(PLANKTON_PREFIX + key, None)
            if val is not None:
                image[key] = val

        image['location'] = 'pithos://%s/%s/%s' % (account, container, object)
        image['updated_at'] = format_timestamp(meta['modified'])
        image['owner'] = account

        # Get the creation date from the date of the first version
        version, created = self.backend.list_versions(user, account, container,
                                                      name=object)[0]
        image['created_at'] = format_timestamp(created)
        
        # Mark as public if there is a * entry for read
        permissions = self._get_permissions(image)
        image['is_public'] = '*' in permissions.get('read', [])
        
        properties = meta.get(PLANKTON_PREFIX + 'properties', None)
        if properties:
            image['properties'] = json.loads(properties)

        return image
    
    def _get_permissions(self, image):
        action, path, permissions = self.backend.get_object_permissions(
                user=self.user,
                account=image['_account'],
                container=image['_container'],
                name=image['_object'])
        return permissions
    
    def _iter(self, keys=[], public=False):
        backend = self.backend
        container = self.container
        user = None if public else self.user
        keys = [PLANKTON_PREFIX + key for key in keys]
        
        for account in backend.list_accounts(user):
            for path, version_id in backend.list_objects(user, account,
                    container, prefix='', delimiter='/', keys=keys):
                try:
                    image = self._get(user, account, container, path)
                    if 'id' in image:
                        yield image
                except NotAllowedError:
                    continue
    
    def _store(self, data):
        """Breaks data into blocks and stores them in the backend.
        
        Returns a tuple of the hashmap and the MD5 checksum
        """
        
        def iterblock(data, block_size):
            while data:
                yield data[:block_size]
                data = data[block_size:]
        
        m = md5()
        hashmap = []
        
        for block in iterblock(data, self.backend.block_size):
            hash = self.backend.put_block(block)
            hashmap.append(hash)
            m.update(block)
        
        return hashmap, m.digest()
    
    def _update_permissions(self, image, permissions):
        self.backend.update_object_permissions(self.user, image['_account'],
                image['_container'], image['_object'], permissions)
    
    def add_user(self, image_id, user):
        image = self.get_meta(image_id)
        assert image, "Image not found"
        
        permissions = self._get_permissions(image)
        read = set(permissions.get('read', []))
        read.add(user)
        permissions['read'] = list(read)
        self._update_permissions(image, permissions)
    
    def close(self):
        self.backend.close()
    
    def get_data(self, image):
        size, hashmap = self.backend.get_object_hashmap(self.user,
                image['_account'], image['_container'], image['_object'])
        data = ''.join(self.backend.get_block(hash) for hash in hashmap)
        assert len(data) == size
        return data
    
    def get_meta(self, image_id):
        for image in self._iter(keys=['id']):
            if image['id'] == image_id:
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
    
    def iter_shared(self):
        for image in self._iter():
            yield image
    
    def list_public_images(self, filters, params):
        images = list(self.iter_public(filters))
        key = itemgetter(params['sort_key'])
        reverse = params['sort_dir'] == 'desc'
        images.sort(key=key, reverse=reverse)
        return images
    
    def list_users(self, image_id):
        image = self.get_meta(image_id)
        assert image, "Image not found"
        
        permissions = self._get_permissions(image)
        return [user for user in permissions.get('read', []) if user != '*']
    
    def put(self, name, data, params):
        meta = {}
        
        location = 'pithos://%s/%s/%s' % (self.user, self.container, name)
        image_id = get_image_id(location)
        
        params.setdefault('store', settings.DEFAULT_IMAGE_STORE)
        params.setdefault('disk_format', settings.DEFAULT_DISK_FORMAT)
        params.setdefault('container_format',
                settings.DEFAULT_CONTAINER_FORMAT)
        
        assert params['store'] in settings.IMAGE_STORES
        assert params['disk_format'] in settings.IMAGE_DISK_FORMATS
        assert params['container_format'] in settings.IMAGE_CONTAINER_FORMATS
        
        is_public = params.pop('is_public', False)
        permissions = {'read': ['*']} if is_public else None
        
        size = params.get('size', len(data))
        if size != len(data):
            raise BackendException("Invalid size")
        
        hashmap, digest = self._store(data)
        hexdigest = hexlify(digest)
        meta['ETag'] = hexdigest
        
        checksum = params.pop('checksum', hexdigest)
        if checksum != hexdigest:
            raise BackendException("Invalid checksum")
        
        set_plankton_attr(meta, id=image_id, name=name, status='available',
                size=size, checksum=checksum, deleted_at='')
        
        properties = params.pop('properties', None)
        if properties:
            set_plankton_attr(meta, properties=json.dumps(properties))
        
        set_plankton_attr(meta, **params)
        
        self.backend.update_object_hashmap(
                user=self.user,
                account=self.user,
                container=self.container,
                name=name,
                size=size,
                hashmap=hashmap,
                meta=meta,
                replace_meta=True,
                permissions=permissions)
        
        return self.get_meta(image_id)
    
    def register(self, name, location, params):
        assert location.startswith('pithos://')
        t = location.split('/', 4)
        assert len(t) == 5
        account, container, object = t[2:5]
        user = self.user
        image_id = get_image_id(location)
        
        params.setdefault('store', settings.DEFAULT_IMAGE_STORE)
        params.setdefault('disk_format', settings.DEFAULT_DISK_FORMAT)
        params.setdefault('container_format',
                settings.DEFAULT_CONTAINER_FORMAT)
        
        assert params['store'] in settings.IMAGE_STORES
        assert params['disk_format'] in settings.IMAGE_DISK_FORMATS
        assert params['container_format'] in settings.IMAGE_CONTAINER_FORMATS
        
        sz, hashmap = self.backend.get_object_hashmap(user, account,
                container, object)
        
        size = params.get('size', sz)
        if size != sz:
            raise BackendException("Invalid size")
        
        m = md5()
        for hash in hashmap:
            m.update(self.backend.get_block(hash))

        digest = m.digest()
        hexdigest = hexlify(digest)
        
        checksum = params.pop('checksum', hexdigest)
        if checksum != hexdigest:
            raise BackendException("Invalid checksum")
        
        is_public = params.pop('is_public', False)
        permissions = {'read': ['*']} if is_public else None
        
        meta = {}
        set_plankton_attr(meta, id=image_id, name=name, status='available',
                size=size, checksum=checksum, deleted_at='')
        
        properties = params.pop('properties', None)
        if properties:
            set_plankton_attr(meta, properties=json.dumps(properties))
        
        set_plankton_attr(meta, **params)
        
        self.backend.update_object_meta(user, account, container, object, meta)
        self.backend.update_object_permissions(user, account, container,
                object, permissions)
        
        return self.get_meta(image_id)
    
    def remove_user(self, image_id, user):
        image = self.get_meta(image_id)
        assert image, "Image not found"

        permissions = self._get_permissions(image)
        try:
            permissions.get('read', []).remove(user)
        except ValueError:
            return      # User did not have access anyway
        self._update_permissions(image, permissions)
    
    def replace_users(self, image_id, users):
        image = self.get_meta(image_id)
        assert image, "Image not found"
        
        permissions = self._get_permissions(image)
        permissions['read'] = users
        if image.get('is_public', False):
            permissions['read'].append('*')
        self._update_permissions(image, permissions)
    
    def update(self, image_id, meta):
        image = self.get_meta(image_id)
        assert image, "Image not found"
        
        is_public = meta.pop('is_public', None)
        if is_public is not None:
            permissions = self._get_permissions(image)
            read = set(permissions.get('read', []))
            if is_public:
                read.add('*')
            else:
                read.discard('*')
            permissions['read'] = list(read)
            self.backend._update_permissions(image, permissions)

        m = {}

        properties = meta.pop('properties', None)
        if properties:
            set_plankton_attr(m, properties=json.dumps(properties))
        
        set_plankton_attr(m, **meta)
        
        self.backend.update_object_meta(self.user, image['_account'],
                image['_container'], image['_object'], m)
        return self.get_meta(image_id)
