# Copyright 2011-2014 GRNET S.A. All rights reserved.
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

from collections import defaultdict

from django.views.decorators.csrf import csrf_exempt

from snf_django.lib.api import faults, utils, api_method
from django.core.cache import cache

from astakos.im import settings
from astakos.im.models import Service, AstakosUser
from astakos.oa2.backends.base import OA2Error
from astakos.oa2.backends.djangobackend import DjangoBackend
from .util import json_response, xml_response, validate_user,\
    get_content_length

import logging
logger = logging.getLogger(__name__)


def compute_endpoints():
    l = []
    for s in Service.objects.all().order_by("id").\
            prefetch_related('endpoints__data').\
            select_related('component'):
        endpoints = []
        for e in s.endpoints.all():
            endpoint = dict((ed.key, ed.value) for ed in e.data.all())
            endpoint["SNF:uiURL"] = s.component.url
            endpoint["region"] = "default"
            if s.name == 'astakos_weblogin':
                endpoint["SNF:webloginURL"] = endpoint["publicURL"]
            endpoints.append(endpoint)
        l.append({"name": s.name,
                  "type": s.type,
                  "endpoints": endpoints,
                  "endpoints_links": []})
    return l


def get_endpoints():
    key = "endpoints"
    result = cache.get(key)
    if result is None:
        result = compute_endpoints()
        cache.set(key, result, settings.ENDPOINT_CACHE_TIMEOUT)
    return result


@csrf_exempt
@api_method(http_method="POST", token_required=False, user_required=False,
            logger=logger)
def authenticate(request):
    try:
        content_length = get_content_length(request)
    except faults.LengthRequired:
        content_length = None

    public_mode = True if not content_length else False

    d = defaultdict(dict)
    if not public_mode:
        req = utils.get_json_body(request)

        uuid = None
        try:
            token_id = req['auth']['token']['id']
        except KeyError:
            try:
                token_id = req['auth']['passwordCredentials']['password']
                uuid = req['auth']['passwordCredentials']['username']
            except KeyError:
                raise faults.BadRequest(
                    'Malformed request: missing credentials')

        tenant = req['auth'].get('tenantName')

        if token_id is None:
            raise faults.BadRequest('Malformed request: missing token')

        try:
            user = AstakosUser.objects.get(auth_token=token_id)
        except AstakosUser.DoesNotExist:
            raise faults.Unauthorized('Invalid token')

        validate_user(user)

        if uuid is not None:
            if user.uuid != uuid:
                raise faults.Unauthorized('Invalid credentials')

        if tenant:
            if user.uuid != tenant:
                raise faults.BadRequest('Not conforming tenantName')

        d["access"]["token"] = {
            "id": user.auth_token,
            "expires": utils.isoformat(user.auth_token_expires),
            "tenant": {"id": user.uuid, "name": user.realname}}
        d["access"]["user"] = {
            "id": user.uuid, 'name': user.realname,
            "roles": [dict(id=str(g['id']), name=g['name']) for g in
                      user.groups.values('id', 'name')],
            "roles_links": []}

    d["access"]["serviceCatalog"] = get_endpoints()

    if request.serialization == 'xml':
        return xml_response({'d': d}, 'api/access.xml')
    else:
        return json_response(d)


@api_method(http_method="GET", token_required=False, user_required=False,
            logger=logger)
def validate_token(request, token_id):
    oa2_backend = DjangoBackend()
    try:
        token = oa2_backend.consume_token(token_id)
    except OA2Error, e:
        raise faults.ItemNotFound(e.message)

    belongsTo = request.GET.get('belongsTo')
    if belongsTo is not None:
        if not belongsTo.startswith(token.scope):
            raise faults.ItemNotFound(
                "The specified tenant is outside the token's scope")

    d = defaultdict(dict)
    d["access"]["token"] = {"id": token.code,
                            "expires": token.expires_at,
                            "tenant": {"id": token.user.uuid,
                                       "name": token.user.realname}}
    d["access"]["user"] = {"id": token.user.uuid,
                           'name': token.user.realname,
                           "roles": [dict(id=str(g['id']), name=g['name']) for
                                     g in token.user.groups.values('id',
                                                                   'name')],
                           "roles_links": []}

    if request.serialization == 'xml':
        return xml_response({'d': d}, 'api/access.xml')
    else:
        return json_response(d)
