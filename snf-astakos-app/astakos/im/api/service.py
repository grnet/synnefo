# Copyright 2011-2012 GRNET S.A. All rights reserved.
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

from functools import wraps
from time import time, mktime

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import simplejson as json

from . import render_fault, __get_uuid_displayname_catalogs, __send_feedback
from .faults import (
    Fault, Unauthorized, InternalServerError, BadRequest, ItemNotFound)
from astakos.im.models import Service

logger = logging.getLogger(__name__)


def api_method(http_method=None, token_required=False):
    """Decorator function for views that implement an API method."""
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            try:
                if http_method and request.method != http_method:
                    raise BadRequest('Method not allowed.')
                x_auth_token = request.META.get('HTTP_X_AUTH_TOKEN')
                if token_required:
                    if not x_auth_token:
                        raise Unauthorized('Access denied')
                    try:
                        service = Service.objects.get(auth_token=x_auth_token)

                        # Check if the token has expired.
                        if service.auth_token_expires:
                            if (time() - mktime(service.auth_token_expires.timetuple())) > 0:
                                raise Unauthorized('Authentication expired')
                    except Service.DoesNotExist, e:
                        raise Unauthorized('Invalid X-Auth-Token')
                response = func(request, *args, **kwargs)
                return response
            except Fault, fault:
                return render_fault(request, fault)
            except BaseException, e:
                logger.exception('Unexpected error: %s' % e)
                fault = InternalServerError('Unexpected error')
                return render_fault(request, fault)
        return wrapper
    return decorator

@csrf_exempt
@api_method(http_method='POST', token_required=True)
def get_uuid_displayname_catalogs(request):
    # Normal Response Codes: 200
    # Error Response Codes: internalServerError (500)
    #                       badRequest (400)
    #                       unauthorised (401)

    return __get_uuid_displayname_catalog(request)

@csrf_exempt
@api_method(http_method='POST', token_required=True)
def send_feedback(request, email_template_name='im/feedback_mail.txt'):
    # Normal Response Codes: 200
    # Error Response Codes: internalServerError (500)
    #                       badRequest (400)
    #                       unauthorised (401)

    return __send_feedback(request, email_template_name)
