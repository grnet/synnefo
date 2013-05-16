# Copyright 2013 GRNET S.A. All rights reserved.
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

# Decorator for API methods, using common utils.api_method decorator.
# It is used for 'get_services' and 'get_menu' methods that do not
# require any sort of authentication

from functools import partial

from django.http import HttpResponse
from django.utils import simplejson as json
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.contrib import messages
from django.contrib.auth.models import User

from snf_django.lib import api
from astakos.im.models import Service
from astakos.im.settings import (INVITATIONS_ENABLED, QUOTAHOLDER_URL,
                                 PROJECTS_VISIBLE)

import logging
logger = logging.getLogger(__name__)

absolute = lambda request, url: request.build_absolute_uri(url)

api_method = partial(api.api_method, user_required=False,
                     token_required=False, logger=logger)


@api_method(http_method=None)
def get_services(request):
    callback = request.GET.get('callback', None)
    mimetype = 'application/json'
    data = json.dumps(Service.catalog().values())

    if callback:
        # Consume session messages. When get_services is loaded from an astakos
        # page, messages should have already been consumed in the html
        # response. When get_services is loaded from another domain/service we
        # consume them here so that no stale messages to appear if user visits
        # an astakos view later on.
        # TODO: messages could be served to other services/sites in the dict
        # response of get_services and/or get_menu. Services could handle those
        # messages respectively.
        messages_list = list(messages.get_messages(request))
        mimetype = 'application/javascript'
        data = '%s(%s)' % (callback, data)

    return HttpResponse(content=data, mimetype=mimetype)


@api_method()
def get_menu(request, with_extra_links=False, with_signout=True):
    user = request.user
    index_url = reverse('index')

    if isinstance(user, User) and user.is_authenticated():
        l = []
        append = l.append
        item = MenuItem
        item.current_path = absolute(request, request.path)
        append(item(url=absolute(request, reverse('index')),
                    name=user.email))
        if with_extra_links:
            append(item(url=absolute(request, reverse('landing')),
                        name="Overview"))
        if with_signout:
            append(item(url=absolute(request, reverse('landing')),
                        name="Dashboard"))
        if with_extra_links:
            append(item(url=absolute(request, reverse('edit_profile')),
                        name="Profile"))

        if with_extra_links:
            if INVITATIONS_ENABLED:
                append(item(url=absolute(request, reverse('invite')),
                            name="Invitations"))

            append(item(url=absolute(request, reverse('resource_usage')),
                        name="Usage"))

            if QUOTAHOLDER_URL and PROJECTS_VISIBLE:
                append(item(url=absolute(request, reverse('project_list')),
                            name="Projects"))
            #append(item(
                #url=absolute(request, reverse('api_access')),
                #name="API Access"))

            append(item(url=absolute(request, reverse('feedback')),
                        name="Contact"))
        if with_signout:
            append(item(url=absolute(request, reverse('logout')),
                        name="Sign out"))
    else:
        l = [{'url': absolute(request, index_url),
              'name': _("Sign in")}]

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
        if self.current_path.startswith(self.get('url')):
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
