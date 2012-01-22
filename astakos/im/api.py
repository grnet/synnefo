# Copyright 2011 GRNET S.A. All rights reserved.
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

from traceback import format_exc
from time import time, mktime
from django.conf import settings
from django.http import HttpResponse
from django.utils import simplejson as json

from astakos.im.faults import BadRequest, Unauthorized, ServiceUnavailable
from astakos.im.models import AstakosUser

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
            user = AstakosUser.objects.get(auth_token=x_auth_token)
        except AstakosUser.DoesNotExist, e:
            return render_fault(request, Unauthorized('Invalid X-Auth-Token')) 
        
        # Check if the is active.
        if not user.is_active:
            return render_fault(request, Unauthorized('User inactive'))
        
        # Check if the token has expired.
        if (time() - mktime(user.auth_token_expires.timetuple())) > 0:
            return render_fault(request, Unauthorized('Authentication expired'))
        
        response = HttpResponse()
        response.status=204
        user_info = {'uniq':user.username,
                     'auth_token':user.auth_token,
                     'auth_token_created':user.auth_token_created,
                     'auth_token_expires':user.auth_token_expires}
        response.content = json.dumps(user_info)
        update_response_headers(response)
        return response
    except BaseException, e:
        fault = ServiceUnavailable('Unexpected error')
        return render_fault(request, fault)
