# Copyright 2012, 2013 GRNET S.A. All rights reserved.
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
from traceback import format_exc
from time import time
from logging import getLogger
from wsgiref.handlers import format_date_time

from django.http import HttpResponse
from django.utils import cache
from django.utils import simplejson as json
from django.template.loader import render_to_string
from django.views.decorators import csrf

from astakosclient import AstakosClient
from astakosclient.errors import AstakosClientException
from django.conf import settings
from snf_django.lib.api import faults

import itertools

log = getLogger(__name__)


def get_token(request):
    """Get the Authentication Token of a request."""
    token = request.GET.get("X-Auth-Token", None)
    if not token:
        token = request.META.get("HTTP_X_AUTH_TOKEN", None)
    return token


def api_method(http_method=None, token_required=True, user_required=True,
               logger=None, format_allowed=True, astakos_url=None,
               serializations=None, strict_serlization=False):
    """Decorator function for views that implement an API method."""
    if not logger:
        logger = log

    serializations = serializations or ['json', 'xml']

    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            try:
                # Get the requested serialization format
                serialization = get_serialization(
                    request, format_allowed, serializations[0])

                # If guessed serialization is not supported, fallback to
                # the default serialization or return an API error in case
                # strict serialization flag is set.
                if not serialization in serializations:
                    if strict_serlization:
                        raise faults.BadRequest(("%s serialization not "
                                                "supported") % serialization)
                    serialization = serializations[0]
                request.serialization = serialization

                # Check HTTP method
                if http_method and request.method != http_method:
                    raise faults.BadRequest("Method not allowed")

                # Get authentication token
                request.x_auth_token = None
                if token_required or user_required:
                    token = get_token(request)
                    if not token:
                        msg = "Access denied. No authentication token"
                        raise faults.Unauthorized(msg)
                    request.x_auth_token = token

                # Authenticate
                if user_required:
                    assert(token_required), "Can not get user without token"
                    astakos = astakos_url or settings.ASTAKOS_BASE_URL
                    astakos = AstakosClient(astakos,
                                            use_pool=True,
                                            retry=2,
                                            logger=logger)
                    user_info = astakos.get_user_info(token)
                    request.user_uniq = user_info["uuid"]
                    request.user = user_info

                # Get the response object
                response = func(request, *args, **kwargs)

                # Fill in response variables
                update_response_headers(request, response)
                return response
            except faults.Fault, fault:
                if fault.code >= 500:
                    logger.exception("API ERROR")
                return render_fault(request, fault)
            except AstakosClientException as err:
                fault = faults.Fault(message=err.message,
                                     details=err.details,
                                     code=err.status)
                if fault.code >= 500:
                    logger.exception("Astakos ERROR")
                return render_fault(request, fault)
            except:
                logger.exception("Unexpected ERROR")
                fault = faults.InternalServerError("Unexpected error")
                return render_fault(request, fault)
        return csrf.csrf_exempt(wrapper)
    return decorator


def get_serialization(request, format_allowed=True,
                      default_serialization="json"):
    """Return the serialization format requested.

    Valid formats are 'json' and 'xml' and 'text'
    """

    if not format_allowed:
        return "text"

    # Try to get serialization from 'format' parameter
    _format = request.GET.get("format")
    if _format:
        if _format == "json":
            return "json"
        elif _format == "xml":
            return "xml"

    # Try to get serialization from path
    path = request.path
    if path.endswith(".json"):
        return "json"
    elif path.endswith(".xml"):
        return "xml"

    for item in request.META.get("HTTP_ACCEPT", "").split(","):
        accept, sep, rest = item.strip().partition(";")
        if accept == "application/json":
            return "json"
        elif accept == "application/xml":
            return "xml"

    return default_serialization


def update_response_headers(request, response):
    if not getattr(response, "override_serialization", False):
        serialization = request.serialization
        if serialization == "xml":
            response["Content-Type"] = "application/xml; charset=UTF-8"
        elif serialization == "json":
            response["Content-Type"] = "application/json; charset=UTF-8"
        elif serialization == "text":
            response["Content-Type"] = "text/plain; charset=UTF-8"
        else:
            raise ValueError("Unknown serialization format '%s'" %
                             serialization)

    if settings.DEBUG or getattr(settings, "TEST", False):
        response["Date"] = format_date_time(time())

    if not response.has_header("Content-Length"):
        # compatibility code for django 1.4
        _is_string = getattr(response, '_is_string', None)  # Django==1.2
        _base_content_is_iter = getattr(response, '_base_content_is_iter',
                                        None)
        if (_is_string is not None and _is_string) or\
                (_base_content_is_iter is not None and
                    not _base_content_is_iter):
            response["Content-Length"] = len(response.content)
        else:
            if not (response.has_header('Content-Type') and
                    response['Content-Type'].startswith(
                        'multipart/byteranges')):
                # save response content from been consumed if it is an iterator
                response._container, data = itertools.tee(response._container)
                response["Content-Length"] = len(str(data))

    cache.add_never_cache_headers(response)
    # Fix Vary and Cache-Control Headers. Issue: #3448
    cache.patch_vary_headers(response, ('X-Auth-Token',))
    cache.patch_cache_control(response, no_cache=True, no_store=True,
                              must_revalidate=True)


def render_fault(request, fault):
    """Render an API fault to an HTTP response."""
    # If running in debug mode add exception information to fault details
    if settings.DEBUG or getattr(settings, "TEST", False):
        fault.details = format_exc()

    try:
        serialization = request.serialization
    except AttributeError:
        request.serialization = "json"
        serialization = "json"

    # Serialize the fault data to xml or json
    if serialization == "xml":
        data = render_to_string("fault.xml", {"fault": fault})
    else:
        d = {fault.name: {"code": fault.code,
                          "message": fault.message,
                          "details": fault.details}}
        data = json.dumps(d)

    response = HttpResponse(data, status=fault.code)
    update_response_headers(request, response)
    return response


@api_method(token_required=False, user_required=False)
def api_endpoint_not_found(request):
    raise faults.BadRequest("API endpoint not found")


@api_method(token_required=False, user_required=False)
def api_method_not_allowed(request):
    raise faults.BadRequest('Method not allowed')


def allow_jsonp(key='callback'):
    """
    Wrapper to enable jsonp responses.
    """
    def wrapper(func):
        def view_wrapper(request, *args, **kwargs):
            response = func(request, *args, **kwargs)
            if 'content-type' in response._headers and \
               response._headers['content-type'][1] == 'application/json':
                callback_name = request.GET.get(key, None)
                if callback_name:
                    response.content = "%s(%s)" % (callback_name,
                                                   response.content)
                    response._headers['content-type'] = ('Content-Type',
                                                         'text/javascript')
            return response
        return view_wrapper
    return wrapper
