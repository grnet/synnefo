
from django.http import HttpResponse
from django.db import transaction 
from django.conf import settings
from synnefo.lib.commissioning import CallError, get_callpoint

from .callpoint import API_Callpoint

import json
from traceback import format_exc

def _get_body(request):
    body = request.raw_post_data
    if body is None:
        body = request.GET.get('body', None)
    return body

callpoints = {('quotaholder', 'v'): API_Callpoint()}

@transaction.commit_on_success
def view(request, appname=None, version=None, callname=None):
    if (appname, version) not in callpoints:
        return HttpResponse(status=404)

    callpoint = callpoints[(appname, version)]
    body = _get_body(request)
    try:
        body = callpoint.make_call_from_json(callname, body)
        status = 200
    except Exception, e:
        status = 450
        if not isinstance(e, CallError):
            e.args += (''.join(format_exc()),)
            e = CallError.from_exception(e)
            status = 500

        body = json.dumps(e.to_dict())

    return HttpResponse(status=status, content=body)
