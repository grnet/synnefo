# Copyright (C) 2010-2014 GRNET S.A.

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

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from astakos.im import transaction

from snf_django.lib import api
from snf_django.lib.api.faults import BadRequest, ItemNotFound
from snf_django.lib.api import utils
from django.core.cache import cache

from astakos.im import settings
from astakos.im import register
from astakos.im.quotas import get_user_quotas, service_get_quotas, \
    service_get_project_quotas, project_ref, Project

import astakos.quotaholder_app.exception as qh_exception
import astakos.quotaholder_app.callpoint as qh

from .util import (json_response, is_integer, are_integer, check_is_dict,
                   user_from_token, component_from_token)


def get_visible_resources():
    key = "resources"
    result = cache.get(key)
    if result is None:
        result = register.get_api_visible_resources()
        cache.set(key, result, settings.RESOURCE_CACHE_TIMEOUT)
    return result


@api.api_method(http_method='GET', token_required=True, user_required=False)
@user_from_token
def quotas(request):
    visible_resources = get_visible_resources()
    resource_names = [r.name for r in visible_resources]
    memberships = request.user.projectmembership_set.actually_accepted()
    memberships = memberships.exclude(project__state__in=Project.HIDDEN_STATES)

    sources = [project_ref(m.project.uuid) for m in memberships]
    result = get_user_quotas(request.user, resources=resource_names,
                             sources=sources)
    return json_response(result)


@api.api_method(http_method='GET', token_required=True, user_required=False)
@component_from_token
def service_quotas(request):
    userstr = request.GET.get('user')
    users = userstr.split(",") if userstr is not None else None
    projectstr = request.GET.get('project')
    projects = projectstr.split(",") if projectstr is not None else None
    result = service_get_quotas(request.component_instance, users=users,
                                sources=projects)

    if userstr is not None and result == {}:
        raise ItemNotFound("No user with UUID '%s'" % userstr)

    return json_response(result)


@api.api_method(http_method='GET', token_required=True, user_required=False)
@component_from_token
def service_project_quotas(request):
    projectstr = request.GET.get('project')
    projects = projectstr.split(',') if projectstr is not None else None
    result = service_get_project_quotas(request.component_instance,
                                        projects=projects)

    if projectstr is not None and result == {}:
        raise ItemNotFound("No project with UUID '%s'" % projectstr)

    return json_response(result)


@api.api_method(http_method='GET', token_required=False, user_required=False)
def resources(request):
    resources = get_visible_resources()
    result = register.resources_to_dict(resources)
    return json_response(result)


@csrf_exempt
def commissions(request):
    method = request.method
    if method == 'GET':
        return get_pending_commissions(request)
    elif method == 'POST':
        return issue_commission(request)
    return api.api_method_not_allowed(request, allowed_methods=['GET', 'POST'])


@api.api_method(http_method='GET', token_required=True, user_required=False)
@component_from_token
def get_pending_commissions(request):
    client_key = unicode(request.component_instance)

    result = qh.get_pending_commissions(clientkey=client_key)
    return json_response(result)


def _provisions_to_list(provisions):
    lst = []
    for provision in provisions:
        try:
            holder = provision['holder']
            source = provision['source']
            resource = provision['resource']
            quantity = provision['quantity']
            key = (holder, source, resource)
            lst.append((key, quantity))
            if not is_integer(quantity):
                raise ValueError()
        except (TypeError, KeyError, ValueError):
            raise BadRequest("Malformed provision %s" % unicode(provision))
    return lst


@csrf_exempt
@api.api_method(http_method='POST', token_required=True, user_required=False)
@component_from_token
def issue_commission(request):
    input_data = utils.get_json_body(request)
    check_is_dict(input_data)

    client_key = unicode(request.component_instance)
    provisions = input_data.get('provisions')
    if provisions is None:
        raise BadRequest("Provisions are missing.")
    if not isinstance(provisions, list):
        raise BadRequest("Provisions should be a list.")

    provisions = _provisions_to_list(provisions)
    force = input_data.get('force', False)
    if not isinstance(force, bool):
        raise BadRequest('"force" option should be a boolean.')

    auto_accept = input_data.get('auto_accept', False)
    if not isinstance(auto_accept, bool):
        raise BadRequest('"auto_accept" option should be a boolean.')

    name = input_data.get('name', "")
    if not isinstance(name, basestring):
        raise BadRequest("Commission name should be a string.")

    try:
        result = _issue_commission(clientkey=client_key,
                                   provisions=provisions,
                                   name=name,
                                   force=force,
                                   accept=auto_accept)
        data = {"serial": result}
        status_code = 201
    except (qh_exception.NoCapacityError,
            qh_exception.NoQuantityError) as e:
        status_code = 413
        body = {"message": e.message,
                "code": status_code,
                "data": e.data,
                }
        data = {"overLimit": body}
    except qh_exception.NoHoldingError as e:
        status_code = 404
        body = {"message": e.message,
                "code": status_code,
                "data": e.data,
                }
        data = {"itemNotFound": body}
    except qh_exception.InvalidDataError as e:
        status_code = 400
        body = {"message": e.message,
                "code": status_code,
                }
        data = {"badRequest": body}

    return json_response(data, status_code=status_code)


@transaction.commit_on_success
def _issue_commission(clientkey, provisions, name, force, accept):
    serial = qh.issue_commission(clientkey=clientkey,
                                 provisions=provisions,
                                 name=name,
                                 force=force)
    if accept:
        qh.resolve_pending_commission(clientkey=clientkey, serial=serial)

    return serial


def notFoundCF(serial):
    body = {"code": 404,
            "message": "serial %s does not exist" % serial,
            }
    return {"itemNotFound": body}


def conflictingCF(serial):
    body = {"code": 400,
            "message": "cannot both accept and reject serial %s" % serial,
            }
    return {"badRequest": body}


@csrf_exempt
@api.api_method(http_method='POST', token_required=True, user_required=False)
@component_from_token
@transaction.commit_on_success
def resolve_pending_commissions(request):
    input_data = utils.get_json_body(request)
    check_is_dict(input_data)

    client_key = unicode(request.component_instance)
    accept = input_data.get('accept', [])
    reject = input_data.get('reject', [])

    if not isinstance(accept, list) or not isinstance(reject, list):
        m = '"accept" and "reject" should reference lists of serials.'
        raise BadRequest(m)

    if not are_integer(accept) or not are_integer(reject):
        raise BadRequest("Serials should be integer.")

    result = qh.resolve_pending_commissions(clientkey=client_key,
                                            accept_set=accept,
                                            reject_set=reject)
    accepted, rejected, notFound, conflicting = result
    notFound = [(serial, notFoundCF(serial)) for serial in notFound]
    conflicting = [(serial, conflictingCF(serial)) for serial in conflicting]
    cloudfaults = notFound + conflicting
    data = {'accepted': accepted,
            'rejected': rejected,
            'failed': cloudfaults
            }

    return json_response(data)


@api.api_method(http_method='GET', token_required=True, user_required=False)
@component_from_token
def get_commission(request, serial):
    data = request.GET
    client_key = unicode(request.component_instance)
    try:
        serial = int(serial)
    except ValueError:
        raise BadRequest("Serial should be an integer.")

    try:
        data = qh.get_commission(clientkey=client_key,
                                 serial=serial)
        status_code = 200
        return json_response(data, status_code)
    except qh_exception.NoCommissionError:
        return HttpResponse(status=404)


@csrf_exempt
@api.api_method(http_method='POST', token_required=True, user_required=False)
@component_from_token
@transaction.commit_on_success
def serial_action(request, serial):
    input_data = utils.get_json_body(request)
    check_is_dict(input_data)

    try:
        serial = int(serial)
    except ValueError:
        raise BadRequest("Serial should be an integer.")

    client_key = unicode(request.component_instance)

    accept = 'accept' in input_data
    reject = 'reject' in input_data

    if accept == reject:
        raise BadRequest('Specify either accept or reject action.')

    result = qh.resolve_pending_commission(clientkey=client_key,
                                           serial=serial,
                                           accept=accept)
    response = HttpResponse()
    if not result:
        response.status_code = 404

    return response
