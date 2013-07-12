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

from logging import getLogger

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson as json
from synnefo.cyclades_settings import COMPUTE_ROOT_URL

from snf_django.lib import api


log = getLogger('synnefo.api')


VERSION_2_0 = {
    "id" : "v2.0",
    "status" : "CURRENT",
    "updated" : "2011-01-21T11:33:21-06:00",
    "links": [
        {
            "rel" : "self",
            "href" : COMPUTE_ROOT_URL,
        },
    ],
}

VERSIONS = [VERSION_2_0]

MEDIA_TYPES = [
    {
        "base" : "application/xml",
        "type" : "application/vnd.openstack.compute.v2+xml"
    },
    {
        "base" : "application/json",
        "type" : "application/vnd.openstack.compute.v2+json"
    }
]

DESCRIBED_BY = [
    {
        "rel" : "describedby",
        "type" : "application/pdf",
        "href" : "http://docs.rackspacecloud.com/servers/api/v2/cs-devguide-20110125.pdf"
    },
    {
        "rel" : "describedby",
        "type" : "application/vnd.sun.wadl+xml",
        "href" : "http://docs.rackspacecloud.com/servers/api/v2/application.wadl"
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
