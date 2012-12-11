# Copyright 2011-2012 GRNET S.A. All rights reserved.
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
from django.utils import simplejson as json

from astakos.im.models import AstakosUser
from astakos.im.api.faults import ItemNotFound

format = ('%a, %d %b %Y %H:%M:%S GMT')

def _get_user_by_username(user_id):
    try:
        user = AstakosUser.objects.get(username = user_id)
    except AstakosUser.DoesNotExist, e:
        raise ItemNotFound('Invalid userid')
    else:
        response = HttpResponse()
        response.status=200
        user_info = {'id':user.id,
                     'username':user.username,
                     'email':[user.email],
                     'name':user.realname,
                     'auth_token_created':user.auth_token_created.strftime(format),
                     'auth_token_expires':user.auth_token_expires.strftime(format),
                     'has_credits':user.has_credits,
                     'enabled':user.is_active,
                     'groups':[g.name for g in user.groups.all()]}
        response.content = json.dumps(user_info)
        response['Content-Type'] = 'application/json; charset=UTF-8'
        response['Content-Length'] = len(response.content)
        return response

def _get_user_by_email(email):
    if not email:
        raise BadRequest('Email missing')
    try:
        user = AstakosUser.objects.get(email = email)
    except AstakosUser.DoesNotExist, e:
        raise ItemNotFound('Invalid email')
    
    if not user.is_active:
        raise ItemNotFound('Inactive user')
    else:
        response = HttpResponse()
        response.status=200
        user_info = {'id':user.id,
                     'username':user.username,
                     'email':[user.email],
                     'enabled':user.is_active,
                     'name':user.realname,
                     'auth_token_created':user.auth_token_created.strftime(format),
                     'auth_token_expires':user.auth_token_expires.strftime(format),
                     'has_credits':user.has_credits,
                     'groups':[g.name for g in user.groups.all()],
                     'user_permissions':[p.codename for p in user.user_permissions.all()]}
        response.content = json.dumps(user_info)
        response['Content-Type'] = 'application/json; charset=UTF-8'
        response['Content-Length'] = len(response.content)
        return response