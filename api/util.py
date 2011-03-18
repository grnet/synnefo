#
# Copyright (c) 2010 Greek Research and Technology Network
#

from synnefo.api.errors import *
from synnefo.db.models import *

from django.http import HttpResponse
from django.template.loader import render_to_string

from functools import wraps
from logging import getLogger
from random import choice
from string import ascii_letters, digits
from traceback import format_exc
from xml.etree import ElementTree
from xml.parsers.expat import ExpatError

import json


log = getLogger('synnefo.api')


def tag_name(e):
    ns, sep, name = e.tag.partition('}')
    return name if sep else e.tag

def xml_to_dict(s):
    def _xml_to_dict(e):
        root = {}
        d = root[tag_name(e)] = dict(e.items())
        for child in e.getchildren():
            d.update(_xml_to_dict(child))
        return root
    return _xml_to_dict(ElementTree.fromstring(s.strip()))

def get_user():
    # XXX Placeholder function, everything belongs to a single SynnefoUser for now
    try:
        return SynnefoUser.objects.all()[0]
    except IndexError:
        raise Unauthorized

def get_request_dict(request):
    data = request.raw_post_data
    if request.type == 'xml':
        try:
            return xml_to_dict(data)
        except ExpatError:
            raise BadRequest
    else:
        try:
            return json.loads(data)
        except ValueError:
            raise BadRequest

def random_password(length=8):
    pool = ascii_letters + digits
    return ''.join(choice(pool) for i in range(length))


def render_fault(fault, request):
    if settings.DEBUG or request.META.get('SERVER_NAME', None) == 'testserver':
        fault.details = format_exc(fault)
    if request.type == 'xml':
        mimetype = 'application/xml'
        data = render_to_string('fault.xml', dict(fault=fault))
    else:
        mimetype = 'application/json'
        d = {fault.name: {'code': fault.code, 'message': fault.message, 'details': fault.details}}
        data = json.dumps(d)
    return HttpResponse(data, mimetype=mimetype, status=fault.code)    

def api_method(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        try:
            if request.path.endswith('.json'):
                type = 'json'
            elif request.path.endswith('.xml'):
                type = 'xml'
            elif request.META.get('HTTP_ACCEPT', None) == 'application/xml':
                type = 'xml'
            else:
                type = 'json'
            request.type = type
            return func(request, *args, **kwargs)
        except Fault, fault:
            return render_fault(fault, request)
        except Exception, e:
            log.exception('Unexpected error: %s' % e)
            return HttpResponse(status=500)
    return wrapper
