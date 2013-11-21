# Copyright 2013 GRNET S.A. All rights reserved.
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

import logging
from django import http
from django.utils import simplejson as json
from snf_django.lib import api
from astakos.im import settings

from astakos.admin import stats

logger = logging.getLogger(__name__)

PERMITTED_GROUPS = settings.ADMIN_STATS_PERMITTED_GROUPS


@api.api_method(http_method='GET', user_required=False, token_required=False,
                logger=logger, serializations=['json'])
@api.allow_jsonp()
def get_public_stats(request):
    _stats = stats.get_public_stats()
    data = json.dumps(_stats)
    return http.HttpResponse(data, status=200, content_type='application/json')


@api.api_method(http_method='GET', user_required=True, token_required=True,
                logger=logger, serializations=['json'])
@api.user_in_groups(permitted_groups=PERMITTED_GROUPS,
                    logger=logger)
def get_astakos_stats(request):
    _stats = stats.get_astakos_stats()
    data = json.dumps(_stats)
    return http.HttpResponse(data, status=200, content_type='application/json')
