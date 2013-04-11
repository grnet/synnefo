# Copyright 2011-2013 GRNET S.A. All rights reserved.

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
import logging
from time import gmtime, strftime
from functools import wraps
from operator import itemgetter

from django.conf import settings
from pithos.backends.base import NotAllowedError, VersionNotExists

logger = logging.getLogger(__name__)


PLANKTON_DOMAIN = 'plankton'
PLANKTON_PREFIX = 'plankton:'
PROPERTY_PREFIX = 'property:'

PLANKTON_META = ('container_format', 'disk_format', 'name', 'properties',
                 'status')

from pithos.backends.util import PithosBackendPool
POOL_SIZE = 8
_pithos_backend_pool = \
    PithosBackendPool(
        POOL_SIZE,
        quotaholder_enabled=settings.CYCLADES_USE_QUOTAHOLDER,
        quotaholder_url=settings.CYCLADES_QUOTAHOLDER_URL,
        quotaholder_token=settings.CYCLADES_QUOTAHOLDER_TOKEN,
        quotaholder_client_poolsize=settings.CYCLADES_QUOTAHOLDER_POOLSIZE,
        db_connection=settings.BACKEND_DB_CONNECTION,
        block_path=settings.BACKEND_BLOCK_PATH)


def get_pithos_backend():
    return _pithos_backend_pool.pool_get()


def create_url(account, container, name):
    assert "/" not in account, "Invalid account"
    assert "/" not in container, "Invalid container"
    return "pithos://%s/%s/%s" % (account, container, name)


def split_url(url):
    """Returns (accout, container, object) from a url string"""
    t = url.split('/', 4)
    assert len(t) == 5, "Invalid url"
    return t[2:5]


def format_timestamp(t):
    return strftime('%Y-%m-%d %H:%M:%S', gmtime(t))


def handle_backend_exceptions(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except NotAllowedError:
            raise Forbidden
        except NameError:
            raise ImageNotFound
        except VersionNotExists:
            raise ImageNotFound
    return wrapper


class ImageBackend(object):
    """A wrapper arround the pithos backend to simplify image handling."""

    def __init__(self, user):
        self.user = user

        original_filters = warnings.filters
        warnings.simplefilter('ignore')         # Suppress SQLAlchemy warnings
        self.backend = get_pithos_backend()
        warnings.filters = original_filters     # Restore warnings

    def close(self):
        """Close PithosBackend(return to pool)"""
        self.backend.close()

    @handle_backend_exceptions
    def get_image(self, image_uuid):
        """Retrieve information about an image."""
        image_url = self._get_image_url(image_uuid)
        return self._get_image(image_url)

    def _get_image_url(self, image_uuid):
        """Get the Pithos url that corresponds to an image UUID."""
        account, container, name = self.backend.get_uuid(self.user, image_uuid)
        return create_url(account, container, name)

    def _get_image(self, image_url):
        """Get information about an Image.

        Get all available information about an Image.
        """
        account, container, name = split_url(image_url)
        versions = self.backend.list_versions(self.user, account, container,
                                              name)
        if not versions:
            raise Exception("Image without versions %s" % image_url)
        try:
            meta = self._get_meta(image_url)
            meta["deleted"] = ""
        except NameError:
            # Object was deleted, use the latest version
            version, timestamp = versions[-1]
            meta = self._get_meta(image_url, version)
            meta["deleted"] = timestamp

        meta["created"] = versions[0][1]

        if PLANKTON_PREFIX + 'name' not in meta:
            raise ImageNotFound("'%s' is not a Plankton image" % image_url)

        permissions = self._get_permissions(image_url)
        return image_to_dict(image_url, meta, permissions)

    def _get_meta(self, image_url, version=None):
        """Get object's metadata."""
        account, container, name = split_url(image_url)
        return self.backend.get_object_meta(self.user, account, container,
                                            name, PLANKTON_DOMAIN, version)

    def _update_meta(self, image_url, meta, replace=False):
        """Update object's metadata."""
        account, container, name = split_url(image_url)

        prefixed = {}
        for key, val in meta.items():
            if key in PLANKTON_META:
                if key == "properties":
                    val = json.dumps(val)
                prefixed[PLANKTON_PREFIX + key] = val

        self.backend.update_object_meta(self.user, account, container, name,
                                        PLANKTON_DOMAIN, prefixed, replace)

    def _get_permissions(self, image_url):
        """Get object's permissions."""
        account, container, name = split_url(image_url)
        _a, path, permissions = \
            self.backend.get_object_permissions(self.user, account, container,
                                                name)

        if path is None:
            logger.warning("Image '%s' got permissions from None path",
                           image_url)

        return permissions

    def _update_permissions(self, image_url, permissions):
        """Update object's permissions."""
        account, container, name = split_url(image_url)
        self.backend.update_object_permissions(self.user, account, container,
                                               name, permissions)

    @handle_backend_exceptions
    def unregister(self, image_uuid):
        """Unregister an image.

        Unregister an image, by removing all metadata from the Pithos
        file that exist in the PLANKTON_DOMAIN.

        """
        image_url = self._get_image_url(image_uuid)
        self._get_image(image_url)  # Assert that it is an image
        # Unregister the image by removing all metadata from domain
        # 'PLANKTON_DOMAIN'
        meta = self._get_meta(image_url)
        for k in meta.keys():
            meta[k] = ""
        self._update_meta(image_url, meta, False)

    @handle_backend_exceptions
    def add_user(self, image_uuid, add_user):
        """Add a user as an image member.

        Update read permissions of Pithos file, to include the specified user.

        """
        image_url = self._get_image_url(image_uuid)
        self._get_image(image_url)  # Assert that it is an image
        permissions = self._get_permissions(image_url)
        read = set(permissions.get("read", []))
        assert(isinstance(add_user, (str, unicode)))
        read.add(add_user)
        permissions["read"] = list(read)
        self._update_permissions(image_url, permissions)

    @handle_backend_exceptions
    def remove_user(self, image_uuid, remove_user):
        """Remove the user from image members.

        Remove the specified user from the read permissions of the Pithos file.

        """
        image_url = self._get_image_url(image_uuid)
        self._get_image(image_url)  # Assert that it is an image
        permissions = self._get_permissions(image_url)
        read = set(permissions.get("read", []))
        assert(isinstance(remove_user, (str, unicode)))
        try:
            read.remove(remove_user)
        except ValueError:
            return  # TODO: User did not have access
        permissions["read"] = list(read)
        self._update_permissions(image_url, permissions)

    @handle_backend_exceptions
    def replace_users(self, image_uuid, replace_users):
        """Replace image members.

        Replace the read permissions of the Pithos files with the specified
        users. If image is specified as public, we must preserve * permission.

        """
        image_url = self._get_image_url(image_uuid)
        image = self._get_image(image_url)
        permissions = self._get_permissions(image_url)
        assert(isinstance(replace_users, list))
        permissions["read"] = replace_users
        if image.get("is_public", False):
            permissions["read"].append("*")
        self._update_permissions(image_url, permissions)

    @handle_backend_exceptions
    def list_users(self, image_uuid):
        """List the image members.

        List the image members, by listing all users that have read permission
        to the corresponding Pithos file.

        """
        image_url = self._get_image_url(image_uuid)
        self._get_image(image_url)  # Assert that it is an image
        permissions = self._get_permissions(image_url)
        return [user for user in permissions.get('read', []) if user != '*']

    @handle_backend_exceptions
    def update_metadata(self, image_uuid, metadata):
        """Update Image metadata."""
        image_url = self._get_image_url(image_uuid)
        self._get_image(image_url)  # Assert that it is an image

        is_public = metadata.pop("is_public", None)
        if is_public is not None:
            permissions = self._get_permissions(image_url)
            read = set(permissions.get("read", []))
            if is_public:
                read.add("*")
            else:
                read.discard("*")
            permissions["read"] = list(read)
            self._update_permissions(image_url, permissions)
        meta = {}
        meta["properties"] = metadata.pop("properties", {})
        meta.update(**metadata)

        self._update_meta(image_url, meta)
        return self.get_image(image_uuid)

    @handle_backend_exceptions
    def register(self, name, image_url, metadata):
        # Validate that metadata are allowed
        if "id" in metadata:
            raise ValueError("Passing an ID is not supported")
        store = metadata.pop("store", "pithos")
        if store != "pithos":
            raise ValueError("Invalid store '%s'. Only 'pithos' store is"
                             "supported" % store)
        disk_format = metadata.setdefault("disk_format",
                                          settings.DEFAULT_DISK_FORMAT)
        if disk_format not in settings.ALLOWED_DISK_FORMATS:
            raise ValueError("Invalid disk format '%s'" % disk_format)
        container_format =\
            metadata.setdefault("container_format",
                                settings.DEFAULT_CONTAINER_FORMAT)
        if container_format not in settings.ALLOWED_CONTAINER_FORMATS:
            raise ValueError("Invalid container format '%s'" %
                             container_format)

        # Validate that 'size' and 'checksum' are valid
        account, container, object = split_url(image_url)

        meta = self._get_meta(image_url)

        size = int(metadata.pop('size', meta['bytes']))
        if size != meta['bytes']:
            raise ValueError("Invalid size")

        checksum = metadata.pop('checksum', meta['hash'])
        if checksum != meta['hash']:
            raise ValueError("Invalid checksum")

        # Fix permissions
        is_public = metadata.pop('is_public', False)
        if is_public:
            permissions = {'read': ['*']}
        else:
            permissions = {'read': [self.user]}

        # Update rest metadata
        meta = {}
        meta['properties'] = metadata.pop('properties', {})
        meta.update(name=name, status='available', **metadata)

        # Do the actualy update in the Pithos backend
        self._update_meta(image_url, meta)
        self._update_permissions(image_url, permissions)
        return self._get_image(image_url)

    def _list_images(self, user=None, filters=None, params=None):
        filters = filters or {}

        # TODO: Use filters
        # # Fix keys
        # keys = [PLANKTON_PREFIX + 'name']
        # size_range = (None, None)
        # for key, val in filters.items():
        #     if key == 'size_min':
        #         size_range = (val, size_range[1])
        #     elif key == 'size_max':
        #         size_range = (size_range[0], val)
        #     else:
        #         keys.append('%s = %s' % (PLANKTON_PREFIX + key, val))
        _images = self.backend.get_domain_objects(domain=PLANKTON_DOMAIN,
                                                  user=user)

        images = []
        for (location, meta, permissions) in _images:
            image_url = "pithos://" + location
            meta["modified"] = meta["version_timestamp"]
            # TODO: Create metadata when registering an Image
            meta["created"] = meta["version_timestamp"]
            images.append(image_to_dict(image_url, meta, permissions))

        if params is None:
            params = {}
        key = itemgetter(params.get('sort_key', 'created_at'))
        reverse = params.get('sort_dir', 'desc') == 'desc'
        images.sort(key=key, reverse=reverse)
        return images

    def list_images(self, filters=None, params=None):
        return self._list_images(user=self.user, filters=filters,
                                 params=params)

    def list_shared_images(self, member, filters=None, params=None):
        images = self._list_images(user=self.user, filters=filters,
                                   params=params)
        is_shared = lambda img: not img["is_public"] and img["owner"] == member
        return filter(is_shared, images)

    def list_public_images(self, filters=None, params=None):
        images = self._list_images(user=None, filters=filters, params=params)
        return filter(lambda img: img["is_public"], images)


class ImageBackendError(Exception):
    pass


class ImageNotFound(ImageBackendError):
    pass


class Forbidden(ImageBackendError):
    pass


def image_to_dict(image_url, meta, permissions):
    """Render an image to a dictionary"""
    account, container, name = split_url(image_url)

    image = {}
    if PLANKTON_PREFIX + 'name' not in meta:
        raise ImageNotFound("'%s' is not a Plankton image" % image_url)

    image["id"] = meta["uuid"]
    image["location"] = image_url
    image["checksum"] = meta["hash"]
    image["created_at"] = format_timestamp(meta["created"])
    deleted = meta.get("deleted", None)
    image["deleted_at"] = format_timestamp(deleted) if deleted else ""
    image["updated_at"] = format_timestamp(meta["modified"])
    image["size"] = meta["bytes"]
    image["store"] = "pithos"
    image['owner'] = account

    # Permissions
    image["is_public"] = "*" in permissions.get('read', [])

    for key, val in meta.items():
        # Get plankton properties
        if key.startswith(PLANKTON_PREFIX):
            # Remove plankton prefix
            key = key.replace(PLANKTON_PREFIX, "")
            # Keep only those in plankton meta
            if key in PLANKTON_META:
                if key == "properties":
                    val = json.loads(val)
                image[key] = val

    return image
