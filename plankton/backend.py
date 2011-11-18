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


def set_image_attrs(meta, **kwargs):
    for key, val in kwargs.items():
        meta[PLANKTON_PREFIX + key] = str(val) if val is not None else ''


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

    def _get_image(self, user, account, container, name):
        meta = self.backend.get_object_meta(user, account, container, name)
        image = {
            '_user': user,
            '_account': account,
            '_container': container,
            '_name': name}
        
        for key in ('id', 'status', 'name', 'disk_format', 'container_format',
                    'size', 'checksum', 'deleted_at'):
            val = meta.get(PLANKTON_PREFIX + key, None)
            if val is not None:
                image[key] = val
        
        image['location'] = 'pithos://%s/%s/%s' % (account, container, name)
        image['updated_at'] = format_timestamp(meta['modified'])
        image['owner'] = account
        
        # Get the creation date from the date of the first version
        version, created = self.backend.list_versions(user, account, container,
                                                      name=name)[0]
        image['created_at'] = format_timestamp(created)
        
        # Mark as public if there is a * entry for read
        action, path, perm = self.backend.get_object_permissions(None, account,
                                                            container, name)
        image['is_public'] = '*' in perm['read']
        
        properties = meta.get(PLANKTON_PREFIX + 'properties', None)
        if properties:
            image['properties'] = json.loads(properties)
        
        return image
    
    def get_public_image(self, image_id):
        backend = self.backend
        container = self.container
        
        # Arguments to be passed to list_objects
        listargs = {
            'user': None,
            'container': container,
            'prefix': '',
            'delimiter': '/',
            'keys': [PLANKTON_PREFIX + 'id']}
        
        for account in backend.list_accounts(None):
            listargs['account'] = account
            print '*', account
            for path, version_id in backend.list_objects(**listargs):
                print '*', path, listargs
                try:
                    image = self._get_image(None, account, container, path)
                    if image['id'] == image_id:
                        return image
                except NotAllowedError:
                    continue
        
        return None
    
    def get_image_data(self, image):
        size, hashmap = self.backend.get_object_hashmap(image['_user'],
                image['_account'], image['_container'], image['_name'])
        
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
        
        return self.get_public_image(image_meta['id'])
    
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
        
        image_meta = {
            'id': str(UUID(bytes=digest)),
            'name': name,
            'status': 'available',
            'store': store,
            'disk_format': disk_format,
            'container_format': container_format,
            'size': size or len(data),
            'checksum': checksum or hexdigest,
            'owner': owner,
            'deleted_at': ''}
        
        if properties:
            image_meta['properties'] = json.dumps(properties)
        
        for key, val in image_meta.items():
            meta[PLANKTON_PREFIX + key] = str(val) if val is not None else ''
        
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
        
        return self.get_public_image(image_meta['id'])
    
    def iter_public_images(self, name=None, container_format=None,
            disk_format=None, status=None, size_min=None, size_max=None):
        
        def add_filter(kwargs, key, val):
            if val is not None and key not in kwargs['keys']:
                kwargs['keys'].append(PLANKTON_PREFIX + key)
        
        def match(image, attr, val):
            if val is None:
                return True
            return image.get(attr, None) == val
        
        def match_gte(image, attr, val):
            if val is None:
                return True
            return image.get(attr, 0) >= val
        
        def match_lte(image, attr, val):
            if val is None:
                return True
            return image.get(attr, 0) <= val
        
        backend = self.backend
        container = self.container
        
        # Args to be passed to 'list_objects'
        listargs = {
            'user': None,
            'container': container,
            'prefix': '',
            'delimiter': '/',
            'keys': []}
        
        add_filter(listargs, 'name', name)
        add_filter(listargs, 'container_format', container_format)
        add_filter(listargs, 'disk_format', disk_format)
        add_filter(listargs, 'status', status)
        add_filter(listargs, 'size', size_min)
        add_filter(listargs, 'size', size_max)
        
        for account in backend.list_accounts(None):
            listargs['account'] = account
            for path, version_id in backend.list_objects(**listargs):
                try:
                    image = self._get_image(None, account, container, path)
                except NotAllowedError:
                    continue
                if not match(image, 'name', name):
                    continue
                if not match(image, 'container_format', container_format):
                    continue
                if not match(image, 'disk_format', disk_format):
                    continue
                if not match(image, 'status', status):
                    continue
                if not match_gte(image, 'size', size_min):
                    continue
                if not match_lte(image, 'size', size_max):
                    continue
                yield image

    def list_public_images(self, name=None, container_format=None,
            disk_format=None, status=None, size_min=None, size_max=None,
            sort_key='created_at', sort_dir='desc'):
        
        assert sort_key in ('id', 'name', 'status', 'size', 'disk_format',
                            'container_format', 'created_at', 'updated_at')
        assert sort_dir in ('asc', 'desc')
        
        images = list(self.iter_public_images(name, container_format,
                                    disk_format, status, size_min, size_max))
        reverse = sort_dir == 'desc'
        images.sort(key=itemgetter(sort_key), reverse=reverse)
        return images
