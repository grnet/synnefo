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
from snf_django.lib.api.proxy import proxy
from snf_django.lib.api.utils import prefix_pattern
from snf_django.utils.urls import extend_with_root_redirects
from snf_django.lib.api.urls import api_patterns
from synnefo.cyclades_settings import (
    BASE_URL, BASE_HOST, BASE_PATH, COMPUTE_PREFIX, VMAPI_PREFIX,
    PLANKTON_PREFIX, HELPDESK_PREFIX, UI_PREFIX, ASTAKOS_BASE_URL,
    USERDATA_PREFIX, ADMIN_PREFIX, ASTAKOS_BASE_PATH, BASE_ASTAKOS_PROXY_PATH,
    ASTAKOS_ACCOUNTS_PREFIX, ASTAKOS_VIEWS_PREFIX, PROXY_USER_SERVICES,
    cyclades_services)

from functools import partial


astakos_proxy = partial(proxy, proxy_base=BASE_ASTAKOS_PROXY_PATH,
                        target_base=ASTAKOS_BASE_URL)

cyclades_patterns = api_patterns(
    '',
    (prefix_pattern(VMAPI_PREFIX), include('synnefo.vmapi.urls')),
    (prefix_pattern(PLANKTON_PREFIX), include('synnefo.plankton.urls')),
    (prefix_pattern(COMPUTE_PREFIX), include('synnefo.api.urls')),
    (prefix_pattern(USERDATA_PREFIX), include('synnefo.userdata.urls')),
    (prefix_pattern(ADMIN_PREFIX), include('synnefo.admin.urls')),
)

cyclades_patterns += patterns(
    '',
    (prefix_pattern(UI_PREFIX), include('synnefo.ui.urls')),
    (prefix_pattern(HELPDESK_PREFIX), include('synnefo.helpdesk.urls')),
)

urlpatterns = patterns(
    '',
    (prefix_pattern(BASE_PATH), include(cyclades_patterns)),
)

if PROXY_USER_SERVICES:
    astakos_proxy = partial(proxy, proxy_base=BASE_ASTAKOS_PROXY_PATH,
                            target_base=ASTAKOS_BASE_URL)

    proxy_patterns = patterns(
        '',
        (prefix_pattern(ASTAKOS_VIEWS_PREFIX), astakos_proxy),
    )
    proxy_patterns += api_patterns(
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

# set utility redirects
extend_with_root_redirects(urlpatterns, cyclades_services, 'cyclades_ui',
                           BASE_PATH)
