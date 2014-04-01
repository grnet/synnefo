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

from django.conf.urls import patterns, url
from snf_django.lib.api import api_endpoint_not_found
from snf_django.lib.api.urls import api_patterns
from astakos.im import settings

urlpatterns = patterns('')

if settings.ADMIN_API_ENABLED:
    urlpatterns += api_patterns(
        'astakos.api.user',
        (r'^v2.0/users(?:/|.json|.xml)?$', 'users_demux'),
        (r'^v2.0/users/detail(?:.json|.xml)?$', 'users_list', {'detail': True}),
        (r'^v2.0/users/([-\w]+)(?:/|.json|.xml)?$', 'user_demux'),
        (r'^v2.0/users/([-\w]+)/action(?:/|.json|.xml)?$', 'user_action')
    )

urlpatterns += patterns(
    'astakos.api.tokens',
    url(r'^v2.0/tokens/(?P<token_id>.+?)/?$', 'validate_token',
        name='validate_token'),
    url(r'^v2.0/tokens/?$', 'authenticate', name='tokens_authenticate'),
    url(r'^.*', api_endpoint_not_found),
)
