
from django.http import HttpResponse
from django.db import transaction 
from django.conf import settings
from commissioning import CommissionException, get_callpoint

import json

def _get_body(request):
    body = request.raw_post_data
    if body is None:
        body = request.GET.get('body', None)
    return body

callpoints = {}

@transaction.commit_on_success
def view(request, appname=None, version=None, callname=None):
    if (appname, version) not in callpoints:
        pointname = 'servers.' + appname
        Callpoint = get_callpoint(pointname, version=version)
        callpoint = Callpoint()
        callpoints[(appname, version)] = callpoint

    callpoint = callpoints[(appname, version)]
    body = _get_body(request)
    try:
        body = callpoint.make_call_from_json(callname, body)
        status = 200
    except CommissionException, e:
        if hasattr(callpoint, 'http_exception'):
            status, body = callpoint.http_exception(e)
        else:
	    from traceback import print_exc
	    print_exc()
            raise e
            status, body = 500, repr(e)

    return HttpResponse(status=status, content=body)

