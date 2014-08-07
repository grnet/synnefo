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

from functools import wraps

from django import http
from django.utils import simplejson as json
from django.forms.models import model_to_dict
from django.core.validators import validate_email, ValidationError

from snf_django.lib import api
from snf_django.lib.api import faults

from astakos.im import settings
from astakos.admin import stats
from astakos.im.models import AstakosUser, get_latest_terms
from astakos.im.auth import make_local_user

logger = logging.getLogger(__name__)

STATS_PERMITTED_GROUPS = settings.ADMIN_STATS_PERMITTED_GROUPS

try:
    AUTH_URL = settings.astakos_services \
                ["astakos_identity"]["endpoints"][0]["publicURL"]
except (IndexError, KeyError) as e:
    logger.error("Failed to load Astakos Auth URL: %s", e)
    AUTH_URL = None


@api.api_method(http_method='GET', user_required=False, token_required=False,
                logger=logger, serializations=['json'])
@api.allow_jsonp()
def get_public_stats(request):
    _stats = stats.get_public_stats()
    data = json.dumps(_stats)
    return http.HttpResponse(data, status=200, content_type='application/json')


@api.api_method(http_method='GET', user_required=True, token_required=True,
                astakos_auth_url=AUTH_URL,
                logger=logger, serializations=['json'])
@api.user_in_groups(permitted_groups=STATS_PERMITTED_GROUPS,
                    logger=logger)
def get_astakos_stats(request):
    _stats = stats.get_astakos_stats()
    data = json.dumps(_stats)
    return http.HttpResponse(data, status=200, content_type='application/json')

