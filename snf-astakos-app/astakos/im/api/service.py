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
from functools import wraps
from django.views.decorators.csrf import csrf_exempt

from . import  __get_uuid_displayname_catalogs, __send_feedback
from snf_django.lib import api
from snf_django.lib.api import faults
from astakos.im.models import Service

import logging
logger = logging.getLogger(__name__)


def service_from_token(func):
    """Decorator for authenticating service by it's token.

    Check that a service with the corresponding token exists. Also,
    if service's token has an expiration token, check that it has not
    expired.

    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        try:
            token = request.x_auth_token
        except AttributeError:
            raise faults.Unauthorized("No authentication token")

        if not token:
            raise faults.Unauthorized("Invalid X-Auth-Token")
        try:
            service = Service.objects.get(auth_token=token)
        except Service.DoesNotExist:
            raise faults.Unauthorized("Invalid X-Auth-Token")

        # Check if the token has expired
        expiration_date = service.auth_token_expires
        if expiration_date:
            expires_at = mktime(expiration_date.timetuple())
            if time() > expires_at:
                raise faults.Unauthorized("Authentication expired")

        request.service_instance = service
        return func(request, *args, **kwargs)
    return wrapper


@csrf_exempt
@api.api_method(http_method='POST', token_required=True, user_required=False,
            logger=logger)
@service_from_token  # Authenticate service !!
def get_uuid_displayname_catalogs(request):
    # Normal Response Codes: 200
    # Error Response Codes: internalServerError (500)
    #                       badRequest (400)
    #                       unauthorised (401)
    return __get_uuid_displayname_catalogs(request, user_call=False)


@csrf_exempt
@api.api_method(http_method='POST', token_required=True, user_required=False,
            logger=logger)
@service_from_token  # Authenticate service !!
def send_feedback(request, email_template_name='im/feedback_mail.txt'):
    # Normal Response Codes: 200
    # Error Response Codes: internalServerError (500)
    #                       badRequest (400)
    #                       unauthorised (401)
    return __send_feedback(request, email_template_name)
