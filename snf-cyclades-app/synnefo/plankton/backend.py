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
The Plankton attributes are the following:
  - checksum: the 'hash' meta
  - container_format: stored as a user meta
  - created_at: the 'modified' meta of the first version
  - deleted_at: the timestamp of the last version
  - disk_format: stored as a user meta
  - id: the 'uuid' meta
  - is_public: True if there is a * entry for the read permission
  - location: generated based on the file's path
  - name: stored as a user meta
  - owner: the file's account
  - properties: stored as user meta prefixed with PROPERTY_PREFIX
  - size: the 'bytes' meta
  - status: stored as a system meta
  - store: is always 'pithos'
  - updated_at: the 'modified' meta
"""

import json
import warnings

from operator import itemgetter
from time import gmtime, strftime
from functools import wraps

from django.conf import settings

from pithos.backends.base import NotAllowedError as PithosNotAllowedError


PLANKTON_DOMAIN = 'plankton'
PLANKTON_PREFIX = 'plankton:'
PROPERTY_PREFIX = 'property:'

PLANKTON_META = ('container_format', 'disk_format', 'name', 'properties',
                 'status')


def get_location(account, container, object):
    assert '/' not in account, "Invalid account"
    assert '/' not in container, "Invalid container"
    return 'pithos://%s/%s/%s' % (account, container, object)


def split_location(location):
    """Returns (accout, container, object) from a location string"""
    t = location.split('/', 4)
    assert len(t) == 5, "Invalid location"
    return t[2:5]


class BackendException(Exception):
    pass


class NotAllowedError(BackendException):
    pass


from pithos.backends.util import PithosBackendPool
POOL_SIZE = 8
_pithos_backend_pool = \
    PithosBackendPool(POOL_SIZE,
                      db_connection=settings.BACKEND_DB_CONNECTION,
                      block_path=settings.BACKEND_BLOCK_PATH)


def get_pithos_backend():
    return _pithos_backend_pool.pool_get()


def handle_backend_exceptions(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except PithosNotAllowedError:
            raise NotAllowedError()
    return wrapper


class ImageBackend(object):
    """A wrapper arround the pithos backend to simplify image handling."""

    def __init__(self, user):
        self.user = user

        original_filters = warnings.filters
        warnings.simplefilter('ignore')         # Suppress SQLAlchemy warnings
        self.backend = get_pithos_backend()
        warnings.filters = original_filters     # Restore warnings

    @handle_backend_exceptions
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

        if PLANKTON_PREFIX + 'name' not in meta:
            return None     # Not a Plankton image

        permissions = self._get_permissions(location)

        image['checksum'] = meta['hash']
        image['created_at'] = format_timestamp(versions[0][1])
        image['id'] = meta['uuid']
        image['is_public'] = '*' in permissions.get('read', [])
        image['location'] = location
        image['owner'] = account
        image['size'] = meta['bytes']
        image['store'] = 'pithos'
        image['updated_at'] = format_timestamp(meta['modified'])
        image['properties'] = {}

        for key, val in meta.items():
            if not key.startswith(PLANKTON_PREFIX):
                continue
            key = key[len(PLANKTON_PREFIX):]
            if key == 'properties':
                val = json.loads(val)
            if key in PLANKTON_META:
                image[key] = val

        return image

    @handle_backend_exceptions
    def _get_meta(self, location, version=None):
        account, container, object = split_location(location)
        try:
            return self.backend.get_object_meta(self.user, account, container,
                                                object, PLANKTON_DOMAIN,
                                                version)
        except NameError:
            return None

    @handle_backend_exceptions
    def _get_permissions(self, location):
        account, container, object = split_location(location)
        _a, _p, permissions = self.backend.get_object_permissions(self.user,
                                                                  account,
                                                                  container,
                                                                  object)
        return permissions

    @handle_backend_exceptions
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

    @handle_backend_exceptions
    def _update(self, location, size, hashmap, meta, permissions):
        account, container, object = split_location(location)
        self.backend.update_object_hashmap(self.user, account, container,
                                           object, size, hashmap, '',
                                           PLANKTON_DOMAIN,
                                           permissions=permissions)
        self._update_meta(location, meta, replace=True)

    @handle_backend_exceptions
    def _update_meta(self, location, meta, replace=False):
        account, container, object = split_location(location)

        prefixed = {}
        for key, val in meta.items():
            if key == 'properties':
                val = json.dumps(val)
            if key in PLANKTON_META:
                prefixed[PLANKTON_PREFIX + key] = val

        self.backend.update_object_meta(self.user, account, container, object,
                                        PLANKTON_DOMAIN, prefixed, replace)

    @handle_backend_exceptions
    def _update_permissions(self, location, permissions):
        account, container, object = split_location(location)
        self.backend.update_object_permissions(self.user, account, container,
                                               object, permissions)

    @handle_backend_exceptions
    def add_user(self, image_id, user):
        image = self.get_image(image_id)
        assert image, "Image not found"

        location = image['location']
        permissions = self._get_permissions(location)
        read = set(permissions.get('read', []))
        read.add(user)
        permissions['read'] = list(read)
        self._update_permissions(location, permissions)

    def close(self):
        self.backend.close()

    @handle_backend_exceptions
    def delete(self, image_id):
        image = self.get_image(image_id)
        account, container, object = split_location(image['location'])
        self.backend.delete_object(self.user, account, container, object)

    @handle_backend_exceptions
    def get_data(self, location):
        account, container, object = split_location(location)
        size, hashmap = self.backend.get_object_hashmap(self.user, account,
                                                        container, object)
        data = ''.join(self.backend.get_block(hash) for hash in hashmap)
        assert len(data) == size
        return data

    @handle_backend_exceptions
    def get_image(self, image_id):
        try:
            account, container, object = self.backend.get_uuid(self.user,
                                                               image_id)
        except NameError:
            return None

        location = get_location(account, container, object)
        return self._get_image(location)

    @handle_backend_exceptions
    def _iter(self, public=False, filters=None, shared_from=None):
        filters = filters or {}

        # Fix keys
        keys = [PLANKTON_PREFIX + 'name']
        size_range = (None, None)
        for key, val in filters.items():
            if key == 'size_min':
                size_range = (val, size_range[1])
            elif key == 'size_max':
                size_range = (size_range[0], val)
            else:
                keys.append('%s = %s' % (PLANKTON_PREFIX + key, val))

        backend = self.backend
        if shared_from:
            # To get shared images, we connect as shared_from member and
            # get the list shared by us
            user = shared_from
            accounts = [self.user]
        else:
            user = None if public else self.user
            accounts = backend.list_accounts(user)

        for account in accounts:
            for container in backend.list_containers(user, account,
                                                     shared=True):
                for path, _ in backend.list_objects(user, account, container,
                                                    domain=PLANKTON_DOMAIN,
                                                    keys=keys, shared=True,
                                                    size_range=size_range):
                    location = get_location(account, container, path)
                    image = self._get_image(location)
                    if image:
                        yield image

    def iter(self, filters=None):
        """Iter over all images available to the user"""
        return self._iter(filters=filters)

    def iter_public(self, filters=None):
        """Iter over public images"""
        return self._iter(public=True, filters=filters)

    def iter_shared(self, filters=None, member=None):
        """Iter over images shared to member"""
        return self._iter(filters=filters, shared_from=member)

    def list(self, filters=None, params={}):
        """Return all images available to the user"""
        images = list(self.iter(filters))
        key = itemgetter(params.get('sort_key', 'created_at'))
        reverse = params.get('sort_dir', 'desc') == 'desc'
        images.sort(key=key, reverse=reverse)
        return images

    def list_public(self, filters, params={}):
        """Return public images"""
        images = list(self.iter_public(filters))
        key = itemgetter(params.get('sort_key', 'created_at'))
        reverse = params.get('sort_dir', 'desc') == 'desc'
        images.sort(key=key, reverse=reverse)
        return images

    def list_users(self, image_id):
        image = self.get_image(image_id)
        assert image, "Image not found"

        permissions = self._get_permissions(image['location'])
        return [user for user in permissions.get('read', []) if user != '*']

    @handle_backend_exceptions
    def put(self, name, f, params):
        assert 'checksum' not in params, "Passing a checksum is not supported"
        assert 'id' not in params, "Passing an ID is not supported"
        assert params.pop('store', 'pithos') == 'pithos', "Invalid store"
        disk_format = params.setdefault('disk_format',
                                        settings.DEFAULT_DISK_FORMAT)
        assert disk_format in settings.ALLOWED_DISK_FORMATS,\
            "Invalid disk_format"
        assert params.setdefault('container_format',
                settings.DEFAULT_CONTAINER_FORMAT) in \
                settings.ALLOWED_CONTAINER_FORMATS, "Invalid container_format"

        container = settings.DEFAULT_PLANKTON_CONTAINER
        filename = params.pop('filename', name)
        location = 'pithos://%s/%s/%s' % (self.user, container, filename)
        is_public = params.pop('is_public', False)
        permissions = {'read': ['*']} if is_public else {}
        size = params.pop('size', None)

        hashmap, size = self._store(f, size)

        meta = {}
        meta['properties'] = params.pop('properties', {})
        meta.update(name=name, status='available', **params)

        self._update(location, size, hashmap, meta, permissions)
        return self._get_image(location)

    @handle_backend_exceptions
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

        # user = self.user
        account, container, object = split_location(location)

        meta = self._get_meta(location)
        assert meta, "File not found"

        size = int(params.pop('size', meta['bytes']))
        if size != meta['bytes']:
            raise BackendException("Invalid size")

        checksum = params.pop('checksum', meta['hash'])
        if checksum != meta['hash']:
            raise BackendException("Invalid checksum")

        is_public = params.pop('is_public', False)
        if is_public:
            permissions = {'read': ['*']}
        else:
            permissions = {'read': [self.user]}

        meta = {}
        meta['properties'] = params.pop('properties', {})
        meta.update(name=name, status='available', **params)

        self._update_meta(location, meta)
        self._update_permissions(location, permissions)
        return self._get_image(location)

    @handle_backend_exceptions
    def remove_user(self, image_id, user):
        image = self.get_image(image_id)
        assert image, "Image not found"

        location = image['location']
        permissions = self._get_permissions(location)
        try:
            permissions.get('read', []).remove(user)
        except ValueError:
            return      # User did not have access anyway
        self._update_permissions(location, permissions)

    @handle_backend_exceptions
    def replace_users(self, image_id, users):
        image = self.get_image(image_id)
        assert image, "Image not found"

        location = image['location']
        permissions = self._get_permissions(location)
        permissions['read'] = users
        if image.get('is_public', False):
            permissions['read'].append('*')
        self._update_permissions(location, permissions)

    @handle_backend_exceptions
    def update(self, image_id, params):
        image = self.get_image(image_id)
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
        return self.get_image(image_id)
