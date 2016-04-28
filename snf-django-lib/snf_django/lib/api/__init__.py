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
import sys
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
django_logger = getLogger("django.request")


def get_token(request):
    """Get the Authentication Token of a request."""
    token = request.GET.get("X-Auth-Token", None)
    if not token:
        token = request.META.get("HTTP_X_AUTH_TOKEN", None)
    return token


def api_method(http_method=None, token_required=True, user_required=True,
               logger=None, format_allowed=True, astakos_auth_url=None,
               serializations=None, strict_serlization=False):
    """Decorator function for views that implement an API method."""
    if not logger:
        logger = log

    serializations = serializations or ['json', 'xml']

    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            try:
                # Explicitly set request encoding to UTF-8 instead of relying
                # to the DEFAULT_CHARSET setting. See:
                # https://docs.djangoproject.com/en/1.4/ref/unicode/#form-submission # flake8: noqa
                request.encoding = 'utf-8'

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
                    raise faults.NotAllowed("Method not allowed",
                                            allowed_methods=[http_method])

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
                    astakos_url = astakos_auth_url
                    if astakos_url is None:
                        try:
                            astakos_url = settings.ASTAKOS_AUTH_URL
                        except AttributeError:
                            logger.error("Cannot authenticate without having"
                                         " an Astakos Authentication URL")
                            raise
                    astakos = AstakosClient(token, astakos_url,
                                            use_pool=True,
                                            retry=2,
                                            logger=logger)
                    user_info = astakos.authenticate()
                    _user_access = user_info["access"]["user"]
                    request.user_uniq = _user_access["id"]
                    request.user_projects = _user_access.get("projects", None)
                    request.user = user_info

                # Get the response object
                response = func(request, *args, **kwargs)

                # Fill in response variables
                update_response_headers(request, response)
                return response
            except faults.Fault as fault:
                if fault.code >= 500:
                    django_logger.error("Unexpected API Error: %s",
                                        request.path,
                                        exc_info=sys.exc_info(),
                                        extra={
                                            "status_code": fault.code,
                                            "request": request})
                return render_fault(request, fault)
            except AstakosClientException as err:
                fault = faults.Fault(message=err.message,
                                     details=err.details,
                                     code=err.status)
                if fault.code >= 500:
                    django_logger.error("Unexpected AstakosClient Error: %s",
                                        request.path,
                                        exc_info=sys.exc_info(),
                                        extra={
                                            "status_code": fault.code,
                                            "request": request})
                return render_fault(request, fault)
            except:
                django_logger.error("Internal Server Error: %s", request.path,
                                    exc_info=sys.exc_info(),
                                    extra={
                                        "status_code": '500',
                                        "request": request})
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
        _base_content_is_iter = getattr(response, '_base_content_is_iter',
                                        None)
        if (_base_content_is_iter is not None and not _base_content_is_iter):
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
    if response.status_code == 405 and hasattr(fault, 'allowed_methods'):
        response['Allow'] = ','.join(fault.allowed_methods)
    update_response_headers(request, response)
    return response


@api_method(token_required=False, user_required=False)
def api_endpoint_not_found(request):
    raise faults.BadRequest("API endpoint not found")


@api_method(token_required=False, user_required=False)
def api_method_not_allowed(request, allowed_methods):
    raise faults.NotAllowed("Method not allowed",
                            allowed_methods=allowed_methods)


def allow_jsonp(key='callback'):
    """
    Wrapper to enable jsonp responses.
    """
    def wrapper(func):
        @wraps(func)
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


def user_in_groups(permitted_groups, logger=None):
    """Check that the request user belongs to one of permitted groups.

    Django view wrapper to check that the already identified request user
    belongs to one of the allowed groups.

    """
    if not logger:
        logger = log

    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            if hasattr(request, "user") and request.user is not None:
                groups = request.user["access"]["user"]["roles"]
                groups = [g["name"] for g in groups]
            else:
                raise faults.Forbidden

            common_groups = set(groups) & set(permitted_groups)

            if not common_groups:
                msg = ("Not allowing access to '%s' by user '%s'. User does"
                       " not belong to a valid group. User groups: %s,"
                       " Required groups %s"
                       % (request.path, request.user, groups,
                          permitted_groups))
                logger.error(msg)
                raise faults.Forbidden

            logger.info("User '%s' in groups '%s' accessed view '%s'",
                        request.user_uniq, groups, request.path)

            return func(request, *args, **kwargs)
        return wrapper
    return decorator
