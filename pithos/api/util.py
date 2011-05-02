#
# Copyright (c) 2011 Greek Research and Technology Network
#

from datetime import timedelta, tzinfo
from functools import wraps
from random import choice
from string import ascii_letters, digits
from time import time
from traceback import format_exc
from wsgiref.handlers import format_date_time

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson as json

from pithos.api.faults import Fault, BadRequest, ItemNotFound, ServiceUnavailable
#from synnefo.db.models import SynnefoUser, Image, ImageMetadata, VirtualMachine, VirtualMachineMetadata

import datetime
import dateutil.parser
import logging

import re
import calendar

# Part of newer Django versions.

__D = r'(?P<day>\d{2})'
__D2 = r'(?P<day>[ \d]\d)'
__M = r'(?P<mon>\w{3})'
__Y = r'(?P<year>\d{4})'
__Y2 = r'(?P<year>\d{2})'
__T = r'(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})'
RFC1123_DATE = re.compile(r'^\w{3}, %s %s %s %s GMT$' % (__D, __M, __Y, __T))
RFC850_DATE = re.compile(r'^\w{6,9}, %s-%s-%s %s GMT$' % (__D, __M, __Y2, __T))
ASCTIME_DATE = re.compile(r'^\w{3} %s %s %s %s$' % (__M, __D2, __T, __Y))

def parse_http_date(date):
    """
    Parses a date format as specified by HTTP RFC2616 section 3.3.1.

    The three formats allowed by the RFC are accepted, even if only the first
    one is still in widespread use.

    Returns an floating point number expressed in seconds since the epoch, in
    UTC.
    """
    # emails.Util.parsedate does the job for RFC1123 dates; unfortunately
    # RFC2616 makes it mandatory to support RFC850 dates too. So we roll
    # our own RFC-compliant parsing.
    for regex in RFC1123_DATE, RFC850_DATE, ASCTIME_DATE:
        m = regex.match(date)
        if m is not None:
            break
    else:
        raise ValueError("%r is not in a valid HTTP date format" % date)
    try:
        year = int(m.group('year'))
        if year < 100:
            if year < 70:
                year += 2000
            else:
                year += 1900
        month = MONTHS.index(m.group('mon').lower()) + 1
        day = int(m.group('day'))
        hour = int(m.group('hour'))
        min = int(m.group('min'))
        sec = int(m.group('sec'))
        result = datetime.datetime(year, month, day, hour, min, sec)
        return calendar.timegm(result.utctimetuple())
    except Exception:
        raise ValueError("%r is not a valid date" % date)

def parse_http_date_safe(date):
    """
    Same as parse_http_date, but returns None if the input is invalid.
    """
    try:
        return parse_http_date(date)
    except Exception:
        pass

# Metadata handling.

def format_meta_key(k):
    return '-'.join([x.capitalize() for x in k.replace('_', '-').split('-')])

def get_meta(request, prefix):
    """
    Get all prefix-* request headers in a dict.
    All underscores are converted to dashes.
    """
    prefix = 'HTTP_' + prefix.upper().replace('-', '_')
    return dict([(format_meta_key(k[5:]), v) for k, v in request.META.iteritems() if k.startswith(prefix)])

# Range parsing.

def get_range(request):
    """
    Parse a Range header from the request.
    Either returns None, or an (offset, length) tuple.
    If no offset is defined offset equals 0.
    If no length is defined length is None.
    """
    
    range = request.GET.get('range')
    if not range:
        return None
    
    range = range.replace(' ', '')
    if not range.startswith('bytes='):
        return None
    
    parts = range.split('-')
    if len(parts) != 2:
        return None
    
    offset, length = parts
    if offset == '' and length == '':
        return None
    
    if offset != '':
        try:
            offset = int(offset)
        except ValueError:
            return None
    else:
        offset = 0
    
    if length != '':
        try:
            length = int(length)
        except ValueError:
            return None
    else:
        length = None
    
    return (offset, length)

# def get_vm(server_id):
#     """Return a VirtualMachine instance or raise ItemNotFound."""
#     
#     try:
#         server_id = int(server_id)
#         return VirtualMachine.objects.get(id=server_id)
#     except ValueError:
#         raise BadRequest('Invalid server ID.')
#     except VirtualMachine.DoesNotExist:
#         raise ItemNotFound('Server not found.')
# 
# def get_vm_meta(server_id, key):
#     """Return a VirtualMachineMetadata instance or raise ItemNotFound."""
#     
#     try:
#         server_id = int(server_id)
#         return VirtualMachineMetadata.objects.get(meta_key=key, vm=server_id)
#     except VirtualMachineMetadata.DoesNotExist:
#         raise ItemNotFound('Metadata key not found.')
# 
# def get_image(image_id):
#     """Return an Image instance or raise ItemNotFound."""
#     
#     try:
#         image_id = int(image_id)
#         return Image.objects.get(id=image_id)
#     except Image.DoesNotExist:
#         raise ItemNotFound('Image not found.')
# 
# def get_image_meta(image_id, key):
#     """Return a ImageMetadata instance or raise ItemNotFound."""
# 
#     try:
#         image_id = int(image_id)
#         return ImageMetadata.objects.get(meta_key=key, image=image_id)
#     except ImageMetadata.DoesNotExist:
#         raise ItemNotFound('Metadata key not found.')
# 
# 
# def get_request_dict(request):
#     """Returns data sent by the client as a python dict."""
#     
#     data = request.raw_post_data
#     if request.META.get('CONTENT_TYPE').startswith('application/json'):
#         try:
#             return json.loads(data)
#         except ValueError:
#             raise BadRequest('Invalid JSON data.')
#     else:
#         raise BadRequest('Unsupported Content-Type.')

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
    
#     if request.serialization == 'xml':
#         data = render_to_string('fault.xml', {'fault': fault})
#     else:
#         d = {fault.name: {'code': fault.code, 'message': fault.message, 'details': fault.details}}
#         data = json.dumps(d)
    
#     resp = HttpResponse(data, status=fault.code)
    resp = HttpResponse(status = fault.code)
    update_response_headers(request, resp)
    return resp

def request_serialization(request, format_allowed=False):
    """
    Return the serialization format requested.
       
    Valid formats are 'text' and 'json', 'xml' if `format_allowed` is True.
    """
    
    if not format_allowed:
        return 'text'
    
    format = request.GET.get('format')
    if format == 'json':
        return 'json'
    elif format == 'xml':
        return 'xml'
    
    # TODO: Do we care of Accept headers?
#     for item in request.META.get('HTTP_ACCEPT', '').split(','):
#         accept, sep, rest = item.strip().partition(';')
#         if accept == 'application/json':
#             return 'json'
#         elif accept == 'application/xml':
#             return 'xml'
    
    return 'text'

def api_method(http_method = None, format_allowed = False):
    """
    Decorator function for views that implement an API method.
    """
    
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            try:
                request.serialization = request_serialization(request, format_allowed)
                # TODO: Authenticate.
                # TODO: Return 401/404 when the account is not found.
                request.user = "test"
                # TODO: Check parameter sizes.
                if http_method and request.method != http_method:
                    raise BadRequest('Method not allowed.')
                
                resp = func(request, *args, **kwargs)
                update_response_headers(request, resp)
                return resp
            
            except Fault, fault:
                return render_fault(request, fault)
            except BaseException, e:
                logging.exception('Unexpected error: %s' % e)
                fault = ServiceUnavailable('Unexpected error')
                return render_fault(request, fault)
        return wrapper
    return decorator
