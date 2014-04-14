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
from snf_django.lib.api import utils, faults
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
    images = True
    backend = None
    if request.body:
        req = utils.get_json_body(request)
        req_stats = utils.get_attribute(req, "stats", required=True,
                                        attr_type=dict)
        # Check backend
        backend_id = utils.get_attribute(req_stats, "backend", required=False,
                                         attr_type=(basestring, int))
        if backend_id is not None:
            try:
                try:
                    backend_id = int(backend_id)
                    backend = Backend.objects.get(id=backend_id)
                except (ValueError, TypeError):
                    backend = Backend.objects.get(clustername=backend_id)
            except Backend.DoesNotExist:
                raise faults.BadRequest("Invalid backend '%s'" % backend_id)
        include_images = utils.get_attribute(req_stats, "images",
                                             required=False,
                                             attr_type=bool)
        if include_images is not None:
            images = include_images

    _stats = stats.get_cyclades_stats(backend=backend, clusters=True,
                                      servers=True, resources=True,
                                      networks=True, images=images)
    data = json.dumps(_stats)
    return http.HttpResponse(data, status=200, content_type='application/json')
