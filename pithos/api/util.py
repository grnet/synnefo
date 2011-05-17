from functools import wraps
from time import time
from traceback import format_exc
from wsgiref.handlers import format_date_time

from django.conf import settings
from django.http import HttpResponse
from django.utils.http import http_date

from pithos.api.compat import parse_http_date_safe
from pithos.api.faults import (Fault, NotModified, BadRequest, ItemNotFound, PreconditionFailed,
                                ServiceUnavailable)
from pithos.backends import backend

import datetime
import logging


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

def get_object_meta(request):
    """Get metadata from an object request"""
    meta = get_meta_prefix(request, 'X-Object-Meta-')
    if request.META.get('CONTENT_TYPE'):
        meta['Content-Type'] = request.META['CONTENT_TYPE']
    if request.META.get('HTTP_CONTENT_ENCODING'):
        meta['Content-Encoding'] = request.META['HTTP_CONTENT_ENCODING']
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
    for k in ('Content-Encoding', 'X-Object-Manifest'):
        if k in meta:
            response[k] = meta[k]

def validate_modification_preconditions(request, meta):
    """Check that the modified timestamp conforms with the preconditions set"""
    if_modified_since = request.META.get('HTTP_IF_MODIFIED_SINCE')
    if if_modified_since is not None:
        if_modified_since = parse_http_date_safe(if_modified_since)
    if if_modified_since is not None and 'modified' in meta and int(meta['modified']) <= if_modified_since:
        raise NotModified('Object has not been modified')
    
    if_unmodified_since = request.META.get('HTTP_IF_UNMODIFIED_SINCE')
    if if_unmodified_since is not None:
        if_unmodified_since = parse_http_date_safe(if_unmodified_since)
    if if_unmodified_since is not None and 'modified' in meta and int(meta['modified']) > if_unmodified_since:
        raise PreconditionFailed('Object has been modified')

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
    try:
        if move:
            backend.move_object(request.user, src_container, src_name, dest_container, dest_name, meta)
        else:
            backend.copy_object(request.user, src_container, src_name, dest_container, dest_name, meta)
    except NameError:
        raise ItemNotFound('Container or object does not exist')

def get_range(request):
    """Parse a Range header from the request
    
    Either returns None, or an (offset, length) tuple.
    If no length is defined length is None.
    May return a negative offset (offset from the end).
    """
    range = request.META.get('HTTP_RANGE', '').replace(' ', '')
    if not range.startswith('bytes='):
        return None
    
    parts = range[6:].split('-')
    if len(parts) != 2:
        return None
    
    offset, upto = parts
    if offset == '' and upto == '':
        return None
    if offset != '':
        try:
            offset = int(offset)
        except ValueError:
            return None
        
        if upto != '':
            try:
                upto = int(upto)
            except ValueError:
                return None
        else:
            return (offset, None)
        
        if offset > upto:
            return None
        return (offset, upto - offset + 1)
    else:
        try:
            offset = -int(upto)
        except ValueError:
            return None
        return (offset, None)

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

def socket_read_iterator(sock, length=-1, blocksize=4096):
    """Return a maximum of blocksize data read from the socket in each iteration
    
    Read up to 'length'. If no 'length' is defined, will attempt a chunked read.
    The maximum ammount of data read is controlled by MAX_UPLOAD_SIZE.
    """
    if length < 0: # Chunked transfers
        while length < MAX_UPLOAD_SIZE:
            chunk_length = sock.readline()
            pos = chunk_length.find(';')
            if pos >= 0:
                chunk_length = chunk_length[:pos]
            try:
                chunk_length = int(chunk_length, 16)
            except Exception, e:
                raise BadRequest('Bad chunk size') # TODO: Change to something more appropriate.
            if chunk_length == 0:
                return
            while chunk_length > 0:
                data = sock.read(min(chunk_length, blocksize))
                chunk_length -= len(data)
                length += len(data)
                yield data
            data = sock.read(2) # CRLF
        # TODO: Raise something to note that maximum size is reached.
    else:
        if length > MAX_UPLOAD_SIZE:
            # TODO: Raise something to note that maximum size is reached.
            pass
        while length > 0:
            data = sock.read(min(length, blocksize))
            length -= len(data)
            yield data

def update_response_headers(request, response):
    if request.serialization == 'xml':
        response['Content-Type'] = 'application/xml; charset=UTF-8'
    elif request.serialization == 'json':
        response['Content-Type'] = 'application/json; charset=UTF-8'
    else:
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
        if accept == 'text/plain':
            return 'text'
        elif accept == 'application/json':
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
