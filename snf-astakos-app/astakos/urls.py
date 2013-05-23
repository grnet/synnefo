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
from synnefo.lib import join_urls
from astakos.im.settings import (
    BASE_PATH, ACCOUNTS_PREFIX, VIEWS_PREFIX, KEYSTONE_PREFIX
)
from snf_django.lib.api.utils import prefix_pattern

astakos_patterns = patterns(
    '',
    (prefix_pattern(VIEWS_PREFIX), include('astakos.im.urls')),
    (prefix_pattern(ACCOUNTS_PREFIX), include('astakos.api.urls')),
    #(prefix_pattern(KEYSTONE_PREFIX), include('astakos.api.keystone_urls')),
)

# Compatibility: expose some API URLs at top-level
compatibility_patterns = patterns(
    'astakos',
    (r'^login/?$', 'im.views.target.redirect.login'),
    (r'^feedback/?$', 'api.user.send_feedback'),
    (r'^user_catalogs/?$', 'api.user.get_uuid_displayname_catalogs'),
    (r'^service/api/user_catalogs/?$',
        'api.service.get_uuid_displayname_catalogs'),
)

astakos_patterns += compatibility_patterns

urlpatterns = patterns(
    '',
    (prefix_pattern(BASE_PATH), include(astakos_patterns)),
)
