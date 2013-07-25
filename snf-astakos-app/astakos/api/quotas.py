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

from django.utils import simplejson as json
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

from snf_django.lib.db.transaction import commit_on_success_strict

from snf_django.lib import api
from snf_django.lib.api.faults import BadRequest, ItemNotFound

from astakos.im.register import get_resources
from astakos.im.quotas import get_user_quotas, service_get_quotas

import astakos.quotaholder_app.exception as qh_exception
import astakos.quotaholder_app.callpoint as qh

from .util import (json_response, is_integer, are_integer,
                   user_from_token, component_from_token)


@api.api_method(http_method='GET', token_required=True, user_required=False)
@user_from_token
def quotas(request):
    result = get_user_quotas(request.user)
    return json_response(result)


@api.api_method(http_method='GET', token_required=True, user_required=False)
@component_from_token
def service_quotas(request):
    user = request.GET.get('user')
    users = [user] if user is not None else None
    result = service_get_quotas(request.component_instance, users=users)

    if user is not None and result == {}:
        raise ItemNotFound("No such user '%s'" % user)

    return json_response(result)


@api.api_method(http_method='GET', token_required=False, user_required=False)
def resources(request):
    result = get_resources()
    return json_response(result)


@csrf_exempt
def commissions(request):
    method = request.method
    if method == 'GET':
        return get_pending_commissions(request)
    elif method == 'POST':
        return issue_commission(request)
    return api.api_method_not_allowed(request)


@api.api_method(http_method='GET', token_required=True, user_required=False)
@component_from_token
def get_pending_commissions(request):
    client_key = str(request.component_instance)

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
            raise BadRequest("Malformed provision %s" % str(provision))
    return lst


@csrf_exempt
@api.api_method(http_method='POST', token_required=True, user_required=False)
@component_from_token
def issue_commission(request):
    data = request.raw_post_data
    try:
        input_data = json.loads(data)
    except json.JSONDecodeError:
        raise BadRequest("POST data should be in json format.")

    client_key = str(request.component_instance)
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


@commit_on_success_strict()
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
@commit_on_success_strict()
def resolve_pending_commissions(request):
    data = request.raw_post_data
    try:
        input_data = json.loads(data)
    except json.JSONDecodeError:
        raise BadRequest("POST data should be in json format.")

    client_key = str(request.component_instance)
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
    client_key = str(request.component_instance)
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
@commit_on_success_strict()
def serial_action(request, serial):
    data = request.raw_post_data
    try:
        input_data = json.loads(data)
    except json.JSONDecodeError:
        raise BadRequest("POST data should be in json format.")

    try:
        serial = int(serial)
    except ValueError:
        raise BadRequest("Serial should be an integer.")

    client_key = str(request.component_instance)

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
