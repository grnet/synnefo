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

from functools import partial
try:
    from django.conf.urls import include, patterns
except ImportError:  # Django==1.2
    from django.conf.urls.defaults import include, patterns

from snf_django.lib.api.proxy import proxy
from snf_django.lib.api.utils import prefix_pattern
from snf_django.lib.api.urls import api_patterns
from snf_django.lib.api import api_endpoint_not_found
from snf_django.utils.urls import extend_endpoint_with_slash
from pithos.api.settings import (
    pithos_services,
    BASE_PATH, ASTAKOS_BASE_URL, BASE_ASTAKOS_PROXY_PATH,
    ASTAKOS_ACCOUNTS_PREFIX, PROXY_USER_SERVICES,
    PITHOS_PREFIX, PUBLIC_PREFIX, UI_PREFIX)


urlpatterns = []

# Redirects should be first, otherwise they may get overridden by wildcards
extend_endpoint_with_slash(urlpatterns, pithos_services, "pithos_ui")
extend_endpoint_with_slash(urlpatterns, pithos_services, "pithos_public")

# TODO: This only works when in this order.
pithos_api_patterns = api_patterns(
    'pithos.api.functions',
    (r'^$', 'top_demux'),
    (r'^(?P<v_account>.+?)/(?P<v_container>.+?)/(?P<v_object>.+?)$',
    'object_demux'),
    (r'^(?P<v_account>.+?)/(?P<v_container>.+?)/?$',
    'container_demux'),
    (r'^(?P<v_account>.+?)/?$', 'account_demux'))

pithos_view_patterns = patterns(
    'pithos.api.views',
    (r'^view/(?P<v_account>.+?)/(?P<v_container>.+?)/(?P<v_object>.+?)$',
    'object_read'))

pithos_patterns = patterns(
    '',
    (r'{0}v1/'.format(prefix_pattern(PITHOS_PREFIX)),
        include(pithos_api_patterns)),
    (r'{0}.*'.format(prefix_pattern(PITHOS_PREFIX)),
        api_endpoint_not_found),
    (r'{0}(?P<v_public>.+?)/?$'.format(prefix_pattern(PUBLIC_PREFIX)),
        'pithos.api.public.public_demux'),
    (r'{0}'.format(prefix_pattern(UI_PREFIX)),
        include(pithos_view_patterns)))

urlpatterns += patterns(
    '',
    (prefix_pattern(BASE_PATH), include(pithos_patterns)),
)

if PROXY_USER_SERVICES:
    astakos_proxy = partial(proxy, proxy_base=BASE_ASTAKOS_PROXY_PATH,
                            target_base=ASTAKOS_BASE_URL)

    proxy_patterns = api_patterns(
        '',
        (r'^login/?$', astakos_proxy),
        (r'^feedback/?$', astakos_proxy),
        (r'^user_catalogs/?$', astakos_proxy),
        (prefix_pattern(ASTAKOS_ACCOUNTS_PREFIX), astakos_proxy),
    )

    urlpatterns += patterns(
        '',
        (prefix_pattern(BASE_ASTAKOS_PROXY_PATH), include(proxy_patterns)),
    )
