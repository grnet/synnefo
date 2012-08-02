# Create your views here.

from django.http import HttpResponse
from django.db import transaction 
from quotaholder import QuotaholderException
from quotaholder.controllers.django_controller import QuotaholderDjangoController

import json

_callpoint = FSCRUDCallpoint()

def _get_body(request):
    body = request.raw_post_data
    if body is None:
        body = request.GET.get('body', None)
    return body


@transaction.commit_on_success
def fscrude_0_1(request, call_name=None):
    body = _get_body(request)
    try:
        body = _callpoint.make_call_from_json(call_name, body)
        status = 200
    except QuotaholderException, e:
        status, body = _callpoint.http_exception(e)

    return HttpResponse(status=status, content=body)

