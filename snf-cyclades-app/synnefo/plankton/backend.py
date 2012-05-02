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
from time import gmtime, strftime, time

from django.conf import settings

from pithos.backends import connect_backend
from pithos.backends.base import NotAllowedError


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


class PithosImageBackend(object):
    """A wrapper arround the pithos backend to simplify image handling."""

    def __init__(self, user):
        self.user = user

        original_filters = warnings.filters
        warnings.simplefilter('ignore')         # Suppress SQLAlchemy warnings
        db_connection = settings.BACKEND_DB_CONNECTION
        block_path = settings.BACKEND_BLOCK_PATH
        self.backend = connect_backend(db_connection=db_connection,
                                       block_path=block_path)
        warnings.filters = original_filters     # Restore warnings

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

    def _get_meta(self, location, version=None):
        account, container, object = split_location(location)
        try:
            return self.backend.get_object_meta(self.user, account, container,
                    object, PLANKTON_DOMAIN, version)
        except NameError:
            return None

    def _get_permissions(self, location):
        account, container, object = split_location(location)
        action, path, permissions = self.backend.get_object_permissions(
                self.user, account, container, object)
        return permissions

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
                object, size, hashmap, '', PLANKTON_DOMAIN,
                permissions=permissions)
        self._update_meta(location, meta, replace=True)

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

    def _update_permissions(self, location, permissions):
        account, container, object = split_location(location)
        self.backend.update_object_permissions(self.user, account, container,
                object, permissions)

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

    def delete(self, image_id):
        image = self.get_image(image_id)
        account, container, object = split_location(image['location'])
        self.backend.delete_object(self.user, account, container, object)

    def get_data(self, location):
        account, container, object = split_location(location)
        size, hashmap = self.backend.get_object_hashmap(self.user, account,
                container, object)
        data = ''.join(self.backend.get_block(hash) for hash in hashmap)
        assert len(data) == size
        return data

    def get_image(self, image_id):
        try:
            account, container, object = self.backend.get_uuid(self.user,
                    image_id)
        except NameError:
            return None

        location = get_location(account, container, object)
        return self._get_image(location)

    def iter(self):
        """Iter over all images available to the user"""

        backend = self.backend
        for account in backend.list_accounts(self.user):
            for container in backend.list_containers(self.user, account,
                                                     shared=True):
                for path, version_id in backend.list_objects(self.user,
                        account, container, domain=PLANKTON_DOMAIN):
                    location = get_location(account, container, path)
                    image = self._get_image(location)
                    if image:
                        yield image

    def iter_public(self, filters=None):
        filters = filters or {}
        backend = self.backend

        keys = [PLANKTON_PREFIX + 'name']
        size_range = (None, None)

        for key, val in filters.items():
            if key == 'size_min':
                size_range = (int(val), size_range[1])
            elif key == 'size_max':
                size_range = (size_range[0], int(val))
            else:
                keys.append('%s = %s' % (PLANKTON_PREFIX + key, val))

        for account in backend.list_accounts(None):
            for container in backend.list_containers(None, account,
                                                     shared=True):
                for path, version_id in backend.list_objects(None, account,
                        container, domain=PLANKTON_DOMAIN, keys=keys,
                        shared=True, size_range=size_range):
                    location = get_location(account, container, path)
                    image = self._get_image(location)
                    if image:
                        yield image

    def iter_shared(self, member):
        """Iterate over image ids shared to this member"""

        backend = self.backend

        # To get the list we connect as member and get the list shared by us
        for container in  backend.list_containers(member, self.user):
            for object, version_id in backend.list_objects(member, self.user,
                    container, domain=PLANKTON_DOMAIN):
                try:
                    location = get_location(self.user, container, object)
                    meta = backend.get_object_meta(member, self.user,
                            container, object, PLANKTON_DOMAIN)
                    if PLANKTON_PREFIX + 'name' in meta:
                        yield meta['uuid']
                except (NameError, NotAllowedError):
                    continue

    def list(self):
        """Iter over all images available to the user"""

        return list(self.iter())

    def list_public(self, filters, params):
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

        meta = self._get_meta(location)
        assert meta, "File not found"

        size = int(params.pop('size', meta['bytes']))
        if size != meta['bytes']:
            raise BackendException("Invalid size")

        checksum = params.pop('checksum', meta['hash'])
        if checksum != meta['hash']:
            raise BackendException("Invalid checksum")

        is_public = params.pop('is_public', False)
        permissions = {'read': ['*']} if is_public else {}

        meta = {}
        meta['properties'] = params.pop('properties', {})
        meta.update(name=name, status='available', **params)

        self._update_meta(location, meta)
        self._update_permissions(location, permissions)
        return self._get_image(location)

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

    def replace_users(self, image_id, users):
        image = self.get_image(image_id)
        assert image, "Image not found"

        location = image['location']
        permissions = self._get_permissions(location)
        permissions['read'] = users
        if image.get('is_public', False):
            permissions['read'].append('*')
        self._update_permissions(location, permissions)

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


class DummyImageBackend():

    def __init__(self, user, images=None):
        self.user = user
        self.images = images or [{"status":"available","name":"Windows","checksum":"c4524d6f6e4f04ecf0212e50bb36f70114f459b223f932f1a3fa6a995e1334f7","created_at":"2012-03-28 14:39:43","disk_format":"diskdump","updated_at":"2012-03-28 16:56:34","properties":{"kernel":"Windows NT Kernel","osfamily":"windows","users":"Administrator","gui":"Windows, Aero Theme","sortorder":"7","size":"10537","os":"windows","root_partition":"2","description":"Windows 2008 R2, Aero Desktop Experience","OS":"windows"},"location":"pithos://images@okeanos.grnet.gr/pithos/windows-2008R2-7-x86_64.diskdump","container_format":"bare","owner":"images@okeanos.grnet.gr","is_public":True,"deleted_at":"","id":"34138811-299e-45db-9a53-acd5f1f7693c","size":11037310976,"metadata":{"values":{"kernel":"Windows NT Kernel","osfamily":"windows","users":"Administrator","gui":"Windows, Aero Theme","sortorder":"7","size":"10537","os":"windows","root_partition":"2","description":"Windows 2008 R2, Aero Desktop Experience","OS":"windows"}},"OS":"windows","description":"Windows 2008 R2, Aero Desktop Experience","kernel":"Windows NT Kernel","GUI":""},{"status":"available","name":"CentOS","checksum":"a7517d876f2387527f35e9d8c19cba4a37419279005354ca03bd625db1cf410e","created_at":"2012-03-28 13:37:28","disk_format":"diskdump","updated_at":"2012-03-28 16:56:33","properties":{"kernel":"2.6.32","osfamily":"linux","users":"root","gui":"No GUI","sortorder":"6","size":"601","os":"centos","root_partition":"1","description":"CentOS 6.0","OS":"centos"},"location":"pithos://images@okeanos.grnet.gr/pithos/centos-6.0-8-x86_64.diskdump","container_format":"bare","owner":"images@okeanos.grnet.gr","is_public":True,"deleted_at":"","id":"8f06e736-d890-4aed-8448-aa0e978695a9","size":628834304,"metadata":{"values":{"kernel":"2.6.32","osfamily":"linux","users":"root","gui":"No GUI","sortorder":"6","size":"601","os":"centos","root_partition":"1","description":"CentOS 6.0","OS":"centos"}},"OS":"centos","description":"CentOS 6.0","kernel":"2.6.32","GUI":""},{"status":"available","name":"Fedora","checksum":"407c7fa05c14937e213503783149aa74ad9bcfc8783ccb653a419fb86bffe0d9","created_at":"2012-03-28 13:52:45","disk_format":"diskdump","updated_at":"2012-03-28 16:56:32","properties":{"kernel":"3.1.9","osfamily":"linux","users":"root user","gui":"GNOME 3.2","sortorder":"5","size":"2641","os":"fedora","root_partition":"1","description":"Fedora 16 Desktop Edition","OS":"fedora"},"location":"debian_base-6.0-7-x86_64","container_format":"bare","owner":"images@okeanos.grnet.gr","is_public":True,"deleted_at":"","id":"1ba3666b-6e57-4d52-813b-e2a33185d12d","size":2765684736,"metadata":{"values":{"kernel":"3.1.9","osfamily":"linux","users":"root user","gui":"GNOME 3.2","sortorder":"5","size":"2641","os":"fedora","root_partition":"1","description":"Fedora 16 Desktop Edition","OS":"fedora"}},"OS":"fedora","description":"Fedora 16 Desktop Edition","kernel":"3.1.9","GUI":""},{"status":"available","name":"Kubuntu","checksum":"a149289f512d70c8f9f6acb0636d2ea9a5b5c3ec0b83e4398aed4a5678da6848","created_at":"2012-03-28 15:05:52","disk_format":"diskdump","updated_at":"2012-03-28 16:56:31","properties":{"kernel":"3.0.0","osfamily":"linux","users":"user","gui":"KDE 4.7.4","sortorder":"4","size":"2850","os":"kubuntu","root_partition":"1","description":"Kubuntu 11.10","OS":"kubuntu"},"location":"pithos://images@okeanos.grnet.gr/pithos/kubuntu-11.10-1-x86_64.diskdump","container_format":"bare","owner":"images@okeanos.grnet.gr","is_public":True,"deleted_at":"","id":"79d24739-af8f-436b-8f6e-eb2d908e0b7e","size":2985041920,"metadata":{"values":{"kernel":"3.0.0","osfamily":"linux","users":"user","gui":"KDE 4.7.4","sortorder":"4","size":"2850","os":"kubuntu","root_partition":"1","description":"Kubuntu 11.10","OS":"kubuntu"}},"OS":"kubuntu","description":"Kubuntu 11.10","kernel":"3.0.0","GUI":""},{"status":"available","name":"Ubuntu","checksum":"f508e1fc8d9cbbd360a9cfc3a68e475933063c77691dac652cb7a5c824791e1b","created_at":"2012-03-28 14:08:35","disk_format":"diskdump","updated_at":"2012-03-28 16:58:10","properties":{"kernel":"3.0.0","osfamily":"linux","users":"user","gui":"Unity 4.22","sortorder":"3","size":"2540","os":"ubuntu","root_partition":"1","description":"Ubuntu 11.10","OS":"ubuntu"},"location":"pithos://images@okeanos.grnet.gr/pithos/ubuntu-11.10-1-x86_64.diskdump","container_format":"bare","owner":"images@okeanos.grnet.gr","is_public":True,"deleted_at":"","id":"d8317451-820a-4c41-917b-665492ab0f81","size":2660171776,"metadata":{"values":{"kernel":"3.0.0","osfamily":"linux","users":"user","gui":"Unity 4.22","sortorder":"3","size":"2540","os":"ubuntu","root_partition":"1","description":"Ubuntu 11.10","OS":"ubuntu"}},"OS":"ubuntu","description":"Ubuntu 11.10","kernel":"3.0.0","GUI":""},{"status":"available","name":"Debian Desktop","checksum":"a7bea0bf6815168a281b505454cd9b2f07ffb9cad0d92e08e950a633c0f05bd2","created_at":"2012-03-28 14:55:37","disk_format":"diskdump","updated_at":"2012-04-03 15:52:09","properties":{"kernel":"2.6.32","osfamily":"linux","users":"root user","gui":"GNOME 2.30","sortorder":"2","size":"3314","os":"debian","root_partition":"1","description":"Debian Squeeze Desktop","OS":"debian"},"location":"pithos://images@okeanos.grnet.gr/pithos/debian_desktop-6.0-6-x86_64.diskdump","container_format":"bare","owner":"images@okeanos.grnet.gr","is_public":True,"deleted_at":"","id":"d7970a84-99b9-40be-b790-ce61001a5b9a","size":3482439680,"metadata":{"values":{"kernel":"2.6.32","osfamily":"linux","users":"root user","gui":"GNOME 2.30","sortorder":"2","size":"3314","os":"debian","root_partition":"1","description":"Debian Squeeze Desktop","OS":"debian"}},"OS":"debian","description":"Debian Squeeze Desktop","kernel":"2.6.32","GUI":""},{"status":"available","name":"Debian Base","checksum":"65352163c9842d6fbc5717437811495f163da2338c807819a1d4d7a50766e56c","created_at":"2012-03-28 13:39:38","disk_format":"diskdump","updated_at":"2012-03-28 16:56:29","properties":{"kernel":"2.6.32","osfamily":"linux","users":"root","gui":"No GUI","sortorder":"1","size":"451","os":"debian","root_partition":"1","description":"Debian Squeeze Base System","OS":"debian"},"location":"pithos://images@okeanos.grnet.gr/pithos/debian_base-6.0-7-x86_64.diskdump","container_format":"bare","owner":"images@okeanos.grnet.gr","is_public":True,"deleted_at":"","id":"49971ade-3bbc-4700-9a84-b3ca00133850","size":471891968,"metadata":{"values":{"kernel":"2.6.32","osfamily":"linux","users":"root","gui":"No GUI","sortorder":"1","size":"451","os":"debian","root_partition":"1","description":"Debian Squeeze Base System","OS":"debian"}},"OS":"debian","description":"Debian Squeeze Base System","kernel":"2.6.32","GUI":""},{"id":"20","name":"(deleted image)","size":-1,"progress":100,"status":"DELETED"},{"id":"21","name":"(deleted image)","size":-1,"progress":100,"status":"DELETED"}]


    def iter(self):
        return self.images

    def get_image(self, image_id):
        for i in self.images:
            if i['id'] == image_id:
                return i
        return None

    def close(self):
        pass

    def list_public(self, filters, params):
        return self.images


ImageBackend = PithosImageBackend
ImageBackend = DummyImageBackend

