# Copyright (C) 2010-2014 GRNET S.A.
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
from django.utils import simplejson as json
from synnefo.cyclades_settings import COMPUTE_ROOT_URL

from snf_django.lib import api


log = getLogger('synnefo.api')


VERSION_2_0 = {
    "id": "v2.0",
    "status": "CURRENT",
    "updated": "2011-01-21T11:33:21-06:00",
    "links": [
        {
            "rel": "self",
            "href": COMPUTE_ROOT_URL,
        },
    ],
}

VERSIONS = [VERSION_2_0]

MEDIA_TYPES = [
    {
        "base": "application/xml",
        "type": "application/vnd.openstack.compute.v2+xml"
    },
    {
        "base": "application/json",
        "type": "application/vnd.openstack.compute.v2+json"
    }
]

DESCRIBED_BY = [
    {
        "rel": "describedby",
        "type": "application/pdf",
        "href": "http://docs.rackspacecloud.com/servers/api/v2/"
                "cs-devguide-20110125.pdf"
    },
    {
        "rel": "describedby",
        "type": "application/vnd.sun.wadl+xml",
        "href": "http://docs.rackspacecloud.com/servers/api/v2/"
                "application.wadl"
    }
]


@api.api_method(http_method='GET', user_required=True, logger=log)
def versions_list(request):
    # Normal Response Codes: 200, 203
    # Error Response Codes: 400, 413, 500, 503

    if request.serialization == 'xml':
        data = render_to_string('versions_list.xml', {'versions': VERSIONS})
    else:
        data = json.dumps({'versions': VERSIONS})

    return HttpResponse(data)


@api.api_method('GET', user_required=True, logger=log)
def version_details(request, api_version):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       overLimit(413)

    log.debug('version_details %s', api_version)
    # We hardcode to v2.0 since it is the only one we support
    version = VERSION_2_0.copy()
    version['links'] = version['links'] + DESCRIBED_BY

    if request.serialization == 'xml':
        version['media_types'] = MEDIA_TYPES
        data = render_to_string('version_details.xml', {'version': version})
    else:
        version['media-types'] = MEDIA_TYPES
        data = json.dumps({'version': version})
    return HttpResponse(data)
