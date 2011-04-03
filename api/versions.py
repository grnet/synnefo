#
# Copyright (c) 2010 Greek Research and Technology Network
#

from datetime import datetime

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson as json

from synnefo.api.util import api_method, isoformat


VERSION_1_1 = {
    'id': 'v1.1',
    'status': 'CURRENT',
    'updated': '2011-04-01',
    'links': [
        {
            'rel': 'self',
            'href': settings.API_ROOT_URL,
        }
    ]
}

VERSIONS = [VERSION_1_1]

MEDIA_TYPES = [
    {'base': 'application/xml', 'type': 'application/vnd.openstack.compute-v1.1+xml'},
    {'base': 'application/json', 'type': 'application/vnd.openstack.compute-v1.1+json'}
]


@api_method('GET', atom_allowed=True)
def versions_list(request):
    # Normal Response Codes: 200, 203
    # Error Response Codes: 400, 413, 500, 503
    
    if request.serialization == 'xml':
        data = render_to_string('versions_list.xml', {'versions': VERSIONS})
    elif request.serialization == 'atom':
        now = isoformat(datetime.now())
        data = render_to_string('versions_list.atom', {'now': now,'versions': VERSIONS})
    else:
        data = json.dumps({'versions': {'values': VERSIONS}})
        
    return HttpResponse(data)

@api_method('GET', atom_allowed=True)
def version_details(request, api_version):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       overLimit(413)

    # We hardcode to v1.1 since it is the only one we support
    version = VERSION_1_1.copy()
    
    if request.serialization == 'xml':
        version['media_types'] = MEDIA_TYPES
        data = render_to_string('version_details.xml', {'version': version})
    elif request.serialization == 'atom':
        version['media_types'] = MEDIA_TYPES
        now = isoformat(datetime.now())
        data = render_to_string('version_details.atom', {'now': now,'version': version})
    else:
        version['media-types'] = MEDIA_TYPES
        data = json.dumps({'version': version})
    return HttpResponse(data)
