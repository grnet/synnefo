# Copyright (C) 2010-2015 GRNET S.A. and individual contributors
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

from collections import defaultdict

from django.views.decorators.csrf import csrf_exempt

from snf_django.lib.api import faults, utils, api_method
from django.core.cache import cache

from astakos.im import settings
from astakos.im.models import Service, AstakosUser, ProjectMembership
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

        user_projects = user.project_set.filter(projectmembership__state__in=\
            ProjectMembership.ACCEPTED_STATES).values_list("uuid", flat=True)

        d["access"]["token"] = {
            "id": user.auth_token,
            "expires": utils.isoformat(user.auth_token_expires),
            "tenant": {"id": user.uuid, "name": user.realname}}
        d["access"]["user"] = {
            "id": user.uuid, 'name': user.realname,
            "roles": [dict(id=str(g['id']), name=g['name']) for g in
                      user.groups.values('id', 'name')],
            "roles_links": [],
            "projects": list(user_projects),
            }

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
