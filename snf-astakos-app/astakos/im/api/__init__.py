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
from astakos.im.api.faults import Fault, ItemNotFound, InternalServerError, BadRequest
from astakos.im.settings import INVITATIONS_ENABLED, COOKIE_NAME, EMAILCHANGE_ENABLED

import logging
logger = logging.getLogger(__name__)

format = ('%a, %d %b %Y %H:%M:%S GMT')

absolute = lambda request, url: request.build_absolute_uri(url)

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
    except AstakosUser.DoesNotExist:
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
    except AstakosUser.DoesNotExist:
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
    user = request.user
    if not isinstance(user, AstakosUser):
        cookie = unquote(request.COOKIES.get(COOKIE_NAME, ''))
        email = cookie.partition('|')[0]
        try:
            if email:
                user = AstakosUser.objects.get(email=email, is_active=True)
        except AstakosUser.DoesNotExist:
            pass
    if not isinstance(user, AstakosUser):
        index_url = reverse('index')
        l = [{ 'url': absolute(request, index_url), 'name': "Sign in"}]
    else:
        l = []
        append = l.append
        item = MenuItem
        item.current_path = absolute(request, request.path)
        append(
            item(
                url=absolute(request, reverse('index')),
                name=user.email
            )
        )
        append(
            item(
                url=absolute(request, reverse('edit_profile')),
                name="My account"
            )
        )
        if with_extra_links:
            if user.has_usable_password() and user.provider in ('local', ''):
                append(
                    item(
                        url=absolute(request, reverse('password_change')),
                        name="Change password"
                    )
                )
            if EMAILCHANGE_ENABLED:
                append(
                    item(
                        url=absolute(request, reverse('email_change')),
                        name="Change email"
                    )
                )
            if INVITATIONS_ENABLED:
                append(
                    item(
                        url=absolute(request, reverse('invite')),
                        name="Invitations"
                    )
                )
            append(
                item(
                    url=absolute(request, reverse('feedback')),
                    name="Feedback"
                )
            )
            append(
                item(
                    url=absolute(request, reverse('group_list')),
                    name="Groups",
                    submenu=(
                        item(
                            url=absolute(request, reverse('group_list')),
                            name="Overview"
                        ),
                        item(
                            url=absolute(request,
                                reverse('group_create_list')
                            ),
                            name="Create"
                        ),
                        item(
                            url=absolute(request, reverse('group_search')),
                            name="Join"
                        ),
                    )
                )
            )
            append(
                item(
                    url=absolute(request, reverse('resource_list')),
                    name="Resources"
                )
            )
            append(
                item(
                    url=absolute(request, reverse('billing')),
                    name="Billing"
                )
            )
        if with_signout:
            append(
                item(
                    url=absolute(request, reverse('logout')),
                    name="Sign out"
                )
            )
    
    callback = request.GET.get('callback', None)
    data = json.dumps(tuple(l))
    mimetype = 'application/json'

    if callback:
        mimetype = 'application/javascript'
        data = '%s(%s)' % (callback, data)

    return HttpResponse(content=data, mimetype=mimetype)

class MenuItem(dict):
    current_path = ''
    
    def __init__(self, *args, **kwargs):
        super(MenuItem, self).__init__(*args, **kwargs)
        if kwargs.get('url') or kwargs.get('submenu'):
            self.__set_is_active__()
    
    def __setitem__(self, key, value):
        super(MenuItem, self).__setitem__(key, value)
        if key in ('url', 'submenu'):
            self.__set_is_active__()
    
    def __set_is_active__(self):
        if self.get('is_active'):
            return
        if self.current_path == self.get('url'):
            self.__setitem__('is_active', True)
        else:
            submenu = self.get('submenu', ())
            current = (i for i in submenu if i.get('url') == self.current_path)
            try:
                current_node = current.next()
                if not current_node.get('is_active'):
                    current_node.__setitem__('is_active', True)
                self.__setitem__('is_active', True)
            except StopIteration:
                return
        
    def __setattribute__(self, name, value):
        super(MenuItem, self).__setattribute__(name, value)
        if name == 'current_path':
            self.__set_is_active__()