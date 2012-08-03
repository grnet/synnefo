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

from functools import wraps
from traceback import format_exc
from urllib import quote, unquote

from django.http import HttpResponse
from django.utils import simplejson as json
from django.conf import settings
from django.core.urlresolvers import reverse

from astakos.im.models import AstakosUser, GroupKind, Service, Resource
from astakos.im.api.faults import Fault, ItemNotFound, InternalServerError
from astakos.im.settings import INVITATIONS_ENABLED, COOKIE_NAME, EMAILCHANGE_ENABLED

import logging
logger = logging.getLogger(__name__)

format = ('%a, %d %b %Y %H:%M:%S GMT')

def render_fault(request, fault):
    if isinstance(fault, InternalServerError) and settings.DEBUG:
        fault.details = format_exc(fault)

    request.serialization = 'text'
    data = fault.message + '\n'
    if fault.details:
        data += '\n' + fault.details
    response = HttpResponse(data, status=fault.code)
    response['Content-Length'] = len(response.content)
    return response

def api_method(http_method=None):
    """Decorator function for views that implement an API method."""
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            try:
                if http_method and request.method != http_method:
                    raise BadRequest('Method not allowed.')
                response = func(request, *args, **kwargs)
                return response
            except Fault, fault:
                return render_fault(request, fault)
            except BaseException, e:
                logger.exception('Unexpected error: %s' % e)
                fault = InternalServerError('Unexpected error')
                return render_fault(request, fault)
        return wrapper
    return decorator

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

@api_method(http_method='GET')
def get_services(request):
    callback = request.GET.get('callback', None)
    services = Service.objects.all()
    data = tuple({'id':s.pk, 'name':s.name, 'url':s.url, 'icon':s.icon} for s in services)
    data = json.dumps(data)
    mimetype = 'application/json'

    if callback:
        mimetype = 'application/javascript'
        data = '%s(%s)' % (callback, data)

    return HttpResponse(content=data, mimetype=mimetype)

@api_method()
def get_menu(request, with_extra_links=False, with_signout=True):
    index_url = reverse('index')
    absolute = lambda (url): request.build_absolute_uri(url)
    l = [{ 'url': absolute(index_url), 'name': "Sign in"}]
    cookie = unquote(request.COOKIES.get(COOKIE_NAME, ''))
    email = cookie.partition('|')[0]
    try:
        if not email:
            raise ValueError
        user = AstakosUser.objects.get(email=email, is_active=True)
    except AstakosUser.DoesNotExist:
        pass
    except ValueError:
        pass
    else:
        l = []
        l.append(dict(url=absolute(reverse('index')), name=user.email))
        l.append(dict(url=absolute(reverse('edit_profile')), name="My account"))
        if with_extra_links:
            if user.has_usable_password() and user.provider == 'local':
                l.append(dict(url=absolute(reverse('password_change')), name="Change password"))
            if EMAILCHANGE_ENABLED:
                l.append(dict(url=absolute(reverse('email_change')), name="Change email"))
            if INVITATIONS_ENABLED:
                l.append(dict(url=absolute(reverse('invite')), name="Invitations"))
            l.append(dict(url=absolute(reverse('feedback')), name="Feedback"))
            if request.user.has_perm('im.add_astakosgroup'):
                l.append(dict(url=absolute(reverse('group_add')), name="Add group"))
            url = absolute(reverse('group_list'))
            l.append(dict(url=url, name="Subscribed groups"))
            url = '%s?relation=owner' % url
            l.append(dict(url=url, name="My groups"))
        if with_signout:
            l.append(dict(url=absolute(reverse('logout')), name="Sign out"))

    callback = request.GET.get('callback', None)
    data = json.dumps(tuple(l))
    mimetype = 'application/json'

    if callback:
        mimetype = 'application/javascript'
        data = '%s(%s)' % (callback, data)

    return HttpResponse(content=data, mimetype=mimetype)