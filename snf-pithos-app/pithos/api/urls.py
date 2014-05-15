# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from functools import partial
from django.conf.urls import include, patterns

from snf_django.lib.api.proxy import proxy
from snf_django.lib.api.utils import prefix_pattern
from snf_django.lib.api.urls import api_patterns
from snf_django.lib.api import api_endpoint_not_found
from snf_django.utils.urls import extend_endpoint_with_slash
from pithos.api.settings import (
    BASE_PATH, PITHOS_PREFIX, PUBLIC_PREFIX, VIEW_PREFIX,
    ASTAKOS_AUTH_PROXY_PATH, ASTAKOS_AUTH_URL,
    ASTAKOS_ACCOUNT_PROXY_PATH, ASTAKOS_ACCOUNT_URL,
    ASTAKOS_UI_PROXY_PATH, ASTAKOS_UI_URL, pithos_services)


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
    (r'^(?P<v_account>.+?)/(?P<v_container>.+?)/(?P<v_object>.+?)$',
     'object_read'))

pithos_patterns = []
pithos_patterns += patterns(
    '',
    (r'{0}v1/'.format(prefix_pattern(PITHOS_PREFIX)),
        include(pithos_api_patterns)),
    (r'{0}.*'.format(prefix_pattern(PITHOS_PREFIX)),
        api_endpoint_not_found),
    (r'{0}(?P<v_public>.+?)/?$'.format(prefix_pattern(PUBLIC_PREFIX)),
        'pithos.api.public.public_demux'),
)

pithos_patterns += patterns(
    '',
    (r'{0}'.format(prefix_pattern(VIEW_PREFIX)),
        include(pithos_view_patterns)))

urlpatterns += patterns(
    '',
    (prefix_pattern(BASE_PATH), include(pithos_patterns)),
)


# --------------------------------------
# PROXY settings
astakos_auth_proxy = \
    partial(proxy, proxy_base=ASTAKOS_AUTH_PROXY_PATH,
            target_base=ASTAKOS_AUTH_URL)
astakos_account_proxy = \
    partial(proxy, proxy_base=ASTAKOS_ACCOUNT_PROXY_PATH,
            target_base=ASTAKOS_ACCOUNT_URL)

# ui views serve html content, redirect instead of proxing
astakos_ui_proxy = \
    partial(proxy, proxy_base=ASTAKOS_UI_PROXY_PATH,
            target_base=ASTAKOS_UI_URL, redirect=True)

urlpatterns += api_patterns(
    '',
    (prefix_pattern(ASTAKOS_AUTH_PROXY_PATH), astakos_auth_proxy),
    (prefix_pattern(ASTAKOS_ACCOUNT_PROXY_PATH), astakos_account_proxy),
)
urlpatterns += patterns(
    '',
    (prefix_pattern(ASTAKOS_UI_PROXY_PATH), astakos_ui_proxy),
)
