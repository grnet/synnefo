# Copyright (C) 2010-2016 GRNET S.A.
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

from logging import getLogger

from django.http import HttpResponse
from django.template.loader import render_to_string
import json
from synnefo.cyclades_settings import NETWORK_ROOT_URL
from synnefo.api.util import build_version_object

from snf_django.lib import api

log = getLogger('synnefo.api')


VERSIONS = [
    build_version_object(NETWORK_ROOT_URL, 2.0, 'v2.0', 'CURRENT')
]


RESOURCES_NAMES = [
    'networks',
    'subnets',
    'ports',
    'floatingips',
]

PLURAL_TO_SINGULAR = {
    'networks': 'network',
    'subnets': 'subnet',
    'ports': 'port',
    'floatingips': 'floatingip'
}

NETWORK_RESOURCES_V2_0 = [
    {
        "links": [
            {
                "href": "{0}/v2.0/{1}".format(NETWORK_ROOT_URL, resource),
                "rel": "self"
            }
        ],
        "name": PLURAL_TO_SINGULAR[resource],
        "collection": resource
    }
    for resource in RESOURCES_NAMES
]


@api.api_method(http_method='GET', user_required=False, logger=log)
def versions_list(request):
    # Normal Response Codes: 200, 203
    # Error Response Codes: 400, 413, 500, 503

    if request.serialization == 'xml':
        data = render_to_string('versions_list.xml', {'versions': VERSIONS})
    else:
        data = json.dumps({'versions': VERSIONS})

    return HttpResponse(data)


@api.api_method('GET', user_required=True, logger=log)
def version_details(request):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       overLimit(413)

    if request.serialization == 'xml':
        data = render_to_string('version_details.xml',
                                {'resources': NETWORK_RESOURCES_V2_0})
    else:
        data = json.dumps({'resources': NETWORK_RESOURCES_V2_0})
    return HttpResponse(data)
