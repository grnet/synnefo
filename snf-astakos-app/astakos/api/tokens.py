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
from django.views.decorators.csrf import csrf_exempt

from snf_django.lib.api import faults, utils, api_method, get_token

from astakos.im.models import Service, AstakosUser
from .util import user_from_token, json_response, xml_response

import logging
logger = logging.getLogger(__name__)


@api_method(http_method="GET", token_required=True, user_required=False,
            logger=logger)
@user_from_token  # Authenticate user!!
def get_endpoints(request, token):
    if token != get_token(request):
        raise faults.Forbidden()

    belongsTo = request.GET.get('belongsTo')
    if belongsTo and belongsTo != request.user.uuid:
        raise faults.BadRequest()

    marker = request.GET.get('marker', 0)
    limit = request.GET.get('limit', 10000)

    endpoints = list(Service.objects.all().order_by('id').
                     filter(id__gt=marker)[:limit].
                     values('name', 'url', 'api_url', 'id', 'type'))
    for e in endpoints:
        e['publicURL'] = e['admiURL'] = e['internalURL'] = e['api_url']
        e['SNF:uiURL'] = e['url']
        e['region'] = e['name']
        e.pop('api_url')

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


@csrf_exempt
@api_method(http_method="POST", token_required=False, user_required=False,
            logger=logger)
def authenticate(request):
    req = utils.get_request_dict(request)

    uuid = None
    try:
        tenant = req['auth']['tenantName']
        token_id = req['auth']['token']['id']
    except KeyError:
        try:
            token_id = req['auth']['passwordCredentials']['password']
            uuid = req['auth']['passwordCredentials']['username']
        except KeyError:
            raise faults.BadRequest('Malformed request')

    if token_id is None:
        raise faults.BadRequest('Malformed request')

    try:
        user = AstakosUser.objects.get(auth_token=token_id)
    except AstakosUser.DoesNotExist:
        raise faults.Unauthorized('Invalid token')

    if tenant != user.uuid:
        raise faults.Unauthorized('Invalid tenant')

    if uuid is not None:
        if user.uuid != uuid:
            raise faults.Unauthorized('Invalid credentials')

    access = {}
    access['token'] = {'id': user.auth_token,
                       'expires': utils.isoformat(user.auth_token_expires),
                       'tenant': {'id': user.uuid, 'name': user.realname}}
    access['user'] = {'id': user.uuid, 'name': user.realname,
                      'roles': list(user.groups.values('id', 'name')),
                      'roles_links': []}
    access['serviceCatalog'] = []
    append = access['serviceCatalog'].append
    for s in Service.objects.all().order_by('id'):
        append({'name': s.name, 'type': s.type,
                'endpoints': [{'adminURL': s.api_url,
                               'publicURL': s.api_url,
                               'internalURL': s.api_url,
                               'SNF:uiURL': s.url,
                               'region': s.name}]})

    if request.serialization == 'xml':
        return xml_response({'access': access}, 'api/access.xml')
    else:
        return json_response(access)
