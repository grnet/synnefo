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

from functools import wraps
from time import time
from traceback import format_exc
from wsgiref.handlers import format_date_time
from binascii import hexlify

from django.conf import settings
from django.http import HttpResponse
from django.utils.http import http_date, parse_etags

from pithos.api.compat import parse_http_date_safe
from pithos.api.faults import (Fault, NotModified, BadRequest, ItemNotFound, LengthRequired,
                                PreconditionFailed, ServiceUnavailable)
from pithos.backends import backend

import datetime
import logging
import re
import hashlib


logger = logging.getLogger(__name__)


def printable_meta_dict(d):
    """Format a meta dictionary for printing out json/xml.
    
    Convert all keys to lower case and replace dashes to underscores.
    Change 'modified' key from backend to 'last_modified' and format date.
    """
    if 'modified' in d:
        d['last_modified'] = datetime.datetime.fromtimestamp(int(d['modified'])).isoformat()
        del(d['modified'])
    return dict([(k.lower().replace('-', '_'), v) for k, v in d.iteritems()])

def format_meta_key(k):
    """Convert underscores to dashes and capitalize intra-dash strings"""
    return '-'.join([x.capitalize() for x in k.replace('_', '-').split('-')])

def get_meta_prefix(request, prefix):
    """Get all prefix-* request headers in a dict. Reformat keys with format_meta_key()"""
    prefix = 'HTTP_' + prefix.upper().replace('-', '_')
    return dict([(format_meta_key(k[5:]), v) for k, v in request.META.iteritems() if k.startswith(prefix)])

def get_account_meta(request):
    """Get metadata from an account request"""
    meta = get_meta_prefix(request, 'X-Account-Meta-')    
    return meta

def put_account_meta(response, meta):
    """Put metadata in an account response"""
    response['X-Account-Container-Count'] = meta['count']
    response['X-Account-Bytes-Used'] = meta['bytes']
    if 'modified' in meta:
        response['Last-Modified'] = http_date(int(meta['modified']))
    for k in [x for x in meta.keys() if x.startswith('X-Account-Meta-')]:
        response[k.encode('utf-8')] = meta[k].encode('utf-8')

def get_container_meta(request):
    """Get metadata from a container request"""
    meta = get_meta_prefix(request, 'X-Container-Meta-')
    return meta

def put_container_meta(response, meta):
    """Put metadata in a container response"""
    response['X-Container-Object-Count'] = meta['count']
    response['X-Container-Bytes-Used'] = meta['bytes']
    if 'modified' in meta:
        response['Last-Modified'] = http_date(int(meta['modified']))
    for k in [x for x in meta.keys() if x.startswith('X-Container-Meta-')]:
        response[k.encode('utf-8')] = meta[k].encode('utf-8')
    response['X-Container-Object-Meta'] = [x[14:] for x in meta['object_meta'] if x.startswith('X-Object-Meta-')]
    response['X-Container-Block-Size'] = backend.block_size
    response['X-Container-Block-Hash'] = backend.hash_algorithm

def get_object_meta(request):
    """Get metadata from an object request"""
    meta = get_meta_prefix(request, 'X-Object-Meta-')
    if request.META.get('CONTENT_TYPE'):
        meta['Content-Type'] = request.META['CONTENT_TYPE']
    if request.META.get('HTTP_CONTENT_ENCODING'):
        meta['Content-Encoding'] = request.META['HTTP_CONTENT_ENCODING']
    if request.META.get('HTTP_CONTENT_DISPOSITION'):
        meta['Content-Disposition'] = request.META['HTTP_CONTENT_DISPOSITION']
    if request.META.get('HTTP_X_OBJECT_MANIFEST'):
        meta['X-Object-Manifest'] = request.META['HTTP_X_OBJECT_MANIFEST']
    return meta

def put_object_meta(response, meta):
    """Put metadata in an object response"""
    response['ETag'] = meta['hash']
    response['Content-Length'] = meta['bytes']
    response['Content-Type'] = meta.get('Content-Type', 'application/octet-stream')
    response['Last-Modified'] = http_date(int(meta['modified']))
    for k in [x for x in meta.keys() if x.startswith('X-Object-Meta-')]:
        response[k.encode('utf-8')] = meta[k].encode('utf-8')
    for k in ('Content-Encoding', 'Content-Disposition', 'X-Object-Manifest'):
        if k in meta:
            response[k] = meta[k]

def validate_modification_preconditions(request, meta):
    """Check that the modified timestamp conforms with the preconditions set"""
    if 'modified' not in meta:
        return # TODO: Always return?
    
    if_modified_since = request.META.get('HTTP_IF_MODIFIED_SINCE')
    if if_modified_since is not None:
        if_modified_since = parse_http_date_safe(if_modified_since)
    if if_modified_since is not None and int(meta['modified']) <= if_modified_since:
        raise NotModified('Resource has not been modified')
    
    if_unmodified_since = request.META.get('HTTP_IF_UNMODIFIED_SINCE')
    if if_unmodified_since is not None:
        if_unmodified_since = parse_http_date_safe(if_unmodified_since)
    if if_unmodified_since is not None and int(meta['modified']) > if_unmodified_since:
        raise PreconditionFailed('Resource has been modified')

def validate_matching_preconditions(request, meta):
    """Check that the ETag conforms with the preconditions set"""
    if 'hash' not in meta:
        return # TODO: Always return?
    
    if_match = request.META.get('HTTP_IF_MATCH')
    if if_match is not None and if_match != '*':
        if meta['hash'] not in [x.lower() for x in parse_etags(if_match)]:
            raise PreconditionFailed('Resource Etag does not match')
    
    if_none_match = request.META.get('HTTP_IF_NONE_MATCH')
    if if_none_match is not None:
        if if_none_match == '*' or meta['hash'] in [x.lower() for x in parse_etags(if_none_match)]:
            raise NotModified('Resource Etag matches')

def copy_or_move_object(request, src_path, dest_path, move=False):
    """Copy or move an object"""
    if type(src_path) == str:
        parts = src_path.split('/')
        if len(parts) < 3 or parts[0] != '':
            raise BadRequest('Invalid X-Copy-From or X-Move-From header')
        src_container = parts[1]
        src_name = '/'.join(parts[2:])
    elif type(src_path) == tuple and len(src_path) == 2:
        src_container, src_name = src_path
    if type(dest_path) == str:
        parts = dest_path.split('/')
        if len(parts) < 3 or parts[0] != '':
            raise BadRequest('Invalid Destination header')
        dest_container = parts[1]
        dest_name = '/'.join(parts[2:])
    elif type(dest_path) == tuple and len(dest_path) == 2:
        dest_container, dest_name = dest_path
    
    meta = get_object_meta(request)
    # Keep previous values of 'Content-Type' (if a new one is absent) and 'hash'.
    try:
        src_meta = backend.get_object_meta(request.user, src_container, src_name)
    except NameError:
        raise ItemNotFound('Container or object does not exist')
    if 'Content-Type' in meta and 'Content-Type' in src_meta:
        del(src_meta['Content-Type'])
    for k in ('Content-Type', 'hash'):
        if k in src_meta:
            meta[k] = src_meta[k]
    
    try:
        if move:
            backend.move_object(request.user, src_container, src_name, dest_container, dest_name, meta, replace_meta=True)
        else:
            backend.copy_object(request.user, src_container, src_name, dest_container, dest_name, meta, replace_meta=True)
    except NameError:
        raise ItemNotFound('Container or object does not exist')

def get_content_length(request):
    content_length = request.META.get('CONTENT_LENGTH')
    if not content_length:
        raise LengthRequired('Missing Content-Length header')
    try:
        content_length = int(content_length)
        if content_length < 0:
            raise ValueError
    except ValueError:
        raise BadRequest('Invalid Content-Length header')
    return content_length

def get_range(request, size):
    """Parse a Range header from the request
    
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
    """Parse a Content-Range header from the request
    
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

def raw_input_socket(request):
    """Return the socket for reading the rest of the request"""
    server_software = request.META.get('SERVER_SOFTWARE')
    if not server_software:
        if 'wsgi.input' in request.environ:
            return request.environ['wsgi.input']
        raise ServiceUnavailable('Unknown server software')
    if server_software.startswith('WSGIServer'):
        return request.environ['wsgi.input']
    elif server_software.startswith('mod_python'):
        return request._req
    raise ServiceUnavailable('Unknown server software')

MAX_UPLOAD_SIZE = 10 * (1024 * 1024) # 10MB

def socket_read_iterator(sock, length=0, blocksize=4096):
    """Return a maximum of blocksize data read from the socket in each iteration
    
    Read up to 'length'. If 'length' is negative, will attempt a chunked read.
    The maximum ammount of data read is controlled by MAX_UPLOAD_SIZE.
    """
    if length < 0: # Chunked transfers
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
            except Exception, e:
                raise BadRequest('Bad chunk size') # TODO: Change to something more appropriate.
            # Check if done.
            if chunk_length == 0:
                if len(data) > 0:
                    yield data
                return
            # Get the actual data.
            while chunk_length > 0:
                chunk = sock.read(min(chunk_length, blocksize))
                chunk_length -= len(chunk)
                length += len(chunk)
                data += chunk
                if len(data) >= blocksize:
                    ret = data[:blocksize]
                    data = data[blocksize:]
                    yield ret
            sock.read(2) # CRLF
        # TODO: Raise something to note that maximum size is reached.
    else:
        if length > MAX_UPLOAD_SIZE:
            # TODO: Raise something to note that maximum size is reached.
            pass
        while length > 0:
            data = sock.read(min(length, blocksize))
            length -= len(data)
            yield data

class ObjectWrapper(object):
    """Return the object's data block-per-block in each iteration
    
    Read from the object using the offset and length provided in each entry of the range list.
    """
    
    def __init__(self, v_account, v_container, v_object, ranges, size, hashmap, boundary):
        self.v_account = v_account
        self.v_container = v_container
        self.v_object = v_object
        self.ranges = ranges
        self.size = size
        self.hashmap = hashmap
        self.boundary = boundary
        
        self.block_index = -1
        self.block = ''
        
        self.range_index = -1
        self.offset, self.length = self.ranges[0]
    
    def __iter__(self):
        return self
    
    def part_iterator(self):
        if self.length > 0:
            # Get the block for the current offset.
            bi = int(self.offset / backend.block_size)
            if self.block_index != bi:
                try:
                    self.block = backend.get_block(self.hashmap[bi])
                except NameError:
                    raise ItemNotFound('Block does not exist')
                self.block_index = bi
            # Get the data from the block.
            bo = self.offset % backend.block_size
            bl = min(self.length, backend.block_size - bo)
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
                if self.range_index > 0:
                    out.append('')
                out.append('--' + self.boundary)
                out.append('Content-Range: bytes %d-%d/%d' % (self.offset, self.offset + self.length - 1, self.size))
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

def hashmap_hash(hashmap):
    """ Produce the root hash, treating the hashmap as a Merkle-like tree."""
    
    def subhash(d):
        h = hashlib.new(backend.hash_algorithm)
        h.update(d)
        return h.digest()
    
    if len(hashmap) == 0:
        return hexlify(subhash(''))
    if len(hashmap) == 1:
        return hexlify(subhash(hashmap[0]))
    s = 2
    while s < len(hashmap):
        s = s * 2
    h = hashmap + ([('\x00' * len(hashmap[0]))] * (s - len(hashmap)))
    h = [subhash(h[x] + (h[x + 1] if x + 1 < len(h) else '')) for x in range(0, len(h), 2)]
    while len(h) > 1:
        h = [subhash(h[x] + (h[x + 1] if x + 1 < len(h) else '')) for x in range(0, len(h), 2)]
    return hexlify(h[0])

def update_response_headers(request, response):
    if request.serialization == 'xml':
        response['Content-Type'] = 'application/xml; charset=UTF-8'
    elif request.serialization == 'json':
        response['Content-Type'] = 'application/json; charset=UTF-8'
    elif not response['Content-Type']:
        response['Content-Type'] = 'text/plain; charset=UTF-8'

    if settings.TEST:
        response['Date'] = format_date_time(time())

def render_fault(request, fault):
    if settings.DEBUG or settings.TEST:
        fault.details = format_exc(fault)

    request.serialization = 'text'
    data = '\n'.join((fault.message, fault.details)) + '\n'
    response = HttpResponse(data, status=fault.code)
    update_response_headers(request, response)
    return response

def request_serialization(request, format_allowed=False):
    """Return the serialization format requested
    
    Valid formats are 'text' and 'json', 'xml' if 'format_allowed' is True.
    """
    if not format_allowed:
        return 'text'
    
    format = request.GET.get('format')
    if format == 'json':
        return 'json'
    elif format == 'xml':
        return 'xml'
    
    for item in request.META.get('HTTP_ACCEPT', '').split(','):
        accept, sep, rest = item.strip().partition(';')
        if accept == 'application/json':
            return 'json'
        elif accept == 'application/xml' or accept == 'text/xml':
            return 'xml'
    
    return 'text'

def api_method(http_method=None, format_allowed=False):
    """Decorator function for views that implement an API method"""
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            try:
                if http_method and request.method != http_method:
                    raise BadRequest('Method not allowed.')

                # The args variable may contain up to (account, container, object).
                if len(args) > 1 and len(args[1]) > 256:
                    raise BadRequest('Container name too large.')
                if len(args) > 2 and len(args[2]) > 1024:
                    raise BadRequest('Object name too large.')
                
                # Fill in custom request variables.
                request.serialization = request_serialization(request, format_allowed)
                # TODO: Authenticate.
                request.user = "test"
                
                response = func(request, *args, **kwargs)
                update_response_headers(request, response)
                return response
            except Fault, fault:
                return render_fault(request, fault)
            except BaseException, e:
                logger.exception('Unexpected error: %s' % e)
                fault = ServiceUnavailable('Unexpected error')
                return render_fault(request, fault)
        return wrapper
    return decorator
