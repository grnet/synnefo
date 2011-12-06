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

import os

from django.conf.urls.defaults import patterns


urlpatterns = patterns('synnefo.admin.views',
    (r'^/?$', 'index'),
    (r'^/flavors/?$', 'flavors_list'),
    (r'^/flavors/create/?$', 'flavors_create'),
    (r'^/flavors/(\d+)/?$', 'flavors_info'),
    (r'^/flavors/(\d+)/modify/?$', 'flavors_modify'),
    (r'^/flavors/(\d+)/delete/?$', 'flavors_delete'),
    
    (r'^/images/?$', 'images_list'),
    (r'^/images/register/?$', 'images_register'),
    (r'^/images/(\d+)/?$', 'images_info'),
    (r'^/images/(\d+)/modify/?$', 'images_modify'),

    (r'^/servers/?$', 'servers_list'),

    (r'^/users/?$', 'users_list'),
    (r'^/users/invite/?$', 'users_invite'),
    (r'^/users/(\d+)/?$', 'users_info'),
    (r'^/users/(\d+)/modify/?$', 'users_modify'),
    (r'^/users/(\d+)/delete/?$', 'users_delete'),

    (r'^/invitations/?$', 'invitations_list'),
    (r'^/invitations/(\d+)/resend/?$', 'invitations_resend'),
)

urlpatterns += patterns('synnefo.admin.api',
    (r'^/api/servers/(\d+)$', 'servers_info'),
    (r'^/api/users/(\d+)$', 'users_info'),
)

urlpatterns += patterns('',
    (r'^/static/(?P<path>.*)$', 'django.views.static.serve', {
        'document_root': os.path.join(os.path.dirname(__file__), 'static')})
)