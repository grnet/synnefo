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


def iterblock(data, block_size):
    while data:
        yield data[:block_size]
        data = data[block_size:]


def format_timestamp(t):
    return strftime('%Y-%m-%d %H:%M:%S', gmtime(t))


def set_plankton_attr(d, **kwargs):
    for key, val in kwargs.items():
        d[PLANKTON_PREFIX + key] = str(val) if val is not None else ''


class BackendException(Exception): pass


class BackendWrapper(object):
    """A proxy object that always passes user as a first argument."""
    
    def __init__(self, user):
        self.user = user
        self.container = settings.PITHOS_IMAGE_CONTAINER
        self.backend = connect_backend()
        try:
            self.backend.put_container(self.user, self.user, self.container)
        except NameError:
            pass    # Container already exists
    
    def close(self):
        self.backend.wrapper.conn.close()

    def _get_image(self, user, account, container, object):
        meta = self.backend.get_object_meta(user, account, container, object)
        image = {
            '_user': user,
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
        action, path, perm = self.backend.get_object_permissions(user, account,
                                                            container, object)
        image['is_public'] = '*' in perm.get('read', [])
        
        properties = meta.get(PLANKTON_PREFIX + 'properties', None)
        if properties:
            image['properties'] = json.loads(properties)
        
        return image
    
    def get_image(self, image_id):
        backend = self.backend
        
        user = self.user
        container = self.container
        
        # Arguments to be passed to list_objects
        listargs = {
            'user': user,
            'container': container,
            'prefix': '',
            'delimiter': '/',
            'keys': [PLANKTON_PREFIX + 'id']}
        
        for account in backend.list_accounts(user):
            listargs['account'] = account
            for path, version_id in backend.list_objects(**listargs):
                try:
                    image = self._get_image(user, account, container, path)
                    if image['id'] == image_id:
                        return image
                except NotAllowedError:
                    continue
        
        return None
    
    def get_image_data(self, image):
        size, hashmap = self.backend.get_object_hashmap(image['_user'],
                image['_account'], image['_container'], image['_object'])
        
        buf = []
        for hash in hashmap:
            buf.append(self.backend.get_block(hash))
        return ''.join(buf)
    
    def register_image(self, name, location, store=None, disk_format=None,
            container_format=None, size=None, checksum=None, is_public=False,
            owner=None, properties={}):
        
        backend = self.backend
        
        assert location.startswith('pithos://')
        t = location.split('/', 4)
        assert len(t) == 5
        account, container, object = t[2:5]
        user = self.user
        
        store = store or settings.DEFAULT_IMAGE_STORE
        disk_format = disk_format or settings.DEFAULT_DISK_FORMAT
        container_format = container_format or \
                                            settings.DEFAULT_CONTAINER_FORMAT
        
        assert store in settings.IMAGE_STORES
        assert disk_format in settings.IMAGE_DISK_FORMATS
        assert container_format in settings.IMAGE_CONTAINER_FORMATS
        
        sz, hashmap = self.backend.get_object_hashmap(user, account,
                container, name)
        if size is not None and size != sz:
            raise BackendException("Invalid size")
        
        m = md5()
        for hash in hashmap:
            m.update(self.backend.get_block(hash))
        
        digest = m.digest()
        hexdigest = hexlify(digest)
        if checksum is not None and checksum != hexdigest:
            raise BackendException("Invalid checksum")
        
        permissions = {'read': ['*']} if is_public else None
        
        image_meta = {
            'id': str(UUID(bytes=digest)),
            'name': name,
            'status': 'available',
            'store': store,
            'disk_format': disk_format,
            'container_format': container_format,
            'size': size or sz,
            'checksum': checksum or hexdigest,
            'owner': owner,
            'deleted_at': ''}
        
        if properties:
            image_meta['properties'] = json.dumps(properties)
        
        meta = {}
        for key, val in image_meta.items():
            meta[PLANKTON_PREFIX + key] = str(val) if val is not None else ''
        
        backend.update_object_meta(user, account, container, object, meta)
        backend.update_object_permissions(user, account, container, object,
                                          permissions)
        
        return self.get_image(image_meta['id'])
    
    def put_image(self, name, data, store=None, disk_format=None,
            container_format=None, size=None, checksum=None, is_public=False,
            owner=None, properties={}):
        
        backend = self.backend
        
        store = store or settings.DEFAULT_IMAGE_STORE
        disk_format = disk_format or settings.DEFAULT_DISK_FORMAT
        container_format = container_format or \
                                            settings.DEFAULT_CONTAINER_FORMAT
        
        assert store in settings.IMAGE_STORES
        assert disk_format in settings.IMAGE_DISK_FORMATS
        assert container_format in settings.IMAGE_CONTAINER_FORMATS
        
        if size is not None and size != len(data):
            raise BackendException("Invalid size")
        
        m = md5()
        hashmap = []
        for block in iterblock(data, backend.block_size):
            hash = backend.put_block(block)
            hashmap.append(hash)
            m.update(block)

        digest = m.digest()
        hexdigest = hexlify(digest)
        if checksum is not None and checksum != hexdigest:
            raise BackendException("Invalid checksum")
        
        permissions = {'read': ['*']} if is_public else None
        
        meta = {'hash': hexdigest}
        
        set_plankton_attr(meta,
            id=str(UUID(bytes=digest)),
            name=name,
            status='available',
            store=store,
            disk_format=disk_format,
            container_format=container_format,
            size=size or len(data),
            checksum=checksum or hexdigest,
            owner=owner,
            deleted_at='')
        
        if properties:
            set_plankton_attr(meta, properties=json.dumps(properties))
        
        backend.update_object_hashmap(
                user=self.user,
                account=self.user,
                container=self.container,
                name=name,
                size=len(data),
                hashmap=hashmap,
                meta=meta,
                replace_meta=True,
                permissions=permissions)
        
        return self.get_image(image_meta['id'])
    
    def iter_public_images(self, filters):
        user = None
        container = self.container
        
        keys = set()
        for key, val in filters.items():
            if key in ('size_min', 'size_max'):
                key = 'size'
            keys.add(PLANKTON_PREFIX + key)
        keys = list(keys)
        
        for account in self.backend.list_accounts(None):
            for path, version_id in self.backend.list_objects(user, account,
                    container, prefix='', delimiter='/', keys=keys):
                try:
                    image = self._get_image(user, account, container, path)
                except NotAllowedError:
                    continue
                
                skip = False
                for key, val in filters.items():
                    if key == 'size_min':
                        if image['size'] < int(val):
                            skip = True
                            break
                    elif key == 'size_max':
                        if image['size'] > int(val):
                            skip = True
                            break
                    else:
                        if image[key] != val:
                            skip = True
                            break
                
                if not skip:
                    yield image
    
    def list_public_images(self, filters, params):
        images = list(self.iter_public_images(filters))
        
        key = itemgetter(params['sort_key'])
        reverse = params['sort_dir'] == 'desc'
        images.sort(key=key, reverse=reverse)
        
        return images
    
    def update_image(self, image_id, meta):
        image = self.get_image(image_id)
        if not image:
            return None
        
        user = self.user
        account = image['_account']
        container = image['_container']
        object = image['_object']
        
        is_public = meta.pop('is_public', None)
        if is_public is not None:
            action, path, permissions = self.backend.get_object_permissions(
                    user, account, container, object)
            read_permissions = set(permissions.get('read', []))
            if is_public:
                read_permissions.add('*')
            else:
                read_permissions.discard('*')
            permissions['read'] = list(read_permissions)
            self.backend.update_object_permissions(user, account, container,
                    object, permissions)
        
        m = {}
        set_plankton_attr(m, **meta)
        
        properties = meta.get('properties', None)
        if properties:
            set_plankton_attr(m, properties=json.dumps(properties))
        
        self.backend.update_object_meta(user, account, container, object, m)
        return self.get_image(image_id)
