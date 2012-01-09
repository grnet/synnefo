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
from django.template.loader import render_to_string

from astakos.im.target.util import prepare_response
from astakos.im.models import User

from urllib import unquote

from hashlib import new as newhasher

def login(request):
    username = request.POST.get('username')
    password = request.POST.get('password')
    
    if not username:
        return HttpResponseBadRequest('No user')
    
    if not password:
        return HttpResponseBadRequest('No password')
    
    try:
        user = User.objects.get(uniq=username)
    except User.DoesNotExist:
        return HttpResponseBadRequest('No such user')
    
    hasher = newhasher('sha256')
    hasher.update(password)
    password = hasher.hexdigest()
    
    if not password or user.password != password:
        return HttpResponseBadRequest('Wrong password')
    
    if user.state == 'UNVERIFIED':
        return HttpResponseBadRequest('Unverified account')
    
    next = request.POST.get('next')
    return prepare_response(request, user, next)
    
def activate(request):
    token = request.GET.get('auth')
    next = request.GET.get('next')
    try:
        user = User.objects.get(auth_token=token)
    except User.DoesNotExist:
        return HttpResponseBadRequest('No such user')
    
    user.state = 'ACTIVE'
    user.save()
    return prepare_response(request, user, next, renew=True)

def reset_password(request):
    if request.method == 'GET':
        cookie_value = unquote(request.COOKIES.get('_pithos2_a', ''))
        if cookie_value and '|' in cookie_value:
            token = cookie_value.split('|', 1)[1]
        else:
            token = request.GET.get('auth')
        next = request.GET.get('next')
        username = request.GET.get('username')
        kwargs = {'auth': token,
                  'next': next,
                  'username' : username}
        if not token:
            kwargs.update({'status': 'error',
                           'message': 'Missing token'})
        html = render_to_string('reset.html', kwargs)
        return HttpResponse(html)
    elif request.method == 'POST':
        token = request.POST.get('auth')
        username = request.POST.get('username')
        password = request.POST.get('password')
        next = request.POST.get('next')
        if not token:
            status = 'error'
            message = 'Bad Request: missing token'
        try:
            user = User.objects.get(auth_token=token)
            if username != user.uniq:
                status = 'error'
                message = 'Bad Request: username mismatch'
            else:
                user.password = password
                user.status = 'NORMAL'
                user.save()
                return prepare_response(request, user, next, renew=True)
        except User.DoesNotExist:
            status = 'error'
            message = 'Bad Request: invalid token'
            
        html = render_to_string('reset.html', {
                'status': status,
                'message': message})
        return HttpResponse(html)
