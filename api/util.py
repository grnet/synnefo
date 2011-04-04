#
# Copyright (c) 2010 Greek Research and Technology Network
#

from datetime import timedelta, tzinfo
from functools import wraps
from random import choice
from string import ascii_letters, digits
from traceback import format_exc

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson as json

from synnefo.api.faults import *
from synnefo.db.models import *

import datetime
import dateutil.parser
import logging


class UTC(tzinfo):
    def utcoffset(self, dt):
        return timedelta(0)
    
    def tzname(self, dt):
        return 'UTC'
    
    def dst(self, dt):
        return timedelta(0)


def isoformat(d):
    """Return an ISO8601 date string that includes a timezon."""
    
    return d.replace(tzinfo=UTC()).isoformat()

def isoparse(s):
    """Parse an ISO8601 date string into a datetime object."""
    
    if not s:
        return None
    
    try:
        since = dateutil.parser.parse(s)
    except ValueError:
        raise BadRequest('Invalid changes-since parameter.')
    
    now = datetime.datetime.now(UTC())
    if since > now:
        raise BadRequest('changes-since value set in the future.')
    
    if now - since > timedelta(seconds=settings.POLL_LIMIT):
        raise BadRequest('Too old changes-since value.')
    
    return since
    
def random_password(length=8):
    pool = ascii_letters + digits
    return ''.join(choice(pool) for i in range(length))


def get_user():
    # XXX Placeholder function, everything belongs to a single SynnefoUser for now
    try:
        return SynnefoUser.objects.all()[0]
    except IndexError:
        raise Unauthorized

def get_vm(server_id):
    """Return a VirtualMachine instance or raise ItemNotFound."""
    
    try:
        server_id = int(server_id)
        return VirtualMachine.objects.get(id=server_id)
    except ValueError:
        raise BadRequest('Invalid server ID.')
    except VirtualMachine.DoesNotExist:
        raise ItemNotFound('Server not found.')

def get_vm_meta(server_id, key):
    """Return a VirtualMachineMetadata instance or raise ItemNotFound."""
    
    try:
        server_id = int(server_id)
        return VirtualMachineMetadata.objects.get(meta_key=key, vm=server_id)
    except VirtualMachineMetadata.DoesNotExist:
        raise ItemNotFound('Metadata key not found.')

def get_image(image_id):
    """Return an Image instance or raise ItemNotFound."""
    
    try:
        image_id = int(image_id)
        return Image.objects.get(id=image_id)
    except Image.DoesNotExist:
        raise ItemNotFound('Image not found.')


def get_request_dict(request):
    """Returns data sent by the client as a python dict."""
    
    data = request.raw_post_data
    if request.META.get('CONTENT_TYPE').startswith('application/json'):
        try:
            return json.loads(data)
        except ValueError:
            raise BadRequest('Invalid JSON data.')
    else:
        raise BadRequest('Unsupported Content-Type.')

def render_fault(request, fault):
    if settings.DEBUG or request.META.get('SERVER_NAME') == 'testserver':
        fault.details = format_exc(fault)
    
    if request.serialization == 'xml':
        data = render_to_string('fault.xml', {'fault': fault})
    else:
        d = {fault.name: {'code': fault.code, 'message': fault.message, 'details': fault.details}}
        data = json.dumps(d)
    
    resp = HttpResponse(data, status=fault.code)
    
    if request.serialization == 'xml':
        resp['Content-Type'] = 'application/xml'
    elif request.serialization == 'atom':
        resp['Content-Type'] = 'application/atom+xml'
    else:
        resp['Content-Type'] = 'application/json'
    
    return resp

def request_serialization(request, atom_allowed=False):
    """Return the serialization format requested.
       
       Valid formats are 'json', 'xml' and 'atom' if `atom_allowed` is True.
    """
    
    path = request.path
    
    if path.endswith('.json'):
        return 'json'
    elif path.endswith('.xml'):
        return 'xml'
    elif atom_allowed and path.endswith('.atom'):
        return 'atom'
    
    for item in request.META.get('HTTP_ACCEPT', '').split(','):
        accept, sep, rest = item.strip().partition(';')
        if accept == 'application/json':
            return 'json'
        elif accept == 'application/xml':
            return 'xml'
        elif atom_allowed and accept == 'application/atom+xml':
            return 'atom'
    
    return 'json'

def api_method(http_method=None, atom_allowed=False):
    """Decorator function for views that implement an API method."""
    
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            try:
                request.serialization = request_serialization(request, atom_allowed)
                if http_method and request.method != http_method:
                    raise BadRequest('Method not allowed.')
                
                resp = func(request, *args, **kwargs)
                if request.serialization == 'xml':
                    resp['Content-Type'] = 'application/xml'
                elif request.serialization == 'atom':
                    resp['Content-Type'] = 'application/atom+xml'
                else:
                    resp['Content-Type'] = 'application/json'
                
                return resp
            
            except Fault, fault:
                return render_fault(request, fault)
            except BaseException, e:
                logging.exception('Unexpected error: %s' % e)
                fault = ServiceUnavailable('Unexpected error')
                return render_fault(request, fault)
        return wrapper
    return decorator
