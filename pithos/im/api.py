from traceback import format_exc
from time import time, mktime
from django.conf import settings
from django.http import HttpResponse
from django.utils import simplejson as json

from pithos.im.faults import BadRequest, Unauthorized, ServiceUnavailable
from pithos.im.models import User

import datetime

def render_fault(request, fault):
    if settings.DEBUG or settings.TEST:
        fault.details = format_exc(fault)
    
    request.serialization = 'text'
    data = '\n'.join((fault.message, fault.details)) + '\n'
    response = HttpResponse(data, status=fault.code)
    return response

def update_response_headers(response):
    response['Content-Type'] = 'application/json; charset=UTF-8'
    response['Content-Length'] = len(response.content)

def authenticate(request):
    # Normal Response Codes: 204
    # Error Response Codes: serviceUnavailable (503)
    #                       badRequest (400)
    #                       unauthorised (401)
    try:
        if request.method != 'GET':
            raise BadRequest('Method not allowed.')
        x_auth_token = request.META.get('HTTP_X_AUTH_TOKEN')
        if not x_auth_token:
            return render_fault(request, BadRequest('Missing X-Auth-Token'))
        
        try:
            user = User.objects.get(auth_token=x_auth_token)
        except User.DoesNotExist, e:
            return render_fault(request, Unauthorized('Invalid X-Auth-Token')) 
        
        # Check if the is active.
        if user.state != 'ACTIVE':
            return render_fault(request, Unauthorized('User inactive'))
        
        # Check if the token has expired.
        if (time() - mktime(user.auth_token_expires.timetuple())) > 0:
            return render_fault(request, Unauthorized('Authentication expired'))
        
        response = HttpResponse()
        response.status=204
        user_info = user.__dict__
        for k,v in user_info.items():
            if isinstance(v,  datetime.datetime):
                user_info[k] = v.strftime('%a, %d-%b-%Y %H:%M:%S %Z')
        user_info.pop('_state')
        response.content = json.dumps(user_info)
        update_response_headers(response)
        return response
    except BaseException, e:
        fault = ServiceUnavailable('Unexpected error')
        return render_fault(request, fault)