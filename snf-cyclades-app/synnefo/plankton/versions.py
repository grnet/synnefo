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
import json

from synnefo.cyclades_settings import IMAGE_ROOT_URL
from synnefo.api.util import build_version_object

from snf_django.lib import api


log = getLogger('synnefo.api')

MEDIA_TYPES = [
    {
        "base": "application/json",
        "type": "application/vnd.openstack.compute.v2+json"
    }
]


VERSIONS = [
    build_version_object(IMAGE_ROOT_URL, 1.0, 'v1.0', 'CURRENT',
                         media_types=MEDIA_TYPES),
    build_version_object(IMAGE_ROOT_URL, 1, 'v1', 'CURRENT',
                         media_types=MEDIA_TYPES),
]


@api.api_method(http_method='GET', user_required=False, logger=log)
def versions_list(request):
    # Normal Response Codes: 200, 203
    # Error Response Codes: 400, 413, 500, 503

    data = json.dumps({'versions': VERSIONS})
    return HttpResponse(data)
