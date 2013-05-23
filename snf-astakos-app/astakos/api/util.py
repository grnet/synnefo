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

from functools import wraps
from time import time, mktime

from django.http import HttpResponse
from django.utils import simplejson as json

from astakos.im.models import AstakosUser, Service
from snf_django.lib.api import faults

from astakos.im.forms import FeedbackForm
from astakos.im.functions import send_feedback as send_feedback_func

import logging
logger = logging.getLogger(__name__)

absolute = lambda request, url: request.build_absolute_uri(url)


def json_response(content, status_code=None):
    response = HttpResponse()
    if status_code is not None:
        response.status_code = status_code

    response.content = json.dumps(content)
    response['Content-Type'] = 'application/json; charset=UTF-8'
    response['Content-Length'] = len(response.content)
    return response


def is_integer(x):
    return isinstance(x, (int, long))


def are_integer(lst):
    return all(map(is_integer, lst))


def user_from_token(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        try:
            token = request.x_auth_token
        except AttributeError:
            raise faults.Unauthorized("No authentication token")

        if not token:
            raise faults.Unauthorized("Invalid X-Auth-Token")

        try:
            user = AstakosUser.objects.get(auth_token=token)
        except AstakosUser.DoesNotExist:
            raise faults.Unauthorized('Invalid X-Auth-Token')

        # Check if the user is active.
        if not user.is_active:
            raise faults.Unauthorized('User inactive')

        # Check if the token has expired.
        if user.token_expired():
            raise faults.Unauthorized('Authentication expired')

        # Check if the user has accepted the terms.
        if not user.signed_terms:
            raise faults.Unauthorized('Pending approval terms')

        request.user = user
        return func(request, *args, **kwargs)
    return wrapper


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


def get_uuid_displayname_catalogs(request, user_call=True):
    # Normal Response Codes: 200
    # Error Response Codes: BadRequest (400)

    try:
        input_data = json.loads(request.raw_post_data)
    except:
        raise faults.BadRequest('Request body should be json formatted.')
    else:
        uuids = input_data.get('uuids', [])
        if uuids is None and user_call:
            uuids = []
        displaynames = input_data.get('displaynames', [])
        if displaynames is None and user_call:
            displaynames = []
        user_obj = AstakosUser.objects
        d = {'uuid_catalog': user_obj.uuid_catalog(uuids),
             'displayname_catalog': user_obj.displayname_catalog(displaynames)}

        response = HttpResponse()
        response.content = json.dumps(d)
        response['Content-Type'] = 'application/json; charset=UTF-8'
        response['Content-Length'] = len(response.content)
        return response


def send_feedback(request, email_template_name='im/feedback_mail.txt'):
    form = FeedbackForm(request.POST)
    if not form.is_valid():
        logger.error("Invalid feedback request: %r", form.errors)
        raise faults.BadRequest('Invalid data')

    msg = form.cleaned_data['feedback_msg']
    data = form.cleaned_data['feedback_data']
    try:
        send_feedback_func(msg, data, request.user, email_template_name)
    except:
        return HttpResponse(status=502)
    return HttpResponse(status=200)
