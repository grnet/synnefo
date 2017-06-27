# Copyright (C) 2010-2017 GRNET S.A.
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

from django.http import JsonResponse
from astakos.im.settings import KEYSTONE_ROOT_URL
from synnefo.util.api import build_version_object

from snf_django.lib import api


log = getLogger('astakos.api')


VERSIONS = [
    build_version_object(KEYSTONE_ROOT_URL, 2.0, 'v2.0', 'CURRENT',
                         updated="2014-04-17T00:00:00Z"),
]

VERSIONS_LIST = {'versions': {'values': VERSIONS}}

MEDIA_TYPES = [
    {
        "base": "application/json",
        "type": "application/vnd.openstack.identity-v2.0+json"
    }
]

DESCRIBED_BY = [
    {
        "rel": "describedby",
        "type": "text/html",
        "href": "https://docs.openstack.org/",
    }
]


@api.api_method(http_method='GET', user_required=False, token_required=False,
                logger=log)
def versions_list(request):
    # Normal Response Codes: 200, 203
    # Error Response Codes: 400, 413, 500, 503
    return JsonResponse(VERSIONS_LIST)


@api.api_method('GET', user_required=False, token_required=False, logger=log)
def version_details(request, api_version):
    # Normal Response Codes: 200, 203
    # Error Response Codes: internalServerError(500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       overLimit(413)

    log.debug('version_details %s', api_version)
    # We hardcode to v2.0 since it is the only one we support
    version = build_version_object(KEYSTONE_ROOT_URL, 2.0, 'v2.0', 'CURRENT',
                                   updated="2014-04-17T00:00:00Z",
                                   media_types=MEDIA_TYPES)
    version['links'] = version['links'] + DESCRIBED_BY

    return JsonResponse({'version': version})
