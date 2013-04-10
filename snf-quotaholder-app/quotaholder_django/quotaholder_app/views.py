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


from django.http import HttpResponse
from django.db import transaction
from django.conf import settings
from synnefo.lib.commissioning import CallError

from .callpoint import API_Callpoint

import json
from traceback import format_exc

import logging
logger = logging.getLogger(__name__)

try:
    from django.views.decorators.csrf import csrf_exempt
except ImportError:
    def csrf_exempt(func):
        return func


def _get_body(request):
    body = request.raw_post_data
    if body is None:
        body = request.GET.get('body', None)
    return body

callpoints = {('quotaholder', 'v'): API_Callpoint()}


@transaction.commit_manually
@csrf_exempt
def view(request, appname='quotaholder', version=None, callname=None):
    if (appname, version) not in callpoints:
        return HttpResponse(status=404)

    if request.META.get('HTTP_X_AUTH_TOKEN') != settings.QUOTAHOLDER_TOKEN:
        return HttpResponse(status=403, content='invalid token')

    callpoint = callpoints[(appname, version)]
    body = _get_body(request)
    try:
        body = callpoint.make_call_from_json(callname, body)
        status = 200
    except Exception as e:
        logger.exception(e)
        status = 450
        if not isinstance(e, CallError):
            e.args += (''.join(format_exc()),)
            e = CallError.from_exception(e)
            status = 500

        body = json.dumps(e.to_dict())

    return HttpResponse(status=status, content=body)
