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

from django.conf.urls import patterns, url, include

from snf_django.lib.api import api_endpoint_not_found


astakos_account_v1_0 = patterns(
    'astakos.api.quotas',
    url(r'^quotas/?$', 'quotas', name="astakos-api-quotas"),
    url(r'^service_quotas/?$', 'service_quotas'),
    url(r'^service_project_quotas/?$', 'service_project_quotas'),
    url(r'^resources/?$', 'resources'),
    url(r'^commissions/?$', 'commissions'),
    url(r'^commissions/action/?$', 'resolve_pending_commissions'),
    url(r'^commissions/(?P<serial>\d+)/?$', 'get_commission'),
    url(r'^commissions/(?P<serial>\d+)/action/?$', 'serial_action'),
)

astakos_account_v1_0 += patterns(
    'astakos.api.user',
    url(r'^feedback/?$', 'send_feedback'),
    url(r'^user_catalogs/?$', 'get_uuid_displayname_catalogs'),
)

astakos_account_v1_0 += patterns(
    'astakos.api.service',
    url(r'^service/user_catalogs/?$', 'get_uuid_displayname_catalogs'),
)

astakos_account_v1_0 += patterns(
    'astakos.api.projects',
    url(r'^projects/?$', 'projects', name='api_projects'),
    url(r'^projects/memberships/?$', 'memberships', name='api_memberships'),
    url(r'^projects/memberships/(?P<memb_id>\d+)/?$', 'membership',
        name='api_membership'),
    url(r'^projects/memberships/(?P<memb_id>\d+)/action/?$',
        'membership_action', name='api_membership_action'),
    url(r'^projects/(?P<project_id>[^/]+)/?$', 'project', name='api_project'),
    url(r'^projects/(?P<project_id>[^/]+)/action/?$', 'project_action',
        name='api_project_action'),
)

urlpatterns = patterns(
    '',
    url(r'^v1.0/', include(astakos_account_v1_0)),
    (r'^.*', api_endpoint_not_found),
)
