#
# Copyright (c) 2011 Greek Research and Technology Network
#

from functools import wraps

from time import time
from wsgiref.handlers import format_date_time

from django.conf import settings
from django.http import HttpResponse

from pithos.api.faults import Fault, BadRequest, ServiceUnavailable

import datetime
import logging

logger = logging.getLogger(__name__)

def format_meta_key(k):
    """
    Convert underscores to dashes and capitalize intra-dash strings.
    """
    return '-'.join([x.capitalize() for x in k.replace('_', '-').split('-')])

def get_meta(request, prefix):
    """
    Get all prefix-* request headers in a dict. Reformat keys with format_meta_key().
    """
    prefix = 'HTTP_' + prefix.upper().replace('-', '_')
    return dict([(format_meta_key(k[5:]), v) for k, v in request.META.iteritems() if k.startswith(prefix)])

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
    response = HttpResponse(status = fault.code)
    update_response_headers(request, response)
    return response

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
    
    for item in request.META.get('HTTP_ACCEPT', '').split(','):
        accept, sep, rest = item.strip().partition(';')
        if accept == 'text/plain':
            return 'text'
        elif accept == 'application/json':
            return 'json'
        elif accept == 'application/xml' or accept == 'text/xml':
            return 'xml'
    
    return 'text'

def api_method(http_method = None, format_allowed = False):
    """
    Decorator function for views that implement an API method.
    """
    
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
