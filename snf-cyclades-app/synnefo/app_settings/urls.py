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

from django.conf.urls.defaults import *
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from snf_django.lib.api.proxy import proxy

from functools import partial

astakos_proxy = partial(proxy, target=settings.ASTAKOS_URL)

urlpatterns = patterns('',
    (r'^ui/', include('synnefo.ui.urls')),
    url(r'^machines/console$', 'synnefo.ui.views.machines_console',
        name='ui_machines_console'),
    url(r'^machines/connect$', 'synnefo.ui.views.machines_connect',
        name='ui_machines_connect'),
    (r'^vmapi/', include('synnefo.vmapi.urls')),
    (r'^api/', include('synnefo.api.urls')),
    (r'^plankton/', include('synnefo.plankton.urls')),
    (r'^helpdesk/', include('synnefo.helpdesk.urls')),
)

PROXY_USER_SERVICES = getattr(settings, 'CYCLADES_PROXY_USER_SERVICES', True)
if PROXY_USER_SERVICES:
    urlpatterns += patterns(
        '',
        (r'^login/?$', csrf_exempt(astakos_proxy)),
        (r'^feedback/?$', csrf_exempt(astakos_proxy)),
        (r'^user_catalogs/?$', csrf_exempt(astakos_proxy)),
        (r'^astakos/api/', csrf_exempt(astakos_proxy)),
    )
