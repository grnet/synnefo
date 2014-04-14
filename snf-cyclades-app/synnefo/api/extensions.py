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

from django.conf.urls import patterns

from django.http import HttpResponse
from django.utils import simplejson as json
from snf_django.lib import api


from logging import getLogger
log = getLogger(__name__)

urlpatterns = patterns(
    'synnefo.api.extensions',
    (r'^(?:/|.json|.xml)?$', 'demux'),
    (r'^/([\w-]+)(?:/|.json|.xml)?$', 'demux_extension'),
)


def demux(request):
    if request.method == 'GET':
        return list_extensions(request)
    else:
        return api.api_method_not_allowed(request, allowed_methods=['GET'])


def demux_extension(request, extension_alias):
    if request.method == 'GET':
        return get_extension(request, extension_alias)
    else:
        return api.api_method_not_allowed(request, allowed_methods=['GET'])


@api.api_method(http_method='GET', user_required=True, logger=log)
def list_extensions(request, detail=False):
    # Temporary return empty list. This will return the SNF: extension.
    data = json.dumps(dict(extensions=[]))
    return HttpResponse(data, status=200)


@api.api_method(http_method='GET', user_required=True, logger=log)
def get_extension(request, extension_alias):
    return HttpResponse(status=404)
