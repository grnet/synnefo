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

from synnefo.lib.db.transaction import commit_on_success_strict
from astakos.api.util import json_response

from snf_django.lib import api
from snf_django.lib.api.faults import BadRequest, InternalServerError

from astakos.im.api import api_method as generic_api_method
from astakos.im.api.user import user_from_token
from astakos.im.api.service import service_from_token

from astakos.im.quotas import get_user_quotas, get_resources

import astakos.quotaholder.exception as qh_exception
from astakos.quotaholder.callpoint import QuotaholderDjangoDBCallpoint
qh = QuotaholderDjangoDBCallpoint()


@api.api_method(http_method='GET', token_required=True, user_required=False)
@user_from_token
def quotas(request, user=None):
    result = get_user_quotas(user)
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
    else:
        raise BadRequest('Method not allowed.')


@api.api_method(http_method='GET', token_required=True, user_required=False)
@service_from_token
def get_pending_commissions(request):
    data = request.GET
    client_key = str(request.service_instance)

    result = qh.get_pending_commissions(clientkey=client_key)
    return json_response(result)


@csrf_exempt
@api.api_method(http_method='POST', token_required=True, user_required=False)
@service_from_token
def issue_commission(request):
    data = request.raw_post_data
    input_data = json.loads(data)

    client_key = str(request.service_instance)
    provisions = input_data['provisions']
    force = input_data.get('force', False)
    auto_accept = input_data.get('auto_accept', False)

    try:
        result = _issue_commission(clientkey=client_key,
                                   provisions=provisions,
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
def _issue_commission(clientkey, provisions, force, accept):
    serial = qh.issue_commission(clientkey=clientkey,
                                 provisions=provisions,
                                 force=force)
    if accept:
        done = qh.accept_commission(clientkey=clientkey,
                                    serial=serial)

    return serial


def failed_to_cloudfault(failed):
    serial, reason = failed
    if reason == 'NOTFOUND':
        body = {"code": 404,
                "message": "serial %s does not exist" % serial,
                }
        cloudfault = {"itemNotFound": body}
    elif reason == 'CONFLICT':
        body = {"code": 400,
                "message": "cannot both accept and reject serial %s" % serial,
                }
        cloudfault = {"badRequest": body}
    else:
        raise InternalServerError('Unexpected error')
    return (serial, cloudfault)


@csrf_exempt
@api.api_method(http_method='POST', token_required=True, user_required=False)
@service_from_token
@commit_on_success_strict()
def resolve_pending_commissions(request):
    data = request.raw_post_data
    input_data = json.loads(data)

    client_key = str(request.service_instance)
    accept = input_data.get('accept', [])
    reject = input_data.get('reject', [])

    result = qh.resolve_pending_commissions(clientkey=client_key,
                                            accept_set=accept,
                                            reject_set=reject)
    accepted, rejected, failed = result
    cloudfaults = [failed_to_cloudfault(f) for f in failed]
    data = {'accepted': accepted,
            'rejected': rejected,
            'failed': cloudfaults
            }

    return json_response(data)


@api.api_method(http_method='GET', token_required=True, user_required=False)
@service_from_token
def get_commission(request, serial):
    data = request.GET
    client_key = str(request.service_instance)
    serial = int(serial)

    try:
        data = qh.get_commission(clientkey=client_key,
                                 serial=serial)
        status_code = 200
        return json_response(data, status_code)
    except qh_exception.NoCommissionError as e:
        return HttpResponse(status=404)


@csrf_exempt
@api.api_method(http_method='POST', token_required=True, user_required=False)
@service_from_token
@commit_on_success_strict()
def serial_action(request, serial):
    data = request.raw_post_data
    input_data = json.loads(data)
    serial = int(serial)

    client_key = str(request.service_instance)

    accept = 'accept' in input_data
    reject = 'reject' in input_data

    if accept == reject:
        raise BadRequest('Specify either accept or reject action.')

    if accept:
        result = qh.accept_commission(clientkey=client_key,
                                      serial=serial)
    else:
        result = qh.reject_commission(clientkey=client_key,
                                      serial=serial)

    response = HttpResponse()
    if not result:
        response.status_code = 404

    return response
