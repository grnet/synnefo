# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json

from logging import getLogger
from string import punctuation
from urllib import unquote, quote

from django.conf import settings
from django.http import HttpResponse
from django.utils.encoding import (smart_unicode, smart_str,
                                   DjangoUnicodeDecodeError)

from snf_django.lib import api
from snf_django.lib.api import faults
from synnefo.plankton.backend import (PlanktonBackend, OBJECT_AVAILABLE,
                                      OBJECT_UNAVAILABLE, OBJECT_ERROR)
from synnefo.plankton.backend import split_url


FILTERS = ('name', 'container_format', 'disk_format', 'status', 'size_min',
           'size_max')

PARAMS = ('sort_key', 'sort_dir')

SORT_KEY_OPTIONS = ('id', 'name', 'status', 'size', 'disk_format',
                    'container_format', 'created_at', 'updated_at')

SORT_DIR_OPTIONS = ('asc', 'desc')

LIST_FIELDS = ('status', 'name', 'disk_format', 'container_format', 'size',
               'id')

DETAIL_FIELDS = ('name', 'disk_format', 'container_format', 'size', 'checksum',
                 'location', 'created_at', 'updated_at', 'deleted_at',
                 'status', 'is_public', 'owner', 'properties', 'id',
                 'is_snapshot', 'description')

PLANKTON_FIELDS = DETAIL_FIELDS + ('store',)

ADD_FIELDS = ('name', 'id', 'store', 'disk_format', 'container_format', 'size',
              'checksum', 'is_public', 'owner', 'properties', 'location')

UPDATE_FIELDS = ('name', 'disk_format', 'container_format', 'is_public',
                 'owner', 'properties', 'status')

DISK_FORMATS = ('diskdump', 'extdump', 'ntfsdump')

CONTAINER_FORMATS = ('aki', 'ari', 'ami', 'bare', 'ovf')

STORE_TYPES = ('pithos')


META_PREFIX = 'HTTP_X_IMAGE_META_'
META_PREFIX_LEN = len(META_PREFIX)
META_PROPERTY_PREFIX = 'HTTP_X_IMAGE_META_PROPERTY_'
META_PROPERTY_PREFIX_LEN = len(META_PROPERTY_PREFIX)


log = getLogger('synnefo.plankton')


API_STATUS_FROM_IMAGE_STATUS = {
    OBJECT_AVAILABLE: "AVAILABLE",
    OBJECT_UNAVAILABLE: "SAVING",
    OBJECT_ERROR: "ERROR",
    "DELETED": "DELETED"}  # Unused status


def _create_image_response(image):
    """Encode the image parameters to HTTP Response Headers.

    This function converts all image parameters to HTTP response headers.
    All parameters are 'utf-8' encoded. User provided values like the
    image name and image properties are also properly quoted.

    """
    response = HttpResponse()

    for key in DETAIL_FIELDS:
        if key == 'properties':
            for pkey, pval in image.get('properties', {}).items():
                pkey = 'x-image-meta-property-' + pkey.replace('_', '-')
                pkey = quote(smart_str(pkey, encoding='utf-8'))
                pval = quote(smart_str(pval, encoding='utf-8'))
                response[pkey] = pval
        else:
            val = image.get(key, '')
            if key == 'status':
                val = API_STATUS_FROM_IMAGE_STATUS.get(val.upper(), "UNKNOWN")
            if key == 'name' or key == 'description':
                val = quote(smart_str(val, encoding='utf-8'))
            key = 'x-image-meta-' + key.replace('_', '-')
            response[key] = val

    return response


def headers_to_image_params(request):
    """Decode the HTTP request headers to the acceptable image parameters.

    Get the image parameters from the headers of the HTTP request. All
    parameters must be encoded using 'utf-8' encoding. User provided parameters
    like the image name or the image properties must be quoted, so we need to
    unquote them.
    Finally, all image parameters name (HTTP header keys) are lowered
    and all punctuation characters are replaced with underscore.

    """

    def normalize(s):
        return ''.join('_' if c in punctuation else c.lower() for c in s)

    params = {}
    properties = {}
    try:
        for key, val in request.META.items():
            if key.startswith(META_PREFIX):
                if key.startswith(META_PROPERTY_PREFIX):
                    key = key[META_PROPERTY_PREFIX_LEN:]
                    key = smart_unicode(unquote(key), encoding='utf-8')
                    val = smart_unicode(unquote(val), encoding='utf-8')
                    properties[normalize(key)] = val
                else:
                    key = smart_unicode(key[META_PREFIX_LEN:],
                                        encoding='utf-8')
                    key = normalize(key)
                    if key in PLANKTON_FIELDS:
                        if key == "name":
                            val = smart_unicode(unquote(val), encoding='utf-8')
                        elif key == "is_public" and not isinstance(val, bool):
                            val = True if val.lower() == 'true' else False
                        params[key] = val
    except DjangoUnicodeDecodeError:
        raise faults.BadRequest("Could not decode request as UTF-8 string")

    params['properties'] = properties

    return params


@api.api_method(http_method="POST", user_required=True, logger=log)
def add_image(request):
    """Add a new virtual machine image

    Described in:
    3.6. Adding a New Virtual Machine Image

    Implementation notes:
      * The implementation is very inefficient as it loads the whole image
        in memory.

    Limitations:
      * x-image-meta-id is not supported. Will always return 409 Conflict.

    Extensions:
      * An x-image-meta-location header can be passed with a link to file,
        instead of uploading the data.
    """

    params = headers_to_image_params(request)
    log.debug('add_image %s', params)

    if not set(params.keys()).issubset(set(ADD_FIELDS)):
        raise faults.BadRequest("Invalid parameters")

    name = params.pop('name', None)
    if name is None:
        raise faults.BadRequest("Image 'name' parameter is required")
    elif len(smart_unicode(name, encoding="utf-8")) == 0:
        raise faults.BadRequest("Invalid image name")
    location = params.pop('location', None)
    if location is None:
        raise faults.BadRequest("'location' parameter is required")

    try:
        split_url(location)
    except AssertionError:
        raise faults.BadRequest("Invalid location '%s'" % location)

    validate_fields(params)

    if location:
        with PlanktonBackend(request.user_uniq) as backend:
            image = backend.register(name, location, params)
    else:
        # f = StringIO(request.body)
        # image = backend.put(name, f, params)
        return HttpResponse(status=501)     # Not Implemented

    if not image:
        return HttpResponse('Registration failed', status=500)

    return _create_image_response(image)


@api.api_method(http_method="DELETE", user_required=True, logger=log)
def delete_image(request, image_id):
    """Delete an Image.

    This API call is not described in the Openstack Glance API.

    Implementation notes:
      * The implementation does not delete the Image from the storage
        backend. Instead it unregisters the image by removing all the
        metadata from the plankton metadata domain.

    """
    log.info("delete_image '%s'" % image_id)
    userid = request.user_uniq
    with PlanktonBackend(userid) as backend:
        backend.unregister(image_id)
    log.info("User '%s' deleted image '%s'" % (userid, image_id))
    return HttpResponse(status=204)


@api.api_method(http_method="PUT", user_required=True, logger=log)
def add_image_member(request, image_id, member):
    """Add a member to an image

    Described in:
    3.9. Adding a Member to an Image

    Limitations:
      * Passing a body to enable `can_share` is not supported.
    """

    log.debug('add_image_member %s %s', image_id, member)
    with PlanktonBackend(request.user_uniq) as backend:
        backend.add_user(image_id, member)
    return HttpResponse(status=204)


@api.api_method(http_method="GET", user_required=True, logger=log)
def get_image(request, image_id):
    """Retrieve a virtual machine image

    Described in:
    3.5. Retrieving a Virtual Machine Image

    Implementation notes:
      * The implementation is very inefficient as it loads the whole image
        in memory.
    """
    return HttpResponse(status=501)     # Not Implemented


@api.api_method(http_method="HEAD", user_required=True, logger=log)
def get_image_meta(request, image_id):
    """Return detailed metadata on a specific image

    Described in:
    3.4. Requesting Detailed Metadata on a Specific Image
    """

    with PlanktonBackend(request.user_uniq) as backend:
        image = backend.get_image(image_id)
    return _create_image_response(image)


@api.api_method(http_method="GET", user_required=True, logger=log)
def list_image_members(request, image_id):
    """List image memberships

    Described in:
    3.7. Requesting Image Memberships
    """

    with PlanktonBackend(request.user_uniq) as backend:
        users = backend.list_users(image_id)

    members = [{'member_id': u, 'can_share': False} for u in users]
    data = json.dumps({'members': members}, indent=settings.DEBUG)
    return HttpResponse(data)


@api.api_method(http_method="GET", user_required=True, logger=log)
def list_images(request, detail=False):
    """Return a list of available images.

    This includes images owned by the user, images shared with the user and
    public images.

    """

    def get_request_params(keys):
        params = {}
        for key in keys:
            val = request.GET.get(key, None)
            if val is not None:
                params[key] = val
        return params

    log.debug('list_public_images detail=%s', detail)

    filters = get_request_params(FILTERS)
    params = get_request_params(PARAMS)

    params.setdefault('sort_key', 'created_at')
    params.setdefault('sort_dir', 'desc')

    if not params['sort_key'] in SORT_KEY_OPTIONS:
        raise faults.BadRequest("Invalid 'sort_key'")
    if not params['sort_dir'] in SORT_DIR_OPTIONS:
        raise faults.BadRequest("Invalid 'sort_dir'")

    if 'size_max' in filters:
        try:
            filters['size_max'] = int(filters['size_max'])
        except ValueError:
            raise faults.BadRequest("Malformed request.")

    if 'size_min' in filters:
        try:
            filters['size_min'] = int(filters['size_min'])
        except ValueError:
            raise faults.BadRequest("Malformed request.")

    with PlanktonBackend(request.user_uniq) as backend:
        images = backend.list_images(filters, params)

    # Remove keys that should not be returned
    fields = DETAIL_FIELDS if detail else LIST_FIELDS
    for image in images:
        for key in image.keys():
            if key not in fields:
                del image[key]

    data = json.dumps(images, indent=settings.DEBUG)
    return HttpResponse(data)


@api.api_method(http_method="GET", user_required=True, logger=log)
def list_shared_images(request, member):
    """Request shared images

    Described in:
    3.8. Requesting Shared Images

    Implementation notes:
      * It is not clear what this method should do. We return the IDs of
        the users's images that are accessible by `member`.
    """

    log.debug('list_shared_images %s', member)

    images = []
    with PlanktonBackend(request.user_uniq) as backend:
        for image in backend.list_shared_images(member=member):
            images.append({'image_id': image["id"], 'can_share': False})

    data = json.dumps({'shared_images': images}, indent=settings.DEBUG)
    return HttpResponse(data)


@api.api_method(http_method="DELETE", user_required=True, logger=log)
def remove_image_member(request, image_id, member):
    """Remove a member from an image

    Described in:
    3.10. Removing a Member from an Image
    """

    log.debug('remove_image_member %s %s', image_id, member)
    with PlanktonBackend(request.user_uniq) as backend:
        backend.remove_user(image_id, member)
    return HttpResponse(status=204)


@api.api_method(http_method="PUT", user_required=True, logger=log)
def update_image(request, image_id):
    """Update an image

    Described in:
    3.6.2. Updating an Image

    Implementation notes:
      * It is not clear which metadata are allowed to be updated. We support:
        name, disk_format, container_format, is_public, owner, properties
        and status.
    """

    meta = headers_to_image_params(request)
    log.debug('update_image %s', meta)

    if not set(meta.keys()).issubset(set(UPDATE_FIELDS)):
        raise faults.BadRequest("Invalid metadata")

    validate_fields(meta)

    with PlanktonBackend(request.user_uniq) as backend:
        image = backend.update_metadata(image_id, meta)
    return _create_image_response(image)


@api.api_method(http_method="PUT", user_required=True, logger=log)
def update_image_members(request, image_id):
    """Replace a membership list for an image

    Described in:
    3.11. Replacing a Membership List for an Image

    Limitations:
      * can_share value is ignored
    """

    log.debug('update_image_members %s', image_id)
    data = api.utils.get_json_body(request)
    members = []

    memberships = api.utils.get_attribute(data, "memberships", attr_type=list)
    for member in memberships:
        if not isinstance(member, dict):
            raise faults.BadRequest("Invalid 'memberships' field")
        member = api.utils.get_attribute(member, "member_id")
        members.append(member)

    with PlanktonBackend(request.user_uniq) as backend:
        backend.replace_users(image_id, members)
    return HttpResponse(status=204)


def validate_fields(params):
    if "id" in params:
        raise faults.BadRequest("Setting the image ID is not supported")

    if "store" in params:
        if params["store"] not in STORE_TYPES:
            raise faults.BadRequest("Invalid store type '%s'" %
                                    params["store"])

    if "disk_format" in params:
        if params["disk_format"] not in DISK_FORMATS:
            raise faults.BadRequest("Invalid disk format '%s'" %
                                    params['disk_format'])

    if "container_format" in params:
        if params["container_format"] not in CONTAINER_FORMATS:
            raise faults.BadRequest("Invalid container format '%s'" %
                                    params['container_format'])
