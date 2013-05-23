# Copyright 2011-2013 GRNET S.A. All rights reserved.
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

from urlparse import urlunsplit, urlsplit

from django.http import urlencode

from snf_django.lib import api

from astakos.im.models import Service

from .util import user_from_token, rename_meta_key, json_response, xml_response

import logging
logger = logging.getLogger(__name__)


@api.api_method(http_method="GET", token_required=True, user_required=False,
                logger=logger)
@user_from_token  # Authenticate user!!
def get_endpoints(request, token):
    if token != api.get_token(request):
        raise api.faults.Forbidden()

    belongsTo = request.GET.get('belongsTo')
    if belongsTo and belongsTo != request.user.uuid:
        raise api.faults.BadRequest()

    marker = request.GET.get('marker', 0)
    limit = request.GET.get('limit', 10000)

    endpoints = list(Service.objects.all().order_by('id').\
        filter(id__gt=marker)[:limit].\
        values('name', 'url', 'api_url', 'id', 'type'))
    for e in endpoints:
        e['api_url'] = e['api_url'] or e['url']
        e['internalURL'] = e['url']
        e['region'] = e['name']
        rename_meta_key(e, 'api_url', 'adminURL')
        rename_meta_key(e, 'url', 'publicURL')

    if endpoints:
        parts = list(urlsplit(request.path))
        params = {'marker': endpoints[-1]['id'], 'limit': limit}
        parts[3] = urlencode(params)
        next_page_url = urlunsplit(parts)
        endpoint_links = [{'href': next_page_url, 'rel': 'next'}]
    else:
        endpoint_links = []

    result = {'endpoints': endpoints, 'endpoint_links': endpoint_links}
    if request.serialization == 'xml':
        return xml_response(result, 'api/endpoints.xml')
    else:
        return json_response(result)
