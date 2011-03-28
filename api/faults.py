# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8
#
# Copyright © 2010 Greek Research and Technology Network
#

from django.http import HttpResponse
from django.utils import simplejson as json
from piston.utils import HttpStatusCode

class Fault(HttpStatusCode):
    """Fault Exception"""
    pass

class _fault_factory(object):
    """
    Openstack API Faults factory
    """

    faults = {
        'serviceUnavailable': {
                'code': 503,
                'message': 'Service Unavailable',
            },
        'unauthorized': {
                'code': 401,
                'message': 'Unauthorized',
            },
        'badRequest': {
                'code': 400,
                'message': 'Bad request',
            },
        'overLimit': {
                'code': 413,
                'message': 'Overlimit',
            },
        'badMediaType': {
                'code': 415,
                'message': 'Bad media type',
            },
        'badMethod': {
                'code': 405,
                'message': 'Bad method',
            },
        'itemNotFound': {
                'code': 404,
                'message': 'Not Found',
            },
        'buildInProgress': {
                'code': 409,
                'message': 'Build in progress',
            },
        'serverCapacityUnavailable': {
                'code': 503,
                'message': 'Server capacity unavailable',
            },
        'backupOrResizeInProgress': {
                'code': 409,
                'message': 'Backup or resize in progress',
            },
        'resizeNotAllowed': {
                'code': 403,
                'message': 'Resize not allowed',
            },
        'notImplemented': {
                'code': 501,
                'message': 'Not Implemented',
            },
        }

    def __getattr__(self, attr):
        try:
            m = self.faults.get(attr)
        except TypeError:
            raise AttributeError(attr)

        # details are not supported for now
        m['details'] = ''

        # piston > 0.2.2 does the serialization for us, but be compatible
        # 'till the next version gets released. XXX: this doesn't do XML!
        message = json.dumps({ attr: m }, ensure_ascii=False, indent=4)
        code = m['code']
        response = HttpResponse(message, status=code)

        return Fault(response)


fault = _fault_factory()

# these are in the 2xx range, hence not faults/exceptions
noContent = HttpResponse(status=204)
accepted = HttpResponse(status=202)
created = HttpResponse(status=201)
notModified = HttpResponse(status=304)
