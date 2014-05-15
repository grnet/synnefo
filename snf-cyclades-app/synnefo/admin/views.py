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

import logging
from django import http
from django.utils import simplejson as json
from django.conf import settings
from snf_django.lib import api
from snf_django.lib.api import faults
from synnefo.db.models import Backend

from synnefo.admin import stats

logger = logging.getLogger(__name__)


@api.api_method(http_method='GET', user_required=False, token_required=False,
                logger=logger, serializations=['json'])
@api.allow_jsonp()
def get_public_stats(request):
    _stats = stats.get_public_stats()
    data = json.dumps(_stats)
    return http.HttpResponse(data, status=200, content_type='application/json')


@api.api_method(http_method='GET', user_required=True, token_required=True,
                logger=logger, serializations=['json'])
@api.user_in_groups(permitted_groups=settings.ADMIN_STATS_PERMITTED_GROUPS,
                    logger=logger)
def get_cyclades_stats(request):
    servers, networks, ip_pools, images = True, True, True, True,
    clusters = True
    backend = None

    backend_id = request.GET.get("backend")
    if backend_id is not None:
        try:
            try:
                backend_id = int(backend_id)
                backend = Backend.objects.get(id=backend_id)
            except (ValueError, TypeError):
                backend = Backend.objects.get(clustername=backend_id)
        except Backend.DoesNotExist:
            raise faults.BadRequest("Invalid backend '%s'" % backend_id)
        # This stats have no meaning per backend
        networks, ip_pools = False, False

    _stats = stats.get_cyclades_stats(backend=backend, clusters=clusters,
                                      servers=servers, networks=networks,
                                      ip_pools=ip_pools, images=images)
    data = json.dumps(_stats)
    return http.HttpResponse(data, status=200, content_type='application/json')
