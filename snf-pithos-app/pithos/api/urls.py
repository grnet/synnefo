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

from django.conf.urls.defaults import include, patterns

import pithos.api.settings as settings

# TODO: This only works when in this order.
api_urlpatterns = patterns(
    'pithos.api.functions',
    (r'^$', 'top_demux'),
    (r'^(?P<v_account>.+?)/(?P<v_container>.+?)/(?P<v_object>.+?)$',
    'object_demux'),
    (r'^(?P<v_account>.+?)/(?P<v_container>.+?)/?$',
    'container_demux'),
    (r'^(?P<v_account>.+?)/?$', 'account_demux'))

urlpatterns = patterns(
    '',
    (r'^v1(?:$|/)', include(api_urlpatterns)),
    (r'^v1\.0(?:$|/)', include(api_urlpatterns)),
    (r'^public/(?P<v_public>.+?)/?$', 'pithos.api.public.public_demux'),
    (r'^login/?$', 'pithos.api.delegate.delegate_to_login_service'))

if settings.PROXY_USER_SERVICES:
    urlpatterns += patterns(
        '',
        (r'^feedback/?$', 'pithos.api.delegate.delegate_to_feedback_service'),
        (r'^user_catalog/?$', 'pithos.api.delegate.delegate_to_user_catalogs_service'))
