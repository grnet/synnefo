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

from functools import wraps
from datetime import datetime
from urllib import quote, unquote

from django.http import HttpResponse, Http404, HttpResponseForbidden
from django.template.loader import render_to_string
from django.utils import simplejson as json
from django.utils.http import http_date, parse_etags
from django.utils.encoding import smart_unicode, smart_str
from django.core.files.uploadhandler import FileUploadHandler
from django.core.files.uploadedfile import UploadedFile
from django.core.urlresolvers import reverse

from snf_django.lib.api.parsedate import parse_http_date_safe, parse_http_date
from snf_django.lib import api
from snf_django.lib.api import faults, utils

from pithos.api.settings import (BACKEND_DB_MODULE, BACKEND_DB_CONNECTION,
                                 BACKEND_BLOCK_MODULE, BACKEND_BLOCK_PATH,
                                 BACKEND_BLOCK_UMASK,
                                 BACKEND_QUEUE_MODULE, BACKEND_QUEUE_HOSTS,
                                 BACKEND_QUEUE_EXCHANGE,
                                 ASTAKOSCLIENT_POOLSIZE,
                                 SERVICE_TOKEN,
                                 ASTAKOS_BASE_URL,
                                 BACKEND_ACCOUNT_QUOTA, BACKEND_CONTAINER_QUOTA,
                                 BACKEND_VERSIONING,
                                 BACKEND_FREE_VERSIONING, BACKEND_POOL_SIZE,
                                 RADOS_STORAGE, RADOS_POOL_BLOCKS,
                                 RADOS_POOL_MAPS, TRANSLATE_UUIDS,
                                 PUBLIC_URL_SECURITY,
                                 PUBLIC_URL_ALPHABET,
                                 COOKIE_NAME, BASE_HOST)
from pithos.api.resources import resources
from pithos.backends.base import (NotAllowedError, QuotaError, ItemNotExists,
                                  VersionNotExists)

from synnefo.lib import join_urls

from astakosclient import AstakosClient
from astakosclient.errors import NoUserName, NoUUID

import logging
import re
import hashlib
import uuid
import decimal

logger = logging.getLogger(__name__)


def json_encode_decimal(obj):
    if isinstance(obj, decimal.Decimal):
        return str(obj)
    raise TypeError(repr(obj) + " is not JSON serializable")


def rename_meta_key(d, old, new):
    if old not in d:
        return
    d[new] = d[old]
    del(d[old])


def printable_header_dict(d):
    """Format a meta dictionary for printing out json/xml.

    Convert all keys to lower case and replace dashes with underscores.
    Format 'last_modified' timestamp.
    """

    if 'last_modified' in d and d['last_modified']:
        d['last_modified'] = utils.isoformat(
            datetime.fromtimestamp(d['last_modified']))
    return dict([(k.lower().replace('-', '_'), v) for k, v in d.iteritems()])


def format_header_key(k):
    """Convert underscores to dashes and capitalize intra-dash strings."""
    return '-'.join([x.capitalize() for x in k.replace('_', '-').split('-')])


def get_header_prefix(request, prefix):
    """Get all prefix-* request headers in a dict.
       Reformat keys with format_header_key()."""

    prefix = 'HTTP_' + prefix.upper().replace('-', '_')
    # TODO: Document or remove '~' replacing.
    return dict([(format_header_key(k[5:]), v.replace('~', ''))
                for k, v in request.META.iteritems()
                if k.startswith(prefix) and len(k) > len(prefix)])


def check_meta_headers(meta):
    if len(meta) > 90:
        raise faults.BadRequest('Too many headers.')
    for k, v in meta.iteritems():
        if len(k) > 128:
            raise faults.BadRequest('Header name too large.')
        if len(v) > 256:
            raise faults.BadRequest('Header value too large.')


def get_account_headers(request):
    meta = get_header_prefix(request, 'X-Account-Meta-')
    check_meta_headers(meta)
    groups = {}
    for k, v in get_header_prefix(request, 'X-Account-Group-').iteritems():
        n = k[16:].lower()
        if '-' in n or '_' in n:
            raise faults.BadRequest('Bad characters in group name')
        groups[n] = v.replace(' ', '').split(',')
        while '' in groups[n]:
            groups[n].remove('')
    return meta, groups


def put_account_headers(response, meta, groups, policy):
    if 'count' in meta:
        response['X-Account-Container-Count'] = meta['count']
    if 'bytes' in meta:
        response['X-Account-Bytes-Used'] = meta['bytes']
    response['Last-Modified'] = http_date(int(meta['modified']))
    for k in [x for x in meta.keys() if x.startswith('X-Account-Meta-')]:
        response[smart_str(
            k, strings_only=True)] = smart_str(meta[k], strings_only=True)
    if 'until_timestamp' in meta:
        response['X-Account-Until-Timestamp'] = http_date(
            int(meta['until_timestamp']))
    for k, v in groups.iteritems():
        k = smart_str(k, strings_only=True)
        k = format_header_key('X-Account-Group-' + k)
        v = smart_str(','.join(v), strings_only=True)
        response[k] = v
    for k, v in policy.iteritems():
        response[smart_str(format_header_key('X-Account-Policy-' + k),
                 strings_only=True)] = smart_str(v, strings_only=True)


def get_container_headers(request):
    meta = get_header_prefix(request, 'X-Container-Meta-')
    check_meta_headers(meta)
    policy = dict([(k[19:].lower(), v.replace(' ', '')) for k, v in
                  get_header_prefix(request,
                                    'X-Container-Policy-').iteritems()])
    return meta, policy


def put_container_headers(request, response, meta, policy):
    if 'count' in meta:
        response['X-Container-Object-Count'] = meta['count']
    if 'bytes' in meta:
        response['X-Container-Bytes-Used'] = meta['bytes']
    response['Last-Modified'] = http_date(int(meta['modified']))
    for k in [x for x in meta.keys() if x.startswith('X-Container-Meta-')]:
        response[smart_str(
            k, strings_only=True)] = smart_str(meta[k], strings_only=True)
    l = [smart_str(x, strings_only=True) for x in meta['object_meta']
         if x.startswith('X-Object-Meta-')]
    response['X-Container-Object-Meta'] = ','.join([x[14:] for x in l])
    response['X-Container-Block-Size'] = request.backend.block_size
    response['X-Container-Block-Hash'] = request.backend.hash_algorithm
    if 'until_timestamp' in meta:
        response['X-Container-Until-Timestamp'] = http_date(
            int(meta['until_timestamp']))
    for k, v in policy.iteritems():
        response[smart_str(format_header_key('X-Container-Policy-' + k),
                           strings_only=True)] = smart_str(v, strings_only=True)


def get_object_headers(request):
    content_type = request.META.get('CONTENT_TYPE', None)
    meta = get_header_prefix(request, 'X-Object-Meta-')
    check_meta_headers(meta)
    if request.META.get('HTTP_CONTENT_ENCODING'):
        meta['Content-Encoding'] = request.META['HTTP_CONTENT_ENCODING']
    if request.META.get('HTTP_CONTENT_DISPOSITION'):
        meta['Content-Disposition'] = request.META['HTTP_CONTENT_DISPOSITION']
    if request.META.get('HTTP_X_OBJECT_MANIFEST'):
        meta['X-Object-Manifest'] = request.META['HTTP_X_OBJECT_MANIFEST']
    return content_type, meta, get_sharing(request), get_public(request)


def put_object_headers(response, meta, restricted=False, token=None):
    response['ETag'] = meta['checksum']
    response['Content-Length'] = meta['bytes']
    response.override_serialization = True
    response['Content-Type'] = meta.get('type', 'application/octet-stream')
    response['Last-Modified'] = http_date(int(meta['modified']))
    if not restricted:
        response['X-Object-Hash'] = meta['hash']
        response['X-Object-UUID'] = meta['uuid']
        if TRANSLATE_UUIDS:
            meta['modified_by'] = \
                retrieve_displayname(token, meta['modified_by'])
        response['X-Object-Modified-By'] = smart_str(
            meta['modified_by'], strings_only=True)
        response['X-Object-Version'] = meta['version']
        response['X-Object-Version-Timestamp'] = http_date(
            int(meta['version_timestamp']))
        for k in [x for x in meta.keys() if x.startswith('X-Object-Meta-')]:
            response[smart_str(
                k, strings_only=True)] = smart_str(meta[k], strings_only=True)
        for k in (
            'Content-Encoding', 'Content-Disposition', 'X-Object-Manifest',
            'X-Object-Sharing', 'X-Object-Shared-By', 'X-Object-Allowed-To',
                'X-Object-Public'):
            if k in meta:
                response[k] = smart_str(meta[k], strings_only=True)
    else:
        for k in ('Content-Encoding', 'Content-Disposition'):
            if k in meta:
                response[k] = smart_str(meta[k], strings_only=True)


def update_manifest_meta(request, v_account, meta):
    """Update metadata if the object has an X-Object-Manifest."""

    if 'X-Object-Manifest' in meta:
        etag = ''
        bytes = 0
        try:
            src_container, src_name = split_container_object_string(
                '/' + meta['X-Object-Manifest'])
            objects = request.backend.list_objects(
                request.user_uniq, v_account,
                src_container, prefix=src_name, virtual=False)
            for x in objects:
                src_meta = request.backend.get_object_meta(request.user_uniq,
                                                           v_account,
                                                           src_container,
                                                           x[0], 'pithos', x[1])
                etag += src_meta['checksum']
                bytes += src_meta['bytes']
        except:
            # Ignore errors.
            return
        meta['bytes'] = bytes
        md5 = hashlib.md5()
        md5.update(etag)
        meta['checksum'] = md5.hexdigest().lower()


def is_uuid(str):
    if str is None:
        return False
    try:
        uuid.UUID(str)
    except ValueError:
        return False
    else:
        return True


##########################
# USER CATALOG utilities #
##########################

def retrieve_displayname(token, uuid, fail_silently=True):
    astakos = AstakosClient(ASTAKOS_BASE_URL, retry=2, use_pool=True,
                            logger=logger)
    try:
        displayname = astakos.get_username(token, uuid)
    except NoUserName:
        if not fail_silently:
            raise ItemNotExists(uuid)
        else:
            # just return the uuid
            return uuid
    return displayname


def retrieve_displaynames(token, uuids, return_dict=False, fail_silently=True):
    astakos = AstakosClient(ASTAKOS_BASE_URL, retry=2, use_pool=True,
                            logger=logger)
    catalog = astakos.get_usernames(token, uuids) or {}
    missing = list(set(uuids) - set(catalog))
    if missing and not fail_silently:
        raise ItemNotExists('Unknown displaynames: %s' % ', '.join(missing))
    return catalog if return_dict else [catalog.get(i) for i in uuids]


def retrieve_uuid(token, displayname):
    if is_uuid(displayname):
        return displayname

    astakos = AstakosClient(ASTAKOS_BASE_URL, retry=2, use_pool=True,
                            logger=logger)
    try:
        uuid = astakos.get_uuid(token, displayname)
    except NoUUID:
        raise ItemNotExists(displayname)
    return uuid


def retrieve_uuids(token, displaynames, return_dict=False, fail_silently=True):
    astakos = AstakosClient(ASTAKOS_BASE_URL, retry=2, use_pool=True,
                            logger=logger)
    catalog = astakos.get_uuids(token, displaynames) or {}
    missing = list(set(displaynames) - set(catalog))
    if missing and not fail_silently:
        raise ItemNotExists('Unknown uuids: %s' % ', '.join(missing))
    return catalog if return_dict else [catalog.get(i) for i in displaynames]


def replace_permissions_displayname(token, holder):
    if holder == '*':
        return holder
    try:
        # check first for a group permission
        account, group = holder.split(':', 1)
    except ValueError:
        return retrieve_uuid(token, holder)
    else:
        return ':'.join([retrieve_uuid(token, account), group])


def replace_permissions_uuid(token, holder):
    if holder == '*':
        return holder
    try:
        # check first for a group permission
        account, group = holder.split(':', 1)
    except ValueError:
        return retrieve_displayname(token, holder)
    else:
        return ':'.join([retrieve_displayname(token, account), group])


def update_sharing_meta(request, permissions, v_account,
                        v_container, v_object, meta):
    if permissions is None:
        return
    allowed, perm_path, perms = permissions
    if len(perms) == 0:
        return

    # replace uuid with displayname
    if TRANSLATE_UUIDS:
        perms['read'] = [replace_permissions_uuid(
            getattr(request, 'token', None), x)
            for x in perms.get('read', [])]
        perms['write'] = [replace_permissions_uuid(
            getattr(request, 'token', None), x)
            for x in perms.get('write', [])]

    ret = []

    r = ','.join(perms.get('read', []))
    if r:
        ret.append('read=' + r)
    w = ','.join(perms.get('write', []))
    if w:
        ret.append('write=' + w)
    meta['X-Object-Sharing'] = '; '.join(ret)
    if '/'.join((v_account, v_container, v_object)) != perm_path:
        meta['X-Object-Shared-By'] = perm_path
    if request.user_uniq != v_account:
        meta['X-Object-Allowed-To'] = allowed


def update_public_meta(public, meta):
    if not public:
        return
    meta['X-Object-Public'] = join_urls(
        BASE_HOST, reverse('pithos.api.public.public_demux', args=(public,)))


def validate_modification_preconditions(request, meta):
    """Check that the modified timestamp conforms with the preconditions set."""

    if 'modified' not in meta:
        return  # TODO: Always return?

    if_modified_since = request.META.get('HTTP_IF_MODIFIED_SINCE')
    if if_modified_since is not None:
        if_modified_since = parse_http_date_safe(if_modified_since)
    if (if_modified_since is not None
            and int(meta['modified']) <= if_modified_since):
        raise faults.NotModified('Resource has not been modified')

    if_unmodified_since = request.META.get('HTTP_IF_UNMODIFIED_SINCE')
    if if_unmodified_since is not None:
        if_unmodified_since = parse_http_date_safe(if_unmodified_since)
    if (if_unmodified_since is not None
            and int(meta['modified']) > if_unmodified_since):
        raise faults.PreconditionFailed('Resource has been modified')


def validate_matching_preconditions(request, meta):
    """Check that the ETag conforms with the preconditions set."""

    etag = meta['checksum']
    if not etag:
        etag = None

    if_match = request.META.get('HTTP_IF_MATCH')
    if if_match is not None:
        if etag is None:
            raise faults.PreconditionFailed('Resource does not exist')
        if (if_match != '*'
                and etag not in [x.lower() for x in parse_etags(if_match)]):
            raise faults.PreconditionFailed('Resource ETag does not match')

    if_none_match = request.META.get('HTTP_IF_NONE_MATCH')
    if if_none_match is not None:
        # TODO: If this passes, must ignore If-Modified-Since header.
        if etag is not None:
            if (if_none_match == '*'
                    or etag in [x.lower() for x in parse_etags(if_none_match)]):
                # TODO: Continue if an If-Modified-Since header is present.
                if request.method in ('HEAD', 'GET'):
                    raise faults.NotModified('Resource ETag matches')
                raise faults.PreconditionFailed(
                    'Resource exists or ETag matches')


def split_container_object_string(s):
    if not len(s) > 0 or s[0] != '/':
        raise ValueError
    s = s[1:]
    pos = s.find('/')
    if pos == -1 or pos == len(s) - 1:
        raise ValueError
    return s[:pos], s[(pos + 1):]


def copy_or_move_object(request, src_account, src_container, src_name,
                        dest_account, dest_container, dest_name,
                        move=False, delimiter=None):
    """Copy or move an object."""

    if 'ignore_content_type' in request.GET and 'CONTENT_TYPE' in request.META:
        del(request.META['CONTENT_TYPE'])
    content_type, meta, permissions, public = get_object_headers(request)
    src_version = request.META.get('HTTP_X_SOURCE_VERSION')
    try:
        if move:
            version_id = request.backend.move_object(
                request.user_uniq, src_account, src_container, src_name,
                dest_account, dest_container, dest_name,
                content_type, 'pithos', meta, False, permissions, delimiter)
        else:
            version_id = request.backend.copy_object(
                request.user_uniq, src_account, src_container, src_name,
                dest_account, dest_container, dest_name,
                content_type, 'pithos', meta, False, permissions,
                src_version, delimiter)
    except NotAllowedError:
        raise faults.Forbidden('Not allowed')
    except (ItemNotExists, VersionNotExists):
        raise faults.ItemNotFound('Container or object does not exist')
    except ValueError:
        raise faults.BadRequest('Invalid sharing header')
    except QuotaError, e:
        raise faults.RequestEntityTooLarge('Quota error: %s' % e)
    if public is not None:
        try:
            request.backend.update_object_public(
                request.user_uniq, dest_account,
                dest_container, dest_name, public)
        except NotAllowedError:
            raise faults.Forbidden('Not allowed')
        except ItemNotExists:
            raise faults.ItemNotFound('Object does not exist')
    return version_id


def get_int_parameter(p):
    if p is not None:
        try:
            p = int(p)
        except ValueError:
            return None
        if p < 0:
            return None
    return p


def get_content_length(request):
    content_length = get_int_parameter(request.META.get('CONTENT_LENGTH'))
    if content_length is None:
        raise faults.LengthRequired('Missing or invalid Content-Length header')
    return content_length


def get_range(request, size):
    """Parse a Range header from the request.

    Either returns None, when the header is not existent or should be ignored,
    or a list of (offset, length) tuples - should be further checked.
    """

    ranges = request.META.get('HTTP_RANGE', '').replace(' ', '')
    if not ranges.startswith('bytes='):
        return None

    ret = []
    for r in (x.strip() for x in ranges[6:].split(',')):
        p = re.compile('^(?P<offset>\d*)-(?P<upto>\d*)$')
        m = p.match(r)
        if not m:
            return None
        offset = m.group('offset')
        upto = m.group('upto')
        if offset == '' and upto == '':
            return None

        if offset != '':
            offset = int(offset)
            if upto != '':
                upto = int(upto)
                if offset > upto:
                    return None
                ret.append((offset, upto - offset + 1))
            else:
                ret.append((offset, size - offset))
        else:
            length = int(upto)
            ret.append((size - length, length))

    return ret


def get_content_range(request):
    """Parse a Content-Range header from the request.

    Either returns None, when the header is not existent or should be ignored,
    or an (offset, length, total) tuple - check as length, total may be None.
    Returns (None, None, None) if the provided range is '*/*'.
    """

    ranges = request.META.get('HTTP_CONTENT_RANGE', '')
    if not ranges:
        return None

    p = re.compile('^bytes (?P<offset>\d+)-(?P<upto>\d*)/(?P<total>(\d+|\*))$')
    m = p.match(ranges)
    if not m:
        if ranges == 'bytes */*':
            return (None, None, None)
        return None
    offset = int(m.group('offset'))
    upto = m.group('upto')
    total = m.group('total')
    if upto != '':
        upto = int(upto)
    else:
        upto = None
    if total != '*':
        total = int(total)
    else:
        total = None
    if (upto is not None and offset > upto) or \
        (total is not None and offset >= total) or \
            (total is not None and upto is not None and upto >= total):
        return None

    if upto is None:
        length = None
    else:
        length = upto - offset + 1
    return (offset, length, total)


def get_sharing(request):
    """Parse an X-Object-Sharing header from the request.

    Raises BadRequest on error.
    """

    permissions = request.META.get('HTTP_X_OBJECT_SHARING')
    if permissions is None:
        return None

    # TODO: Document or remove '~' replacing.
    permissions = permissions.replace('~', '')

    ret = {}
    permissions = permissions.replace(' ', '')
    if permissions == '':
        return ret
    for perm in (x for x in permissions.split(';')):
        if perm.startswith('read='):
            ret['read'] = list(set(
                [v.replace(' ', '').lower() for v in perm[5:].split(',')]))
            if '' in ret['read']:
                ret['read'].remove('')
            if '*' in ret['read']:
                ret['read'] = ['*']
            if len(ret['read']) == 0:
                raise faults.BadRequest(
                    'Bad X-Object-Sharing header value: invalid length')
        elif perm.startswith('write='):
            ret['write'] = list(set(
                [v.replace(' ', '').lower() for v in perm[6:].split(',')]))
            if '' in ret['write']:
                ret['write'].remove('')
            if '*' in ret['write']:
                ret['write'] = ['*']
            if len(ret['write']) == 0:
                raise faults.BadRequest(
                    'Bad X-Object-Sharing header value: invalid length')
        else:
            raise faults.BadRequest(
                'Bad X-Object-Sharing header value: missing prefix')

    # replace displayname with uuid
    if TRANSLATE_UUIDS:
        try:
            ret['read'] = [replace_permissions_displayname(
                getattr(request, 'token', None), x)
                for x in ret.get('read', [])]
            ret['write'] = [replace_permissions_displayname(
                getattr(request, 'token', None), x)
                for x in ret.get('write', [])]
        except ItemNotExists, e:
            raise faults.BadRequest(
                'Bad X-Object-Sharing header value: unknown account: %s' % e)

    # Keep duplicates only in write list.
    dups = [x for x in ret.get(
        'read', []) if x in ret.get('write', []) and x != '*']
    if dups:
        for x in dups:
            ret['read'].remove(x)
        if len(ret['read']) == 0:
            del(ret['read'])

    return ret


def get_public(request):
    """Parse an X-Object-Public header from the request.

    Raises BadRequest on error.
    """

    public = request.META.get('HTTP_X_OBJECT_PUBLIC')
    if public is None:
        return None

    public = public.replace(' ', '').lower()
    if public == 'true':
        return True
    elif public == 'false' or public == '':
        return False
    raise faults.BadRequest('Bad X-Object-Public header value')


def raw_input_socket(request):
    """Return the socket for reading the rest of the request."""

    server_software = request.META.get('SERVER_SOFTWARE')
    if server_software and server_software.startswith('mod_python'):
        return request._req
    if 'wsgi.input' in request.environ:
        return request.environ['wsgi.input']
    raise NotImplemented('Unknown server software')

MAX_UPLOAD_SIZE = 5 * (1024 * 1024 * 1024)  # 5GB


def socket_read_iterator(request, length=0, blocksize=4096):
    """Return a maximum of blocksize data read from the socket in each iteration

    Read up to 'length'. If 'length' is negative, will attempt a chunked read.
    The maximum ammount of data read is controlled by MAX_UPLOAD_SIZE.
    """

    sock = raw_input_socket(request)
    if length < 0:  # Chunked transfers
        # Small version (server does the dechunking).
        if (request.environ.get('mod_wsgi.input_chunked', None)
                or request.META['SERVER_SOFTWARE'].startswith('gunicorn')):
            while length < MAX_UPLOAD_SIZE:
                data = sock.read(blocksize)
                if data == '':
                    return
                yield data
            raise faults.BadRequest('Maximum size is reached')

        # Long version (do the dechunking).
        data = ''
        while length < MAX_UPLOAD_SIZE:
            # Get chunk size.
            if hasattr(sock, 'readline'):
                chunk_length = sock.readline()
            else:
                chunk_length = ''
                while chunk_length[-1:] != '\n':
                    chunk_length += sock.read(1)
                chunk_length.strip()
            pos = chunk_length.find(';')
            if pos >= 0:
                chunk_length = chunk_length[:pos]
            try:
                chunk_length = int(chunk_length, 16)
            except Exception:
                raise faults.BadRequest('Bad chunk size')
                                 # TODO: Change to something more appropriate.
            # Check if done.
            if chunk_length == 0:
                if len(data) > 0:
                    yield data
                return
            # Get the actual data.
            while chunk_length > 0:
                chunk = sock.read(min(chunk_length, blocksize))
                chunk_length -= len(chunk)
                if length > 0:
                    length += len(chunk)
                data += chunk
                if len(data) >= blocksize:
                    ret = data[:blocksize]
                    data = data[blocksize:]
                    yield ret
            sock.read(2)  # CRLF
        raise faults.BadRequest('Maximum size is reached')
    else:
        if length > MAX_UPLOAD_SIZE:
            raise faults.BadRequest('Maximum size is reached')
        while length > 0:
            data = sock.read(min(length, blocksize))
            if not data:
                raise faults.BadRequest()
            length -= len(data)
            yield data


class SaveToBackendHandler(FileUploadHandler):
    """Handle a file from an HTML form the django way."""

    def __init__(self, request=None):
        super(SaveToBackendHandler, self).__init__(request)
        self.backend = request.backend

    def put_data(self, length):
        if len(self.data) >= length:
            block = self.data[:length]
            self.file.hashmap.append(self.backend.put_block(block))
            self.md5.update(block)
            self.data = self.data[length:]

    def new_file(self, field_name, file_name, content_type,
                 content_length, charset=None):
        self.md5 = hashlib.md5()
        self.data = ''
        self.file = UploadedFile(
            name=file_name, content_type=content_type, charset=charset)
        self.file.size = 0
        self.file.hashmap = []

    def receive_data_chunk(self, raw_data, start):
        self.data += raw_data
        self.file.size += len(raw_data)
        self.put_data(self.request.backend.block_size)
        return None

    def file_complete(self, file_size):
        l = len(self.data)
        if l > 0:
            self.put_data(l)
        self.file.etag = self.md5.hexdigest().lower()
        return self.file


class ObjectWrapper(object):
    """Return the object's data block-per-block in each iteration.

    Read from the object using the offset and length provided
    in each entry of the range list.
    """

    def __init__(self, backend, ranges, sizes, hashmaps, boundary):
        self.backend = backend
        self.ranges = ranges
        self.sizes = sizes
        self.hashmaps = hashmaps
        self.boundary = boundary
        self.size = sum(self.sizes)

        self.file_index = 0
        self.block_index = 0
        self.block_hash = -1
        self.block = ''

        self.range_index = -1
        self.offset, self.length = self.ranges[0]

    def __iter__(self):
        return self

    def part_iterator(self):
        if self.length > 0:
            # Get the file for the current offset.
            file_size = self.sizes[self.file_index]
            while self.offset >= file_size:
                self.offset -= file_size
                self.file_index += 1
                file_size = self.sizes[self.file_index]

            # Get the block for the current position.
            self.block_index = int(self.offset / self.backend.block_size)
            if self.block_hash != \
                    self.hashmaps[self.file_index][self.block_index]:
                self.block_hash = self.hashmaps[
                    self.file_index][self.block_index]
                try:
                    self.block = self.backend.get_block(self.block_hash)
                except ItemNotExists:
                    raise faults.ItemNotFound('Block does not exist')

            # Get the data from the block.
            bo = self.offset % self.backend.block_size
            bs = self.backend.block_size
            if (self.block_index == len(self.hashmaps[self.file_index]) - 1 and
                    self.sizes[self.file_index] % self.backend.block_size):
                bs = self.sizes[self.file_index] % self.backend.block_size
            bl = min(self.length, bs - bo)
            data = self.block[bo:bo + bl]
            self.offset += bl
            self.length -= bl
            return data
        else:
            raise StopIteration

    def next(self):
        if len(self.ranges) == 1:
            return self.part_iterator()
        if self.range_index == len(self.ranges):
            raise StopIteration
        try:
            if self.range_index == -1:
                raise StopIteration
            return self.part_iterator()
        except StopIteration:
            self.range_index += 1
            out = []
            if self.range_index < len(self.ranges):
                # Part header.
                self.offset, self.length = self.ranges[self.range_index]
                self.file_index = 0
                if self.range_index > 0:
                    out.append('')
                out.append('--' + self.boundary)
                out.append('Content-Range: bytes %d-%d/%d' % (
                    self.offset, self.offset + self.length - 1, self.size))
                out.append('Content-Transfer-Encoding: binary')
                out.append('')
                out.append('')
                return '\r\n'.join(out)
            else:
                # Footer.
                out.append('')
                out.append('--' + self.boundary + '--')
                out.append('')
                return '\r\n'.join(out)


def object_data_response(request, sizes, hashmaps, meta, public=False):
    """Get the HttpResponse object for replying with the object's data."""

    # Range handling.
    size = sum(sizes)
    ranges = get_range(request, size)
    if ranges is None:
        ranges = [(0, size)]
        ret = 200
    else:
        check = [True for offset, length in ranges if
                 length <= 0 or length > size or
                 offset < 0 or offset >= size or
                 offset + length > size]
        if len(check) > 0:
            raise faults.RangeNotSatisfiable(
                'Requested range exceeds object limits')
        ret = 206
        if_range = request.META.get('HTTP_IF_RANGE')
        if if_range:
            try:
                # Modification time has passed instead.
                last_modified = parse_http_date(if_range)
                if last_modified != meta['modified']:
                    ranges = [(0, size)]
                    ret = 200
            except ValueError:
                if if_range != meta['checksum']:
                    ranges = [(0, size)]
                    ret = 200

    if ret == 206 and len(ranges) > 1:
        boundary = uuid.uuid4().hex
    else:
        boundary = ''
    wrapper = ObjectWrapper(request.backend, ranges, sizes, hashmaps, boundary)
    response = HttpResponse(wrapper, status=ret)
    put_object_headers(
        response, meta, restricted=public,
        token=getattr(request, 'token', None))
    if ret == 206:
        if len(ranges) == 1:
            offset, length = ranges[0]
            response[
                'Content-Length'] = length  # Update with the correct length.
            response['Content-Range'] = 'bytes %d-%d/%d' % (
                offset, offset + length - 1, size)
        else:
            del(response['Content-Length'])
            response['Content-Type'] = 'multipart/byteranges; boundary=%s' % (
                boundary,)
    return response


def put_object_block(request, hashmap, data, offset):
    """Put one block of data at the given offset."""

    bi = int(offset / request.backend.block_size)
    bo = offset % request.backend.block_size
    bl = min(len(data), request.backend.block_size - bo)
    if bi < len(hashmap):
        hashmap[bi] = request.backend.update_block(hashmap[bi], data[:bl], bo)
    else:
        hashmap.append(request.backend.put_block(('\x00' * bo) + data[:bl]))
    return bl  # Return ammount of data written.


def hashmap_md5(backend, hashmap, size):
    """Produce the MD5 sum from the data in the hashmap."""

    # TODO: Search backend for the MD5 of another object
    #       with the same hashmap and size...
    md5 = hashlib.md5()
    bs = backend.block_size
    for bi, hash in enumerate(hashmap):
        data = backend.get_block(hash)  # Blocks come in padded.
        if bi == len(hashmap) - 1:
            data = data[:size % bs]
        md5.update(data)
    return md5.hexdigest().lower()


def simple_list_response(request, l):
    if request.serialization == 'text':
        return '\n'.join(l) + '\n'
    if request.serialization == 'xml':
        return render_to_string('items.xml', {'items': l})
    if request.serialization == 'json':
        return json.dumps(l)


from pithos.backends.util import PithosBackendPool

if RADOS_STORAGE:
    BLOCK_PARAMS = {'mappool': RADOS_POOL_MAPS,
                    'blockpool': RADOS_POOL_BLOCKS, }
else:
    BLOCK_PARAMS = {'mappool': None,
                    'blockpool': None, }


_pithos_backend_pool = PithosBackendPool(
        size=BACKEND_POOL_SIZE,
        db_module=BACKEND_DB_MODULE,
        db_connection=BACKEND_DB_CONNECTION,
        block_module=BACKEND_BLOCK_MODULE,
        block_path=BACKEND_BLOCK_PATH,
        block_umask=BACKEND_BLOCK_UMASK,
        queue_module=BACKEND_QUEUE_MODULE,
        queue_hosts=BACKEND_QUEUE_HOSTS,
        queue_exchange=BACKEND_QUEUE_EXCHANGE,
        astakos_url=ASTAKOS_BASE_URL,
        service_token=SERVICE_TOKEN,
        astakosclient_poolsize=ASTAKOSCLIENT_POOLSIZE,
        free_versioning=BACKEND_FREE_VERSIONING,
        block_params=BLOCK_PARAMS,
        public_url_security=PUBLIC_URL_SECURITY,
        public_url_alphabet=PUBLIC_URL_ALPHABET,
        account_quota_policy=BACKEND_ACCOUNT_QUOTA,
        container_quota_policy=BACKEND_CONTAINER_QUOTA,
        container_versioning_policy=BACKEND_VERSIONING)


def get_backend():
    backend = _pithos_backend_pool.pool_get()
    backend.messages = []
    return backend


def update_request_headers(request):
    # Handle URL-encoded keys and values.
    meta = dict([(
        k, v) for k, v in request.META.iteritems() if k.startswith('HTTP_')])
    for k, v in meta.iteritems():
        try:
            k.decode('ascii')
            v.decode('ascii')
        except UnicodeDecodeError:
            raise faults.BadRequest('Bad character in headers.')
        if '%' in k or '%' in v:
            del(request.META[k])
            request.META[unquote(k)] = smart_unicode(unquote(
                v), strings_only=True)


def update_response_headers(request, response):
    # URL-encode unicode in headers.
    meta = response.items()
    for k, v in meta:
        if (k.startswith('X-Account-') or k.startswith('X-Container-') or
                k.startswith('X-Object-') or k.startswith('Content-')):
            del(response[k])
            response[quote(k)] = quote(v, safe='/=,:@; ')


def get_pithos_usage(token):
    """Get Pithos Usage from astakos."""
    astakos = AstakosClient(ASTAKOS_BASE_URL, retry=2, use_pool=True,
                            logger=logger)
    quotas = astakos.get_quotas(token)['system']
    pithos_resources = [r['name'] for r in resources]
    map(quotas.pop, filter(lambda k: k not in pithos_resources, quotas.keys()))
    return quotas.popitem()[-1] # assume only one resource


def api_method(http_method=None, token_required=True, user_required=True, logger=None,
               format_allowed=False, serializations=None,
               strict_serlization=False):
    serializations = serializations or ['json', 'xml']
    def decorator(func):
        @api.api_method(http_method=http_method, token_required=token_required,
                        user_required=user_required,
                        logger=logger, format_allowed=format_allowed,
                        astakos_url=ASTAKOS_BASE_URL,
                        serializations=serializations,
                        strict_serlization=strict_serlization)
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # The args variable may contain up to (account, container, object).
            if len(args) > 1 and len(args[1]) > 256:
                raise faults.BadRequest("Container name too large")
            if len(args) > 2 and len(args[2]) > 1024:
                raise faults.BadRequest('Object name too large.')

            try:
                # Add a PithosBackend as attribute of the request object
                request.backend = get_backend()
                request.backend.lock_container_path = lock_container_path
                request.backend.wrapper.execute()
                request.backend.serials = []
                request.backend.messages = []

                # Many API method expect thet X-Auth-Token in request,token
                request.token = request.x_auth_token
                update_request_headers(request)
                response = func(request, *args, **kwargs)
                update_response_headers(request, response)

                # send messages produced
                for m in request.backend.messages:
                    request.backend.queue.send(*m)

                # register serials
                if request.backend.serials:
                    request.backend.commission_serials.insert_many(
                        request.backend.serials)

                    # commit to ensure that the serials are registered
                    # even if resolve commission fails
                    request.backend.wrapper.commit()

                    # start new transaction
                    request.backend.wrapper.execute()

                    r = request.backend.astakosclient.resolve_commissions(
                                token=request.backend.service_token,
                                accept_serials=request.backend.serials,
                                reject_serials=[])
                    request.backend.commission_serials.delete_many(
                        r['accepted'])

                request.backend.wrapper.commit()
                return response
            except:
                if request.backend.serials:
                    request.backend.astakosclient.resolve_commissions(
                        token=request.backend.service_token,
                        accept_serials=[],
                        reject_serials=request.backend.serials)
                request.backend.wrapper.rollback()
                raise
            finally:
                # Always close PithosBackend connection
                if getattr(request, "backend", None) is not None:
                    request.backend.close()
        return wrapper
    return decorator


def get_token_from_cookie(request):
    assert(request.method == 'GET'),\
        "Cookie based authentication is only allowed to GET requests"
    token = None
    if COOKIE_NAME in request.COOKIES:
        cookie_value = unquote(request.COOKIES.get(COOKIE_NAME, ''))
        account, sep, token = cookie_value.partition('|')
    return token


def view_method():
    """Decorator function for views."""

    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            request.META['HTTP_X_AUTH_TOKEN'] = get_token_from_cookie(request)
            # Get the response object
            response = func(request, *args, **kwargs)
            if response.status_code == 200:
                return response
            elif response.status_code == 404:
                raise Http404()
            elif response.status_code in [401, 403]:
                return HttpResponseForbidden()
            else:
                raise Exception(response)
        return wrapper
    return decorator
