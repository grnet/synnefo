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

from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.conf import settings

from pithos.im.target.util import prepare_response
from pithos.im.models import User

def login(request):
    username = '%s@local' % request.POST.get('username')
    password = request.POST.get('password')
    
    if not username:
        return HttpResponseBadRequest('No user')
    
    if not username:
        return HttpResponseBadRequest('No password')
    
    try:
        user = User.objects.get(uniq=username)
    except User.DoesNotExist:
        return HttpResponseBadRequest('No such user')
    
    if not password or user.password != password:
        return HttpResponseBadRequest('Wrong password')
    
    if user.state == 'UNVERIFIED':
        return HttpResponseBadRequest('Unverified account')
    
    next = request.POST.get('next')
    #if not next:
    #    return HttpResponse('')
    #if not request.user:
    #    return HttpResponseRedirect(next)
    
    return prepare_response(request, user, next)

def activate(request):
    token = request.GET.get('auth')
    url = request.GET.get('next')
    try:
        user = User.objects.get(auth_token=token)
    except User.DoesNotExist:
        return HttpResponseBadRequest('No such user')
    
    url = '%s?next=%sui' %(url, settings.BASE_URL)
    user.state = 'ACTIVE'
    user.renew_token()
    user.save()
    response = HttpResponse()
    response['Location'] = url
    response.status_code = 302
    return response