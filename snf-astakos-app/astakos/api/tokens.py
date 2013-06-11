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

from collections import defaultdict

from django.views.decorators.csrf import csrf_exempt

from snf_django.lib.api import faults, utils, api_method

from astakos.im.models import Service, AstakosUser
from .util import json_response, xml_response, validate_user,\
    get_content_length

import logging
logger = logging.getLogger(__name__)


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
        req = utils.get_request_dict(request)

        uuid = None
        try:
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

        validate_user(user)

        if uuid is not None:
            if user.uuid != uuid:
                raise faults.Unauthorized('Invalid credentials')

        d["access"]["token"] = {
            "id": user.auth_token,
            "expires": utils.isoformat(user.auth_token_expires),
            "tenant": {"id": user.uuid, "name": user.realname}}
        d["access"]["user"] = {
            "id": user.uuid, 'name': user.realname,
            "roles": list(user.groups.values("id", "name")),
            "roles_links": []}

    d["access"]["serviceCatalog"] = []
    append = d["access"]["serviceCatalog"].append
    for s in Service.objects.all().order_by("id"):
        endpoints = []
        for l in [e.data.values('key', 'value') for e in s.endpoints.all()]:
            endpoint = dict((d['key'], d['value']) for d in l)
            endpoints.append(endpoint)
        append({"name": s.name,
                "type": s.type,
                "SNF:uiURL": s.component.url,
                "endpoints": endpoints,
                "endpoints_links": []})

    if request.serialization == 'xml':
        return xml_response({'d': d}, 'api/access.xml')
    else:
        return json_response(d)
