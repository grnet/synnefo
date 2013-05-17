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

from time import time, mktime

from django.http import HttpResponse
from django.utils import simplejson as json
from django.views.decorators.csrf import csrf_exempt

from snf_django.lib import api
from snf_django.lib.api import faults

from astakos.im.util import epoch

from .util import (
    get_uuid_displayname_catalogs as get_uuid_displayname_catalogs_util,
    send_feedback as send_feedback_util,
    user_from_token)

import logging
logger = logging.getLogger(__name__)


@api.api_method(http_method="GET", token_required=True, user_required=False,
                logger=logger)
@user_from_token  # Authenticate user!!
def authenticate(request):
    # Normal Response Codes: 200
    # Error Response Codes: internalServerError (500)
    #                       badRequest (400)
    #                       unauthorised (401)
    user = request.user
    if not user:
        raise faults.BadRequest('No user')

    # Check if the is active.
    if not user.is_active:
        raise faults.Unauthorized('User inactive')

    # Check if the token has expired.
    if (time() - mktime(user.auth_token_expires.timetuple())) > 0:
        raise faults.Unauthorized('Authentication expired')

    if not user.signed_terms:
        raise faults.Unauthorized('Pending approval terms')

    response = HttpResponse()
    user_info = {
        'id': user.id,
        'username': user.username,
        'uuid': user.uuid,
        'email': [user.email],
        'name': user.realname,
        'groups': list(user.groups.all().values_list('name', flat=True)),
        'auth_token': request.META.get('HTTP_X_AUTH_TOKEN'),
        'auth_token_created': epoch(user.auth_token_created),
        'auth_token_expires': epoch(user.auth_token_expires)}

    response.content = json.dumps(user_info)
    response['Content-Type'] = 'application/json; charset=UTF-8'
    response['Content-Length'] = len(response.content)
    return response


@csrf_exempt
@api.api_method(http_method="POST", token_required=True, user_required=False,
                logger=logger)
@user_from_token  # Authenticate user!!
def get_uuid_displayname_catalogs(request):
    # Normal Response Codes: 200
    # Error Response Codes: internalServerError (500)
    #                       badRequest (400)
    #                       unauthorised (401)

    return get_uuid_displayname_catalogs_util(request)


@csrf_exempt
@api.api_method(http_method="POST", token_required=True, user_required=False,
                logger=logger)
@user_from_token  # Authenticate user!!
def send_feedback(request, email_template_name='im/feedback_mail.txt'):
    # Normal Response Codes: 200
    # Error Response Codes: internalServerError (500)
    #                       badRequest (400)
    #                       unauthorised (401)

    return send_feedback_util(request, email_template_name)
